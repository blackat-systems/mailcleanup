import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import {
  AlertMessage,
  Badge,
  EmptyState,
  LoadingState,
  PageHeader,
  StatusMessage,
} from "../../components/Primitives";
import { formatBytes, formatCount, formatDate } from "../../utils";
import { asStudyApiError, StudyApiError, studyApi } from "../api";
import { prepareCreate } from "../commands";
import { comparePublicTargets, compareTimestamps, isCivilDate, isSafePlanProgression } from "../decoders";
import {
  dispositionLabels,
  inventoryStateLabels,
  planStateLabels,
  readStateLabels,
  storageEffectLabels,
} from "../presenters";
import type { StudyContextState } from "../hooks";
import {
  matchesCreateDraft,
  type SetStudyCommandMemory,
  type StudyCommandEntry,
  type StudyCommandMemory,
} from "../commandMemory";
import type {
  CreateReceipt,
  Disposition,
  PlanDetail,
  PlanState,
  PlanSummary,
  PreparedCommand,
  PublicTarget,
  ReadState,
  SelectionTarget,
  StudyContext,
  TargetKind,
  TemporalFilter,
} from "../types";

type Props = {
  contexts: StudyContextState;
  refreshContexts: () => Promise<StudyContextState>;
  commandMemory: StudyCommandMemory | null;
  setCommandMemory: SetStudyCommandMemory;
  planSnapshots: Map<string, PlanDetail>;
};

type HistoryState = {
  loading: boolean;
  items: PlanSummary[];
  nextCursor: string | null;
  listingAsOf: string | null;
  catalogRevision: number | null;
  error: StudyApiError | null;
  needsRestart: boolean;
};

type CatalogState = {
  loading: boolean;
  items: PublicTarget[];
  nextCursor: string | null;
  mapRevision: string | null;
  policyRevision: number | null;
  error: StudyApiError | null;
  needsRestart: boolean;
};

type TemporalKind = TemporalFilter["kind"];
type FormErrors = Partial<Record<"targets" | "labels" | "date" | "range" | "days" | "keep", string>>;
type CollectionFocusIntent = { kind: "page" | "restart"; token: number } | null;

const EMPTY_HISTORY: HistoryState = {
  loading: true,
  items: [],
  nextCursor: null,
  listingAsOf: null,
  catalogRevision: null,
  error: null,
  needsRestart: false,
};

const EMPTY_CATALOG: CatalogState = {
  loading: false,
  items: [],
  nextCursor: null,
  mapRevision: null,
  policyRevision: null,
  error: null,
  needsRestart: false,
};

function planTone(state: PlanState): "neutral" | "positive" | "warning" | "critical" {
  if (state === "frozen") return "positive";
  if (state === "reduced") return "warning";
  if (state === "invalidated" || state === "expired") return "critical";
  return "neutral";
}

function targetLabel(target: PublicTarget): string {
  return target.kind === "sender" ? target.displayAddress : target.displayName;
}

function targetKey(target: Pick<PublicTarget, "kind" | "targetId"> | SelectionTarget): string {
  return `${target.kind}:${target.targetId}`;
}

function plansRemainOrdered(items: readonly PlanSummary[]): boolean {
  const ids = new Set(items.map((item) => item.planId));
  return ids.size === items.length && items.every((item, index) => {
    if (index === 0) return true;
    const previous = items[index - 1]!;
    const timestampOrder = compareTimestamps(previous.createdAt, item.createdAt);
    return timestampOrder > 0 || (timestampOrder === 0 && previous.planId < item.planId);
  });
}

function targetsRemainOrdered(items: readonly PublicTarget[]): boolean {
  const ids = new Set(items.map(targetKey));
  return ids.size === items.length && items.every((item, index) =>
    index === 0 || comparePublicTargets(items[index - 1]!, item) < 0);
}

function temporalSummary(
  kind: TemporalKind,
  beforeDate: string,
  onOrAfterDate: string,
  olderThanDays: string,
): string {
  if (kind === "all") return "Sin corte de fecha";
  if (kind === "beforeDate") return beforeDate ? `Antes del ${beforeDate} (exclusivo)` : "Fecha pendiente";
  if (kind === "dateRange") {
    return onOrAfterDate && beforeDate
      ? `Desde ${onOrAfterDate} incluido hasta ${beforeDate} excluido`
      : "Rango pendiente";
  }
  return olderThanDays ? `Más antiguos que ${olderThanDays} días civiles completos` : "Antigüedad pendiente";
}

function availabilityMessage(context: StudyContext): string {
  const availability = context.availability;
  if (!availability.accountAvailable) return "La cuenta sintética de demostración está ausente.";
  if (availability.inventoryState !== "completed") {
    return `El inventario está ${availability.inventoryState ? inventoryStateLabels[availability.inventoryState].toLocaleLowerCase("es-AR") : "sin estado"}.`;
  }
  if (!availability.completeSnapshotAvailable) return "La fotografía completa todavía no está disponible.";
  if (!availability.planCreateAvailable) return "El catálogo y la creación están temporalmente bloqueados.";
  return "Catálogo sintético disponible para preparar un estudio.";
}

function navigateToPlan(planId: string): void {
  window.location.hash = `#/study/plans/${encodeURIComponent(planId)}`;
}

