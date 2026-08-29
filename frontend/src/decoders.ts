import {
  BINDING_STATES,
  CONFIANZAS,
  INTENCIONES,
  POLICY_EVIDENCE_CODES,
  PROTECCIONES,
  PROTECTION_REASONS,
  REVIEW_BINDING_STATES,
  RUBROS,
  SUSCRIPCIONES,
  SYNC_STATES,
  type ClassificationEvidence,
  type ConnectionResponse,
  type ContextProbe,
  type DecisionEvent,
  type DecisionListResponse,
  type EvidenceOrigin,
  type EvidenceStrength,
  type FlowProjection,
  type IndexResponse,
  type MapEvidence,
  type MapResponse,
  type MessageSample,
  type MonthlyVolume,
  type PartitionGroupSummary,
  type PolicyBindingStatus,
  type PolicyEvidence,
  type PolicyReviewBinding,
  type ProtectionProjection,
  type SourceDetailResponse,
  type SourceProjection,
  type SyncProjection,
  type SyncResponse,
  type TargetSummary,
  type WriteResponse,
} from "./types";

const EVIDENCE_STRENGTHS = ["strong", "medium", "weak"] as const;
const EVIDENCE_ORIGINS = [
  "record",
  "sender",
  "authentication",
  "subject",
  "label",
  "category",
  "list",
  "unsubscribe",
  "aggregation",
] as const;
const TARGET_KINDS = ["source", "flow", "message", "sender", "label"] as const;
const ANCHOR_KINDS = ["flow", "message", "sender"] as const;

function isObject(value: unknown): value is object {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isUnknownArray(value: unknown): value is unknown[] {
  return Array.isArray(value);
}

function field(value: object, key: string): unknown {
  return Reflect.get(value, key);
}

function hasExactKeys(value: unknown, expected: readonly string[]): value is object {
  if (!isObject(value)) return false;
  const actual = Object.keys(value).sort();
  const wanted = [...expected].sort();
  return actual.length === wanted.length && actual.every((key, index) => key === wanted[index]);
}

function isString(value: unknown): value is string {
  return typeof value === "string";
}

function isNonEmptyString(value: unknown): value is string {
  return isString(value) && value.length > 0;
}

function isBoolean(value: unknown): value is boolean {
  return typeof value === "boolean";
}

function isNonNegativeInteger(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value) && value >= 0;
}

function isPositiveInteger(value: unknown): value is number {
  return isNonNegativeInteger(value) && value > 0;
}

function matchesPattern(value: unknown, pattern: RegExp): value is string {
  return isString(value) && pattern.test(value);
}

function isShortArray(value: unknown, maximum: number): value is unknown[] {
  return isUnknownArray(value) && value.length <= maximum;
}

function isNullableString(value: unknown): value is string | null {
  return value === null || isString(value);
}

function isNullableErrorCode(value: unknown): value is string | null {
  return value === null || matchesPattern(value, /^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$/);
}

function isDateTime(value: unknown): value is string {
  return (
    isString(value) &&
    value.length <= 64 &&
    /(?:Z|\+00:00)$/.test(value) &&
    !Number.isNaN(Date.parse(value))
  );
}

function isNullableDateTime(value: unknown): value is string | null {
  return value === null || isDateTime(value);
}

function isStringArray(value: unknown): value is string[] {
  return isUnknownArray(value) && value.every(isString);
}

function isArrayOf<T>(value: unknown, guard: (item: unknown) => item is T): value is T[] {
  return isUnknownArray(value) && value.every(guard);
}

function isMember<T extends string>(value: unknown, options: readonly T[]): value is T {
  return isString(value) && options.some((option) => option === value);
}

function isClassificationEvidence(value: unknown): value is ClassificationEvidence {
  return (
    hasExactKeys(value, ["kind", "code", "label", "detail", "strength", "origin"]) &&
    field(value, "kind") === "classification" &&
    isNonEmptyString(field(value, "code")) &&
    isNonEmptyString(field(value, "label")) &&
    isNonEmptyString(field(value, "detail")) &&
    isMember<EvidenceStrength>(field(value, "strength"), EVIDENCE_STRENGTHS) &&
    isMember<EvidenceOrigin>(field(value, "origin"), EVIDENCE_ORIGINS)
  );
}

