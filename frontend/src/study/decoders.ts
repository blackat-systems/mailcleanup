import {
  EVENT_TYPES,
  EXCLUSION_REASONS,
  INVENTORY_STATES,
  MEMBER_FILTERS,
  PLAN_STATES,
  STUDY_ERROR_CODES,
  TARGET_KINDS,
  WARNING_CODES,
  type CancelReceipt,
  type CreateReceipt,
  type EventsResponse,
  type ExclusionReason,
  type MessagesResponse,
  type PlanDetail,
  type PlanEvent,
  type PlanMember,
  type PlanSample,
  type PlanSelection,
  type PlanState,
  type PlanSummary,
  type PlansResponse,
  type PublicTarget,
  type RevalidateReceipt,
  type SelectionTarget,
  type StudyContext,
  type StudyErrorCode,
  type StudyEnvelope,
  type TargetKind,
  type TargetsResponse,
  type TargetSnapshot,
  type TemporalFilter,
} from "./types";

type UnknownRecord = Record<string, unknown>;
type Guard<T> = (value: unknown) => value is T;

const UTF8 = new TextEncoder();
const UUID_V4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/u;
const MAP_REVISION = /^map-v1-[0-9a-f]{64}$/u;
const SOURCE_ID = /^effective-source-v1-[0-9a-f]{24}$/u;
const FLOW_ID = /^effective-flow-v1-[0-9a-f]{24}$/u;
const SENDER_ID = /^sender-v1-[0-9a-f]{64}$/u;
const LABEL_ID = /^label-v1-[0-9a-f]{64}$/u;
const MESSAGE_ID = /^message-v1-[0-9a-f]{64}$/u;
const PLAN_ID = /^cleanup-plan-v1-([0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})$/u;
const RFC3339_UTC = /^\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d{1,6})?Z$/u;
const CIVIL_DATE = /^(\d{4})-(\d{2})-(\d{2})$/u;
const CURSOR = /^[\x21-\x7e]{1,1024}$/u;
const SYNTHETIC_ADDRESS = /^[^@\s]+@[^@\s]+\.example$/iu;
const TIMESTAMP_PARTS = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,6}))?Z$/u;

