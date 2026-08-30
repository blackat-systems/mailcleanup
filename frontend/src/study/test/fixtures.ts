import type {
  CancelReceipt,
  CreateReceipt,
  EventsResponse,
  MessagesResponse,
  PlanDetail,
  PlanState,
  PlansResponse,
  RevalidateReceipt,
  StudyContext,
  StudyErrorCode,
  TargetsResponse,
} from "../types";

export const mapRevision = `map-v1-${"a".repeat(64)}`;
export const nextMapRevision = `map-v1-${"b".repeat(64)}`;
export const sourceId = `effective-source-v1-${"a".repeat(24)}`;
export const flowId = `effective-flow-v1-${"b".repeat(24)}`;
export const senderId = `sender-v1-${"c".repeat(64)}`;
export const labelId = `label-v1-${"d".repeat(64)}`;
export const messageId = `message-v1-${"e".repeat(64)}`;
export const excludedMessageId = `message-v1-${"f".repeat(64)}`;
export const planId = "cleanup-plan-v1-12345678-1234-4234-8234-123456789abc";

export const studyContext: StudyContext = {
  contractVersion: 1,
  dataMode: "synthetic",
  canExecute: false,
  timeZone: "America/Argentina/Cordoba",
  planValiditySeconds: 86400,
  limits: {
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
  },
  capabilities: {
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
  },
  availability: {
    accountAvailable: true,
    inventoryState: "completed",
    completeSnapshotAvailable: true,
    currentMapRevision: mapRevision,
    currentPolicyRevision: 7,
    targetReadAvailable: true,
    planCreateAvailable: true,
    planRevalidateAvailable: true,
    blockerCodes: [],
  },
};

export const targetsResponse: TargetsResponse = {
  contractVersion: 1,
  dataMode: "synthetic",
  canExecute: false,
  mapRevision,
  policyRevision: 7,
  kind: null,
  items: [
    { kind: "source", targetId: sourceId, displayName: "Boletines Example", messageCount: 12 },
    { kind: "flow", targetId: flowId, sourceId, displayName: "Resumen semanal", messageCount: 8 },
    { kind: "sender", targetId: senderId, displayAddress: "news@sender.example", messageCount: 8 },
    { kind: "label", targetId: labelId, displayName: "Recibidos", messageCount: 12 },
  ],
  nextCursor: null,
};

const summary = {
  planId,
  planRevision: 1,
  state: "frozen" as const,
  createdAt: "2026-08-29T12:00:00Z",
  expiresAt: "2026-08-30T12:00:00Z",
  lastRevalidatedAt: null,
  disposition: "archive" as const,
  selectedAtCreationCount: 1,
  selectedAtCreationSizeEstimateBytes: 2048,
  excludedAtCreationCount: 1,
  excludedAtCreationSizeEstimateBytes: 1024,
  currentEligibleCount: 1,
  currentEligibleSizeEstimateBytes: 2048,
  storageEffect: "none" as const,
  effectiveFreedBytes: null,
  canExecute: false as const,
};

export const planDetail: PlanDetail = {
  contractVersion: 1,
  dataMode: "synthetic",
  ...summary,
  selection: {
    disposition: "archive",
    targets: [{ kind: "source", targetId: sourceId }],
    targetSnapshots: [{ kind: "source", targetId: sourceId, displayName: "Boletines Example" }],
    temporalFilterRequested: { kind: "all" },
    resolvedOnOrAfterUtc: null,
    resolvedBeforeUtc: null,
    timeZone: "America/Argentina/Cordoba",
    readState: "any",
    excludedLabelIds: [],
    excludedLabelSnapshots: [],
    keepLatestPerFlow: 0,
  },
  createdFromMapRevision: mapRevision,
  createdFromPolicyRevision: 7,
  currentMapRevision: mapRevision,
  currentPolicyRevision: 7,
  includedSamples: [{
    messageId,
    receivedAt: "2026-08-20T12:00:00Z",
    senderName: "Noticias Example",
    senderAddress: "news@sender.example",
    subject: "Resumen de demostración",
    sizeEstimateBytes: 2048,
    sourceId,
    flowId,
    readState: "read",
    exclusionReasons: [],
  }],
  excludedSamples: [{
    messageId: excludedMessageId,
    receivedAt: "2026-08-19T12:00:00Z",
    senderName: null,
    senderAddress: "protected@sender.example",
    subject: null,
    sizeEstimateBytes: 1024,
    sourceId,
    flowId,
    readState: "unread",
    exclusionReasons: ["starred"],
  }],
  eventCount: 1,
  recentEvents: [{
    revision: 1,
    type: "created",
    recordedAt: "2026-08-29T12:00:00Z",
    state: "frozen",
    observedMapRevision: mapRevision,
    observedPolicyRevision: 7,
    removedCount: 0,
    remainingCount: 1,
  }],
  warnings: [],
};

const revalidatedAt = "2026-08-29T13:00:00Z";