function isPolicyEvidence(value: unknown): value is PolicyEvidence {
  return (
    hasExactKeys(value, ["kind", "code", "decisionId"]) &&
    field(value, "kind") === "policy" &&
    isMember(field(value, "code"), POLICY_EVIDENCE_CODES) &&
    isNonEmptyString(field(value, "decisionId"))
  );
}

function isMapEvidence(value: unknown): value is MapEvidence {
  return isClassificationEvidence(value) || isPolicyEvidence(value);
}

function isProtection(value: unknown): value is ProtectionProjection {
  return (
    hasExactKeys(value, [
      "automatic",
      "effective",
      "protected",
      "reviewRequired",
      "hardExcluded",
      "reasons",
    ]) &&
    isMember(field(value, "automatic"), PROTECCIONES) &&
    isMember(field(value, "effective"), PROTECCIONES) &&
    isBoolean(field(value, "protected")) &&
    isBoolean(field(value, "reviewRequired")) &&
    isBoolean(field(value, "hardExcluded")) &&
    isArrayOf(field(value, "reasons"), (item): item is (typeof PROTECTION_REASONS)[number] =>
      isMember(item, PROTECTION_REASONS),
    )
  );
}

export function isSyncProjection(value: unknown): value is SyncProjection {
  const state = isObject(value) ? field(value, "state") : null;
  const partial = isObject(value) ? field(value, "partial") : null;
  return (
    hasExactKeys(value, [
      "state",
      "mode",
      "processedCount",
      "startedAt",
      "updatedAt",
      "errorCode",
      "partial",
    ]) &&
    isMember(state, SYNC_STATES) &&
    (field(value, "mode") === null || field(value, "mode") === "full" || field(value, "mode") === "partial") &&
    isNonNegativeInteger(field(value, "processedCount")) &&
    isNullableDateTime(field(value, "startedAt")) &&
    isNullableDateTime(field(value, "updatedAt")) &&
    isNullableErrorCode(field(value, "errorCode")) &&
    isBoolean(partial) &&
    partial === (state !== "completed")
  );
}

function isMonthlyVolume(value: unknown): value is MonthlyVolume {
  return (
    hasExactKeys(value, ["month", "messageCount", "totalBytes"]) &&
    matchesPattern(field(value, "month"), /^\d{4}-(?:0[1-9]|1[0-2])$/) &&
    isNonNegativeInteger(field(value, "messageCount")) &&
    isNonNegativeInteger(field(value, "totalBytes"))
  );
}

function isFlow(value: unknown): value is FlowProjection {
  return (
    hasExactKeys(value, [
      "id",
      "sourceId",
      "automaticFlowId",
      "automaticDisplayName",
      "effectiveDisplayName",
      "automaticIntention",
      "effectiveIntention",
      "subscription",
      "automaticConfidence",
      "effectiveConfidence",
      "messageCount",
      "protectedMessageCount",
      "reviewRequiredMessageCount",
      "hardExcludedMessageCount",
      "totalBytes",
      "firstSeen",
      "lastSeen",
      "protection",
      "automaticEvidence",
      "effectiveEvidence",
      "decisionIds",
      "structuralDecisionIds",
    ]) &&
    isNonEmptyString(field(value, "id")) &&
    isNonEmptyString(field(value, "sourceId")) &&
    isNonEmptyString(field(value, "automaticFlowId")) &&
    isNonEmptyString(field(value, "automaticDisplayName")) &&
    isNonEmptyString(field(value, "effectiveDisplayName")) &&
    isMember(field(value, "automaticIntention"), INTENCIONES) &&
    isMember(field(value, "effectiveIntention"), INTENCIONES) &&
    isMember(field(value, "subscription"), SUSCRIPCIONES) &&
    isMember(field(value, "automaticConfidence"), CONFIANZAS) &&
    isMember(field(value, "effectiveConfidence"), CONFIANZAS) &&
    isNonNegativeInteger(field(value, "messageCount")) &&
    isNonNegativeInteger(field(value, "protectedMessageCount")) &&
    isNonNegativeInteger(field(value, "reviewRequiredMessageCount")) &&
    isNonNegativeInteger(field(value, "hardExcludedMessageCount")) &&
    isNonNegativeInteger(field(value, "totalBytes")) &&
    isDateTime(field(value, "firstSeen")) &&
    isDateTime(field(value, "lastSeen")) &&
    isProtection(field(value, "protection")) &&
    isArrayOf(field(value, "automaticEvidence"), isClassificationEvidence) &&
    isArrayOf(field(value, "effectiveEvidence"), isMapEvidence) &&
    isStringArray(field(value, "decisionIds")) &&
    isStringArray(field(value, "structuralDecisionIds"))
  );
}