function timestampMicros(value: string): bigint {
  const match = TIMESTAMP_PARTS.exec(value);
  if (!match) throw new RangeError("invalid timestamp");
  const date = new Date(0);
  date.setUTCHours(Number(match[4]), Number(match[5]), Number(match[6]), 0);
  date.setUTCFullYear(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
  const fractionalMicros = BigInt((match[7] ?? "").padEnd(6, "0"));
  return BigInt(date.getTime()) * 1000n + fractionalMicros;
}

export function compareTimestamps(left: string, right: string): number {
  const leftValue = timestampMicros(left);
  const rightValue = timestampMicros(right);
  return leftValue < rightValue ? -1 : leftValue > rightValue ? 1 : 0;
}

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasExactKeys(value: UnknownRecord, keys: readonly string[]): boolean {
  const actual = Object.keys(value).sort();
  const expected = [...keys].sort();
  return actual.length === expected.length && actual.every((key, index) => key === expected[index]);
}

function isOneOf<const T extends readonly string[]>(value: unknown, values: T): value is T[number] {
  return typeof value === "string" && values.some((candidate) => candidate === value);
}

function isSafeInteger(value: unknown, minimum = 0, maximum = Number.MAX_SAFE_INTEGER): value is number {
  return typeof value === "number" && Number.isSafeInteger(value) && value >= minimum && value <= maximum;
}

function isVisibleText(value: unknown, allowEmpty = false): value is string {
  return typeof value === "string" && (allowEmpty || value.length > 0) && UTF8.encode(value).byteLength <= 16384;
}

function isNullableVisibleText(value: unknown): value is string | null {
  return value === null || isVisibleText(value, true);
}

function isSyntheticAddress(value: unknown): value is string {
  return typeof value === "string" && SYNTHETIC_ADDRESS.test(value) && UTF8.encode(value).byteLength <= 16384;
}

function isNullableSyntheticAddress(value: unknown): value is string | null {
  return value === null || isSyntheticAddress(value);
}

function isPattern(value: unknown, pattern: RegExp): value is string {
  return typeof value === "string" && pattern.test(value);
}

function isMapRevision(value: unknown): value is string {
  return isPattern(value, MAP_REVISION);
}

export function isPlanId(value: unknown): value is string {
  if (!isPattern(value, PLAN_ID)) return false;
  const match = PLAN_ID.exec(value);
  return match !== null && UUID_V4.test(match[1] ?? "");
}

function isTimestamp(value: unknown): value is string {
  if (typeof value !== "string" || !RFC3339_UTC.test(value)) return false;
  return isCivilDate(value.slice(0, 10));
}

export function isCivilDate(value: unknown): value is string {
  if (typeof value !== "string") return false;
  const match = CIVIL_DATE.exec(value);
  if (!match) return false;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  if (year < 1) return false;
  const date = new Date(0);
  date.setUTCHours(0, 0, 0, 0);
  date.setUTCFullYear(year, month - 1, day);
  return date.getUTCFullYear() === year && date.getUTCMonth() === month - 1 && date.getUTCDate() === day;
}

function isCursor(value: unknown): value is string | null {
  return value === null || (typeof value === "string" && CURSOR.test(value));
}

function isArrayOf<T>(value: unknown, guard: Guard<T>, maximum = Number.MAX_SAFE_INTEGER): value is T[] {
  return Array.isArray(value) && value.length <= maximum && value.every(guard);
}

function isUnique<T>(items: readonly T[], key: (item: T) => string): boolean {
  return new Set(items.map(key)).size === items.length;
}

function isContractOrdered<T extends string>(items: readonly T[], order: readonly T[]): boolean {
  let previous = -1;
  const seen = new Set<T>();
  for (const item of items) {
    const rank = order.indexOf(item);
    if (rank < 0 || rank <= previous || seen.has(item)) return false;
    seen.add(item);
    previous = rank;
  }
  return true;
}

function isEnvelope(value: UnknownRecord): value is UnknownRecord & StudyEnvelope {
  return value.contractVersion === 1 && value.dataMode === "synthetic" && value.canExecute === false;
}

const LIMITS = {
  maxTargets: 100,
  maxExcludedLabels: 100,
  maxConsideredMessages: 100000,
  maxKeepLatestPerFlow: 10000,
  maxMessageSizeEstimateBytes: 2147483647,
  maxAggregateSizeEstimateBytes: 214748364700000,
  maxTargetPageSize: 100,
  maxPlanPageSize: 100,
  maxMessagePageSize: 500,
  maxEventPageSize: 100,
  maxCursorChars: 1024,
  maxQueryStringBytes: 4096,
  maxVisibleMetadataBytes: 16384,
  maxRequestBodyBytes: 65536,
  maxIncludedSamples: 5,
  maxExcludedSamples: 5,
} as const;

const CAPABILITIES = {
  studyRead: true,
  targetRead: true,
  planCreate: true,
  planRevalidate: true,
  planCancel: true,
  systemLabelFilter: true,
  customLabelFilter: false,
  gmailConnection: false,
  oauth: false,
  externalNetwork: false,
  realData: false,
  messageMutation: false,
  unsubscribe: false,
  execute: false,
} as const;

function hasExactConstants(value: unknown, constants: UnknownRecord): boolean {
  if (!isRecord(value) || !hasExactKeys(value, Object.keys(constants))) return false;
  return Object.entries(constants).every(([key, expected]) => value[key] === expected);
}

function isAvailability(value: unknown): boolean {
  if (!isRecord(value) || !hasExactKeys(value, [
    "accountAvailable", "inventoryState", "completeSnapshotAvailable", "currentMapRevision",
    "currentPolicyRevision", "targetReadAvailable", "planCreateAvailable",
    "planRevalidateAvailable", "blockerCodes",
  ])) return false;
  const inventory = value.inventoryState;
  const blockers = value.blockerCodes;
  if (!(inventory === null || isOneOf(inventory, INVENTORY_STATES))) return false;
  if (!Array.isArray(blockers) || !isContractOrdered(blockers, [
    "account_unavailable", "inventory_incomplete", "study_unavailable",
  ] as const)) return false;
  if (
    typeof value.accountAvailable !== "boolean" ||
    typeof value.completeSnapshotAvailable !== "boolean" ||
    !(value.currentMapRevision === null || isMapRevision(value.currentMapRevision)) ||
    !(value.currentPolicyRevision === null || isSafeInteger(value.currentPolicyRevision)) ||
    typeof value.targetReadAvailable !== "boolean" ||
    typeof value.planCreateAvailable !== "boolean" ||
    typeof value.planRevalidateAvailable !== "boolean"
  ) return false;
  const allAvailable = value.targetReadAvailable && value.planCreateAvailable && value.planRevalidateAvailable;
  const noneAvailable = !value.targetReadAvailable && !value.planCreateAvailable && !value.planRevalidateAvailable;
  if (!value.accountAvailable) {
    return inventory === null && !value.completeSnapshotAvailable && value.currentMapRevision === null &&
      value.currentPolicyRevision === null && noneAvailable && blockers.length === 1 && blockers[0] === "account_unavailable";
  }
  if (inventory !== "completed") {
    return inventory !== null && !value.completeSnapshotAvailable && value.currentMapRevision === null && value.currentPolicyRevision === null && noneAvailable &&
      blockers.length === 1 && blockers[0] === "inventory_incomplete";
  }
  if (!value.completeSnapshotAvailable) {
    return value.currentMapRevision === null && value.currentPolicyRevision === null && noneAvailable &&
      blockers.length === 1 && blockers[0] === "study_unavailable";
  }
  return value.currentMapRevision !== null && value.currentPolicyRevision !== null && allAvailable && blockers.length === 0;
}

export function isStudyContext(value: unknown): value is StudyContext {
  return isRecord(value) && hasExactKeys(value, [
    "contractVersion", "dataMode", "canExecute", "timeZone", "planValiditySeconds",
    "limits", "capabilities", "availability",
  ]) && isEnvelope(value) && value.timeZone === "America/Argentina/Cordoba" &&
    value.planValiditySeconds === 86400 && hasExactConstants(value.limits, LIMITS) &&
    hasExactConstants(value.capabilities, CAPABILITIES) && isAvailability(value.availability);
}

function isTarget(value: unknown): value is PublicTarget {
  if (!isRecord(value) || !isOneOf(value.kind, TARGET_KINDS)) return false;
  if (value.kind === "source") {
    return hasExactKeys(value, ["kind", "targetId", "displayName", "messageCount"]) &&
      isPattern(value.targetId, SOURCE_ID) && isVisibleText(value.displayName) && isSafeInteger(value.messageCount, 1);
  }
  if (value.kind === "flow") {
    return hasExactKeys(value, ["kind", "targetId", "sourceId", "displayName", "messageCount"]) &&
      isPattern(value.targetId, FLOW_ID) && isPattern(value.sourceId, SOURCE_ID) &&
      isVisibleText(value.displayName) && isSafeInteger(value.messageCount, 1);
  }
  if (value.kind === "sender") {
    return hasExactKeys(value, ["kind", "targetId", "displayAddress", "messageCount"]) &&
      isPattern(value.targetId, SENDER_ID) && isSyntheticAddress(value.displayAddress) && isSafeInteger(value.messageCount, 1);
  }
  return hasExactKeys(value, ["kind", "targetId", "displayName", "messageCount"]) &&
    isPattern(value.targetId, LABEL_ID) && isVisibleText(value.displayName) && isSafeInteger(value.messageCount, 1);
}

function compareCodePoints(left: string, right: string): number {
  const leftPoints = Array.from(left, (value) => value.codePointAt(0)!);
  const rightPoints = Array.from(right, (value) => value.codePointAt(0)!);
  const length = Math.min(leftPoints.length, rightPoints.length);
  for (let index = 0; index < length; index += 1) {
    if (leftPoints[index] !== rightPoints[index]) return leftPoints[index]! - rightPoints[index]!;
  }
  return leftPoints.length - rightPoints.length;
}

// Unicode full case folding has no browser primitive. This compact table contains
// every code point whose Python casefold() result differs from lowercase; all
// remaining code points use the platform Unicode lowercase mapping.
const CASEFOLD_DATA = `
b5:3bc;df:73,73;149:2bc,6e;17f:73;1f0:6a,30c;345:3b9;390:3b9,308,301;3b0:3c5,308,301;3c2:3c3;3d0:3b2;3d1:3b8;3d5:3c6;3d6:3c0;3f0:3ba;3f1:3c1;3f5:3b5;587:565,582;
13a0:13a0;13a1:13a1;13a2:13a2;13a3:13a3;13a4:13a4;13a5:13a5;13a6:13a6;13a7:13a7;13a8:13a8;13a9:13a9;13aa:13aa;13ab:13ab;13ac:13ac;13ad:13ad;13ae:13ae;13af:13af;13b0:13b0;13b1:13b1;13b2:13b2;13b3:13b3;13b4:13b4;13b5:13b5;13b6:13b6;13b7:13b7;13b8:13b8;13b9:13b9;13ba:13ba;13bb:13bb;13bc:13bc;13bd:13bd;13be:13be;13bf:13bf;
13c0:13c0;13c1:13c1;13c2:13c2;13c3:13c3;13c4:13c4;13c5:13c5;13c6:13c6;13c7:13c7;13c8:13c8;13c9:13c9;13ca:13ca;13cb:13cb;13cc:13cc;13cd:13cd;13ce:13ce;13cf:13cf;13d0:13d0;13d1:13d1;13d2:13d2;13d3:13d3;13d4:13d4;13d5:13d5;13d6:13d6;13d7:13d7;13d8:13d8;13d9:13d9;13da:13da;13db:13db;13dc:13dc;13dd:13dd;13de:13de;13df:13df;
13e0:13e0;13e1:13e1;13e2:13e2;13e3:13e3;13e4:13e4;13e5:13e5;13e6:13e6;13e7:13e7;13e8:13e8;13e9:13e9;13ea:13ea;13eb:13eb;13ec:13ec;13ed:13ed;13ee:13ee;13ef:13ef;13f0:13f0;13f1:13f1;13f2:13f2;13f3:13f3;13f4:13f4;13f5:13f5;13f8:13f0;13f9:13f1;13fa:13f2;13fb:13f3;13fc:13f4;13fd:13f5;
1c80:432;1c81:434;1c82:43e;1c83:441;1c84:442;1c85:442;1c86:44a;1c87:463;1c88:a64b;1e96:68,331;1e97:74,308;1e98:77,30a;1e99:79,30a;1e9a:61,2be;1e9b:1e61;1e9e:73,73;1f50:3c5,313;1f52:3c5,313,300;1f54:3c5,313,301;1f56:3c5,313,342;
1f80:1f00,3b9;1f81:1f01,3b9;1f82:1f02,3b9;1f83:1f03,3b9;1f84:1f04,3b9;1f85:1f05,3b9;1f86:1f06,3b9;1f87:1f07,3b9;1f88:1f00,3b9;1f89:1f01,3b9;1f8a:1f02,3b9;1f8b:1f03,3b9;1f8c:1f04,3b9;1f8d:1f05,3b9;1f8e:1f06,3b9;1f8f:1f07,3b9;1f90:1f20,3b9;1f91:1f21,3b9;1f92:1f22,3b9;1f93:1f23,3b9;1f94:1f24,3b9;1f95:1f25,3b9;1f96:1f26,3b9;1f97:1f27,3b9;
1f98:1f20,3b9;1f99:1f21,3b9;1f9a:1f22,3b9;1f9b:1f23,3b9;1f9c:1f24,3b9;1f9d:1f25,3b9;1f9e:1f26,3b9;1f9f:1f27,3b9;1fa0:1f60,3b9;1fa1:1f61,3b9;1fa2:1f62,3b9;1fa3:1f63,3b9;1fa4:1f64,3b9;1fa5:1f65,3b9;1fa6:1f66,3b9;1fa7:1f67,3b9;1fa8:1f60,3b9;1fa9:1f61,3b9;1faa:1f62,3b9;1fab:1f63,3b9;1fac:1f64,3b9;1fad:1f65,3b9;1fae:1f66,3b9;1faf:1f67,3b9;
1fb2:1f70,3b9;1fb3:3b1,3b9;1fb4:3ac,3b9;1fb6:3b1,342;1fb7:3b1,342,3b9;1fbc:3b1,3b9;1fbe:3b9;1fc2:1f74,3b9;1fc3:3b7,3b9;1fc4:3ae,3b9;1fc6:3b7,342;1fc7:3b7,342,3b9;1fcc:3b7,3b9;1fd2:3b9,308,300;1fd3:3b9,308,301;1fd6:3b9,342;1fd7:3b9,308,342;1fe2:3c5,308,300;1fe3:3c5,308,301;1fe4:3c1,313;1fe6:3c5,342;1fe7:3c5,308,342;1ff2:1f7c,3b9;1ff3:3c9,3b9;1ff4:3ce,3b9;1ff6:3c9,342;1ff7:3c9,342,3b9;1ffc:3c9,3b9;
ab70:13a0;ab71:13a1;ab72:13a2;ab73:13a3;ab74:13a4;ab75:13a5;ab76:13a6;ab77:13a7;ab78:13a8;ab79:13a9;ab7a:13aa;ab7b:13ab;ab7c:13ac;ab7d:13ad;ab7e:13ae;ab7f:13af;ab80:13b0;ab81:13b1;ab82:13b2;ab83:13b3;ab84:13b4;ab85:13b5;ab86:13b6;ab87:13b7;ab88:13b8;ab89:13b9;ab8a:13ba;ab8b:13bb;ab8c:13bc;ab8d:13bd;ab8e:13be;ab8f:13bf;
ab90:13c0;ab91:13c1;ab92:13c2;ab93:13c3;ab94:13c4;ab95:13c5;ab96:13c6;ab97:13c7;ab98:13c8;ab99:13c9;ab9a:13ca;ab9b:13cb;ab9c:13cc;ab9d:13cd;ab9e:13ce;ab9f:13cf;aba0:13d0;aba1:13d1;aba2:13d2;aba3:13d3;aba4:13d4;aba5:13d5;aba6:13d6;aba7:13d7;aba8:13d8;aba9:13d9;abaa:13da;abab:13db;abac:13dc;abad:13dd;abae:13de;abaf:13df;
abb0:13e0;abb1:13e1;abb2:13e2;abb3:13e3;abb4:13e4;abb5:13e5;abb6:13e6;abb7:13e7;abb8:13e8;abb9:13e9;abba:13ea;abbb:13eb;abbc:13ec;abbd:13ed;abbe:13ee;abbf:13ef;fb00:66,66;fb01:66,69;fb02:66,6c;fb03:66,66,69;fb04:66,66,6c;fb05:73,74;fb06:73,74;fb13:574,576;fb14:574,565;fb15:574,56b;fb16:57e,576;fb17:574,56d
`.replace(/\s+/gu, "");

const CASEFOLD_OVERRIDES = new Map<number, string>(CASEFOLD_DATA.split(";").map((entry) => {
  const [source, encodedResult] = entry.split(":") as [string, string];
  const result = encodedResult.split(",").map((point) => String.fromCodePoint(Number.parseInt(point, 16))).join("");
  return [Number.parseInt(source, 16), result];
}));

function contractCasefold(value: string): string {
  return Array.from(value, (character) =>
    CASEFOLD_OVERRIDES.get(character.codePointAt(0)!) ?? character.toLowerCase()).join("");
}

export function comparePublicTargets(left: PublicTarget, right: PublicTarget): number {
  const rankDifference = TARGET_KINDS.indexOf(left.kind) - TARGET_KINDS.indexOf(right.kind);
  if (rankDifference !== 0) return rankDifference;
  const leftLabel = contractCasefold(left.kind === "sender" ? left.displayAddress : left.displayName);
  const rightLabel = contractCasefold(right.kind === "sender" ? right.displayAddress : right.displayName);
  const labelDifference = compareCodePoints(leftLabel, rightLabel);
  return labelDifference !== 0 ? labelDifference : compareCodePoints(left.targetId, right.targetId);
}

export function isTargetsResponse(value: unknown): value is TargetsResponse {
  if (!isRecord(value) || !hasExactKeys(value, [
    "contractVersion", "dataMode", "canExecute", "mapRevision", "policyRevision", "kind", "items", "nextCursor",
  ]) || !isEnvelope(value) || !isMapRevision(value.mapRevision) || !isSafeInteger(value.policyRevision) ||
    !(value.kind === null || isOneOf(value.kind, TARGET_KINDS)) || !isArrayOf(value.items, isTarget, 100) || !isCursor(value.nextCursor)) return false;
  const items = value.items;
  if (!isUnique(items, (item) => `${item.kind}:${item.targetId}`)) return false;
  if (value.kind !== null && items.some((item) => item.kind !== value.kind)) return false;
  return items.every((item, index) => index === 0 || comparePublicTargets(items[index - 1]!, item) < 0);
}

function isSelectionTarget(value: unknown): value is SelectionTarget {
  if (!isRecord(value) || !hasExactKeys(value, ["kind", "targetId"])) return false;
  if (value.kind === "source") return isPattern(value.targetId, SOURCE_ID);
  if (value.kind === "flow") return isPattern(value.targetId, FLOW_ID);
  if (value.kind === "sender") return isPattern(value.targetId, SENDER_ID);
  return false;
}

function isTargetSnapshot(value: unknown): value is TargetSnapshot {
  if (!isRecord(value)) return false;
  if (value.kind === "source") return hasExactKeys(value, ["kind", "targetId", "displayName"]) && isPattern(value.targetId, SOURCE_ID) && isVisibleText(value.displayName);
  if (value.kind === "flow") return hasExactKeys(value, ["kind", "targetId", "displayName"]) && isPattern(value.targetId, FLOW_ID) && isVisibleText(value.displayName);
  if (value.kind === "sender") return hasExactKeys(value, ["kind", "targetId", "displayAddress"]) && isPattern(value.targetId, SENDER_ID) && isSyntheticAddress(value.displayAddress);
  return false;
}

function isLabelSnapshot(value: unknown): value is { labelId: string; displayName: string } {
  return isRecord(value) && hasExactKeys(value, ["labelId", "displayName"]) &&
    isPattern(value.labelId, LABEL_ID) && isVisibleText(value.displayName);
}

export function isTemporalFilter(value: unknown): value is TemporalFilter {
  if (!isRecord(value)) return false;
  if (value.kind === "all") return hasExactKeys(value, ["kind"]);
  if (value.kind === "beforeDate") return hasExactKeys(value, ["kind", "date"]) && isCivilDate(value.date);
  if (value.kind === "dateRange") return hasExactKeys(value, ["kind", "onOrAfterDate", "beforeDate"]) &&
    isCivilDate(value.onOrAfterDate) && isCivilDate(value.beforeDate) && value.onOrAfterDate < value.beforeDate;
  if (value.kind === "olderThanDays") return hasExactKeys(value, ["kind", "days"]) && isSafeInteger(value.days, 1, 36500);
  return false;
}

function isPlanSelection(value: unknown): value is PlanSelection {
  if (!isRecord(value) || !hasExactKeys(value, [
    "disposition", "targets", "targetSnapshots", "temporalFilterRequested", "resolvedOnOrAfterUtc",
    "resolvedBeforeUtc", "timeZone", "readState", "excludedLabelIds", "excludedLabelSnapshots", "keepLatestPerFlow",
  ])) return false;
  const excludedLabelIds = value.excludedLabelIds;
  const excludedLabelSnapshots = value.excludedLabelSnapshots;
  if (!(value.disposition === "archive" || value.disposition === "trash") ||
    !isArrayOf(value.targets, isSelectionTarget, 100) || value.targets.length < 1 ||
    !isUnique(value.targets, (item) => `${item.kind}:${item.targetId}`) ||
    !isArrayOf(value.targetSnapshots, isTargetSnapshot, 100) ||
    value.targetSnapshots.length !== value.targets.length ||
    !isTemporalFilter(value.temporalFilterRequested) ||
    !(value.resolvedOnOrAfterUtc === null || isTimestamp(value.resolvedOnOrAfterUtc)) ||
    !(value.resolvedBeforeUtc === null || isTimestamp(value.resolvedBeforeUtc)) ||
    value.timeZone !== "America/Argentina/Cordoba" ||
    !(value.readState === "any" || value.readState === "read" || value.readState === "unread") ||
    !Array.isArray(excludedLabelIds) || excludedLabelIds.length > 100 ||
    !excludedLabelIds.every((id) => isPattern(id, LABEL_ID)) || new Set(excludedLabelIds).size !== excludedLabelIds.length ||
    !isArrayOf(excludedLabelSnapshots, isLabelSnapshot, 100) || excludedLabelSnapshots.length !== excludedLabelIds.length ||
    !isSafeInteger(value.keepLatestPerFlow, 0, 10000)) return false;
  const temporal = value.temporalFilterRequested;
  const temporalBoundsValid = temporal.kind === "all"
    ? value.resolvedOnOrAfterUtc === null && value.resolvedBeforeUtc === null
    : temporal.kind === "dateRange"
      ? value.resolvedOnOrAfterUtc !== null && value.resolvedBeforeUtc !== null &&
        compareTimestamps(value.resolvedOnOrAfterUtc, value.resolvedBeforeUtc) < 0
      : value.resolvedOnOrAfterUtc === null && value.resolvedBeforeUtc !== null;
  if (!temporalBoundsValid) return false;
  const targetKeys = value.targets.map((item) => `${item.kind}:${item.targetId}`);
  const snapshotKeys = value.targetSnapshots.map((item) => `${item.kind}:${item.targetId}`);
  const canonicalTargetKeys = [...targetKeys].sort((left, right) => {
    const leftKind = left.slice(0, left.indexOf(":"));
    const rightKind = right.slice(0, right.indexOf(":"));
    const rank = ["source", "flow", "sender"];
    return rank.indexOf(leftKind) - rank.indexOf(rightKind) || left.localeCompare(right);
  });
  return targetKeys.every((key, index) => key === snapshotKeys[index] && key === canonicalTargetKeys[index]) &&
    excludedLabelIds.every((id, index) => id === excludedLabelSnapshots[index]?.labelId &&
      (index === 0 || excludedLabelIds[index - 1]! < id));
}

const SUMMARY_KEYS = [
  "planId", "planRevision", "state", "createdAt", "expiresAt", "lastRevalidatedAt", "disposition",
  "selectedAtCreationCount", "selectedAtCreationSizeEstimateBytes", "excludedAtCreationCount",
  "excludedAtCreationSizeEstimateBytes", "currentEligibleCount", "currentEligibleSizeEstimateBytes",
  "storageEffect", "effectiveFreedBytes", "canExecute",
] as const;

function hasSummary(value: UnknownRecord): value is UnknownRecord & PlanSummary {
  if (!(isPlanId(value.planId) && isSafeInteger(value.planRevision, 1) && isOneOf(value.state, PLAN_STATES) &&
    isTimestamp(value.createdAt) && isTimestamp(value.expiresAt) &&
    (value.lastRevalidatedAt === null || isTimestamp(value.lastRevalidatedAt)) &&
    (value.disposition === "archive" || value.disposition === "trash") &&
    isSafeInteger(value.selectedAtCreationCount, 0, 100000) &&
    isSafeInteger(value.selectedAtCreationSizeEstimateBytes, 0, 214748364700000) &&
    isSafeInteger(value.excludedAtCreationCount, 0, 100000) &&
    isSafeInteger(value.excludedAtCreationSizeEstimateBytes, 0, 214748364700000) &&
    isSafeInteger(value.currentEligibleCount, 0, 100000) &&
    isSafeInteger(value.currentEligibleSizeEstimateBytes, 0, 214748364700000) &&
    ((value.disposition === "archive" && value.storageEffect === "none") ||
      (value.disposition === "trash" && value.storageEffect === "not_guaranteed")) &&
    value.effectiveFreedBytes === null && value.canExecute === false)) return false;
  const createdAt = timestampMicros(value.createdAt);
  const expiresAt = timestampMicros(value.expiresAt);
  const lastRevalidatedAt = value.lastRevalidatedAt === null ? null : timestampMicros(value.lastRevalidatedAt);
  const selectionReduced = value.currentEligibleCount < value.selectedAtCreationCount;
  const stateCountsValid = value.state === "frozen"
    ? value.currentEligibleCount > 0 && value.currentEligibleCount === value.selectedAtCreationCount
    : value.state === "reduced"
      ? value.currentEligibleCount > 0 && selectionReduced
      : value.state === "invalidated"
        ? value.currentEligibleCount === 0
        : value.currentEligibleCount > 0;
  return expiresAt - createdAt === 86_400_000_000n &&
    (lastRevalidatedAt === null || (lastRevalidatedAt >= createdAt && lastRevalidatedAt < expiresAt)) &&
    value.selectedAtCreationCount + value.excludedAtCreationCount >= 1 &&
    value.selectedAtCreationCount + value.excludedAtCreationCount <= 100000 &&
    value.currentEligibleCount <= value.selectedAtCreationCount &&
    value.selectedAtCreationSizeEstimateBytes <= value.selectedAtCreationCount * 2147483647 &&
    value.excludedAtCreationSizeEstimateBytes <= value.excludedAtCreationCount * 2147483647 &&
    value.currentEligibleSizeEstimateBytes <= value.currentEligibleCount * 2147483647 &&
    value.currentEligibleSizeEstimateBytes <= value.selectedAtCreationSizeEstimateBytes &&
    (value.selectedAtCreationCount !== 0 || value.selectedAtCreationSizeEstimateBytes === 0) &&
    (value.excludedAtCreationCount !== 0 || value.excludedAtCreationSizeEstimateBytes === 0) &&
    (value.currentEligibleCount !== 0 || value.currentEligibleSizeEstimateBytes === 0) && stateCountsValid;
}

function isPlanSummary(value: unknown): value is PlanSummary {
  return isRecord(value) && hasExactKeys(value, SUMMARY_KEYS) && hasSummary(value);
}

function isOrderedReasons(value: unknown): value is ExclusionReason[] {
  return Array.isArray(value) && isContractOrdered(value, EXCLUSION_REASONS);
}

function isCreationReasons(value: readonly ExclusionReason[]): boolean {
  return value.every((reason) => EXCLUSION_REASONS.indexOf(reason) < 18);
}

function isRemovalReasons(value: readonly ExclusionReason[]): boolean {
  if (value.length === 0) return false;
  if (value.includes("missing_after_creation")) return value.length === 1;
  const hasCurrentProtection = value.some((reason) => EXCLUSION_REASONS.indexOf(reason) < 14);
  return hasCurrentProtection === value.includes("protection_changed");
}

function isSampleOrder(items: readonly PlanSample[]): boolean {
  return isUnique(items, (item) => item.messageId) && items.every((item, index) => {
    if (index === 0) return true;
    const previous = items[index - 1]!;
    const timestampOrder = compareTimestamps(previous.receivedAt, item.receivedAt);
    return timestampOrder > 0 || (timestampOrder === 0 && previous.messageId < item.messageId);
  });
}

function isSample(value: unknown): value is PlanSample {
  return isRecord(value) && hasExactKeys(value, [
    "messageId", "receivedAt", "senderName", "senderAddress", "subject", "sizeEstimateBytes",
    "sourceId", "flowId", "readState", "exclusionReasons",
  ]) && isPattern(value.messageId, MESSAGE_ID) && isTimestamp(value.receivedAt) &&
    isNullableVisibleText(value.senderName) && isNullableSyntheticAddress(value.senderAddress) &&
    isNullableVisibleText(value.subject) && isSafeInteger(value.sizeEstimateBytes, 0, 2147483647) &&
    isPattern(value.sourceId, SOURCE_ID) && isPattern(value.flowId, FLOW_ID) &&
    (value.readState === "read" || value.readState === "unread") && isOrderedReasons(value.exclusionReasons);
}

function isEvent(value: unknown): value is PlanEvent {
  if (!isRecord(value) || !hasExactKeys(value, [
    "revision", "type", "recordedAt", "state", "observedMapRevision", "observedPolicyRevision",
    "removedCount", "remainingCount",
  ]) || !isSafeInteger(value.revision, 1) || !isOneOf(value.type, EVENT_TYPES) || !isTimestamp(value.recordedAt) ||
    !isOneOf(value.state, ["frozen", "reduced", "invalidated", "cancelled"] as const) ||
    !(value.observedMapRevision === null || isMapRevision(value.observedMapRevision)) ||
    !(value.observedPolicyRevision === null || isSafeInteger(value.observedPolicyRevision)) ||
    !isSafeInteger(value.removedCount, 0, 100000) || !isSafeInteger(value.remainingCount, 0, 100000)) return false;
  if ((value.revision === 1) !== (value.type === "created")) return false;
  const observedCurrentSnapshot = value.observedMapRevision !== null && value.observedPolicyRevision !== null;
  if (value.type === "created") return observedCurrentSnapshot && value.revision === 1 && value.removedCount === 0 &&
    ((value.state === "frozen" && value.remainingCount > 0) || (value.state === "invalidated" && value.remainingCount === 0));
  if (value.type === "revalidated") return observedCurrentSnapshot && value.removedCount === 0 && value.remainingCount > 0 &&
    (value.state === "frozen" || value.state === "reduced");
  if (value.type === "reduced") return observedCurrentSnapshot && value.removedCount > 0 && value.remainingCount > 0 && value.state === "reduced";
  if (value.type === "invalidated") return observedCurrentSnapshot && value.removedCount > 0 && value.remainingCount === 0 && value.state === "invalidated";
  return value.removedCount === 0 && value.remainingCount > 0 && value.state === "cancelled" &&
    value.observedMapRevision === null && value.observedPolicyRevision === null;
}

export function isLedgerTransition(older: PlanEvent, newer: PlanEvent): boolean {
  if (older.state === "cancelled" || older.state === "invalidated") return false;
  if (newer.revision !== older.revision + 1 || compareTimestamps(newer.recordedAt, older.recordedAt) < 0) return false;
  if (newer.type === "revalidated") {
    return newer.state === older.state && newer.remainingCount === older.remainingCount;
  }
  if (newer.type === "reduced" || newer.type === "invalidated") {
    return newer.remainingCount === older.remainingCount - newer.removedCount;
  }
  return newer.type === "cancelled" && newer.remainingCount === older.remainingCount;
}

function canonicalJson(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
  if (typeof value === "object" && value !== null) {
    const entries = Object.entries(value).sort(([left], [right]) => left < right ? -1 : left > right ? 1 : 0);
    return `{${entries.map(([key, item]) => `${JSON.stringify(key)}:${canonicalJson(item)}`).join(",")}}`;
  }
  return JSON.stringify(value) ?? "null";
}

function frozenPlanIdentity(plan: PlanDetail): string {
  return canonicalJson({
    planId: plan.planId,
    createdAt: plan.createdAt,
    expiresAt: plan.expiresAt,
    disposition: plan.disposition,
    selectedAtCreationCount: plan.selectedAtCreationCount,
    selectedAtCreationSizeEstimateBytes: plan.selectedAtCreationSizeEstimateBytes,
    excludedAtCreationCount: plan.excludedAtCreationCount,
    excludedAtCreationSizeEstimateBytes: plan.excludedAtCreationSizeEstimateBytes,
    storageEffect: plan.storageEffect,
    effectiveFreedBytes: plan.effectiveFreedBytes,
    selection: plan.selection,
    createdFromMapRevision: plan.createdFromMapRevision,
    createdFromPolicyRevision: plan.createdFromPolicyRevision,
    includedSamples: plan.includedSamples,
    excludedSamples: plan.excludedSamples,
  });
}

export function overlappingEventsKeepIdentity(left: readonly PlanEvent[], right: readonly PlanEvent[]): boolean {
  const leftByRevision = new Map(left.map((event) => [event.revision, canonicalJson(event)]));
  return right.every((event) => {
    const previous = leftByRevision.get(event.revision);
    return previous === undefined || previous === canonicalJson(event);
  });
}

function planLedgersHaveContinuity(previous: PlanDetail, next: PlanDetail): boolean {
  if (!overlappingEventsKeepIdentity(previous.recentEvents, next.recentEvents)) return false;
  const previousRevisions = new Set(previous.recentEvents.map((event) => event.revision));
  if (next.recentEvents.some((event) => previousRevisions.has(event.revision))) return true;
  const previousLatest = previous.recentEvents[0];
  const nextOldest = next.recentEvents.at(-1);
  return previousLatest !== undefined && nextOldest !== undefined &&
    nextOldest.revision === previous.planRevision + 1 &&
    isLedgerTransition(previousLatest, nextOldest);
}

export function isSafePlanProgression(previous: PlanDetail, next: PlanDetail): boolean {
  const sameRevision = previous.planRevision === next.planRevision;
  const previousTerminal = previous.state === "cancelled" || previous.state === "invalidated" || previous.state === "expired";
  const stateProgresses = sameRevision
    ? previous.state === next.state ||
      ((previous.state === "frozen" || previous.state === "reduced") && next.state === "expired")
    : previous.state === "frozen" ||
      (previous.state === "reduced" && next.state !== "frozen") ||
      (previous.state === "invalidated" && next.state === "invalidated") ||
      (previous.state === "cancelled" && next.state === "cancelled") ||
      (previous.state === "expired" && next.state === "expired");
  const sameRevisionSnapshot = !sameRevision || (
    previous.currentEligibleCount === next.currentEligibleCount &&
    previous.currentEligibleSizeEstimateBytes === next.currentEligibleSizeEstimateBytes &&
    previous.lastRevalidatedAt === next.lastRevalidatedAt &&
    previous.eventCount === next.eventCount &&
    canonicalJson(previous.recentEvents) === canonicalJson(next.recentEvents)
  );
  return frozenPlanIdentity(previous) === frozenPlanIdentity(next) &&
    (!previousTerminal || sameRevision) &&
    next.planRevision >= previous.planRevision &&
    next.currentEligibleCount <= previous.currentEligibleCount &&
    next.currentEligibleSizeEstimateBytes <= previous.currentEligibleSizeEstimateBytes &&
    planLedgersHaveContinuity(previous, next) &&
    sameRevisionSnapshot && stateProgresses;
}

export function isPlanDetail(value: unknown): value is PlanDetail {
  const detailKeys = [
    "contractVersion", "dataMode", "canExecute", ...SUMMARY_KEYS.filter((key) => key !== "canExecute"),
    "selection", "createdFromMapRevision", "createdFromPolicyRevision", "currentMapRevision",
    "currentPolicyRevision", "includedSamples", "excludedSamples", "eventCount", "recentEvents", "warnings",
  ];
  if (!isRecord(value)) return false;
  const recentEvents = value.recentEvents;
  if (!hasExactKeys(value, detailKeys) || !isEnvelope(value) || !hasSummary(value) ||
    !isPlanSelection(value.selection) || !isMapRevision(value.createdFromMapRevision) ||
    !isSafeInteger(value.createdFromPolicyRevision) ||
    !(value.currentMapRevision === null || isMapRevision(value.currentMapRevision)) ||
    !(value.currentPolicyRevision === null || isSafeInteger(value.currentPolicyRevision)) ||
    !isArrayOf(value.includedSamples, isSample, 5) || !isArrayOf(value.excludedSamples, isSample, 5) ||
    !value.includedSamples.every((sample) => sample.exclusionReasons.length === 0) ||
    !value.excludedSamples.every((sample) => sample.exclusionReasons.length > 0 && isCreationReasons(sample.exclusionReasons)) ||
    !isSampleOrder(value.includedSamples) || !isSampleOrder(value.excludedSamples) ||
    !isUnique([...value.includedSamples, ...value.excludedSamples], (sample) => sample.messageId) ||
    value.includedSamples.length > value.selectedAtCreationCount ||
    value.excludedSamples.length > value.excludedAtCreationCount ||
    !isSafeInteger(value.eventCount, 1) || !isArrayOf(recentEvents, isEvent, 10) || recentEvents.length === 0 ||
    !Array.isArray(value.warnings) || !isContractOrdered(value.warnings, WARNING_CODES)) return false;
  const snapshotUnavailable = value.currentMapRevision === null && value.currentPolicyRevision === null;
  const revisionsPaired = (value.currentMapRevision === null) === (value.currentPolicyRevision === null);
  const hasUnavailableWarning = value.warnings.includes("current_snapshot_unavailable");
  const selectionReduced = value.currentEligibleCount < value.selectedAtCreationCount;
  const summaryStateValid = value.state === "frozen"
    ? value.currentEligibleCount === value.selectedAtCreationCount
    : value.state === "reduced"
      ? value.currentEligibleCount > 0 && selectionReduced
      : value.state === "invalidated"
        ? value.currentEligibleCount === 0
        : value.currentEligibleCount > 0;
  const latestEvent = recentEvents[0]!;
  const latestRevalidation = recentEvents.find((event) =>
    event.type === "revalidated" || event.type === "reduced" || event.type === "invalidated");
  return value.selection.disposition === value.disposition && summaryStateValid &&
    value.warnings.includes("selection_reduced") === selectionReduced &&
    revisionsPaired && snapshotUnavailable === hasUnavailableWarning &&
    (!snapshotUnavailable || (!value.warnings.includes("map_changed_since_creation") && !value.warnings.includes("policy_changed_since_creation"))) &&
    (snapshotUnavailable || value.warnings.includes("map_changed_since_creation") === (value.currentMapRevision !== value.createdFromMapRevision)) &&
    (snapshotUnavailable || value.warnings.includes("policy_changed_since_creation") === (value.currentPolicyRevision !== value.createdFromPolicyRevision)) &&
    value.eventCount === value.planRevision && recentEvents.length === Math.min(value.planRevision, 10) &&
    recentEvents[0]!.revision === value.planRevision &&
    value.lastRevalidatedAt === (latestRevalidation?.recordedAt ?? null) &&
    latestEvent.remainingCount === value.currentEligibleCount &&
    (value.state === "expired" ? (latestEvent.state === "frozen" || latestEvent.state === "reduced") : latestEvent.state === value.state) &&
    recentEvents.every((event, index) =>
      event.revision <= value.planRevision &&
      compareTimestamps(event.recordedAt, value.createdAt) >= 0 &&
      compareTimestamps(event.recordedAt, value.expiresAt) < 0 &&
      (index === 0 || isLedgerTransition(event, recentEvents[index - 1]!))) &&
    (recentEvents.at(-1)!.revision !== 1 || (
      recentEvents.at(-1)!.type === "created" &&
      compareTimestamps(recentEvents.at(-1)!.recordedAt, value.createdAt) === 0 &&
      recentEvents.at(-1)!.observedMapRevision === value.createdFromMapRevision &&
      recentEvents.at(-1)!.observedPolicyRevision === value.createdFromPolicyRevision &&
      recentEvents.at(-1)!.remainingCount === value.selectedAtCreationCount
    ));
}

export function isPlansResponse(value: unknown): value is PlansResponse {
  if (!isRecord(value)) return false;
  const items = value.items;
  if (!(hasExactKeys(value, [
    "contractVersion", "dataMode", "canExecute", "listingAsOf", "catalogRevision", "state", "items", "nextCursor",
  ]) && isEnvelope(value) && isTimestamp(value.listingAsOf) && isSafeInteger(value.catalogRevision) &&
    (value.state === null || isOneOf(value.state, PLAN_STATES)) && isArrayOf(items, isPlanSummary, 100) &&
    isCursor(value.nextCursor) && isUnique(items, (item) => item.planId))) return false;
  const listingAsOf = value.listingAsOf;
  return items.every((item) => value.state === null || item.state === value.state) &&
    items.every((item) => {
      const listingOrder = compareTimestamps(listingAsOf, item.expiresAt);
      return item.state === "expired" ? listingOrder >= 0 :
        (item.state === "frozen" || item.state === "reduced") ? listingOrder < 0 : true;
    }) &&
    items.every((item, index) => {
      if (index === 0) return true;
      const timestampOrder = compareTimestamps(items[index - 1]!.createdAt, item.createdAt);
      return timestampOrder > 0 || (timestampOrder === 0 && items[index - 1]!.planId < item.planId);
    });
}

function isMember(value: unknown): value is PlanMember {
  if (!isRecord(value) || !hasExactKeys(value, [
    "messageId", "initialState", "currentState", "receivedAt", "sizeEstimateBytes", "reasonCodes",
  ]) || !isPattern(value.messageId, MESSAGE_ID) || !(value.initialState === "selected" || value.initialState === "excluded") ||
    !(value.currentState === "eligible" || value.currentState === "excluded" || value.currentState === "removed") ||
    !isTimestamp(value.receivedAt) || !isSafeInteger(value.sizeEstimateBytes, 0, 2147483647) || !isOrderedReasons(value.reasonCodes)) return false;
  if (value.initialState === "excluded") return value.currentState === "excluded" && value.reasonCodes.length > 0 && isCreationReasons(value.reasonCodes);
  if (value.currentState === "eligible") return value.reasonCodes.length === 0;
  if (value.currentState === "removed") return isRemovalReasons(value.reasonCodes);
  return false;
}

export function isMessagesResponse(value: unknown): value is MessagesResponse {
  if (!isRecord(value)) return false;
  const items = value.items;
  return isRecord(value) && hasExactKeys(value, [
    "contractVersion", "dataMode", "canExecute", "planId", "planRevision", "state", "items", "nextCursor",
  ]) && isEnvelope(value) && isPlanId(value.planId) && isSafeInteger(value.planRevision, 1) &&
    isOneOf(value.state, MEMBER_FILTERS) && isArrayOf(items, isMember, 500) && isCursor(value.nextCursor) &&
    isUnique(items, (item) => item.messageId) && items.every((item, index) => {
      if (index === 0) return true;
      const timestampOrder = compareTimestamps(items[index - 1]!.receivedAt, item.receivedAt);
      return timestampOrder > 0 || (timestampOrder === 0 && items[index - 1]!.messageId < item.messageId);
    }) &&
    items.every((item) => {
      if (value.state === "all") return true;
      if (value.state === "selected") return item.initialState === "selected";
      if (value.state === "eligible") return item.currentState === "eligible";
      if (value.state === "excluded") return item.initialState === "excluded";
      return item.currentState === "removed";
    });
}

export function isEventsResponse(value: unknown): value is EventsResponse {
  if (!isRecord(value)) return false;
  const items = value.items;
  if (!(hasExactKeys(value, [
    "contractVersion", "dataMode", "canExecute", "planId", "planRevision", "items", "nextCursor",
  ]) && isEnvelope(value) && isPlanId(value.planId) && isSafeInteger(value.planRevision, 1) &&
    isArrayOf(items, isEvent, 100) && items.length > 0 && isCursor(value.nextCursor))) return false;
  const planRevision = value.planRevision;
  return items.every((event, index) => event.revision <= planRevision &&
    (index === 0 || isLedgerTransition(items[index - 1]!, event)));
}

function receiptBase(value: UnknownRecord): boolean {
  return isEnvelope(value) && typeof value.replayed === "boolean" && isSafeInteger(value.commandRevision, 1) && isPlanId(value.planId);
}

export function isCreateReceipt(value: unknown): value is CreateReceipt {
  return isRecord(value) && hasExactKeys(value, [
    "contractVersion", "dataMode", "canExecute", "status", "replayed", "commandRevision", "planId",
  ]) && receiptBase(value) && value.status === "created" && value.commandRevision === 1;
}

export function isRevalidateReceipt(value: unknown): value is RevalidateReceipt {
  return isRecord(value) && hasExactKeys(value, [
    "contractVersion", "dataMode", "canExecute", "status", "replayed", "commandRevision", "removedCount", "planId",
  ]) && receiptBase(value) && value.status === "revalidated" && isSafeInteger(value.commandRevision, 2) &&
    isSafeInteger(value.removedCount, 0, 100000);
}

export function isCancelReceipt(value: unknown): value is CancelReceipt {
  return isRecord(value) && hasExactKeys(value, [
    "contractVersion", "dataMode", "canExecute", "status", "replayed", "commandRevision", "planId",
  ]) && receiptBase(value) && value.status === "cancelled" && isSafeInteger(value.commandRevision, 2);
}

const ERROR_STATUS: Record<StudyErrorCode, number> = {
  invalid_request: 400,
  invalid_cursor: 400,
  invalid_local_origin: 403,
  route_not_found: 404,
  target_not_found: 404,
  plan_not_found: 404,
  method_not_allowed: 405,
  map_revision_conflict: 409,
  policy_revision_conflict: 409,
  plan_revision_conflict: 409,
  command_id_conflict: 409,
  cursor_stale: 409,
  invalid_transition: 409,
  plan_expired: 409,
  payload_too_large: 413,
  plan_too_large: 413,
  json_required: 415,
  unsupported_target: 422,
  invalid_filter: 422,
  study_unavailable: 503,
  inventory_incomplete: 503,
  account_unavailable: 503,
  internal_error: 500,
};

const SERVER_ERROR_MESSAGES: Record<StudyErrorCode, string> = {
  invalid_request: "El pedido no es válido.",
  invalid_cursor: "El cursor no es válido.",
  invalid_local_origin: "El origen local no está permitido.",
  route_not_found: "La ruta solicitada no existe.",
  target_not_found: "El objetivo no existe en la vista actual.",
  plan_not_found: "El plan solicitado no existe.",
  method_not_allowed: "El método no está permitido para esta ruta.",
  map_revision_conflict: "El mapa cambió. Actualizá la vista antes de reintentar.",
  policy_revision_conflict: "Las decisiones cambiaron. Actualizá la vista antes de reintentar.",
  plan_revision_conflict: "El plan cambió. Actualizá la vista antes de reintentar.",
  command_id_conflict: "El identificador del comando ya fue utilizado.",
  cursor_stale: "La página cambió. Reiniciá la consulta.",
  invalid_transition: "La transición solicitada no está permitida.",
  plan_expired: "El plan venció. Creá uno nuevo.",
  payload_too_large: "El pedido supera el tamaño permitido.",
  plan_too_large: "El plan supera el límite de mensajes permitido.",
  json_required: "Se requiere un cuerpo JSON.",
  unsupported_target: "El tipo de objetivo no está permitido.",
  invalid_filter: "El filtro solicitado no es válido.",
  study_unavailable: "El Estudio de Limpieza no está disponible.",
  inventory_incomplete: "El inventario todavía no está completo.",
  account_unavailable: "La cuenta sintética no está disponible.",
  internal_error: "No se pudo completar la operación.",
};

export function decodeStudyError(value: unknown, status: number): StudyErrorCode | null {
  if (!isRecord(value) || !hasExactKeys(value, ["contractVersion", "dataMode", "canExecute", "error"]) || !isEnvelope(value)) return null;
  const error = value.error;
  if (!isRecord(error) || !hasExactKeys(error, ["code", "message"]) || !isOneOf(error.code, STUDY_ERROR_CODES)) return null;
  return ERROR_STATUS[error.code] === status && error.message === SERVER_ERROR_MESSAGES[error.code] ? error.code : null;
}

export function isPlanState(value: unknown): value is PlanState {
  return isOneOf(value, PLAN_STATES);
}

export function isTargetKind(value: unknown): value is TargetKind {
  return isOneOf(value, TARGET_KINDS);
}
