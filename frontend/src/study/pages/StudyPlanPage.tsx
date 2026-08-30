import { useCallback, useEffect, useRef, useState } from "react";
import {
  AlertMessage,
  Badge,
  DisclosurePanel,
  EmptyState,
  LoadingState,
  PageHeader,
  PublicId,
  StatusMessage,
} from "../../components/Primitives";
import { formatBytes, formatCount, formatDate } from "../../utils";
import { asStudyApiError, StudyApiError, studyApi } from "../api";
import { prepareCancel, prepareRevalidate } from "../commands";
import {
  compareTimestamps,
  isLedgerTransition,
  isSafePlanProgression,
  overlappingEventsKeepIdentity,
} from "../decoders";
import type { StudyContextState } from "../hooks";
import { matchesCreateDraft, type SetStudyCommandMemory, type StudyCommandMemory } from "../commandMemory";
import {
  dispositionLabels,
  eventTypeLabels,
  exclusionReasonLabels,
  memberCurrentLabels,
  memberFilterLabels,
  memberInitialLabels,
  planStateLabels,
  readStateLabels,
  storageEffectLabels,
  warningLabels,
} from "../presenters";
import type {
  CancelReceipt,
  MemberFilter,
  PlanDetail,
  PlanEvent,
  PlanMember,
  PlanSample,
  PreparedCommand,
  RevalidateReceipt,
  TemporalFilter,
} from "../types";

type Props = {
  planId: string;
  contexts: StudyContextState;
  refreshContexts: () => Promise<StudyContextState>;
  commandMemory: StudyCommandMemory | null;
  setCommandMemory: SetStudyCommandMemory;
  planSnapshots: Map<string, PlanDetail>;
};

type CollectionFocusIntent = { kind: "page" | "restart"; token: number } | null;

type DetailState = {
  loading: boolean;
  data: PlanDetail | null;
  error: StudyApiError | null;
};

type MemberState = {
  loaded: boolean;
  loading: boolean;
  items: PlanMember[];
  nextCursor: string | null;
  planRevision: number | null;
  error: StudyApiError | null;
  needsRestart: boolean;
  needsDetailRefresh: boolean;
};

type EventState = {
  loaded: boolean;
  loading: boolean;
  items: PlanEvent[];
  nextCursor: string | null;
  planRevision: number | null;
  error: StudyApiError | null;
  needsRestart: boolean;
  needsDetailRefresh: boolean;
};

type PendingCommand =
  | {
      kind: "revalidate";
      expectedPlanRevision: number;
      expectedMapRevision: string;
      expectedPolicyRevision: number;
      command: PreparedCommand<RevalidateReceipt>;
    }
  | { kind: "cancel"; expectedPlanRevision: number; command: PreparedCommand<CancelReceipt> };

const EMPTY_MEMBERS: MemberState = {
  loaded: false,
  loading: false,
  items: [],
  nextCursor: null,
  planRevision: null,
  error: null,
  needsRestart: false,
  needsDetailRefresh: false,
};

const EMPTY_EVENTS: EventState = {
  loaded: false,
  loading: false,
  items: [],
  nextCursor: null,
  planRevision: null,
  error: null,
  needsRestart: false,
  needsDetailRefresh: false,
};

function membersNeedRestart(): MemberState {
  return {
    ...EMPTY_MEMBERS,
    loaded: true,
    error: new StudyApiError("cursor_stale", 409),
    needsRestart: true,
  };
}

function eventsNeedRestart(): EventState {
  return {
    ...EMPTY_EVENTS,
    loaded: true,
    error: new StudyApiError("cursor_stale", 409),
    needsRestart: true,
  };
}

type MemberAggregate = {
  count: number;
  sizeEstimateBytes: number;
};

type MemberPartitions = {
  total: MemberAggregate;
  selected: MemberAggregate;
  eligible: MemberAggregate;
  excluded: MemberAggregate;
  removed: MemberAggregate;
};

function safeAggregateSum(left: number, right: number): number | null {
  if (!Number.isSafeInteger(left) || !Number.isSafeInteger(right) || left < 0 || right < 0) return null;
  if (left > Number.MAX_SAFE_INTEGER - right) return null;
  return left + right;
}

function safeAggregateDifference(left: number, right: number): number | null {
  if (!Number.isSafeInteger(left) || !Number.isSafeInteger(right) || left < 0 || right < 0 || right > left) {
    return null;
  }
  return left - right;
}

function expectedMemberAggregate(plan: PlanDetail, filter: MemberFilter): MemberAggregate | null {
  if (filter === "selected") {
    return {
      count: plan.selectedAtCreationCount,
      sizeEstimateBytes: plan.selectedAtCreationSizeEstimateBytes,
    };
  }
  if (filter === "eligible") {
    return {
      count: plan.currentEligibleCount,
      sizeEstimateBytes: plan.currentEligibleSizeEstimateBytes,
    };
  }
  if (filter === "excluded") {
    return {
      count: plan.excludedAtCreationCount,
      sizeEstimateBytes: plan.excludedAtCreationSizeEstimateBytes,
    };
  }
  if (filter === "removed") {
    const count = safeAggregateDifference(plan.selectedAtCreationCount, plan.currentEligibleCount);
    const sizeEstimateBytes = safeAggregateDifference(
      plan.selectedAtCreationSizeEstimateBytes,
      plan.currentEligibleSizeEstimateBytes,
    );
    return count === null || sizeEstimateBytes === null ? null : { count, sizeEstimateBytes };
  }
  const count = safeAggregateSum(plan.selectedAtCreationCount, plan.excludedAtCreationCount);
  const sizeEstimateBytes = safeAggregateSum(
    plan.selectedAtCreationSizeEstimateBytes,
    plan.excludedAtCreationSizeEstimateBytes,
  );
  return count === null || sizeEstimateBytes === null ? null : { count, sizeEstimateBytes };
}

function addMemberToAggregate(aggregate: MemberAggregate, member: PlanMember): MemberAggregate | null {
  const count = safeAggregateSum(aggregate.count, 1);
  const sizeEstimateBytes = safeAggregateSum(aggregate.sizeEstimateBytes, member.sizeEstimateBytes);
  return count === null || sizeEstimateBytes === null ? null : { count, sizeEstimateBytes };
}

function observedMemberPartitions(items: readonly PlanMember[]): MemberPartitions | null {
  let partitions: MemberPartitions = {
    total: { count: 0, sizeEstimateBytes: 0 },
    selected: { count: 0, sizeEstimateBytes: 0 },
    eligible: { count: 0, sizeEstimateBytes: 0 },
    excluded: { count: 0, sizeEstimateBytes: 0 },
    removed: { count: 0, sizeEstimateBytes: 0 },
  };
  for (const item of items) {
    const total = addMemberToAggregate(partitions.total, item);
    const initial = addMemberToAggregate(
      item.initialState === "selected" ? partitions.selected : partitions.excluded,
      item,
    );
    const current = item.currentState === "eligible"
      ? addMemberToAggregate(partitions.eligible, item)
      : item.currentState === "removed"
        ? addMemberToAggregate(partitions.removed, item)
        : partitions.excluded;
    if (total === null || initial === null || current === null) return null;
    partitions = {
      ...partitions,
      total,
      [item.initialState]: initial,
      ...(item.currentState === "eligible" || item.currentState === "removed"
        ? { [item.currentState]: current }
        : {}),
    };
  }
  return partitions;
}