export function isSource(value: unknown): value is SourceProjection {
  return (
    hasExactKeys(value, [
      "id",
      "automaticSourceIds",
      "automaticDisplayName",
      "effectiveDisplayName",
      "automaticRubro",
      "effectiveRubro",
      "automaticConfidence",
      "effectiveConfidence",
      "messageCount",
      "flowCount",
      "protectedMessageCount",
      "reviewRequiredMessageCount",
      "hardExcludedMessageCount",
      "totalBytes",
      "firstSeen",
      "lastSeen",
      "senders",
      "domains",
      "monthlyVolume",
      "protection",
      "automaticEvidence",
      "effectiveEvidence",
      "decisionIds",
      "structuralDecisionIds",
      "flows",
    ]) &&
    isNonEmptyString(field(value, "id")) &&
    isStringArray(field(value, "automaticSourceIds")) &&
    isNonEmptyString(field(value, "automaticDisplayName")) &&
    isNonEmptyString(field(value, "effectiveDisplayName")) &&
    isMember(field(value, "automaticRubro"), RUBROS) &&
    isMember(field(value, "effectiveRubro"), RUBROS) &&
    isMember(field(value, "automaticConfidence"), CONFIANZAS) &&
    isMember(field(value, "effectiveConfidence"), CONFIANZAS) &&
    isNonNegativeInteger(field(value, "messageCount")) &&
    isNonNegativeInteger(field(value, "flowCount")) &&
    isNonNegativeInteger(field(value, "protectedMessageCount")) &&
    isNonNegativeInteger(field(value, "reviewRequiredMessageCount")) &&
    isNonNegativeInteger(field(value, "hardExcludedMessageCount")) &&
    isNonNegativeInteger(field(value, "totalBytes")) &&
    isDateTime(field(value, "firstSeen")) &&
    isDateTime(field(value, "lastSeen")) &&
    isStringArray(field(value, "senders")) &&
    isStringArray(field(value, "domains")) &&
    isArrayOf(field(value, "monthlyVolume"), isMonthlyVolume) &&
    isProtection(field(value, "protection")) &&
    isArrayOf(field(value, "automaticEvidence"), isClassificationEvidence) &&
    isArrayOf(field(value, "effectiveEvidence"), isMapEvidence) &&
    isStringArray(field(value, "decisionIds")) &&
    isStringArray(field(value, "structuralDecisionIds")) &&
    isArrayOf(field(value, "flows"), isFlow)
  );
}

function isMapSummary(value: unknown): boolean {
  return (
    hasExactKeys(value, [
      "messageCount",
      "sourceCount",
      "flowCount",
      "protectedMessageCount",
      "reviewRequiredMessageCount",
      "hardExcludedMessageCount",
      "totalBytes",
      "firstSeen",
      "lastSeen",
    ]) &&
    isNonNegativeInteger(field(value, "messageCount")) &&
    isNonNegativeInteger(field(value, "sourceCount")) &&
    isNonNegativeInteger(field(value, "flowCount")) &&
    isNonNegativeInteger(field(value, "protectedMessageCount")) &&
    isNonNegativeInteger(field(value, "reviewRequiredMessageCount")) &&
    isNonNegativeInteger(field(value, "hardExcludedMessageCount")) &&
    isNonNegativeInteger(field(value, "totalBytes")) &&
    isNullableDateTime(field(value, "firstSeen")) &&
    isNullableDateTime(field(value, "lastSeen"))
  );
}

function isReviewBinding(value: unknown): value is PolicyReviewBinding {
  return (
    hasExactKeys(value, ["decisionId", "status", "currentEffectiveIds"]) &&
    isNonEmptyString(field(value, "decisionId")) &&
    isMember(field(value, "status"), REVIEW_BINDING_STATES) &&
    isStringArray(field(value, "currentEffectiveIds"))
  );
}

function isPolicyReview(value: unknown): boolean {
  return (
    hasExactKeys(value, ["total", "bindings"]) &&
    isNonNegativeInteger(field(value, "total")) &&
    isArrayOf(field(value, "bindings"), isReviewBinding)
  );
}

