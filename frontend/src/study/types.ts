export const PLAN_STATES = [
  "frozen",
  "reduced",
  "invalidated",
  "cancelled",
  "expired",
] as const;
export type PlanState = (typeof PLAN_STATES)[number];

export const INVENTORY_STATES = [
  "not_started",
  "running",
  "paused",
  "completed",
  "requires_full_resync",
  "failed",
] as const;
export type InventoryState = (typeof INVENTORY_STATES)[number];

export const TARGET_KINDS = ["source", "flow", "sender", "label"] as const;
export type TargetKind = (typeof TARGET_KINDS)[number];
export type SelectableTargetKind = Exclude<TargetKind, "label">;

export const MEMBER_FILTERS = ["all", "selected", "eligible", "excluded", "removed"] as const;
export type MemberFilter = (typeof MEMBER_FILTERS)[number];
export type Disposition = "archive" | "trash";
export type StorageEffect = "none" | "not_guaranteed";
export type ReadState = "any" | "read" | "unread";
export type MessageReadState = Exclude<ReadState, "any">;
export type MemberInitialState = "selected" | "excluded";
export type MemberCurrentState = "eligible" | "excluded" | "removed";

export const WARNING_CODES = [
  "current_snapshot_unavailable",
  "map_changed_since_creation",
  "policy_changed_since_creation",
  "selection_reduced",
] as const;
export type WarningCode = (typeof WARNING_CODES)[number];

export const EXCLUSION_REASONS = [
  "sent",
  "draft",
  "trash",
  "starred",
  "important",
  "protected_label",
  "security",
  "document",
  "personal",
  "low_confidence",
  "contradiction",
  "mixed_conversation",
  "manual_policy",
  "policy_review",
  "outside_date",
  "read_state_mismatch",
  "excluded_label",
  "keep_latest",
  "missing_after_creation",
  "scope_changed",
  "protection_changed",
] as const;
export type ExclusionReason = (typeof EXCLUSION_REASONS)[number];

export const EVENT_TYPES = [
  "created",
  "revalidated",
  "reduced",
  "invalidated",
  "cancelled",
] as const;
export type EventType = (typeof EVENT_TYPES)[number];

export const STUDY_ERROR_CODES = [
  "invalid_request",
  "invalid_cursor",
  "invalid_local_origin",
  "route_not_found",
  "target_not_found",
  "plan_not_found",
  "method_not_allowed",
  "map_revision_conflict",
  "policy_revision_conflict",
  "plan_revision_conflict",
  "command_id_conflict",
  "cursor_stale",
  "invalid_transition",
  "plan_expired",
  "payload_too_large",
  "plan_too_large",
  "json_required",
  "unsupported_target",
  "invalid_filter",
  "study_unavailable",
  "inventory_incomplete",
  "account_unavailable",
  "internal_error",
] as const;
export type StudyErrorCode = (typeof STUDY_ERROR_CODES)[number];
export type StudyClientErrorCode = StudyErrorCode | "transport_error" | "invalid_response";

export type StudyEnvelope = {
  contractVersion: 1;
  dataMode: "synthetic";
  canExecute: false;
};

export type StudyLimits = {
  maxTargets: 100;
  maxExcludedLabels: 100;
  maxConsideredMessages: 100000;
  maxKeepLatestPerFlow: 10000;
  maxMessageSizeEstimateBytes: 2147483647;
  maxAggregateSizeEstimateBytes: 214748364700000;
  maxTargetPageSize: 100;
  maxPlanPageSize: 100;
  maxMessagePageSize: 500;
  maxEventPageSize: 100;
  maxCursorChars: 1024;
  maxQueryStringBytes: 4096;
  maxVisibleMetadataBytes: 16384;
  maxRequestBodyBytes: 65536;
  maxIncludedSamples: 5;
  maxExcludedSamples: 5;
};

export type StudyCapabilities = {
  studyRead: true;
  targetRead: true;
  planCreate: true;
  planRevalidate: true;
  planCancel: true;
  systemLabelFilter: true;
  customLabelFilter: false;
  gmailConnection: false;
  oauth: false;
  externalNetwork: false;
  realData: false;
  messageMutation: false;
  unsubscribe: false;
  execute: false;
};

export type StudyBlockerCode = "account_unavailable" | "inventory_incomplete" | "study_unavailable";

export type StudyAvailability = {
  accountAvailable: boolean;
  inventoryState: InventoryState | null;
  completeSnapshotAvailable: boolean;
  currentMapRevision: string | null;
  currentPolicyRevision: number | null;
  targetReadAvailable: boolean;
  planCreateAvailable: boolean;
  planRevalidateAvailable: boolean;
  blockerCodes: StudyBlockerCode[];
};

export type StudyContext = StudyEnvelope & {
  timeZone: "America/Argentina/Cordoba";
  planValiditySeconds: 86400;
  limits: StudyLimits;
  capabilities: StudyCapabilities;
  availability: StudyAvailability;
};

export type SourceTarget = {
  kind: "source";
  targetId: string;
  displayName: string;
  messageCount: number;
};
export type FlowTarget = {
  kind: "flow";
  targetId: string;
  sourceId: string;
  displayName: string;
  messageCount: number;
};
export type SenderTarget = {
  kind: "sender";
  targetId: string;
  displayAddress: string;
  messageCount: number;
};
export type LabelTarget = {
  kind: "label";
  targetId: string;
  displayName: string;
  messageCount: number;
};
export type PublicTarget = SourceTarget | FlowTarget | SenderTarget | LabelTarget;