export function detailForState(state: PlanState): PlanDetail {
  if (state === "frozen") return planDetail;
  if (state === "expired") return { ...planDetail, state: "expired" };
  if (state === "cancelled") {
    return {
      ...planDetail,
      planRevision: 2,
      state: "cancelled",
      eventCount: 2,
      recentEvents: [{
        revision: 2,
        type: "cancelled",
        recordedAt: revalidatedAt,
        state: "cancelled",
        observedMapRevision: null,
        observedPolicyRevision: null,
        removedCount: 0,
        remainingCount: 1,
      }, ...planDetail.recentEvents],
    };
  }
  if (state === "reduced") {
    return {
      ...planDetail,
      planRevision: 2,
      state: "reduced",
      lastRevalidatedAt: revalidatedAt,
      selectedAtCreationCount: 2,
      selectedAtCreationSizeEstimateBytes: 4096,
      currentEligibleCount: 1,
      currentEligibleSizeEstimateBytes: 2048,
      eventCount: 2,
      recentEvents: [{
        revision: 2,
        type: "reduced",
        recordedAt: revalidatedAt,
        state: "reduced",
        observedMapRevision: mapRevision,
        observedPolicyRevision: 7,
        removedCount: 1,
        remainingCount: 1,
      }, { ...planDetail.recentEvents[0]!, remainingCount: 2 }],
      warnings: ["selection_reduced"],
    };
  }
  return {
    ...planDetail,
    state: "invalidated",
    selectedAtCreationCount: 0,
    selectedAtCreationSizeEstimateBytes: 0,
    excludedAtCreationCount: 2,
    excludedAtCreationSizeEstimateBytes: 3072,
    currentEligibleCount: 0,
    currentEligibleSizeEstimateBytes: 0,
    includedSamples: [],
    recentEvents: [{ ...planDetail.recentEvents[0]!, state: "invalidated", remainingCount: 0 }],
  };
}

export function detailAfterRevalidation(state: "frozen" | "reduced" | "invalidated"): PlanDetail {
  if (state === "reduced") return detailForState("reduced");
  if (state === "invalidated") {
    return {
      ...planDetail,
      planRevision: 2,
      state: "invalidated",
      lastRevalidatedAt: revalidatedAt,
      currentEligibleCount: 0,
      currentEligibleSizeEstimateBytes: 0,
      eventCount: 2,
      recentEvents: [{
        revision: 2,
        type: "invalidated",
        recordedAt: revalidatedAt,
        state: "invalidated",
        observedMapRevision: mapRevision,
        observedPolicyRevision: 7,
        removedCount: 1,
        remainingCount: 0,
      }, ...planDetail.recentEvents],
      warnings: ["selection_reduced"],
    };
  }
  return {
    ...planDetail,
    planRevision: 2,
    lastRevalidatedAt: revalidatedAt,
    eventCount: 2,
    recentEvents: [{
      revision: 2,
      type: "revalidated",
      recordedAt: revalidatedAt,
      state: "frozen",
      observedMapRevision: mapRevision,
      observedPolicyRevision: 7,
      removedCount: 0,
      remainingCount: 1,
    }, ...planDetail.recentEvents],
  };
}

export const frozenTwoDetail: PlanDetail = {
  ...planDetail,
  selectedAtCreationCount: 2,
  selectedAtCreationSizeEstimateBytes: 4096,
  currentEligibleCount: 2,
  currentEligibleSizeEstimateBytes: 4096,
  recentEvents: [{ ...planDetail.recentEvents[0]!, remainingCount: 2 }],
};

export const cancelledAfterRevalidationDetail: PlanDetail = {
  ...detailAfterRevalidation("frozen"),
  planRevision: 3,
  state: "cancelled",
  eventCount: 3,
  recentEvents: [{
    revision: 3,
    type: "cancelled",
    recordedAt: "2026-08-29T14:00:00Z",
    state: "cancelled",
    observedMapRevision: null,
    observedPolicyRevision: null,
    removedCount: 0,
    remainingCount: 1,
  }, ...detailAfterRevalidation("frozen").recentEvents],
};

export const plansResponse: PlansResponse = {
  contractVersion: 1,
  dataMode: "synthetic",
  canExecute: false,
  listingAsOf: "2026-08-29T12:30:00Z",
  catalogRevision: 1,
  state: null,
  items: [summary],
  nextCursor: null,
};

export const messagesResponse: MessagesResponse = {
  contractVersion: 1,
  dataMode: "synthetic",
  canExecute: false,
  planId,
  planRevision: 1,
  state: "all",
  items: [{
    messageId,
    initialState: "selected",
    currentState: "eligible",
    receivedAt: "2026-08-20T12:00:00Z",
    sizeEstimateBytes: 2048,
    reasonCodes: [],
  }, {
    messageId: excludedMessageId,
    initialState: "excluded",
    currentState: "excluded",
    receivedAt: "2026-08-19T12:00:00Z",
    sizeEstimateBytes: 1024,
    reasonCodes: ["starred"],
  }],
  nextCursor: null,
};

export const eventsResponse: EventsResponse = {
  contractVersion: 1,
  dataMode: "synthetic",
  canExecute: false,
  planId,
  planRevision: 1,
  items: [...planDetail.recentEvents].reverse(),
  nextCursor: null,
};

export const createReceipt: CreateReceipt = {
  contractVersion: 1,
  dataMode: "synthetic",
  canExecute: false,
  status: "created",
  replayed: false,
  commandRevision: 1,
  planId,
};

export const revalidateReceipt: RevalidateReceipt = {
  contractVersion: 1,
  dataMode: "synthetic",
  canExecute: false,
  status: "revalidated",
  replayed: false,
  commandRevision: 2,
  removedCount: 0,
  planId,
};

export const cancelReceipt: CancelReceipt = {
  contractVersion: 1,
  dataMode: "synthetic",
  canExecute: false,
  status: "cancelled",
  replayed: false,
  commandRevision: 2,
  planId,
};

const serverMessages: Record<StudyErrorCode, string> = {
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

export function studyError(code: StudyErrorCode) {
  return {
    contractVersion: 1,
    dataMode: "synthetic",
    canExecute: false,
    error: { code, message: serverMessages[code] },
  };
}

export function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", "Cache-Control": "no-store" },
  });
}