export function isContextProbe(value: unknown): value is ContextProbe {
  const account = isObject(value) ? field(value, "account") : null;
  const capabilities = isObject(value) ? field(value, "capabilities") : null;
  return (
    hasExactKeys(value, ["contractVersion", "dataMode", "appVersion", "account", "capabilities"]) &&
    isNonNegativeInteger(field(value, "contractVersion")) &&
    isString(field(value, "dataMode")) &&
    isNonEmptyString(field(value, "appVersion")) &&
    hasExactKeys(account, ["state", "displayAddress"]) &&
    isString(field(account, "state")) &&
    isNullableString(field(account, "displayAddress")) &&
    hasExactKeys(capabilities, [
      "mapRead",
      "policyWrite",
      "policyUndo",
      "gmailConnection",
      "oauth",
      "externalNetwork",
      "realData",
      "syncControl",
      "cleanupPlan",
      "messageMutation",
      "unsubscribe",
      "execute",
    ]) &&
    [
      "mapRead",
      "policyWrite",
      "policyUndo",
      "gmailConnection",
      "oauth",
      "externalNetwork",
      "realData",
      "syncControl",
      "cleanupPlan",
      "messageMutation",
      "unsubscribe",
      "execute",
    ].every((key) => isBoolean(field(capabilities, key)))
  );
}

export function isConnectionResponse(value: unknown): value is ConnectionResponse {
  const capabilities = isObject(value) ? field(value, "capabilities") : null;
  return (
    hasExactKeys(value, ["contractVersion", "dataMode", "state", "displayAddress", "capabilities"]) &&
    field(value, "contractVersion") === 1 &&
    field(value, "dataMode") === "synthetic" &&
    field(value, "state") === "synthetic" &&
    field(value, "displayAddress") === null &&
    hasExactKeys(capabilities, ["gmailConnection", "oauth", "externalNetwork", "realData"]) &&
    field(capabilities, "gmailConnection") === false &&
    field(capabilities, "oauth") === false &&
    field(capabilities, "externalNetwork") === false &&
    field(capabilities, "realData") === false
  );
}

export function isSyncResponse(value: unknown): value is SyncResponse {
  if (!isObject(value)) return false;
  const projection = {
    state: field(value, "state"),
    mode: field(value, "mode"),
    processedCount: field(value, "processedCount"),
    startedAt: field(value, "startedAt"),
    updatedAt: field(value, "updatedAt"),
    errorCode: field(value, "errorCode"),
    partial: field(value, "partial"),
  };
  return (
    hasExactKeys(value, [
      "contractVersion",
      "dataMode",
      "state",
      "mode",
      "processedCount",
      "startedAt",
      "updatedAt",
      "errorCode",
      "partial",
    ]) &&
    field(value, "contractVersion") === 1 &&
    field(value, "dataMode") === "synthetic" &&
    isSyncProjection(projection)
  );
}

export function isIndexResponse(value: unknown): value is IndexResponse {
  return (
    hasExactKeys(value, [
      "contractVersion",
      "dataMode",
      "state",
      "fixtureVersion",
      "schemaVersion",
      "messageCount",
      "partial",
      "canDelete",
    ]) &&
    field(value, "contractVersion") === 1 &&
    field(value, "dataMode") === "synthetic" &&
    field(value, "state") === "synthetic_fixture" &&
    isNonEmptyString(field(value, "fixtureVersion")) &&
    isNonNegativeInteger(field(value, "schemaVersion")) &&
    isNonNegativeInteger(field(value, "messageCount")) &&
    isBoolean(field(value, "partial")) &&
    field(value, "canDelete") === false
  );
}

export function isMapResponse(value: unknown): value is MapResponse {
  return (
    hasExactKeys(value, [
      "contractVersion",
      "dataMode",
      "mapRevision",
      "policyRevision",
      "sync",
      "summary",
      "policyReview",
      "sources",
    ]) &&
    field(value, "contractVersion") === 1 &&
    field(value, "dataMode") === "synthetic" &&
    matchesPattern(field(value, "mapRevision"), /^map-v1-[0-9a-f]{64}$/) &&
    isNonNegativeInteger(field(value, "policyRevision")) &&
    isSyncProjection(field(value, "sync")) &&
    isMapSummary(field(value, "summary")) &&
    isPolicyReview(field(value, "policyReview")) &&
    isArrayOf(field(value, "sources"), isSource)
  );
}