export type TargetsResponse = StudyEnvelope & {
  mapRevision: string;
  policyRevision: number;
  kind: TargetKind | null;
  items: PublicTarget[];
  nextCursor: string | null;
};

export type SelectionTarget = { kind: SelectableTargetKind; targetId: string };
export type TargetSnapshot =
  | { kind: "source"; targetId: string; displayName: string }
  | { kind: "flow"; targetId: string; displayName: string }
  | { kind: "sender"; targetId: string; displayAddress: string };
export type LabelSnapshot = { labelId: string; displayName: string };

export type TemporalFilter =
  | { kind: "all" }
  | { kind: "beforeDate"; date: string }
  | { kind: "dateRange"; onOrAfterDate: string; beforeDate: string }
  | { kind: "olderThanDays"; days: number };

export type PlanSelection = {
  disposition: Disposition;
  targets: SelectionTarget[];
  targetSnapshots: TargetSnapshot[];
  temporalFilterRequested: TemporalFilter;
  resolvedOnOrAfterUtc: string | null;
  resolvedBeforeUtc: string | null;
  timeZone: "America/Argentina/Cordoba";
  readState: ReadState;
  excludedLabelIds: string[];
  excludedLabelSnapshots: LabelSnapshot[];
  keepLatestPerFlow: number;
};

export type PlanSummary = {
  planId: string;
  planRevision: number;
  state: PlanState;
  createdAt: string;
  expiresAt: string;
  lastRevalidatedAt: string | null;
  disposition: Disposition;
  selectedAtCreationCount: number;
  selectedAtCreationSizeEstimateBytes: number;
  excludedAtCreationCount: number;
  excludedAtCreationSizeEstimateBytes: number;
  currentEligibleCount: number;
  currentEligibleSizeEstimateBytes: number;
  storageEffect: StorageEffect;
  effectiveFreedBytes: null;
  canExecute: false;
};

export type PlanSample = {
  messageId: string;
  receivedAt: string;
  senderName: string | null;
  senderAddress: string | null;
  subject: string | null;
  sizeEstimateBytes: number;
  sourceId: string;
  flowId: string;
  readState: MessageReadState;
  exclusionReasons: ExclusionReason[];
};

export type PlanEvent = {
  revision: number;
  type: EventType;
  recordedAt: string;
  state: Exclude<PlanState, "expired">;
  observedMapRevision: string | null;
  observedPolicyRevision: number | null;
  removedCount: number;
  remainingCount: number;
};

export type PlanDetail = StudyEnvelope & PlanSummary & {
  selection: PlanSelection;
  createdFromMapRevision: string;
  createdFromPolicyRevision: number;
  currentMapRevision: string | null;
  currentPolicyRevision: number | null;
  includedSamples: PlanSample[];
  excludedSamples: PlanSample[];
  eventCount: number;
  recentEvents: PlanEvent[];
  warnings: WarningCode[];
};

export type PlansResponse = StudyEnvelope & {
  listingAsOf: string;
  catalogRevision: number;
  state: PlanState | null;
  items: PlanSummary[];
  nextCursor: string | null;
};

export type PlanMember = {
  messageId: string;
  initialState: MemberInitialState;
  currentState: MemberCurrentState;
  receivedAt: string;
  sizeEstimateBytes: number;
  reasonCodes: ExclusionReason[];
};

export type MessagesResponse = StudyEnvelope & {
  planId: string;
  planRevision: number;
  state: MemberFilter;
  items: PlanMember[];
  nextCursor: string | null;
};

export type EventsResponse = StudyEnvelope & {
  planId: string;
  planRevision: number;
  items: PlanEvent[];
  nextCursor: string | null;
};

export type CreatePlanRequest = {
  commandId: string;
  expectedMapRevision: string;
  expectedPolicyRevision: number;
  disposition: Disposition;
  targets: SelectionTarget[];
  temporalFilter: TemporalFilter;
  readState: ReadState;
  excludedLabelIds: string[];
  keepLatestPerFlow: number;
};

export type RevalidatePlanRequest = {
  commandId: string;
  expectedPlanRevision: number;
  expectedMapRevision: string;
  expectedPolicyRevision: number;
};

export type CancelPlanRequest = {
  commandId: string;
  expectedPlanRevision: number;
};

export type CreateReceipt = StudyEnvelope & {
  status: "created";
  replayed: boolean;
  commandRevision: number;
  planId: string;
};

export type RevalidateReceipt = StudyEnvelope & {
  status: "revalidated";
  replayed: boolean;
  commandRevision: number;
  removedCount: number;
  planId: string;
};

export type CancelReceipt = StudyEnvelope & {
  status: "cancelled";
  replayed: boolean;
  commandRevision: number;
  planId: string;
};

export type PreparedCommand<TReceipt> = {
  path: string;
  serializedBody: string;
  decode: (payload: unknown) => payload is TReceipt;
};

export type CommandReceipt = CreateReceipt | RevalidateReceipt | CancelReceipt;