export function StudyPage({ contexts, refreshContexts, commandMemory, setCommandMemory, planSnapshots }: Props) {
  const initialCreateEntry = commandMemory?.entry.kind === "create" ? commandMemory.entry : null;
  const initialDraft = initialCreateEntry?.draft;
  const initialTemporal = initialDraft?.temporalFilter;
  const historyGeneration = useRef(0);
  const catalogGeneration = useRef(0);
  const historySnapshot = useRef<HistoryState>(EMPTY_HISTORY);
  const catalogSnapshot = useRef<CatalogState>(EMPTY_CATALOG);
  const mountedRef = useRef(true);
  const createButtonRef = useRef<HTMLButtonElement>(null);
  const createTitleRef = useRef<HTMLHeadingElement>(null);
  const builderTitleRef = useRef<HTMLHeadingElement>(null);
  const historyStatusRef = useRef<HTMLSpanElement>(null);
  const historyRestartRef = useRef<HTMLButtonElement>(null);
  const historyFocusIntent = useRef<CollectionFocusIntent>(null);
  const catalogStatusRef = useRef<HTMLSpanElement>(null);
  const catalogRestartRef = useRef<HTMLButtonElement>(null);
  const catalogFocusIntent = useRef<CollectionFocusIntent>(null);
  const collectionFocusToken = useRef(0);
  const previousBuilderOpen = useRef(false);
  const [historyFilter, setHistoryFilter] = useState<PlanState | "all">("all");
  const [history, setHistory] = useState<HistoryState>(EMPTY_HISTORY);
  const [builderOpen, setBuilderOpen] = useState(initialCreateEntry !== null);
  const [catalog, setCatalog] = useState<CatalogState>(EMPTY_CATALOG);
  const [step, setStep] = useState(initialDraft ? 5 : 1);
  const [selectedTargets, setSelectedTargets] = useState<SelectionTarget[]>(() => initialDraft ? [...initialDraft.targets] : []);
  const [disposition, setDisposition] = useState<Disposition>(initialDraft?.disposition ?? "archive");
  const [temporalKind, setTemporalKind] = useState<TemporalKind>(initialTemporal?.kind ?? "all");
  const [beforeDate, setBeforeDate] = useState(() => initialTemporal?.kind === "beforeDate"
    ? initialTemporal.date
    : initialTemporal?.kind === "dateRange" ? initialTemporal.beforeDate : "");
  const [onOrAfterDate, setOnOrAfterDate] = useState(() => initialTemporal?.kind === "dateRange" ? initialTemporal.onOrAfterDate : "");
  const [olderThanDays, setOlderThanDays] = useState(() => initialTemporal?.kind === "olderThanDays" ? String(initialTemporal.days) : "");
  const [readState, setReadState] = useState<ReadState>(initialDraft?.readState ?? "any");
  const [excludedLabelIds, setExcludedLabelIds] = useState<string[]>(() => initialDraft ? [...initialDraft.excludedLabelIds] : []);
  const [keepLatestPerFlow, setKeepLatestPerFlow] = useState(() => String(initialDraft?.keepLatestPerFlow ?? 0));
  const [errors, setErrors] = useState<FormErrors>({});
  const [pending, setPending] = useState(false);
  const [commandAlert, setCommandAlert] = useState<string | null>(null);
  const [commandSuccess, setCommandSuccess] = useState<string | null>(null);
  const [revisionBlocked, setRevisionBlocked] = useState(false);
  const [availabilityBlocked, setAvailabilityBlocked] = useState(false);
  const [requiresNewDecision, setRequiresNewDecision] = useState(false);
  const [commandsClosed, setCommandsClosed] = useState(false);
  const commitHistory = useCallback((update: HistoryState | ((current: HistoryState) => HistoryState)) => {
    const next = typeof update === "function" ? update(historySnapshot.current) : update;
    historySnapshot.current = next;
    setHistory(next);
  }, []);
  const commitCatalog = useCallback((update: CatalogState | ((current: CatalogState) => CatalogState)) => {
    const next = typeof update === "function" ? update(catalogSnapshot.current) : update;
    catalogSnapshot.current = next;
    setCatalog(next);
  }, []);
  const createEntry = commandMemory?.entry.kind === "create"
    ? commandMemory.entry
    : null;
  const uncertainMemory = commandMemory?.status === "uncertain" && createEntry ? commandMemory : null;
  const uncertain = uncertainMemory ? createEntry?.command ?? null : null;
  const unconfirmedPlan = commandMemory?.status === "unconfirmed" && commandMemory.entry.kind === "create"
    ? commandMemory
    : null;
  const busy = pending || commandMemory?.status === "pending";
  const foreignCommandMemory = commandMemory !== null && createEntry === null && unconfirmedPlan === null;

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      historyGeneration.current += 1;
      catalogGeneration.current += 1;
      collectionFocusToken.current += 1;
      historyFocusIntent.current = null;
      catalogFocusIntent.current = null;
    };
  }, []);

  useEffect(() => {
    const wasOpen = previousBuilderOpen.current;
    previousBuilderOpen.current = builderOpen;
    queueMicrotask(() => {
      if (builderOpen) builderTitleRef.current?.focus();
      else if (wasOpen) {
        if (createButtonRef.current && !createButtonRef.current.disabled) createButtonRef.current.focus();
        else createTitleRef.current?.focus();
      }
    });
  }, [builderOpen, step]);

  useEffect(() => {
    const intent = historyFocusIntent.current;
    if (history.loading || intent === null) return;
    historyFocusIntent.current = null;
    if (intent.token !== collectionFocusToken.current) return;
    if (history.error) historyRestartRef.current?.focus();
    else historyStatusRef.current?.focus();
  }, [history.error, history.loading, history.needsRestart, history.nextCursor]);

  useEffect(() => {
    const intent = catalogFocusIntent.current;
    if (catalog.loading || intent === null) return;
    catalogFocusIntent.current = null;
    if (!builderOpen || intent.token !== collectionFocusToken.current) return;
    if (catalog.error) catalogRestartRef.current?.focus();
    else catalogStatusRef.current?.focus();
  }, [builderOpen, catalog.error, catalog.loading, catalog.needsRestart, catalog.nextCursor]);

  const loadHistory = useCallback(async (cursor?: string, focusAfterRestart = false) => {
    if (!mountedRef.current) return false;
    const generation = ++historyGeneration.current;
    const appending = cursor !== undefined;
    if (appending || focusAfterRestart) {
      const token = ++collectionFocusToken.current;
      catalogFocusIntent.current = null;
      historyFocusIntent.current = { kind: appending ? "page" : "restart", token };
    } else {
      historyFocusIntent.current = null;
    }
    commitHistory((current) => ({
      ...(appending ? current : EMPTY_HISTORY),
      loading: true,
      error: null,
      needsRestart: false,
    }));
    try {
      const page = await studyApi.plans({
        ...(historyFilter === "all" ? {} : { state: historyFilter }),
        ...(cursor ? { cursor } : {}),
        limit: 10,
      });
      if (!mountedRef.current || generation !== historyGeneration.current) return false;
      const requestedState = historyFilter === "all" ? null : historyFilter;
      if (page.state !== requestedState) {
        commitHistory({ ...EMPTY_HISTORY, loading: false, error: new StudyApiError("invalid_response", 200) });
        return false;
      }
      const current = historySnapshot.current;
      if (appending && (
        current.listingAsOf !== page.listingAsOf ||
        current.catalogRevision !== page.catalogRevision
      )) {
        commitHistory({
          ...EMPTY_HISTORY,
          loading: false,
          error: new StudyApiError("invalid_response", 200),
        });
        return false;
      }
      const items = appending ? [...current.items, ...page.items] : page.items;
      if (!plansRemainOrdered(items)) {
        commitHistory({ ...EMPTY_HISTORY, loading: false, error: new StudyApiError("invalid_response", 200) });
        return false;
      }
      commitHistory({
        loading: false,
        items,
        nextCursor: page.nextCursor,
        listingAsOf: page.listingAsOf,
        catalogRevision: page.catalogRevision,
        error: null,
        needsRestart: false,
      });
      return true;
    } catch (reason) {
      if (generation !== historyGeneration.current) return false;
      const error = asStudyApiError(reason);
      if (appending && (error.code === "cursor_stale" || error.code === "invalid_cursor")) {
        commitHistory({ ...EMPTY_HISTORY, loading: false, error, needsRestart: true });
      } else {
        commitHistory((current) => ({ ...current, loading: false, error }));
      }
      return false;
    }
  }, [commitHistory, historyFilter]);

  useEffect(() => {
    let active = true;
    queueMicrotask(() => {
      if (active) void loadHistory();
    });
    return () => {
      active = false;
    };
  }, [loadHistory]);

  const loadCatalog = useCallback(async (cursor?: string, focusAfterRestart = false) => {
    if (!mountedRef.current) return false;
    const generation = ++catalogGeneration.current;
    const appending = cursor !== undefined;
    if (appending || focusAfterRestart) {
      const token = ++collectionFocusToken.current;
      historyFocusIntent.current = null;
      catalogFocusIntent.current = { kind: appending ? "page" : "restart", token };
    } else {
      catalogFocusIntent.current = null;
    }
    commitCatalog((current) => ({
      ...(appending ? current : EMPTY_CATALOG),
      loading: true,
      error: null,
      needsRestart: false,
    }));
    try {
      const page = await studyApi.targets({ ...(cursor ? { cursor } : {}), limit: 50 });
      if (!mountedRef.current || generation !== catalogGeneration.current) return false;
      if (page.kind !== null) {
        commitCatalog({ ...EMPTY_CATALOG, error: new StudyApiError("invalid_response", 200) });
        return false;
      }
      const current = catalogSnapshot.current;
      if (appending && (
        current.mapRevision !== page.mapRevision ||
        current.policyRevision !== page.policyRevision
      )) {
        commitCatalog({
          ...EMPTY_CATALOG,
          error: new StudyApiError("invalid_response", 200),
        });
        return false;
      }
      const items = appending ? [...current.items, ...page.items] : page.items;
      if (!targetsRemainOrdered(items)) {
        commitCatalog({ ...EMPTY_CATALOG, error: new StudyApiError("invalid_response", 200) });
        return false;
      }
      commitCatalog({
        loading: false,
        items,
        nextCursor: page.nextCursor,
        mapRevision: page.mapRevision,
        policyRevision: page.policyRevision,
        error: null,
        needsRestart: false,
      });
      return true;
    } catch (reason) {
      if (generation !== catalogGeneration.current) return false;
      const error = asStudyApiError(reason);
      if (appending && (error.code === "cursor_stale" || error.code === "invalid_cursor")) {
        commitCatalog({ ...EMPTY_CATALOG, error, needsRestart: true });
      } else {
        commitCatalog((current) => ({ ...current, loading: false, error }));
      }
      return false;
    }
  }, [commitCatalog]);

  const context = contexts.context;
  const commandsCompatible = !contexts.loading && contexts.compatible && context !== null;
  const malformedSurface = history.error?.code === "invalid_response" || history.error?.code === "transport_error" ||
    catalog.error?.code === "invalid_response" || catalog.error?.code === "transport_error";
  const commandBlocked = commandMemory !== null || revisionBlocked || availabilityBlocked ||
    requiresNewDecision || commandsClosed;
  const catalogAvailable = commandsCompatible && context.availability.targetReadAvailable && !malformedSurface;
  const createAvailable = commandsCompatible && context.availability.planCreateAvailable && !catalog.loading &&
    catalog.error === null && !malformedSurface && !commandBlocked;
  const resumableBuilder = createEntry !== null || revisionBlocked || availabilityBlocked ||
    requiresNewDecision || commandsClosed;
  const canOpenBuilder = createAvailable || resumableBuilder;
  const retryContractOpen = commandsCompatible && !commandsClosed && !malformedSurface &&
    uncertainMemory?.recoveryRequired !== true && uncertainMemory?.replayInvalidated !== true;

  useEffect(() => {
    if (!builderOpen || !catalogAvailable || catalog.loading || catalog.error || catalog.mapRevision !== null) return;
    let active = true;
    queueMicrotask(() => {
      if (active) void loadCatalog();
    });
    return () => {
      active = false;
    };
  }, [builderOpen, catalog.error, catalog.loading, catalog.mapRevision, catalogAvailable, loadCatalog]);

  const openBuilder = () => {
    collectionFocusToken.current += 1;
    historyFocusIntent.current = null;
    catalogFocusIntent.current = null;
    setBuilderOpen(true);
    if (!resumableBuilder) {
      setStep(1);
      setCommandAlert(null);
      setCommandSuccess(null);
    }
    if (catalogAvailable && catalog.items.length === 0 && !catalog.loading) void loadCatalog();
  };

  const invalidateUncertain = () => {
    if (uncertain || requiresNewDecision) {
      if (uncertainMemory?.recoveryRequired) {
        setCommandMemory((current) => current?.status === "uncertain" && current.entry === uncertainMemory.entry
          ? { ...current, replayInvalidated: true }
          : current);
        setCommandAlert(
          "El formulario cambió, pero la respuesta incompatible anterior todavía exige recuperación. No se generará otra clave hasta validar contrato e historia.",
        );
        return;
      }
      if (uncertain) setCommandMemory(null);
      setRequiresNewDecision(false);
      setCommandAlert("El formulario cambió. El envío incierto anterior ya no puede repetirse; confirmá una decisión nueva.");
    }
  };

  const refreshForReview = async () => {
    const [nextContext, historyReady] = await Promise.all([refreshContexts(), loadHistory()]);
    if (!nextContext.compatible || nextContext.context === null || !historyReady) {
      return;
    }
    if (uncertainMemory) {
      setCommandsClosed(false);
      if (uncertainMemory.replayInvalidated) {
        setCommandMemory(null);
        setRequiresNewDecision(true);
        setCommandAlert("Contrato e historia validados. El envío anterior quedó invalidado por la edición; confirmá una decisión nueva antes de generar otra clave.");
      } else {
        setCommandMemory((current) => current?.status === "uncertain" && current.entry === uncertainMemory.entry
          ? { ...current, recoveryRequired: false }
          : current);
        setCommandAlert("Contrato e historia validados. El mismo envío exacto sigue disponible; no se generó otra clave.");
      }
    }
    if (!nextContext.context.availability.targetReadAvailable) {
      if (!uncertainMemory) setAvailabilityBlocked(true);
      return;
    }
    const catalogReady = await loadCatalog();
    if (catalogReady && nextContext.compatible && nextContext.context?.availability.targetReadAvailable) {
      setRevisionBlocked(false);
      if (nextContext.context.availability.planCreateAvailable) setAvailabilityBlocked(false);
    }
  };

  const rememberConfirmedPlan = (confirmed: PlanDetail): boolean => {
    if (!mountedRef.current) return false;
    const previous = planSnapshots.get(confirmed.planId);
    if (previous !== undefined && !isSafePlanProgression(previous, confirmed)) return false;
    if (!mountedRef.current) return false;
    planSnapshots.set(confirmed.planId, confirmed);
    return true;
  };

  const confirmAcceptedState = async () => {
    if (!unconfirmedPlan) return;
    try {
      const [confirmed, nextContext, historyReady] = await Promise.all([
        studyApi.plan(unconfirmedPlan.planId),
        refreshContexts(),
        loadHistory(),
      ]);
      if (!mountedRef.current) return;
      if (unconfirmedPlan.entry.kind !== "create" || !nextContext.compatible || !historyReady || confirmed.planRevision < unconfirmedPlan.commandRevision ||
        !matchesCreateDraft(confirmed, unconfirmedPlan.entry.draft)) {
        throw new StudyApiError("invalid_response", 200);
      }
      if (!rememberConfirmedPlan(confirmed)) {
        throw new StudyApiError("invalid_response", 200);
      }
      const confirmedPlanId = unconfirmedPlan.planId;
      setCommandMemory(null);
      setCommandAlert(null);
      setCommandSuccess("El estado actual del estudio aceptado quedó confirmado.");
      navigateToPlan(confirmedPlanId);
    } catch {
      if (!mountedRef.current) return;
      setCommandAlert("El comando fue aceptado, pero el estado actual todavía no pudo confirmarse. No envíes otro comando.");
    }
  };

  const selectedKeys = useMemo(() => new Set(selectedTargets.map(targetKey)), [selectedTargets]);
  const selectableTargets = catalog.items.filter((item) => item.kind !== "label");
  const labelTargets = catalog.items.filter((item) => item.kind === "label");
  const catalogComplete = catalog.mapRevision !== null && catalog.nextCursor === null && !catalog.loading && catalog.error === null;
  const catalogPendingSelection = selectedTargets.filter((selected) =>
    !selectableTargets.some((candidate) => targetKey(candidate) === targetKey(selected))
  );
  const catalogPendingLabels = excludedLabelIds.filter((labelId) =>
    !labelTargets.some((candidate) => candidate.targetId === labelId)
  );
  const missingSelection = catalogComplete ? catalogPendingSelection : [];
  const missingLabels = catalogComplete ? catalogPendingLabels : [];
  const unverifiedSelection = catalogComplete ? [] : catalogPendingSelection;
  const unverifiedLabels = catalogComplete ? [] : catalogPendingLabels;
  const targetKindRank = { source: 0, flow: 1, sender: 2 } as const;
  const canonicalSelectedTargets = [...selectedTargets].sort((left, right) =>
    targetKindRank[left.kind] - targetKindRank[right.kind] || left.targetId.localeCompare(right.targetId));
  const canonicalExcludedLabelIds = [...excludedLabelIds].sort();

  const toggleTarget = (target: PublicTarget) => {
    if (target.kind === "label") return;
    invalidateUncertain();
    const selection: SelectionTarget = { kind: target.kind, targetId: target.targetId };
    setSelectedTargets((current) => current.some((item) => targetKey(item) === targetKey(selection))
      ? current.filter((item) => targetKey(item) !== targetKey(selection))
      : [...current, selection]);
    setErrors((current) => ({ ...current, targets: undefined }));
  };

  const toggleLabel = (labelId: string) => {
    invalidateUncertain();
    setExcludedLabelIds((current) => current.includes(labelId)
      ? current.filter((item) => item !== labelId)
      : [...current, labelId]);
  };

  const buildTemporalFilter = (): TemporalFilter | null => {
    if (temporalKind === "all") return { kind: "all" };
    if (temporalKind === "beforeDate") {
      return isCivilDate(beforeDate) ? { kind: "beforeDate", date: beforeDate } : null;
    }
    if (temporalKind === "dateRange") {
      return isCivilDate(onOrAfterDate) && isCivilDate(beforeDate) && onOrAfterDate < beforeDate
        ? { kind: "dateRange", onOrAfterDate, beforeDate }
        : null;
    }
    const days = Number(olderThanDays);
    return Number.isSafeInteger(days) && days >= 1 && days <= 36500
      ? { kind: "olderThanDays", days }
      : null;
  };

  const validateStep = (requestedStep: number): boolean => {
    const next: FormErrors = {};
    if (requestedStep >= 1 && (selectedTargets.length < 1 || selectedTargets.length > 100 || missingSelection.length > 0 || unverifiedSelection.length > 0)) {
      next.targets = unverifiedSelection.length > 0
        ? "Todavía faltan páginas del catálogo para verificar todos los objetivos conservados. Cargalas antes de continuar."
        : missingSelection.length > 0
        ? "Hay objetivos que ya no aparecen en el catálogo. Quitalos o reiniciá la selección."
        : "Elegí entre 1 y 100 objetivos públicos.";
    }
    if (requestedStep >= 3 && buildTemporalFilter() === null) {
      if (temporalKind === "beforeDate") next.date = "Ingresá una fecha civil válida.";
      if (temporalKind === "dateRange") next.range = "Ingresá un rango válido cuyo inicio sea anterior al final.";
      if (temporalKind === "olderThanDays") next.days = "Ingresá entre 1 y 36.500 días civiles completos.";
    }
    const keep = keepLatestPerFlow === "" ? Number.NaN : Number(keepLatestPerFlow);
    if (requestedStep >= 4 && (!Number.isSafeInteger(keep) || keep < 0 || keep > 10000)) {
      next.keep = "Ingresá un entero entre 0 y 10.000.";
    }
    if (requestedStep >= 4 && (missingLabels.length > 0 || unverifiedLabels.length > 0)) {
      next.labels = unverifiedLabels.length > 0
        ? "Todavía faltan páginas del catálogo para verificar todas las etiquetas conservadas. Cargalas antes de confirmar."
        : "Hay etiquetas que ya no aparecen en el catálogo. Quitalas o actualizá la selección.";
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const advance = () => {
    if (validateStep(step)) {
      collectionFocusToken.current += 1;
      historyFocusIntent.current = null;
      catalogFocusIntent.current = null;
      setStep((current) => Math.min(5, current + 1));
    }
  };

  const runCreate = async (
    command: PreparedCommand<CreateReceipt>,
    preservedEntry?: Extract<StudyCommandEntry, { kind: "create" }>,
  ) => {
    if (pending || commandMemory?.status === "pending") return;
    if (preservedEntry && (
      !retryContractOpen || uncertainMemory === null || uncertainMemory.entry !== preservedEntry
    )) return;
    const temporalFilter = buildTemporalFilter();
    if (!preservedEntry && (!temporalFilter || !catalog.mapRevision || catalog.policyRevision === null)) return;
    collectionFocusToken.current += 1;
    historyFocusIntent.current = null;
    catalogFocusIntent.current = null;
    const entry: Extract<StudyCommandEntry, { kind: "create" }> = preservedEntry ?? {
      kind: "create",
      command,
      draft: {
        expectedMapRevision: catalog.mapRevision!,
        expectedPolicyRevision: catalog.policyRevision!,
        disposition,
        targets: canonicalSelectedTargets,
        temporalFilter: temporalFilter!,
        readState,
        excludedLabelIds: canonicalExcludedLabelIds,
        keepLatestPerFlow: Number(keepLatestPerFlow),
        targetLabels: canonicalSelectedTargets.flatMap((selected) => {
          const target = selectableTargets.find((candidate) => targetKey(candidate) === targetKey(selected));
          return target ? [{ ...selected, label: targetLabel(target) }] : [];
        }),
        excludedLabelLabels: canonicalExcludedLabelIds.flatMap((targetId) => {
          const label = labelTargets.find((candidate) => candidate.targetId === targetId);
          return label ? [{ targetId, label: targetLabel(label) }] : [];
        }),
      },
    };
    setPending(true);
    setCommandMemory({ status: "pending", entry });
    setCommandAlert(null);
    setCommandSuccess(null);
    try {
      const receipt = await studyApi.create(command);
      const preserveUnconfirmed = () => {
        setCommandMemory((current) => current?.entry === entry
          ? {
              status: "unconfirmed",
              entry,
              planId: receipt.planId,
              commandRevision: receipt.commandRevision,
              removedCount: null,
            }
          : current);
      };
      if (!mountedRef.current) {
        preserveUnconfirmed();
        return;
      }
      let confirmedState: PlanState;
      try {
        const [confirmed, nextContext, historyReady] = await Promise.all([
          studyApi.plan(receipt.planId),
          refreshContexts(),
          loadHistory(),
        ]);
        if (!mountedRef.current) {
          preserveUnconfirmed();
          return;
        }
        if (!nextContext.compatible || !historyReady || confirmed.planRevision < receipt.commandRevision ||
          !matchesCreateDraft(confirmed, entry.draft)) {
          throw new StudyApiError("invalid_response", 200);
        }
        if (!rememberConfirmedPlan(confirmed)) {
          throw new StudyApiError("invalid_response", 200);
        }
        confirmedState = confirmed.state;
      } catch {
        preserveUnconfirmed();
        if (mountedRef.current) {
          setCommandAlert(
            "El comando respondió, pero no pudimos confirmar el estado actual. No lo reenvíes como un comando nuevo; actualizá la historia.",
          );
        }
        return;
      }
      setCommandMemory(null);
      setRevisionBlocked(false);
      setAvailabilityBlocked(false);
      setRequiresNewDecision(false);
      setCommandSuccess(receipt.replayed
        ? `Replay confirmado. Estado actual: ${planStateLabels[confirmedState]}.`
        : `Estudio aceptado. Estado actual confirmado: ${planStateLabels[confirmedState]}.`);
      navigateToPlan(receipt.planId);
    } catch (reason) {
      const error = asStudyApiError(reason);
      if (error.uncertainWrite) {
        const recoveryRequired = error.code === "invalid_response";
        setCommandMemory({ status: "uncertain", entry, recoveryRequired, replayInvalidated: false });
        if (recoveryRequired) setCommandsClosed(true);
        setCommandAlert(recoveryRequired
          ? "Resultado incierto con respuesta incompatible: el comando pudo haber sido aceptado, pero su reenvío queda cerrado hasta actualizar y validar contrato e historia."
          : "Resultado incierto: el comando pudo haber sido aceptado. No se reenviará solo. Podés repetir exactamente el mismo envío o actualizar la historia.");
      } else {
        if (error.code === "command_id_conflict" || error.code === "plan_too_large" || error.code === "payload_too_large") {
          setCommandMemory(null);
          setRequiresNewDecision(true);
        }
        if (error.code === "map_revision_conflict" || error.code === "policy_revision_conflict" || error.code === "target_not_found") {
          setRevisionBlocked(true);
        }
        if (error.code === "inventory_incomplete" || error.code === "account_unavailable" || error.code === "study_unavailable") {
          setAvailabilityBlocked(true);
        }
        if (error.code === "invalid_response") setCommandsClosed(true);
        setCommandMemory(null);
        setCommandAlert(error.message);
      }
    } finally {
      if (mountedRef.current) setPending(false);
    }
  };

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (busy || commandBlocked || !validateStep(5) || !createAvailable || !catalog.mapRevision || catalog.policyRevision === null) return;
    const temporalFilter = buildTemporalFilter();
    if (!temporalFilter) return;
    const command = prepareCreate({
      expectedMapRevision: catalog.mapRevision,
      expectedPolicyRevision: catalog.policyRevision,
      disposition,
      targets: canonicalSelectedTargets,
      temporalFilter,
      readState,
      excludedLabelIds: canonicalExcludedLabelIds,
      keepLatestPerFlow: Number(keepLatestPerFlow),
    });
    void runCreate(command);
  };

  const effectiveCommandAlert = commandAlert ?? (uncertain
    ? uncertainMemory?.replayInvalidated
      ? "La respuesta incompatible y la edición posterior siguen cerradas hasta una recuperación explícita."
      : "Resultado incierto conservado en memoria. Sólo podés repetir exactamente el mismo envío o editar el formulario para tomar una decisión nueva."
    : unconfirmedPlan
      ? "El comando fue aceptado, pero su estado actual todavía no pudo confirmarse. No envíes otro comando."
      : createEntry && commandMemory?.status === "pending"
        ? "El comando de creación sigue pendiente. No cierres ni envíes otro."
        : null);

  const groupedTargets: Record<Exclude<TargetKind, "label">, PublicTarget[]> = {
    source: [], flow: [], sender: [],
  };
  for (const item of selectableTargets) groupedTargets[item.kind].push(item);

  return (
    <div className="page study-page">
      <PageHeader
        eyebrow="Proceso sintético"
        title="Estudio de Limpieza"
        description="Prepará y comprendé planes congelados antes de considerar cualquier proceso posterior."
      />

      <section className="panel study-availability" aria-labelledby="study-availability-title">
        <div>
          <span className="eyebrow">Estado seguro</span>
          <h2 id="study-availability-title">Sin efectos y con contrato cerrado</h2>
          <p role="status" aria-live="polite">
            {context ? availabilityMessage(context) : "Los comandos permanecen cerrados hasta comprobar ambos contextos locales."}
          </p>
        </div>
        <div className="study-availability-badges">
          <Badge tone="protected">Datos de demostración</Badge>
          <Badge tone="neutral">Ejecución desactivada</Badge>
          {context?.availability.inventoryState ? (
            <Badge tone={context.availability.inventoryState === "completed" ? "positive" : "warning"}>
              {inventoryStateLabels[context.availability.inventoryState]}
            </Badge>
          ) : null}
        </div>
      </section>

      {foreignCommandMemory ? (
        <AlertMessage>
          Hay otro comando de Estudio pendiente de resolución en memoria. Volvé al detalle correspondiente antes de crear un estudio nuevo.
        </AlertMessage>
      ) : null}

      {!builderOpen ? (
        <section className="study-primary-action" aria-labelledby="new-study-title">
          <div>
            <span className="eyebrow">Vista previa local</span>
            <h2 id="new-study-title" ref={createTitleRef} tabIndex={-1}>Crear un estudio nuevo</h2>
            <p>Definí objetivos, intención, período y exclusiones. Archivo y Papelera son intenciones inertes.</p>
          </div>
          <button
            ref={createButtonRef}
            className="button button-primary"
            type="button"
            onClick={openBuilder}
            disabled={!canOpenBuilder}
            aria-describedby={!canOpenBuilder ? "create-blocked-reason" : undefined}
          >
            {resumableBuilder ? "Retomar estudio pendiente" : "Crear estudio"}
          </button>
          {!canOpenBuilder ? (
            <p id="create-blocked-reason" className="field-help">
              La creación está bloqueada; la historia y los planes congelados siguen disponibles.
            </p>
          ) : null}
        </section>
      ) : (
        <section className="study-builder panel" aria-labelledby="study-builder-title">
          <div className="study-builder-heading">
            <div>
              <span className="eyebrow">Paso {step} de 5</span>
              <h2 id="study-builder-title" ref={builderTitleRef} tabIndex={-1}>Preparar un estudio</h2>
            </div>
            <button className="button button-ghost" type="button" onClick={() => {
              collectionFocusToken.current += 1;
              historyFocusIntent.current = null;
              catalogFocusIntent.current = null;
              setBuilderOpen(false);
            }} disabled={busy}>
              Cerrar constructor
            </button>
          </div>

          <aside className="study-builder-summary" aria-label="Resumen del estudio en preparación" role="status" aria-live="polite" aria-atomic="true">
            <span><strong>{selectedTargets.length}</strong> objetivos</span>
            <span><strong>{dispositionLabels[disposition]}</strong> como intención</span>
            <span>{temporalSummary(temporalKind, beforeDate, onOrAfterDate, olderThanDays)}</span>
            <span>{readStateLabels[readState]}</span>
            <span><strong>{excludedLabelIds.length}</strong> etiquetas excluidas</span>
          </aside>

          <form onSubmit={submit} aria-busy={busy} noValidate>
            {step === 1 ? (
              <fieldset className="study-fieldset" disabled={busy} aria-describedby={errors.targets ? "targets-error" : undefined}>
                <legend>Qué estudiar</legend>
                <p className="field-help">Elegí de 1 a 100 fuentes, flujos o remitentes públicos. Las etiquetas no son objetivos.</p>
                {catalog.loading && catalog.items.length === 0 ? <LoadingState label="Leyendo el catálogo sintético…" /> : null}
                {catalog.error ? (
                  <AlertMessage>
                    {catalog.error.message}
                    <button ref={catalogRestartRef} className="button button-secondary" type="button" onClick={() => void loadCatalog(undefined, true)}>
                      {catalog.needsRestart ? "Reiniciar catálogo desde la primera página" : "Reintentar lectura del catálogo"}
                    </button>
                  </AlertMessage>
                ) : null}
                {errors.targets ? <p className="field-error" id="targets-error" role="alert">{errors.targets}</p> : null}
                {!catalog.loading && !catalog.error && catalog.items.length === 0 ? (
                  <EmptyState title="Catálogo vacío" detail="La fotografía sintética no publicó objetivos ni etiquetas para estudiar." />
                ) : null}
                {missingSelection.length > 0 ? (
                  <button className="button button-secondary" type="button" onClick={() => {
                    invalidateUncertain();
                    setSelectedTargets((current) => current.filter((item) => !missingSelection.some((missing) => targetKey(missing) === targetKey(item))));
                    setErrors((current) => ({ ...current, targets: undefined }));
                  }}>
                    Quitar objetivos que ya no están disponibles
                  </button>
                ) : null}
                {(["source", "flow", "sender"] as const).map((kind) => (
                  groupedTargets[kind].length > 0 ? (
                    <div className="study-target-group" key={kind}>
                      <h3>{kind === "source" ? "Fuentes" : kind === "flow" ? "Flujos" : "Remitentes"}</h3>
                      <div className="study-choice-list">
                        {groupedTargets[kind].map((target) => (
                          <label className="study-choice-card" key={targetKey(target)}>
                            <input
                              type="checkbox"
                              checked={selectedKeys.has(targetKey(target))}
                              onChange={() => toggleTarget(target)}
                              disabled={selectedTargets.length >= 100 && !selectedKeys.has(targetKey(target))}
                            />
                            <span><strong>{targetLabel(target)}</strong><small>{formatCount(target.messageCount)} mensajes sintéticos</small></span>
                          </label>
                        ))}
                      </div>
                    </div>
                  ) : null
                ))}
                {catalog.mapRevision !== null && !catalog.error ? (
                  <div className="study-pagination">
                    <span ref={catalogStatusRef} role="status" aria-live="polite" tabIndex={-1}>{formatCount(catalog.items.length)} objetivos y etiquetas cargados</span>
                    {catalog.nextCursor ? (
                      <button className="button button-secondary" type="button" onClick={() => void loadCatalog(catalog.nextCursor ?? undefined)} disabled={catalog.loading}>
                        Cargar más objetivos y etiquetas
                      </button>
                    ) : null}
                  </div>
                ) : null}
              </fieldset>
            ) : null}

            {step === 2 ? (
              <fieldset className="study-fieldset" disabled={busy}>
                <legend>Intención</legend>
                <p className="field-help">La intención se guarda en la vista previa. No mueve ni modifica mensajes.</p>
                <div className="study-choice-list study-choice-list-two">
                  {(["archive", "trash"] as const).map((value) => (
                    <label className="study-choice-card" key={value}>
                      <input
                        type="radio"
                        name="disposition"
                        value={value}
                        checked={disposition === value}
                        onChange={() => { invalidateUncertain(); setDisposition(value); }}
                      />
                      <span>
                        <strong>{dispositionLabels[value]}</strong>
                        <small>{value === "archive" ? "Archivar no libera almacenamiento." : "Papelera no garantiza liberación inmediata ni definitiva."}</small>
                      </span>
                    </label>
                  ))}
                </div>
              </fieldset>
            ) : null}

            {step === 3 ? (
              <div className="study-stage-stack">
                <fieldset className="study-fieldset" disabled={busy}>
                  <legend>Período civil de Córdoba</legend>
                  <p className="field-help">Las fechas son civiles de America/Argentina/Cordoba. El servidor conserva la autoridad del corte UTC.</p>
                  <div className="study-radio-grid">
                    {([
                      ["all", "Todo el período"],
                      ["beforeDate", "Antes de una fecha"],
                      ["dateRange", "Entre dos fechas"],
                      ["olderThanDays", "Más antiguos que N días"],
                    ] as const).map(([value, label]) => (
                      <label key={value}>
                        <input type="radio" name="temporal-kind" checked={temporalKind === value} onChange={() => { invalidateUncertain(); setTemporalKind(value); }} />
                        <span>{label}</span>
                      </label>
                    ))}
                  </div>
                  {temporalKind === "beforeDate" ? (
                    <div className="field-group">
                      <label htmlFor="study-before-date">Fecha final exclusiva</label>
                      <input id="study-before-date" type="date" value={beforeDate} onChange={(event) => { invalidateUncertain(); setBeforeDate(event.target.value); }} aria-describedby={`before-date-help${errors.date ? " before-date-error" : ""}`} />
                      <p id="before-date-help" className="field-help">Se incluyen mensajes anteriores; la fecha indicada queda afuera.</p>
                      {errors.date ? <p id="before-date-error" className="field-error" role="alert">{errors.date}</p> : null}
                    </div>
                  ) : null}
                  {temporalKind === "dateRange" ? (
                    <div className="study-date-grid">
                      <div className="field-group">
                        <label htmlFor="study-on-or-after">Inicio incluido</label>
                        <input id="study-on-or-after" type="date" value={onOrAfterDate} onChange={(event) => { invalidateUncertain(); setOnOrAfterDate(event.target.value); }} aria-describedby={errors.range ? "date-range-error" : undefined} />
                      </div>
                      <div className="field-group">
                        <label htmlFor="study-range-before">Final excluido</label>
                        <input id="study-range-before" type="date" value={beforeDate} onChange={(event) => { invalidateUncertain(); setBeforeDate(event.target.value); }} aria-describedby={errors.range ? "date-range-error" : undefined} />
                      </div>
                      {errors.range ? <p id="date-range-error" className="field-error" role="alert">{errors.range}</p> : null}
                    </div>
                  ) : null}
                  {temporalKind === "olderThanDays" ? (
                    <div className="field-group">
                      <label htmlFor="study-older-days">Días civiles completos</label>
                      <input id="study-older-days" type="number" min="1" max="36500" step="1" value={olderThanDays} onChange={(event) => { invalidateUncertain(); setOlderThanDays(event.target.value); }} aria-describedby={`older-days-help${errors.days ? " older-days-error" : ""}`} />
                      <p id="older-days-help" className="field-help">Entre 1 y 36.500; no son bloques móviles de 24 horas calculados por el navegador.</p>
                      {errors.days ? <p id="older-days-error" className="field-error" role="alert">{errors.days}</p> : null}
                    </div>
                  ) : null}
                </fieldset>
                <fieldset className="study-fieldset" disabled={busy}>
                  <legend>Estado de lectura</legend>
                  <div className="study-radio-grid">
                    {(["any", "read", "unread"] as const).map((value) => (
                      <label key={value}>
                        <input type="radio" name="read-state" checked={readState === value} onChange={() => { invalidateUncertain(); setReadState(value); }} />
                        <span>{readStateLabels[value]}</span>
                      </label>
                    ))}
                  </div>
                </fieldset>
              </div>
            ) : null}

            {step === 4 ? (
              <fieldset className="study-fieldset" disabled={busy} aria-describedby={errors.labels ? "labels-error" : undefined}>
                <legend>Exclusiones</legend>
                <p className="field-help">Sólo se ofrecen etiquetas de sistema del catálogo. Las protecciones del motor se aplican sin duplicarlas en la interfaz.</p>
                {errors.labels ? <p id="labels-error" className="field-error" role="alert">{errors.labels}</p> : null}
                {missingLabels.length > 0 ? (
                  <button className="button button-secondary" type="button" onClick={() => {
                    invalidateUncertain();
                    setExcludedLabelIds((current) => current.filter((labelId) => !missingLabels.includes(labelId)));
                    setErrors((current) => ({ ...current, labels: undefined }));
                  }}>
                    Quitar etiquetas que ya no están disponibles
                  </button>
                ) : null}
                {labelTargets.length === 0 ? (
                  <EmptyState title="Sin etiquetas en esta página" detail="Cargá más catálogo si existe otra página; no escribas IDs manualmente." />
                ) : (
                  <div className="study-choice-list">
                    {labelTargets.map((label) => (
                      <label className="study-choice-card" key={label.targetId}>
                        <input type="checkbox" checked={excludedLabelIds.includes(label.targetId)} onChange={() => toggleLabel(label.targetId)} disabled={excludedLabelIds.length >= 100 && !excludedLabelIds.includes(label.targetId)} />
                        <span><strong>{targetLabel(label)}</strong><small>{formatCount(label.messageCount)} mensajes en el catálogo</small></span>
                      </label>
                    ))}
                  </div>
                )}
                <div className="field-group study-keep-field">
                  <label htmlFor="study-keep-latest">Conservar los últimos N por flujo</label>
                  <input id="study-keep-latest" type="number" min="0" max="10000" step="1" value={keepLatestPerFlow} onChange={(event) => { invalidateUncertain(); setKeepLatestPerFlow(event.target.value); }} aria-describedby={`keep-help${errors.keep ? " keep-error" : ""}`} />
                  <p id="keep-help" className="field-help">0 desactiva este criterio; el máximo contractual es 10.000.</p>
                  {errors.keep ? <p id="keep-error" className="field-error" role="alert">{errors.keep}</p> : null}
                </div>
              </fieldset>
            ) : null}

            {step === 5 ? (
              <fieldset className="study-fieldset study-review" disabled={busy}>
                <legend>Revisión final</legend>
                <p>Revisá el resumen canónico antes de crear. El servidor volverá a aplicar elegibilidad y protecciones.</p>
                <dl className="study-review-list">
                  <div><dt>Objetivos públicos</dt><dd>{formatCount(selectedTargets.length)}</dd></div>
                  <div><dt>Intención inerte</dt><dd>{dispositionLabels[disposition]}</dd></div>
                  <div><dt>Período</dt><dd>{temporalSummary(temporalKind, beforeDate, onOrAfterDate, olderThanDays)}</dd></div>
                  <div><dt>Lectura</dt><dd>{readStateLabels[readState]}</dd></div>
                  <div><dt>Etiquetas excluidas</dt><dd>{formatCount(excludedLabelIds.length)}</dd></div>
                  <div><dt>Últimos por flujo</dt><dd>{formatCount(Number(keepLatestPerFlow))}</dd></div>
                </dl>
                <details className="study-review-details" open>
                  <summary>Objetivos públicos elegidos</summary>
                  <ul className="study-simple-list">
                    {canonicalSelectedTargets.map((selected) => {
                      const target = selectableTargets.find((candidate) => targetKey(candidate) === targetKey(selected));
                      const savedLabel = createEntry?.draft.targetLabels.find((candidate) => targetKey(candidate) === targetKey(selected))?.label;
                      const label = target ? targetLabel(target) : savedLabel;
                      return label ? (
                        <li key={targetKey(selected)}>
                          <strong>{label}</strong>
                          <small>{selected.kind === "source" ? "Fuente" : selected.kind === "flow" ? "Flujo" : "Remitente"}</small>
                        </li>
                      ) : null;
                    })}
                  </ul>
                </details>
                <details className="study-review-details" open>
                  <summary>Etiquetas de sistema excluidas</summary>
                  {canonicalExcludedLabelIds.length === 0 ? <p>Ninguna etiqueta adicional.</p> : (
                    <ul className="study-simple-list">
                      {canonicalExcludedLabelIds.map((labelId) => {
                        const label = labelTargets.find((candidate) => candidate.targetId === labelId);
                        const savedLabel = createEntry?.draft.excludedLabelLabels.find((candidate) => candidate.targetId === labelId)?.label;
                        return label || savedLabel ? <li key={labelId}>{label ? targetLabel(label) : savedLabel}</li> : null;
                      })}
                    </ul>
                  )}
                </details>
                <AlertMessage>
                  Vista previa sin efectos; no modifica Gmail. Un universo no vacío completamente excluido produce un plan válido e invalidado, no un error.
                </AlertMessage>
              </fieldset>
            ) : null}

            {effectiveCommandAlert ? (
              <AlertMessage>
                <p>{effectiveCommandAlert}</p>
                <div className="study-inline-actions">
                  {uncertain ? (
                    <button className="button button-secondary" type="button" disabled={busy || !retryContractOpen} onClick={() => void runCreate(uncertain, createEntry ?? undefined)}>
                      Repetir exactamente el mismo envío
                    </button>
                  ) : null}
                  {unconfirmedPlan ? (
                    <button className="button button-secondary" type="button" disabled={busy} onClick={() => void confirmAcceptedState()}>
                      Confirmar el estado del estudio aceptado
                    </button>
                  ) : null}
                  {requiresNewDecision ? (
                    <button className="button button-secondary" type="button" disabled={busy} onClick={() => setRequiresNewDecision(false)}>
                      Confirmar una decisión nueva con este formulario
                    </button>
                  ) : null}
                  <button className="button button-secondary" type="button" disabled={busy} onClick={() => void refreshForReview()}>
                    Actualizar contexto y catálogo para revisar
                  </button>
                  <button className="button button-secondary" type="button" disabled={busy} onClick={() => void loadHistory()}>
                    Actualizar historia
                  </button>
                </div>
              </AlertMessage>
            ) : null}
            {commandSuccess ? <StatusMessage>{commandSuccess}</StatusMessage> : null}

            <div className="study-builder-actions">
              {step > 1 ? <button className="button button-secondary" type="button" onClick={() => {
                collectionFocusToken.current += 1;
                historyFocusIntent.current = null;
                catalogFocusIntent.current = null;
                setStep((current) => Math.max(1, current - 1));
              }} disabled={busy}>Paso anterior</button> : null}
              {step < 5 ? <button className="button button-primary" type="button" onClick={advance} disabled={busy}>Continuar al paso {step + 1}</button> : null}
              {step === 5 ? <button className="button button-primary" type="submit" disabled={busy || !createAvailable || commandBlocked}>{busy ? "Creando estudio…" : "Crear estudio"}</button> : null}
            </div>
          </form>
        </section>
      )}

      <section className="study-history" aria-labelledby="study-history-title">
        <div className="section-heading study-history-heading">
          <div>
            <span className="eyebrow">Historia congelada</span>
            <h2 id="study-history-title">Planes recientes</h2>
          </div>
          <div className="field-group compact-field">
            <label htmlFor="history-state">Filtrar por estado</label>
            <select id="history-state" value={historyFilter} onChange={(event) => {
              const nextFilter = event.target.value as PlanState | "all";
              historyGeneration.current += 1;
              collectionFocusToken.current += 1;
              historyFocusIntent.current = null;
              catalogFocusIntent.current = null;
              commitHistory(EMPTY_HISTORY);
              setHistoryFilter(nextFilter);
            }}>
              <option value="all">Todos</option>
              <option value="frozen">Congelados</option>
              <option value="reduced">Reducidos</option>
              <option value="invalidated">Invalidados</option>
              <option value="cancelled">Cancelados</option>
              <option value="expired">Vencidos</option>
            </select>
          </div>
        </div>

        {history.loading && history.items.length === 0 ? <LoadingState label="Leyendo planes sintéticos…" /> : null}
        {history.error ? (
          <AlertMessage>
            <p>{history.error.message}</p>
            <button ref={historyRestartRef} className="button button-secondary" type="button" onClick={() => void loadHistory(undefined, true)}>
              {history.needsRestart ? "Reiniciar historia desde la primera página" : "Reintentar lectura"}
            </button>
          </AlertMessage>
        ) : null}
        {!history.loading && !history.error && history.items.length === 0 ? (
          <EmptyState title="Todavía no hay planes" detail="La historia aparecerá acá después de crear el primer estudio sintético." />
        ) : null}
        <div className="study-plan-list" role="list">
          {history.items.map((plan) => (
            <article className="study-plan-card panel" key={plan.planId} role="listitem">
              <div className="study-plan-card-heading">
                <div>
                  <Badge tone={planTone(plan.state)}>{planStateLabels[plan.state]}</Badge>
                  <h3>{dispositionLabels[plan.disposition]}</h3>
                </div>
                <a
                  className="button button-secondary"
                  href={`#/study/plans/${encodeURIComponent(plan.planId)}`}
                  aria-label={`Ver detalle del plan ${planStateLabels[plan.state]} creado ${formatDate(plan.createdAt, true)}, ID ${plan.planId.slice(-8)}`}
                >
                  Ver detalle
                </a>
              </div>
              <dl className="study-plan-summary">
                <div><dt>Creado</dt><dd>{formatDate(plan.createdAt, true)}</dd></div>
                <div><dt>Vence</dt><dd>{formatDate(plan.expiresAt, true)}</dd></div>
                <div><dt>Seleccionados al crear</dt><dd>{formatCount(plan.selectedAtCreationCount)} · {formatBytes(plan.selectedAtCreationSizeEstimateBytes)}</dd></div>
                <div><dt>Excluidos al crear</dt><dd>{formatCount(plan.excludedAtCreationCount)} · {formatBytes(plan.excludedAtCreationSizeEstimateBytes)}</dd></div>
                <div><dt>Elegibles actuales</dt><dd>{formatCount(plan.currentEligibleCount)} · {formatBytes(plan.currentEligibleSizeEstimateBytes)}</dd></div>
              </dl>
              <p className="study-effect-note">{storageEffectLabels[plan.storageEffect]} No existe una medición de liberación efectiva.</p>
            </article>
          ))}
        </div>
        {!history.loading && !history.error ? (
          <div className="study-pagination">
            <span ref={historyStatusRef} role="status" aria-live="polite" tabIndex={-1}>{formatCount(history.items.length)} planes cargados</span>
            {history.nextCursor ? (
              <button className="button button-secondary" type="button" disabled={history.loading} onClick={() => void loadHistory(history.nextCursor ?? undefined)} aria-label="Cargar la siguiente página de planes">
                Cargar más planes
              </button>
            ) : null}
          </div>
        ) : null}
      </section>
    </div>
  );
}