function isMessageSample(value: unknown): value is MessageSample {
  return (
    hasExactKeys(value, [
      "id",
      "receivedAt",
      "senderName",
      "senderAddress",
      "subject",
      "labelIds",
      "category",
      "sizeEstimateBytes",
      "sourceId",
      "flowId",
      "automaticRubro",
      "effectiveRubro",
      "automaticIntention",
      "effectiveIntention",
      "subscription",
      "automaticConfidence",
      "effectiveConfidence",
      "protection",
    ]) &&
    isNonEmptyString(field(value, "id")) &&
    isDateTime(field(value, "receivedAt")) &&
    isNullableString(field(value, "senderName")) &&
    isNullableString(field(value, "senderAddress")) &&
    isNullableString(field(value, "subject")) &&
    isStringArray(field(value, "labelIds")) &&
    isNullableString(field(value, "category")) &&
    isNonNegativeInteger(field(value, "sizeEstimateBytes")) &&
    isNonEmptyString(field(value, "sourceId")) &&
    isNonEmptyString(field(value, "flowId")) &&
    isMember(field(value, "automaticRubro"), RUBROS) &&
    isMember(field(value, "effectiveRubro"), RUBROS) &&
    isMember(field(value, "automaticIntention"), INTENCIONES) &&
    isMember(field(value, "effectiveIntention"), INTENCIONES) &&
    isMember(field(value, "subscription"), SUSCRIPCIONES) &&
    isMember(field(value, "automaticConfidence"), CONFIANZAS) &&
    isMember(field(value, "effectiveConfidence"), CONFIANZAS) &&
    isProtection(field(value, "protection"))
  );
}

export function isSourceDetailResponse(value: unknown): value is SourceDetailResponse {
  if (!isObject(value)) return false;
  const sourceKeys = [
    "id",
    "automaticSourceIds",
    "automaticDisplayName",
    "effectiveDisplayName",
    "automaticRubro",
    "effectiveRubro",
    "automaticConfidence",
    "effectiveConfidence",
    "messageCount",
    "flowCount",
    "protectedMessageCount",
    "reviewRequiredMessageCount",
    "hardExcludedMessageCount",
    "totalBytes",
    "firstSeen",
    "lastSeen",
    "senders",
    "domains",
    "monthlyVolume",
    "protection",
    "automaticEvidence",
    "effectiveEvidence",
    "decisionIds",
    "structuralDecisionIds",
    "flows",
  ];
  const source = Object.fromEntries(sourceKeys.map((key) => [key, field(value, key)]));
  return (
    hasExactKeys(value, [...sourceKeys, "contractVersion", "dataMode", "recentMessages"]) &&
    field(value, "contractVersion") === 1 &&
    field(value, "dataMode") === "synthetic" &&
    isSource(source) &&
    isArrayOf(field(value, "recentMessages"), isMessageSample) &&
    isShortArray(field(value, "recentMessages"), 5)
  );
}

function isPolicyBindingStatus(value: unknown): value is PolicyBindingStatus {
  return isMember(value, BINDING_STATES);
}

function hasDecisionBase(value: object, undo: boolean): boolean {
  return (
    (undo ? field(value, "decisionId") === null : isNonEmptyString(field(value, "decisionId"))) &&
    isNonEmptyString(field(value, "commandId")) &&
    isPositiveInteger(field(value, "revision")) &&
    isDateTime(field(value, "occurredAt")) &&
    isBoolean(field(value, "active")) &&
    isBoolean(field(value, "undoable")) &&
    (field(value, "targetDecisionId") === null || isNonEmptyString(field(value, "targetDecisionId"))) &&
    isStringArray(field(value, "supersedesDecisionIds")) &&
    (field(value, "bindingStatus") === null || isPolicyBindingStatus(field(value, "bindingStatus"))) &&
    isStringArray(field(value, "currentTargetIds"))
  );
}

const DECISION_BASE_KEYS = [
  "decisionId",
  "commandId",
  "type",
  "revision",
  "occurredAt",
  "active",
  "undoable",
  "targetDecisionId",
  "supersedesDecisionIds",
  "bindingStatus",
  "currentTargetIds",
] as const;

function isTargetSummary(value: unknown): value is TargetSummary {
  return (
    hasExactKeys(value, ["kind", "observedEffectiveId", "observedSourceIds", "observedFlowIds"]) &&
    isMember(field(value, "kind"), TARGET_KINDS) &&
    (field(value, "observedEffectiveId") === null || isNonEmptyString(field(value, "observedEffectiveId"))) &&
    isStringArray(field(value, "observedSourceIds")) &&
    isStringArray(field(value, "observedFlowIds"))
  );
}