function aggregateMatches(actual: MemberAggregate, expected: MemberAggregate, terminal: boolean): boolean {
  if (terminal) {
    return actual.count === expected.count && actual.sizeEstimateBytes === expected.sizeEstimateBytes;
  }
  return actual.count <= expected.count && actual.sizeEstimateBytes <= expected.sizeEstimateBytes;
}

function membersMatchDetail(
  items: readonly PlanMember[],
  plan: PlanDetail,
  filter: MemberFilter,
  terminal: boolean,
): boolean {
  const expected = expectedMemberAggregate(plan, filter);
  const observed = observedMemberPartitions(items);
  if (expected === null || observed === null || !aggregateMatches(observed.total, expected, terminal)) return false;
  if (!terminal && observed.total.count >= expected.count) return false;
  if (filter !== "all" && filter !== "selected") return true;

  const expectedSelected = expectedMemberAggregate(plan, "selected");
  const expectedEligible = expectedMemberAggregate(plan, "eligible");
  const expectedRemoved = expectedMemberAggregate(plan, "removed");
  if (expectedSelected === null || expectedEligible === null || expectedRemoved === null ||
    !aggregateMatches(observed.selected, expectedSelected, terminal) ||
    !aggregateMatches(observed.eligible, expectedEligible, terminal) ||
    !aggregateMatches(observed.removed, expectedRemoved, terminal)) return false;
  if (filter === "selected") return true;

  const expectedExcluded = expectedMemberAggregate(plan, "excluded");
  return expectedExcluded !== null && aggregateMatches(observed.excluded, expectedExcluded, terminal);
}

function temporalDescription(filter: TemporalFilter): string {
  if (filter.kind === "all") return "Todo el período disponible al crear";
  if (filter.kind === "beforeDate") return `Anterior al ${filter.date}; la fecha final es exclusiva`;
  if (filter.kind === "dateRange") return `Desde ${filter.onOrAfterDate} incluido hasta ${filter.beforeDate} excluido`;
  return `Más antiguos que ${formatCount(filter.days)} días civiles completos`;
}

function stateTone(state: PlanDetail["state"]): "positive" | "warning" | "critical" | "neutral" {
  if (state === "frozen") return "positive";
  if (state === "reduced") return "warning";
  if (state === "cancelled") return "neutral";
  return "critical";
}

function sampleTitle(sample: PlanSample): string {
  if (sample.subject) return sample.subject;
  if (sample.senderName) return `Mensaje de ${sample.senderName}`;
  return "Mensaje sintético sin asunto visible";
}

function membersRemainOrdered(items: readonly PlanMember[]): boolean {
  const ids = new Set(items.map((item) => item.messageId));
  return ids.size === items.length && items.every((item, index) => {
    if (index === 0) return true;
    const previous = items[index - 1]!;
    const timestampOrder = compareTimestamps(previous.receivedAt, item.receivedAt);
    return timestampOrder > 0 || (timestampOrder === 0 && previous.messageId < item.messageId);
  });
}

function eventsRemainOrdered(items: readonly PlanEvent[]): boolean {
  return new Set(items.map((item) => item.revision)).size === items.length &&
    items.every((item, index) => index === 0 || isLedgerTransition(items[index - 1]!, item));
}

function matchesRevalidationReceiptEvent(
  event: PlanEvent | undefined,
  removedCount: number,
  expectedMapRevision: string,
  expectedPolicyRevision: number,
): boolean {
  return event !== undefined && event.removedCount === removedCount &&
    event.observedMapRevision === expectedMapRevision &&
    event.observedPolicyRevision === expectedPolicyRevision &&
    (removedCount === 0
      ? event.type === "revalidated"
      : event.type === (event.remainingCount === 0 ? "invalidated" : "reduced"));
}