function isPartitionGroupSummary(value: unknown): value is PartitionGroupSummary {
  return (
    hasExactKeys(value, [
      "groupIndex",
      "anchorCount",
      "anchorKinds",
      "observedSourceIds",
      "observedFlowIds",
    ]) &&
    isNonNegativeInteger(field(value, "groupIndex")) &&
    isNonNegativeInteger(field(value, "anchorCount")) &&
    isArrayOf(field(value, "anchorKinds"), (item): item is (typeof ANCHOR_KINDS)[number] =>
      isMember(item, ANCHOR_KINDS),
    ) &&
    isStringArray(field(value, "observedSourceIds")) &&
    isStringArray(field(value, "observedFlowIds"))
  );
}

function isDecisionEvent(value: unknown): value is DecisionEvent {
  if (!isObject(value)) return false;
  const type = field(value, "type");
  if (!isString(type)) return false;
  const undo = type === "undoPolicy";
  if (!hasDecisionBase(value, undo)) return false;
  switch (type) {
    case "setSourceDisplayName":
      return (
        hasExactKeys(value, [...DECISION_BASE_KEYS, "sourceId", "displayName"]) &&
        isNonEmptyString(field(value, "sourceId")) &&
        isNonEmptyString(field(value, "displayName"))
      );
    case "setSourceRubro":
      return (
        hasExactKeys(value, [...DECISION_BASE_KEYS, "sourceId", "rubro"]) &&
        isNonEmptyString(field(value, "sourceId")) &&
        isMember(field(value, "rubro"), RUBROS)
      );
    case "setFlowDisplayName":
      return (
        hasExactKeys(value, [...DECISION_BASE_KEYS, "flowId", "displayName"]) &&
        isNonEmptyString(field(value, "flowId")) &&
        isNonEmptyString(field(value, "displayName"))
      );
    case "setFlowIntention":
      return (
        hasExactKeys(value, [...DECISION_BASE_KEYS, "flowId", "intention"]) &&
        isNonEmptyString(field(value, "flowId")) &&
        isMember(field(value, "intention"), INTENCIONES)
      );
    case "mergeSources":
      return (
        hasExactKeys(value, [...DECISION_BASE_KEYS, "sourceIds"]) &&
        isStringArray(field(value, "sourceIds"))
      );
    case "partitionSource":
      return (
        hasExactKeys(value, [...DECISION_BASE_KEYS, "sourceId", "groupCount", "groups"]) &&
        isNonEmptyString(field(value, "sourceId")) &&
        isNonNegativeInteger(field(value, "groupCount")) &&
        isArrayOf(field(value, "groups"), isPartitionGroupSummary)
      );
    case "protectTarget":
      return (
        hasExactKeys(value, [...DECISION_BASE_KEYS, "target"]) &&
        isTargetSummary(field(value, "target"))
      );
    case "undoPolicy":
      return (
        hasExactKeys(value, DECISION_BASE_KEYS) &&
        isNonEmptyString(field(value, "targetDecisionId"))
      );
    default:
      return false;
  }
}

export function isDecisionListResponse(value: unknown): value is DecisionListResponse {
  return (
    hasExactKeys(value, ["contractVersion", "dataMode", "policyRevision", "events"]) &&
    field(value, "contractVersion") === 1 &&
    field(value, "dataMode") === "synthetic" &&
    isNonNegativeInteger(field(value, "policyRevision")) &&
    isArrayOf(field(value, "events"), isDecisionEvent)
  );
}

export function isWriteResponse(value: unknown): value is WriteResponse {
  return (
    hasExactKeys(value, [
      "contractVersion",
      "dataMode",
      "status",
      "replayed",
      "decisionId",
      "policyRevision",
      "mapRevision",
      "bindingStatus",
    ]) &&
    field(value, "contractVersion") === 1 &&
    field(value, "dataMode") === "synthetic" &&
    field(value, "status") === "applied" &&
    isBoolean(field(value, "replayed")) &&
    isNonEmptyString(field(value, "decisionId")) &&
    isNonNegativeInteger(field(value, "policyRevision")) &&
    matchesPattern(field(value, "mapRevision"), /^map-v1-[0-9a-f]{64}$/) &&
    (field(value, "bindingStatus") === null || isPolicyBindingStatus(field(value, "bindingStatus")))
  );
}