export function StudyPlanPage({
  planId,
  contexts,
  refreshContexts,
  commandMemory,
  setCommandMemory,
  planSnapshots,
}: Props) {
  const detailGeneration = useRef(0);
  const memberGeneration = useRef(0);
  const eventGeneration = useRef(0);
  const mountedRef = useRef(true);
  const detailRecoveryEpoch = useRef(0);
  const detailSnapshot = useRef<PlanDetail | null>(planSnapshots.get(planId) ?? null);
  const memberStatusRef = useRef<HTMLSpanElement>(null);
  const memberRestartRef = useRef<HTMLButtonElement>(null);
  const memberFocusIntent = useRef<CollectionFocusIntent>(null);
  const membersOpenRef = useRef(false);
  const memberPanelEpoch = useRef(0);
  const memberRecoveryEpoch = useRef(0);
  const eventStatusRef = useRef<HTMLSpanElement>(null);
  const eventRestartRef = useRef<HTMLButtonElement>(null);
  const eventFocusIntent = useRef<CollectionFocusIntent>(null);
  const eventsOpenRef = useRef(false);
  const eventPanelEpoch = useRef(0);
  const eventRecoveryEpoch = useRef(0);
  const collectionFocusToken = useRef(0);
  const [detail, setDetail] = useState<DetailState>({ loading: true, data: null, error: null });
  const [memberFilter, setMemberFilter] = useState<MemberFilter>("all");
  const [membersOpen, setMembersOpen] = useState(false);
  const [members, setMembers] = useState<MemberState>(EMPTY_MEMBERS);
  const [eventsOpen, setEventsOpen] = useState(false);
  const [events, setEvents] = useState<EventState>(EMPTY_EVENTS);
  const [pending, setPending] = useState(false);
  const [commandAlert, setCommandAlert] = useState<string | null>(null);
  const [commandStatus, setCommandStatus] = useState<string | null>(null);
  const [availabilityBlocked, setAvailabilityBlocked] = useState(false);
  const [requiresNewDecision, setRequiresNewDecision] = useState(false);
  const [commandsClosed, setCommandsClosed] = useState(false);
  const commandContractCompatible = !contexts.loading && contexts.compatible && contexts.context !== null;
  const matchingEntry = commandMemory?.status !== "unconfirmed" && commandMemory?.entry.kind !== "create" &&
    commandMemory?.entry.planId === planId ? commandMemory.entry : null;
  const uncertainMemory = commandMemory?.status === "uncertain" && matchingEntry ? commandMemory : null;
  const uncertain = uncertainMemory
    ? matchingEntry as PendingCommand
    : null;
  const conflictRecovery = commandMemory?.status === "recovery_required" && matchingEntry ? commandMemory : null;
  const unconfirmedCommand = commandMemory?.status === "unconfirmed" && commandMemory.planId === planId
    ? commandMemory
    : null;
  const busy = pending || commandMemory?.status === "pending";
  const foreignCommandMemory = commandMemory !== null && matchingEntry === null && unconfirmedCommand === null;

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      detailGeneration.current += 1;
      memberGeneration.current += 1;
      eventGeneration.current += 1;
      detailRecoveryEpoch.current += 1;
      memberRecoveryEpoch.current += 1;
      eventRecoveryEpoch.current += 1;
      collectionFocusToken.current += 1;
      membersOpenRef.current = false;
      eventsOpenRef.current = false;
      memberFocusIntent.current = null;
      eventFocusIntent.current = null;
    };
  }, []);

  const rememberDetail = useCallback((data: PlanDetail) => {
    const previous = detailSnapshot.current;
    const shared = planSnapshots.get(planId);
    if (!mountedRef.current ||
      (previous !== null && !isSafePlanProgression(previous, data)) ||
      (shared !== undefined && !isSafePlanProgression(shared, data))) {
      return false;
    }
    detailSnapshot.current = data;
    planSnapshots.set(planId, data);
    if (previous === null || previous.planRevision === data.planRevision) return true;

    memberGeneration.current += 1;
    eventGeneration.current += 1;
    memberFocusIntent.current = null;
    eventFocusIntent.current = null;
    setMembers((current) => current.loaded ? membersNeedRestart() : current);
    setEvents((current) => current.loaded ? eventsNeedRestart() : current);
    return true;
  }, [planId, planSnapshots]);

  useEffect(() => {
    const intent = memberFocusIntent.current;
    if (!membersOpenRef.current || members.loading || intent === null) return;
    memberFocusIntent.current = null;
    if (intent.token !== collectionFocusToken.current) return;
    if (members.error) memberRestartRef.current?.focus();
    else memberStatusRef.current?.focus();
  }, [members.error, members.loading, members.needsRestart, members.nextCursor]);

  useEffect(() => {
    const intent = eventFocusIntent.current;
    if (!eventsOpenRef.current || events.loading || intent === null) return;
    eventFocusIntent.current = null;
    if (intent.token !== collectionFocusToken.current) return;
    if (events.error) eventRestartRef.current?.focus();
    else eventStatusRef.current?.focus();
  }, [events.error, events.loading, events.needsRestart, events.nextCursor]);

  const loadDetail = useCallback(async () => {
    const generation = ++detailGeneration.current;
    setDetail((current) => ({ ...current, loading: true, error: null }));
    try {
      const data = await studyApi.plan(planId);
      if (generation !== detailGeneration.current) throw new StudyApiError("invalid_response", 200);
      if (!rememberDetail(data)) {
        throw new StudyApiError("invalid_response", 200);
      }
      setDetail({ loading: false, data, error: null });
      return data;
    } catch (reason) {
      const error = asStudyApiError(reason);
      if (generation === detailGeneration.current) {
        setDetail((current) => ({ ...current, loading: false, error }));
      }
      throw error;
    }
  }, [planId, rememberDetail]);

  useEffect(() => {
    let active = true;
    queueMicrotask(() => {
      if (!active) return;
      void loadDetail().catch(() => undefined);
    });
    return () => {
      active = false;
    };
  }, [loadDetail]);

  const loadMembers = useCallback(async (
    cursor?: string,
    expectedDetailRevision = detailSnapshot.current?.planRevision ?? null,
    focusAfterRestart = false,
    recoveryEpoch?: number,
    inheritedFocusToken?: number,
  ) => {
    if (!mountedRef.current) return;
    if (recoveryEpoch === undefined) memberRecoveryEpoch.current += 1;
    else if (recoveryEpoch !== memberRecoveryEpoch.current) return;
    const appending = cursor !== undefined;
    if (appending || focusAfterRestart) {
      const token = inheritedFocusToken ?? ++collectionFocusToken.current;
      if (inheritedFocusToken !== undefined && token !== collectionFocusToken.current) return;
      if (inheritedFocusToken === undefined) eventFocusIntent.current = null;
      memberFocusIntent.current = { kind: appending ? "page" : "restart", token };
    } else {
      memberFocusIntent.current = null;
    }
    const generation = ++memberGeneration.current;
    setMembers((current) => ({
      ...(appending ? current : EMPTY_MEMBERS),
      loaded: true,
      loading: true,
      error: null,
      needsRestart: false,
      needsDetailRefresh: false,
    }));
    try {
      const page = await studyApi.messages(planId, {
        state: memberFilter,
        ...(cursor ? { cursor } : {}),
        limit: 100,
      });
      if (!mountedRef.current || generation !== memberGeneration.current) return;
      if (expectedDetailRevision === null || page.planRevision !== expectedDetailRevision || page.state !== memberFilter) {
        setMembers({
          ...EMPTY_MEMBERS,
          loaded: true,
          error: new StudyApiError("invalid_response", 200),
          needsDetailRefresh: true,
        });
        return;
      }
      setMembers((current) => {
        if (appending && current.planRevision !== page.planRevision) {
          return {
            ...EMPTY_MEMBERS,
            loaded: true,
            error: new StudyApiError("invalid_response", 200),
            needsDetailRefresh: true,
          };
        }
        const items = appending ? [...current.items, ...page.items] : page.items;
        if (!membersRemainOrdered(items)) {
          return {
            ...EMPTY_MEMBERS,
            loaded: true,
            error: new StudyApiError("invalid_response", 200),
            needsRestart: appending,
          };
        }
        const currentDetail = detailSnapshot.current;
        if (
          currentDetail === null ||
          currentDetail.planRevision !== page.planRevision ||
          !membersMatchDetail(items, currentDetail, memberFilter, page.nextCursor === null)
        ) {
          return {
            ...EMPTY_MEMBERS,
            loaded: true,
            error: new StudyApiError("invalid_response", 200),
            needsRestart: appending,
          };
        }
        return {
          loaded: true,
          loading: false,
          items,
          nextCursor: page.nextCursor,
          planRevision: page.planRevision,
          error: null,
          needsRestart: false,
          needsDetailRefresh: false,
        };
      });
    } catch (reason) {
      if (generation !== memberGeneration.current) return;
      const error = asStudyApiError(reason);
      if (appending && (error.code === "cursor_stale" || error.code === "invalid_cursor")) {
        setMembers({ ...EMPTY_MEMBERS, loaded: true, error, needsRestart: true });
      } else {
        setMembers((current) => ({ ...current, loaded: true, loading: false, error }));
      }
    }
  }, [memberFilter, planId]);

  useEffect(() => {
    if (!membersOpen) return;
    let active = true;
    queueMicrotask(() => {
      if (active) void loadMembers();
    });
    return () => {
      active = false;
    };
  }, [loadMembers, membersOpen]);

  const loadEvents = useCallback(async (
    cursor?: string,
    expectedDetailRevision = detailSnapshot.current?.planRevision ?? null,
    focusAfterRestart = false,
    recoveryEpoch?: number,
    inheritedFocusToken?: number,
  ) => {
    if (!mountedRef.current) return;
    if (recoveryEpoch === undefined) eventRecoveryEpoch.current += 1;
    else if (recoveryEpoch !== eventRecoveryEpoch.current) return;
    const appending = cursor !== undefined;
    if (appending || focusAfterRestart) {
      const token = inheritedFocusToken ?? ++collectionFocusToken.current;
      if (inheritedFocusToken !== undefined && token !== collectionFocusToken.current) return;
      if (inheritedFocusToken === undefined) memberFocusIntent.current = null;
      eventFocusIntent.current = { kind: appending ? "page" : "restart", token };
    } else {
      eventFocusIntent.current = null;
    }
    const generation = ++eventGeneration.current;
    setEvents((current) => ({
      ...(appending ? current : EMPTY_EVENTS),
      loaded: true,
      loading: true,
      error: null,
      needsRestart: false,
      needsDetailRefresh: false,
    }));
    try {
      const page = await studyApi.events(planId, { ...(cursor ? { cursor } : {}), limit: 50 });
      if (!mountedRef.current || generation !== eventGeneration.current) return;
      if (expectedDetailRevision === null || page.planRevision !== expectedDetailRevision) {
        setEvents({
          ...EMPTY_EVENTS,
          loaded: true,
          error: new StudyApiError("invalid_response", 200),
          needsDetailRefresh: true,
        });
        return;
      }
      const currentDetail = detailSnapshot.current;
      if (currentDetail === null || currentDetail.planRevision !== page.planRevision ||
        !overlappingEventsKeepIdentity(currentDetail.recentEvents, page.items)) {
        setEvents({
          ...EMPTY_EVENTS,
          loaded: true,
          error: new StudyApiError("invalid_response", 200),
          needsDetailRefresh: true,
        });
        return;
      }
      setEvents((current) => {
        if (appending && current.planRevision !== page.planRevision) {
          return {
            ...EMPTY_EVENTS,
            loaded: true,
            error: new StudyApiError("invalid_response", 200),
            needsDetailRefresh: true,
          };
        }
        const items = appending ? [...current.items, ...page.items] : page.items;
        if (!eventsRemainOrdered(items)) {
          return { ...EMPTY_EVENTS, loaded: true, error: new StudyApiError("invalid_response", 200) };
        }
        return {
          loaded: true,
          loading: false,
          items,
          nextCursor: page.nextCursor,
          planRevision: page.planRevision,
          error: null,
          needsRestart: false,
          needsDetailRefresh: false,
        };
      });
    } catch (reason) {
      if (generation !== eventGeneration.current) return;
      const error = asStudyApiError(reason);
      if (appending && (error.code === "cursor_stale" || error.code === "invalid_cursor")) {
        setEvents({ ...EMPTY_EVENTS, loaded: true, error, needsRestart: true });
      } else {
        setEvents((current) => ({ ...current, loaded: true, loading: false, error }));
      }
    }
  }, [planId]);

  useEffect(() => {
    if (!eventsOpen) return;
    let active = true;
    queueMicrotask(() => {
      if (active) void loadEvents();
    });
    return () => {
      active = false;
    };
  }, [eventsOpen, loadEvents]);

  const refreshDetailAndMembers = async (focusAfterRestart = false) => {
    const panelEpoch = memberPanelEpoch.current;
    const recoveryEpoch = ++memberRecoveryEpoch.current;
    const sharedRecoveryEpoch = ++detailRecoveryEpoch.current;
    memberGeneration.current += 1;
    const focusToken = focusAfterRestart ? ++collectionFocusToken.current : undefined;
    if (focusAfterRestart) {
      eventFocusIntent.current = null;
      memberFocusIntent.current = { kind: "restart", token: focusToken! };
    }
    try {
      const confirmed = await loadDetail();
      if (sharedRecoveryEpoch !== detailRecoveryEpoch.current || recoveryEpoch !== memberRecoveryEpoch.current ||
        (focusAfterRestart && (!membersOpenRef.current || memberPanelEpoch.current !== panelEpoch))) return;
      await loadMembers(undefined, confirmed.planRevision, focusAfterRestart, recoveryEpoch, focusToken);
    } catch {
      // loadDetail/loadMembers ya exponen el cierre seguro y no reintentan solos.
      if (focusAfterRestart && memberPanelEpoch.current === panelEpoch &&
        sharedRecoveryEpoch === detailRecoveryEpoch.current && recoveryEpoch === memberRecoveryEpoch.current &&
        focusToken === collectionFocusToken.current) {
        memberFocusIntent.current = null;
        if (membersOpenRef.current) queueMicrotask(() => memberRestartRef.current?.focus());
      }
    }
  };

  const refreshDetailAndEvents = async (focusAfterRestart = false) => {
    const panelEpoch = eventPanelEpoch.current;
    const recoveryEpoch = ++eventRecoveryEpoch.current;
    const sharedRecoveryEpoch = ++detailRecoveryEpoch.current;
    eventGeneration.current += 1;
    const focusToken = focusAfterRestart ? ++collectionFocusToken.current : undefined;
    if (focusAfterRestart) {
      memberFocusIntent.current = null;
      eventFocusIntent.current = { kind: "restart", token: focusToken! };
    }
    try {
      const confirmed = await loadDetail();
      if (sharedRecoveryEpoch !== detailRecoveryEpoch.current || recoveryEpoch !== eventRecoveryEpoch.current ||
        (focusAfterRestart && (!eventsOpenRef.current || eventPanelEpoch.current !== panelEpoch))) return;
      await loadEvents(undefined, confirmed.planRevision, focusAfterRestart, recoveryEpoch, focusToken);
    } catch {
      // loadDetail/loadEvents ya exponen el cierre seguro y no reintentan solos.
      if (focusAfterRestart && eventPanelEpoch.current === panelEpoch &&
        sharedRecoveryEpoch === detailRecoveryEpoch.current && recoveryEpoch === eventRecoveryEpoch.current &&
        focusToken === collectionFocusToken.current) {
        eventFocusIntent.current = null;
        if (eventsOpenRef.current) queueMicrotask(() => eventRestartRef.current?.focus());
      }
    }
  };

  const runCommand = async (pendingCommand: PendingCommand) => {
    if (pending || commandMemory?.status === "pending") return;
    if (commandMemory?.status === "uncertain" && (
      !commandContractCompatible || commandsClosed || commandMemory.recoveryRequired
    )) return;
    if (commandMemory?.status === "recovery_required") return;
    const entry = { ...pendingCommand, planId } as const;
    const previousPlan = detail.data;
    const commandFocusToken = ++collectionFocusToken.current;
    memberFocusIntent.current = null;
    eventFocusIntent.current = null;
    setPending(true);
    setCommandMemory({ status: "pending", entry });
    setCommandAlert(null);
    setCommandStatus(null);
    try {
      const receipt = pendingCommand.kind === "revalidate"
        ? await studyApi.revalidate(pendingCommand.command)
        : await studyApi.cancel(pendingCommand.command);
      if (receipt.planId !== planId) throw new StudyApiError("invalid_response", 200, true);
      if (receipt.commandRevision !== pendingCommand.expectedPlanRevision + 1) {
        throw new StudyApiError("invalid_response", 200, true);
      }
      let confirmedState: PlanDetail["state"];
      try {
        const [confirmed, nextContext] = await Promise.all([
          studyApi.plan(planId),
          refreshContexts(),
          studyApi.plans({ limit: 10 }),
        ]);
        const safeProgression = previousPlan !== null && isSafePlanProgression(previousPlan, confirmed);
        const receiptEvent = confirmed.recentEvents.find((event) => event.revision === receipt.commandRevision);
        const exactRevalidation = receipt.status !== "revalidated" ||
          (pendingCommand.kind === "revalidate" && matchesRevalidationReceiptEvent(
            receiptEvent,
            receipt.removedCount,
            pendingCommand.expectedMapRevision,
            pendingCommand.expectedPolicyRevision,
          ));
        const exactCancellation = pendingCommand.kind !== "cancel" || (
          confirmed.state === "cancelled" && receiptEvent?.type === "cancelled"
        );
        if (!nextContext.compatible || confirmed.planRevision < receipt.commandRevision || !safeProgression ||
          !exactRevalidation || !exactCancellation) {
          throw new StudyApiError("invalid_response", 200);
        }
        const latestPlan = detailSnapshot.current;
        if (latestPlan === null || !isSafePlanProgression(latestPlan, confirmed) || !rememberDetail(confirmed)) {
          throw new StudyApiError("invalid_response", 200);
        }
        confirmedState = confirmed.state;
        setDetail({ loading: false, data: confirmed, error: null });
        if (membersOpenRef.current) {
          memberFocusIntent.current = commandFocusToken === collectionFocusToken.current
            ? { kind: "restart", token: commandFocusToken }
            : null;
          setMembers(membersNeedRestart());
        }
        if (eventsOpenRef.current) {
          eventFocusIntent.current = !membersOpenRef.current && commandFocusToken === collectionFocusToken.current
            ? { kind: "restart", token: commandFocusToken }
            : null;
          setEvents(eventsNeedRestart());
        }
      } catch {
        setCommandMemory({
          status: "unconfirmed",
          entry,
          planId,
          commandRevision: receipt.commandRevision,
          removedCount: receipt.status === "revalidated" ? receipt.removedCount : null,
        });
        setCommandAlert(
          "El comando respondió, pero no pudimos confirmar el estado actual. No lo reenvíes como un comando nuevo; actualizá el detalle.",
        );
        return;
      }
      setCommandMemory(null);
      setAvailabilityBlocked(false);
      setRequiresNewDecision(false);
      setCommandStatus(receipt.replayed
        ? `Replay confirmado; estado actual: ${planStateLabels[confirmedState]}.`
        : pendingCommand.kind === "revalidate"
          ? `Alcance revalidado; estado actual confirmado: ${planStateLabels[confirmedState]}.`
          : "Plan local cancelado y estado actual confirmado. No se modificaron mensajes.");
    } catch (reason) {
      const error = asStudyApiError(reason);
      if (error.uncertainWrite) {
        const recoveryRequired = error.code === "invalid_response";
        setCommandMemory({ status: "uncertain", entry, recoveryRequired, replayInvalidated: false });
        if (recoveryRequired) setCommandsClosed(true);
        setCommandAlert(recoveryRequired
          ? "Resultado incierto con respuesta incompatible: el comando pudo haber sido aceptado, pero su reenvío queda cerrado hasta actualizar y validar detalle y contrato."
          : "Resultado incierto: el comando pudo haber sido aceptado. No se reintentará automáticamente. Podés repetir exactamente el mismo envío.");
      } else {
        const revisionConflict = error.code === "plan_revision_conflict" ||
          error.code === "map_revision_conflict" || error.code === "policy_revision_conflict";
        if (error.code === "command_id_conflict") {
          setRequiresNewDecision(true);
        }
        if (error.code === "inventory_incomplete" || error.code === "account_unavailable" || error.code === "study_unavailable") {
          setAvailabilityBlocked(true);
        }
        if (error.code === "invalid_response" || revisionConflict) setCommandsClosed(true);
        if (revisionConflict) {
          setCommandMemory({ status: "recovery_required", entry, code: error.code });
        } else {
          setCommandMemory(null);
        }
        setCommandAlert(error.message);
        if (error.code === "plan_expired" || error.code === "invalid_transition") {
          void loadDetail().catch(() => undefined);
        }
      }
    } finally {
      setPending(false);
    }
  };

  if (detail.loading && detail.data === null) {
    return (
      <div className="page study-plan-page">
        <h1 className="sr-only">Detalle del Estudio de Limpieza</h1>
        <LoadingState label="Leyendo el plan congelado…" />
      </div>
    );
  }

  if (detail.error && detail.data === null) {
    return (
      <div className="page study-plan-page">
        <h1>Detalle del Estudio de Limpieza no disponible</h1>
        <AlertMessage>
          <p>{detail.error.message}</p>
          <div className="study-inline-actions">
            <button className="button button-secondary" type="button" onClick={() => void loadDetail().catch(() => undefined)}>Reintentar lectura del plan</button>
            <a className="button button-secondary" href="#/study">Volver a Estudio de Limpieza</a>
          </div>
        </AlertMessage>
      </div>
    );
  }

  const plan = detail.data;
  if (!plan) return null;
  const active = plan.state === "frozen" || plan.state === "reduced";
  const currentSnapshotAvailable = !plan.warnings.includes("current_snapshot_unavailable");
  const context = contexts.context;
  const collectionMalformed = members.error?.code === "invalid_response" || events.error?.code === "invalid_response";
  const commandGateOpen = !busy && !contexts.loading && !detail.loading && detail.error === null &&
    !collectionMalformed && commandMemory === null && !requiresNewDecision && !commandsClosed;
  const retryContractOpen = commandContractCompatible && !commandsClosed && !collectionMalformed &&
    detail.error === null && uncertainMemory?.recoveryRequired !== true && uncertainMemory?.replayInvalidated !== true;
  const canRevalidate = active && commandGateOpen && !availabilityBlocked && commandContractCompatible && context !== null && currentSnapshotAvailable &&
    context.availability.planRevalidateAvailable && context.availability.currentMapRevision !== null &&
    context.availability.currentPolicyRevision !== null && plan.currentMapRevision !== null &&
    plan.currentPolicyRevision !== null;
  const canCancel = active && commandGateOpen && commandContractCompatible;

  const refreshCommandSurface = async () => {
    try {
      const [confirmed, nextContext] = await Promise.all([
        loadDetail(),
        refreshContexts(),
        studyApi.plans({ limit: 10 }),
      ]);
      const unconfirmedMatches = !unconfirmedCommand || (
        confirmed.planRevision >= unconfirmedCommand.commandRevision &&
        (() => {
          const receiptEvent = confirmed.recentEvents.find((event) => event.revision === unconfirmedCommand.commandRevision);
          if (unconfirmedCommand.entry.kind === "cancel") {
            return confirmed.state === "cancelled" && receiptEvent?.type === "cancelled";
          }
          if (unconfirmedCommand.entry.kind === "revalidate") {
            return unconfirmedCommand.removedCount !== null && matchesRevalidationReceiptEvent(
              receiptEvent,
              unconfirmedCommand.removedCount,
              unconfirmedCommand.entry.expectedMapRevision,
              unconfirmedCommand.entry.expectedPolicyRevision,
            );
          }
          return unconfirmedCommand.entry.kind === "create" &&
            matchesCreateDraft(confirmed, unconfirmedCommand.entry.draft);
        })()
      );
      if (nextContext.compatible && nextContext.context !== null && unconfirmedMatches) {
        setCommandsClosed(false);
        if (unconfirmedCommand) {
          setCommandMemory(null);
          setCommandAlert(null);
          setCommandStatus("El estado actual del comando aceptado quedó confirmado.");
        } else if (uncertainMemory) {
          setCommandMemory((current) => current?.status === "uncertain" && current.entry === uncertainMemory.entry
            ? { ...current, recoveryRequired: false }
            : current);
          setCommandAlert("Detalle y contrato validados. El mismo envío exacto sigue disponible; no se generó otra clave.");
        } else if (conflictRecovery) {
          setCommandMemory(null);
          setCommandAlert(null);
          setCommandStatus("Detalle y contrato actualizados. No se repitió el comando en conflicto.");
        }
        if (nextContext.context.availability.planRevalidateAvailable) setAvailabilityBlocked(false);
      }
    } catch {
      // Los estados seguros ya se actualizan en loadDetail/useStudyContexts.
    }
  };

  const revalidate = () => {
    if (!canRevalidate || !context?.availability.currentMapRevision || context.availability.currentPolicyRevision === null) return;
    const command = prepareRevalidate(planId, {
      expectedPlanRevision: plan.planRevision,
      expectedMapRevision: context.availability.currentMapRevision,
      expectedPolicyRevision: context.availability.currentPolicyRevision,
    });
    void runCommand({
      kind: "revalidate",
      expectedPlanRevision: plan.planRevision,
      expectedMapRevision: context.availability.currentMapRevision,
      expectedPolicyRevision: context.availability.currentPolicyRevision,
      command,
    });
  };

  const cancel = () => {
    if (!canCancel) return;
    const command = prepareCancel(planId, { expectedPlanRevision: plan.planRevision });
    void runCommand({ kind: "cancel", expectedPlanRevision: plan.planRevision, command });
  };

  return (
    <div className="page study-plan-page">
      <PageHeader
        eyebrow="Plan congelado"
        title="Detalle del Estudio de Limpieza"
        description="Leé el alcance histórico y su estado efectivo sin reconstruirlo desde el mapa actual."
        actions={<a className="button button-secondary" href="#/study">Volver a planes</a>}
      />

      {foreignCommandMemory ? (
        <AlertMessage>
          Hay otro comando de Estudio pendiente de resolución en memoria. Volvé al plan o constructor donde se originó antes de tomar otra decisión.
        </AlertMessage>
      ) : null}

      {detail.error ? (
        <AlertMessage>
          El último intento de actualizar el detalle falló: {detail.error.message} Los comandos permanecen bloqueados hasta una recuperación explícita.
        </AlertMessage>
      ) : null}

      <section className={`study-plan-hero panel state-${plan.state}`} aria-labelledby="plan-effective-state">
        <div className="study-plan-hero-heading">
          <div>
            <span className="eyebrow">Estado efectivo</span>
            <h2 id="plan-effective-state">{planStateLabels[plan.state]}</h2>
          </div>
          <Badge tone={stateTone(plan.state)}>{dispositionLabels[plan.disposition]}</Badge>
        </div>
        <p className="study-no-effect"><strong>Vista previa sin efectos; no modifica Gmail.</strong></p>
        {plan.state === "reduced" ? <AlertMessage>La selección fue reducida: ningún mensaje retirado se reincorporó.</AlertMessage> : null}
        {plan.state === "invalidated" ? <AlertMessage>El alcance actual quedó vacío o dejó de ser válido. Este estado es terminal.</AlertMessage> : null}
        {plan.state === "cancelled" ? <AlertMessage>El plan local está cancelado. Conserva su vista previa histórica y no modificó mensajes.</AlertMessage> : null}
        {plan.state === "expired" ? <AlertMessage>El servidor marcó este plan como vencido. No se calculó ese estado en el navegador.</AlertMessage> : null}
        {plan.warnings.map((warning) => (
          <AlertMessage key={warning}>{warningLabels[warning]}</AlertMessage>
        ))}
        <p className="study-protection-summary">
          Al crear se excluyeron {formatCount(plan.excludedAtCreationCount)} mensajes por filtros o protecciones.
          La elegibilidad actual sólo puede conservarse o reducirse.
        </p>
      </section>

      <section className="study-metrics" aria-label="Conteos y tamaños del plan">
        <article className="panel"><span>Seleccionados al crear</span><strong>{formatCount(plan.selectedAtCreationCount)}</strong><small>{formatBytes(plan.selectedAtCreationSizeEstimateBytes)} estimados</small></article>
        <article className="panel"><span>Excluidos al crear</span><strong>{formatCount(plan.excludedAtCreationCount)}</strong><small>{formatBytes(plan.excludedAtCreationSizeEstimateBytes)} estimados</small></article>
        <article className="panel"><span>Elegibles actualmente</span><strong>{formatCount(plan.currentEligibleCount)}</strong><small>{formatBytes(plan.currentEligibleSizeEstimateBytes)} estimados</small></article>
        <article className="panel"><span>Liberación efectiva</span><strong>Sin medición</strong><small>effectiveFreedBytes es nulo</small></article>
      </section>

      <section className="panel study-plan-timing" aria-labelledby="plan-timing-title">
        <h2 id="plan-timing-title">Vigencia e intención</h2>
        <dl className="study-review-list">
          <div><dt>Intención</dt><dd>{dispositionLabels[plan.disposition]}</dd></div>
          <div><dt>Creado</dt><dd>{formatDate(plan.createdAt, true)}</dd></div>
          <div><dt>Vence</dt><dd>{formatDate(plan.expiresAt, true)}</dd></div>
          <div><dt>Última revalidación</dt><dd>{plan.lastRevalidatedAt ? formatDate(plan.lastRevalidatedAt, true) : "Todavía no revalidado"}</dd></div>
        </dl>
        <p>{storageEffectLabels[plan.storageEffect]} No existe una medición de liberación efectiva.</p>
      </section>

      {(commandAlert || uncertain || unconfirmedCommand || conflictRecovery || matchingEntry?.kind) ? (
        <AlertMessage>
          <p>{commandAlert ?? (uncertain
            ? "Resultado incierto conservado en memoria. Sólo podés repetir exactamente el mismo envío."
            : unconfirmedCommand
              ? "El comando fue aceptado, pero su estado actual todavía no pudo confirmarse. No envíes otro comando."
              : conflictRecovery
                ? new StudyApiError(conflictRecovery.code, 409).message
                : "El comando sigue pendiente; no envíes otro.")}</p>
          <div className="study-inline-actions">
            {uncertain ? (
              <button className="button button-secondary" type="button" disabled={busy || !retryContractOpen} onClick={() => void runCommand(uncertain)}>
                Repetir exactamente el mismo envío
              </button>
            ) : null}
            {requiresNewDecision ? (
              <button className="button button-secondary" type="button" disabled={busy} onClick={() => setRequiresNewDecision(false)}>
                Confirmar una nueva decisión sobre este plan
              </button>
            ) : null}
            <button className="button button-secondary" type="button" disabled={busy} onClick={() => void refreshCommandSurface()}>
              Actualizar detalle y contrato
            </button>
          </div>
        </AlertMessage>
      ) : null}
      {commandStatus ? <StatusMessage>{commandStatus}</StatusMessage> : null}

      <section className="panel study-plan-actions" aria-labelledby="plan-actions-title" aria-busy={busy}>
        <div>
          <h2 id="plan-actions-title">Decisiones sobre el plan local</h2>
          <p>Revalidar sólo puede conservar o retirar miembros. Cancelar no mueve, revierte ni modifica mensajes.</p>
        </div>
        <div className="study-inline-actions">
          {active ? (
            <>
              <button className="button button-primary" type="button" disabled={!canRevalidate || busy} onClick={revalidate} aria-describedby={!canRevalidate ? "revalidate-disabled" : undefined}>
                {busy ? "Comando pendiente…" : "Revalidar alcance"}
              </button>
              <button className="button button-secondary" type="button" disabled={!canCancel || busy} onClick={cancel}>
                Cancelar plan
              </button>
            </>
          ) : <p>Este plan está en un estado terminal y no admite comandos.</p>}
        </div>
        {active && !canRevalidate ? (
          <p id="revalidate-disabled" className="field-help">
            La revalidación requiere contrato compatible y fotografía sintética completa.
            {canCancel
              ? " La cancelación local sigue disponible."
              : " Los comandos permanecen bloqueados hasta resolver el estado pendiente o comprobar el contrato."}
          </p>
        ) : null}
      </section>

      <DisclosurePanel
        eyebrow="Criterios históricos"
        title="Objetivos y filtros congelados"
        summary={`${formatCount(plan.selection.targets.length)} objetivos · ${readStateLabels[plan.selection.readState]}`}
      >
        <dl className="study-review-list">
          <div><dt>Intención</dt><dd>{dispositionLabels[plan.selection.disposition]}</dd></div>
          <div><dt>Período pedido</dt><dd>{temporalDescription(plan.selection.temporalFilterRequested)}</dd></div>
          <div><dt>Lectura</dt><dd>{readStateLabels[plan.selection.readState]}</dd></div>
          <div><dt>Últimos por flujo</dt><dd>{formatCount(plan.selection.keepLatestPerFlow)}</dd></div>
          <div><dt>Zona civil</dt><dd>{plan.selection.timeZone}</dd></div>
        </dl>
        <h3>Nombres históricos inmutables</h3>
        <ul className="study-simple-list">
          {plan.selection.targetSnapshots.map((snapshot) => (
            <li key={`${snapshot.kind}:${snapshot.targetId}`}>
              <strong>{snapshot.kind === "sender" ? snapshot.displayAddress : snapshot.displayName}</strong>
              <small>{snapshot.kind === "source" ? "Fuente" : snapshot.kind === "flow" ? "Flujo" : "Remitente"}</small>
            </li>
          ))}
        </ul>
        <h3>Etiquetas excluidas al crear</h3>
        {plan.selection.excludedLabelSnapshots.length === 0 ? <p>Ninguna etiqueta adicional.</p> : (
          <ul className="study-simple-list">
            {plan.selection.excludedLabelSnapshots.map((label) => <li key={label.labelId}>{label.displayName}</li>)}
          </ul>
        )}
      </DisclosurePanel>

      <DisclosurePanel
        eyebrow="Muestras acotadas"
        title="Incluidas y excluidas"
        summary={`${formatCount(plan.includedSamples.length)} incluidas · ${formatCount(plan.excludedSamples.length)} excluidas`}
      >
        <SampleList title="Incluidas" samples={plan.includedSamples} included />
        <SampleList title="Excluidas" samples={plan.excludedSamples} included={false} />
      </DisclosurePanel>

      <details
        className="panel disclosure-panel"
        onToggle={(event) => {
          collectionFocusToken.current += 1;
          memberFocusIntent.current = null;
          eventFocusIntent.current = null;
          membersOpenRef.current = event.currentTarget.open;
          if (!event.currentTarget.open) {
            memberGeneration.current += 1;
            memberPanelEpoch.current += 1;
            memberRecoveryEpoch.current += 1;
            setMembers(EMPTY_MEMBERS);
          }
          setMembersOpen(event.currentTarget.open);
        }}
      >
        <summary>
          <span className="disclosure-title"><span className="eyebrow">Universo congelado</span><span className="disclosure-heading" role="heading" aria-level={2}>Miembros y razones</span></span>
          <span className="disclosure-summary">selected y removed pueden superponerse</span>
        </summary>
        <div className="disclosure-content">
          <p>Un retirado sigue perteneciendo a la selección original; no se reclasifica como exclusión inicial.</p>
          <div className="field-group compact-field">
            <label htmlFor="member-filter">Filtrar miembros</label>
            <select id="member-filter" value={memberFilter} onChange={(event) => {
              const nextFilter = event.target.value as MemberFilter;
              memberGeneration.current += 1;
              memberRecoveryEpoch.current += 1;
              collectionFocusToken.current += 1;
              memberFocusIntent.current = null;
              eventFocusIntent.current = null;
              setMembers(EMPTY_MEMBERS);
              setMemberFilter(nextFilter);
            }}>
              <option value="all">Todo el universo inicial</option>
              <option value="selected">Selección original</option>
              <option value="eligible">Elegibles actuales</option>
              <option value="excluded">Excluidos al crear</option>
              <option value="removed">Retirados después</option>
            </select>
          </div>
          {members.loading && members.items.length === 0 ? <LoadingState label="Leyendo miembros congelados…" /> : null}
          {members.error ? (
            <AlertMessage>
              <p>{members.error.message}</p>
              <button ref={memberRestartRef} className="button button-secondary" type="button" onClick={() => void (
                members.needsDetailRefresh ? refreshDetailAndMembers(true) : loadMembers(undefined, undefined, true)
              )}>
                {members.needsDetailRefresh
                  ? "Actualizar detalle y reiniciar miembros"
                  : members.needsRestart ? "Reiniciar miembros desde la primera página" : "Reintentar miembros"}
              </button>
            </AlertMessage>
          ) : null}
          {members.loaded && !members.loading && !members.error && members.items.length === 0 ? (
            <EmptyState title="Sin miembros para este filtro" detail={memberFilterLabels[memberFilter]} />
          ) : null}
          <ul className="study-member-list">
            {members.items.map((member) => (
              <li key={member.messageId}>
                <div><strong>{memberInitialLabels[member.initialState]}</strong><span>{memberCurrentLabels[member.currentState]}</span></div>
                <span>{formatDate(member.receivedAt, true)} · {formatBytes(member.sizeEstimateBytes)}</span>
                {member.reasonCodes.length > 0 ? <small>{member.reasonCodes.map((reason) => exclusionReasonLabels[reason]).join(" · ")}</small> : <small>Sin motivo de exclusión o retiro</small>}
                <PublicId value={member.messageId} />
              </li>
            ))}
          </ul>
          {members.loaded && !members.loading && !members.error ? (
            <div className="study-pagination">
              <span ref={memberStatusRef} role="status" aria-live="polite" tabIndex={-1}>{formatCount(members.items.length)} miembros cargados</span>
              {members.nextCursor ? (
                <button className="button button-secondary" type="button" disabled={busy || members.loading} onClick={() => void loadMembers(members.nextCursor ?? undefined)} aria-label={`Cargar la siguiente página de ${memberFilterLabels[memberFilter].toLocaleLowerCase("es-AR")}`}>
                  Cargar más miembros
                </button>
              ) : null}
            </div>
          ) : null}
        </div>
      </details>

      <details className="panel disclosure-panel" onToggle={(event) => {
        collectionFocusToken.current += 1;
        memberFocusIntent.current = null;
        eventFocusIntent.current = null;
        eventsOpenRef.current = event.currentTarget.open;
        if (!event.currentTarget.open) {
          eventGeneration.current += 1;
          eventPanelEpoch.current += 1;
          eventRecoveryEpoch.current += 1;
          setEvents(EMPTY_EVENTS);
        }
        setEventsOpen(event.currentTarget.open);
      }}>
        <summary>
          <span className="disclosure-title"><span className="eyebrow">Trazabilidad local</span><span className="disclosure-heading" role="heading" aria-level={2}>Eventos completos</span></span>
          <span className="disclosure-summary">{formatCount(plan.eventCount)} eventos</span>
        </summary>
        <div className="disclosure-content">
          {events.loading && events.items.length === 0 ? <LoadingState label="Leyendo eventos del plan…" /> : null}
          {events.error ? (
            <AlertMessage>
              <p>{events.error.message}</p>
              <button ref={eventRestartRef} className="button button-secondary" type="button" onClick={() => void (
                events.needsDetailRefresh ? refreshDetailAndEvents(true) : loadEvents(undefined, undefined, true)
              )}>
                {events.needsDetailRefresh
                  ? "Actualizar detalle y reiniciar eventos"
                  : events.needsRestart ? "Reiniciar eventos desde la primera página" : "Reintentar eventos"}
              </button>
            </AlertMessage>
          ) : null}
          <ol className="study-event-list">
            {events.items.map((event) => (
              <li key={event.revision}>
                <div><strong>{eventTypeLabels[event.type]}</strong><Badge>{planStateLabels[event.state]}</Badge></div>
                <p>{formatDate(event.recordedAt, true)} · retirados {formatCount(event.removedCount)} · restantes {formatCount(event.remainingCount)}</p>
                <small>Revisión {formatCount(event.revision)}</small>
                <small>Mapa observado: {event.observedMapRevision ?? "No materializado"}</small>
                <small>Política observada: {event.observedPolicyRevision === null ? "No materializada" : formatCount(event.observedPolicyRevision)}</small>
              </li>
            ))}
          </ol>
          {events.loaded && !events.loading && !events.error && events.items.length === 0 ? <EmptyState title="Sin eventos" detail="El contrato no devolvió eventos para este plan." /> : null}
          {events.loaded && !events.loading && !events.error ? (
            <div className="study-pagination">
              <span ref={eventStatusRef} role="status" aria-live="polite" tabIndex={-1}>{formatCount(events.items.length)} eventos cargados</span>
              {events.nextCursor ? (
                <button className="button button-secondary" type="button" disabled={busy || events.loading} onClick={() => void loadEvents(events.nextCursor ?? undefined)} aria-label="Cargar la siguiente página de eventos">
                  Cargar más eventos
                </button>
              ) : null}
            </div>
          ) : null}
        </div>
      </details>

      <DisclosurePanel
        eyebrow="Diagnóstico"
        title="Revisiones e IDs públicos"
        summary={`Plan r${formatCount(plan.planRevision)}`}
      >
        <dl className="study-review-list">
          <div><dt>Revisión del plan</dt><dd>{formatCount(plan.planRevision)}</dd></div>
          <div><dt>Mapa al crear</dt><dd><code>{plan.createdFromMapRevision}</code></dd></div>
          <div><dt>Política al crear</dt><dd>{formatCount(plan.createdFromPolicyRevision)}</dd></div>
          <div><dt>Mapa actual observado</dt><dd>{plan.currentMapRevision ? <code>{plan.currentMapRevision}</code> : "No disponible"}</dd></div>
          <div><dt>Política actual observada</dt><dd>{plan.currentPolicyRevision === null ? "No disponible" : formatCount(plan.currentPolicyRevision)}</dd></div>
        </dl>
        <PublicId value={plan.planId} />
      </DisclosurePanel>
    </div>
  );
}

function SampleList({ title, samples, included }: { title: string; samples: PlanSample[]; included: boolean }) {
  return (
    <section className="study-sample-section" aria-label={title}>
      <h3>{title}</h3>
      {samples.length === 0 ? <p>No hay muestras para esta categoría.</p> : (
        <ul className="study-sample-list">
          {samples.map((sample) => (
            <li key={sample.messageId}>
              <strong>{sampleTitle(sample)}</strong>
              <span>{sample.senderName ?? "Remitente sin nombre"} · {sample.senderAddress ?? "Dirección no visible"}</span>
              <span>{formatDate(sample.receivedAt, true)} · {formatBytes(sample.sizeEstimateBytes)}</span>
              <small>{included ? "Incluida en la selección original" : sample.exclusionReasons.map((reason) => exclusionReasonLabels[reason]).join(" · ")}</small>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
