import type {
  ConnectionResponse,
  DecisionEvent,
  DecisionListResponse,
  IndexResponse,
  MapContext,
  MapResponse,
  ProtectionProjection,
  SourceDetailResponse,
  SourceProjection,
  SyncResponse,
  WriteResponse,
} from "../types";

export const mapRevision = `map-v1-${"a".repeat(64)}`;
export const nextMapRevision = `map-v1-${"b".repeat(64)}`;
export const sourceAId = `effective-source-v1-${"1".repeat(24)}`;
export const sourceBId = `effective-source-v1-${"2".repeat(24)}`;
export const sourceCId = `effective-source-v1-${"3".repeat(24)}`;
export const flowA1Id = `effective-flow-v1-${"1".repeat(24)}`;
export const flowA2Id = `effective-flow-v1-${"2".repeat(24)}`;
export const flowBId = `effective-flow-v1-${"3".repeat(24)}`;
export const flowCId = `effective-flow-v1-${"4".repeat(24)}`;
export const messageAId = `message-v1-${"1".repeat(64)}`;
export const messageBId = `message-v1-${"2".repeat(64)}`;

const decisionIds = [
  "11111111-1111-4111-8111-111111111111",
  "22222222-2222-4222-8222-222222222222",
  "33333333-3333-4333-8333-333333333333",
  "44444444-4444-4444-8444-444444444444",
  "55555555-5555-4555-8555-555555555555",
  "66666666-6666-4666-8666-666666666666",
  "77777777-7777-4777-8777-777777777777",
] as const;

const ordinaryProtection: ProtectionProjection = {
  automatic: "Ordinaria",
  effective: "Ordinaria",
  protected: false,
  reviewRequired: false,
  hardExcluded: false,
  reasons: [],
};

const protectedProjection: ProtectionProjection = {
  automatic: "Ordinaria",
  effective: "Elegida por el usuario",
  protected: true,
  reviewRequired: true,
  hardExcluded: false,
  reasons: ["manual_policy", "policy_review"],
};

const hardProtection: ProtectionProjection = {
  automatic: "Crítica",
  effective: "Crítica",
  protected: true,
  reviewRequired: false,
  hardExcluded: true,
  reasons: ["trash"],
};

const automaticEvidence = [{
  kind: "classification" as const,
  code: "source.authenticated",
  label: "Identidad autenticada",
  detail: "Las señales públicas del fixture coinciden.",
  strength: "strong" as const,
  origin: "authentication" as const,
}];

export const sourceA: SourceProjection = {
  id: sourceAId,
  automaticSourceIds: ["automatic-source-a"],
  automaticDisplayName: "Diario Horizonte",
  effectiveDisplayName: "Horizonte local",
  automaticRubro: "Medios y contenido",
  effectiveRubro: "Trabajo y educación",
  automaticConfidence: "Alta",
  effectiveConfidence: "Media",
  messageCount: 3,
  flowCount: 2,
  protectedMessageCount: 1,
  reviewRequiredMessageCount: 1,
  hardExcludedMessageCount: 0,
  totalBytes: 3600,
  firstSeen: "2026-06-10T10:00:00Z",
  lastSeen: "2026-08-20T12:00:00Z",
  senders: ["boletin@horizonte.example", "seguridad@horizonte.example"],
  domains: ["horizonte.example"],
  monthlyVolume: [
    { month: "2026-06", messageCount: 1, totalBytes: 1000 },
    { month: "2026-08", messageCount: 2, totalBytes: 2600 },
  ],
  protection: protectedProjection,
  automaticEvidence,
  effectiveEvidence: [
    ...automaticEvidence,
    { kind: "policy", code: "policy.source_display_name", decisionId: decisionIds[0] },
    { kind: "policy", code: "policy.source_rubro", decisionId: decisionIds[1] },
  ],
  decisionIds: [decisionIds[0], decisionIds[1]],
  structuralDecisionIds: [],
  flows: [
    {
      id: flowA1Id,
      sourceId: sourceAId,
      automaticFlowId: "automatic-flow-editorial",
      automaticDisplayName: "Boletín editorial",
      effectiveDisplayName: "Noticias para el equipo",
      automaticIntention: "Informativo o editorial",
      effectiveIntention: "Notificación",
      subscription: "Confirmada",
      automaticConfidence: "Alta",
      effectiveConfidence: "Media",
      messageCount: 2,
      protectedMessageCount: 0,
      reviewRequiredMessageCount: 0,
      hardExcludedMessageCount: 0,
      totalBytes: 2400,
      firstSeen: "2026-06-10T10:00:00Z",
      lastSeen: "2026-08-20T12:00:00Z",
      protection: ordinaryProtection,
      automaticEvidence,
      effectiveEvidence: [
        ...automaticEvidence,
        { kind: "policy", code: "policy.flow_display_name", decisionId: decisionIds[2] },
      ],
      decisionIds: [decisionIds[2]],
      structuralDecisionIds: [],
    },
    {
      id: flowA2Id,
      sourceId: sourceAId,
      automaticFlowId: "automatic-flow-security",
      automaticDisplayName: "Alertas de seguridad",
      effectiveDisplayName: "Alertas de seguridad",
      automaticIntention: "Seguridad",
      effectiveIntention: "Seguridad",
      subscription: "No corresponde",
      automaticConfidence: "Baja",
      effectiveConfidence: "Contradictoria",
      messageCount: 1,
      protectedMessageCount: 1,
      reviewRequiredMessageCount: 1,
      hardExcludedMessageCount: 0,
      totalBytes: 1200,
      firstSeen: "2026-08-18T11:00:00Z",
      lastSeen: "2026-08-18T11:00:00Z",
      protection: protectedProjection,
      automaticEvidence,
      effectiveEvidence: [
        ...automaticEvidence,
        { kind: "policy", code: "policy.protect_target", decisionId: decisionIds[6] },
      ],
      decisionIds: [decisionIds[6]],
      structuralDecisionIds: [],
    },
  ],
};

export const sourceB: SourceProjection = {
  id: sourceBId,
  automaticSourceIds: ["automatic-source-b"],
  automaticDisplayName: "Nube Taller",
  effectiveDisplayName: "Nube Taller",
  automaticRubro: "Software y servicios digitales",
  effectiveRubro: "Software y servicios digitales",
  automaticConfidence: "Media",
  effectiveConfidence: "Media",
  messageCount: 1,
  flowCount: 1,
  protectedMessageCount: 0,
  reviewRequiredMessageCount: 0,
  hardExcludedMessageCount: 0,
  totalBytes: 900,
  firstSeen: "2026-08-12T08:30:00Z",
  lastSeen: "2026-08-12T08:30:00Z",
  senders: ["avisos@nube-taller.example"],
  domains: ["nube-taller.example"],
  monthlyVolume: [{ month: "2026-08", messageCount: 1, totalBytes: 900 }],
  protection: ordinaryProtection,
  automaticEvidence,
  effectiveEvidence: automaticEvidence,
  decisionIds: [],
  structuralDecisionIds: [],
  flows: [{
    id: flowBId,
    sourceId: sourceBId,
    automaticFlowId: "automatic-flow-service",
    automaticDisplayName: "Avisos de servicio",
    effectiveDisplayName: "Avisos de servicio",
    automaticIntention: "Operativo o soporte",
    effectiveIntention: "Operativo o soporte",
    subscription: "Desconocido",
    automaticConfidence: "Media",
    effectiveConfidence: "Media",
    messageCount: 1,
    protectedMessageCount: 0,
    reviewRequiredMessageCount: 0,
    hardExcludedMessageCount: 0,
    totalBytes: 900,
    firstSeen: "2026-08-12T08:30:00Z",
    lastSeen: "2026-08-12T08:30:00Z",
    protection: ordinaryProtection,
    automaticEvidence,
    effectiveEvidence: automaticEvidence,
    decisionIds: [],
    structuralDecisionIds: [],
  }],
};

export const sourceC: SourceProjection = {
  id: sourceCId,
  automaticSourceIds: ["automatic-source-c"],
  automaticDisplayName: "Remitente aislado",
  effectiveDisplayName: "Remitente aislado",
  automaticRubro: "Desconocido",
  effectiveRubro: "Desconocido",
  automaticConfidence: "Contradictoria",
  effectiveConfidence: "Contradictoria",
  messageCount: 1,
  flowCount: 1,
  protectedMessageCount: 1,
  reviewRequiredMessageCount: 0,
  hardExcludedMessageCount: 1,
  totalBytes: 700,
  firstSeen: "2026-08-21T09:00:00Z",
  lastSeen: "2026-08-21T09:00:00Z",
  senders: ["alerta@aislado.example"],
  domains: ["aislado.example"],
  monthlyVolume: [{ month: "2026-08", messageCount: 1, totalBytes: 700 }],
  protection: hardProtection,
  automaticEvidence,
  effectiveEvidence: automaticEvidence,
  decisionIds: [],
  structuralDecisionIds: [],
  flows: [{
    id: flowCId,
    sourceId: sourceCId,
    automaticFlowId: "automatic-flow-suspicious",
    automaticDisplayName: "Señal sospechosa",
    effectiveDisplayName: "Señal sospechosa",
    automaticIntention: "Sospechoso",
    effectiveIntention: "Sospechoso",
    subscription: "Desconocido",
    automaticConfidence: "Contradictoria",
    effectiveConfidence: "Contradictoria",
    messageCount: 1,
    protectedMessageCount: 1,
    reviewRequiredMessageCount: 0,
    hardExcludedMessageCount: 1,
    totalBytes: 700,
    firstSeen: "2026-08-21T09:00:00Z",
    lastSeen: "2026-08-21T09:00:00Z",
    protection: hardProtection,
    automaticEvidence,
    effectiveEvidence: automaticEvidence,
    decisionIds: [],
    structuralDecisionIds: [],
  }],
};

export const context: MapContext = {
  contractVersion: 1,
  dataMode: "synthetic",
  appVersion: "0.1.0",
  account: { state: "synthetic", displayAddress: null },
  capabilities: {
    mapRead: true,
    policyWrite: true,
    policyUndo: true,
    gmailConnection: false,
    oauth: false,
    externalNetwork: false,
    realData: false,
    syncControl: false,
    cleanupPlan: false,
    messageMutation: false,
    unsubscribe: false,
    execute: false,
  },
};

export const connection: ConnectionResponse = {
  contractVersion: 1,
  dataMode: "synthetic",
  state: "synthetic",
  displayAddress: null,
  capabilities: {
    gmailConnection: false,
    oauth: false,
    externalNetwork: false,
    realData: false,
  },
};

export const sync: SyncResponse = {
  contractVersion: 1,
  dataMode: "synthetic",
  state: "completed",
  mode: "full",
  processedCount: 5,
  startedAt: "2026-08-27T20:00:00Z",
  updatedAt: "2026-08-27T20:01:00Z",
  errorCode: null,
  partial: false,
};

export const indexResponse: IndexResponse = {
  contractVersion: 1,
  dataMode: "synthetic",
  state: "synthetic_fixture",
  fixtureVersion: "map-fixture-v1",
  schemaVersion: 5,
  messageCount: 5,
  partial: false,
  canDelete: false,
};

export const mapResponse: MapResponse = {
  contractVersion: 1,
  dataMode: "synthetic",
  mapRevision,
  policyRevision: 7,
  sync: {
    state: sync.state,
    mode: sync.mode,
    processedCount: sync.processedCount,
    startedAt: sync.startedAt,
    updatedAt: sync.updatedAt,
    errorCode: sync.errorCode,
    partial: sync.partial,
  },
  summary: {
    messageCount: 5,
    sourceCount: 3,
    flowCount: 4,
    protectedMessageCount: 2,
    reviewRequiredMessageCount: 1,
    hardExcludedMessageCount: 1,
    totalBytes: 5200,
    firstSeen: "2026-06-10T10:00:00Z",
    lastSeen: "2026-08-21T09:00:00Z",
  },
  policyReview: {
    total: 4,
    bindings: [
      { decisionId: decisionIds[0], status: "NEEDS_REVIEW", currentEffectiveIds: [sourceAId] },
      { decisionId: decisionIds[1], status: "ORPHANED", currentEffectiveIds: [] },
      { decisionId: decisionIds[2], status: "AMBIGUOUS", currentEffectiveIds: [flowA1Id, flowA2Id] },
      { decisionId: decisionIds[3], status: "CONFLICT", currentEffectiveIds: [sourceBId] },
    ],
  },
  sources: [sourceA, sourceB, sourceC],
};

export const sourceDetail: SourceDetailResponse = {
  ...sourceA,
  contractVersion: 1,
  dataMode: "synthetic",
  recentMessages: [
    {
      id: messageAId,
      receivedAt: "2026-08-20T12:00:00Z",
      senderName: "Horizonte",
      senderAddress: "boletin@horizonte.example",
      subject: "Resumen del laboratorio",
      labelIds: ["IMPORTANT"],
      category: "CATEGORY_UPDATES",
      sizeEstimateBytes: 1400,
      sourceId: sourceAId,
      flowId: flowA1Id,
      automaticRubro: "Medios y contenido",
      effectiveRubro: "Trabajo y educación",
      automaticIntention: "Informativo o editorial",
      effectiveIntention: "Notificación",
      subscription: "Confirmada",
      automaticConfidence: "Alta",
      effectiveConfidence: "Media",
      protection: ordinaryProtection,
    },
    {
      id: messageBId,
      receivedAt: "2026-08-18T11:00:00Z",
      senderName: "Seguridad Horizonte",
      senderAddress: "seguridad@horizonte.example",
      subject: "Revisión de acceso de demostración",
      labelIds: ["STARRED"],
      category: null,
      sizeEstimateBytes: 1200,
      sourceId: sourceAId,
      flowId: flowA2Id,
      automaticRubro: "Medios y contenido",
      effectiveRubro: "Trabajo y educación",
      automaticIntention: "Seguridad",
      effectiveIntention: "Seguridad",
      subscription: "No corresponde",
      automaticConfidence: "Baja",
      effectiveConfidence: "Contradictoria",
      protection: protectedProjection,
    },
  ],
};

function eventBase(index: number, status: DecisionEvent["bindingStatus"]) {
  const decisionId = decisionIds[index]!;
  return {
    decisionId,
    commandId: `a${index}000000-0000-4000-8000-00000000000${index}`,
    revision: index + 1,
    occurredAt: `2026-08-27T20:0${index}:00Z`,
    active: true,
    undoable: true,
    targetDecisionId: null,
    supersedesDecisionIds: [],
    bindingStatus: status,
    currentTargetIds: [],
  };
}

export const decisionEvents: readonly DecisionEvent[] = [
  { ...eventBase(0, "NEEDS_REVIEW"), type: "setSourceDisplayName", sourceId: sourceAId, displayName: "Horizonte local" },
  { ...eventBase(1, "ORPHANED"), type: "setSourceRubro", sourceId: sourceAId, rubro: "Trabajo y educación" },
  { ...eventBase(2, "AMBIGUOUS"), type: "setFlowDisplayName", flowId: flowA1Id, displayName: "Noticias para el equipo" },
  { ...eventBase(3, "CONFLICT"), type: "setFlowIntention", flowId: flowA1Id, intention: "Notificación" },
  { ...eventBase(4, "EXACT"), type: "mergeSources", sourceIds: [sourceBId, sourceCId] },
  {
    ...eventBase(5, "EXACT"),
    type: "partitionSource",
    sourceId: sourceAId,
    groupCount: 2,
    groups: [
      { groupIndex: 0, anchorCount: 1, anchorKinds: ["flow"], observedSourceIds: [sourceAId], observedFlowIds: [flowA1Id] },
      { groupIndex: 1, anchorCount: 1, anchorKinds: ["flow"], observedSourceIds: [sourceAId], observedFlowIds: [flowA2Id] },
    ],
  },
  {
    ...eventBase(6, "EXACT"),
    type: "protectTarget",
    target: { kind: "flow", observedEffectiveId: flowA2Id, observedSourceIds: [sourceAId], observedFlowIds: [flowA2Id] },
  },
];

export const decisionsResponse: DecisionListResponse = {
  contractVersion: 1,
  dataMode: "synthetic",
  policyRevision: 7,
  events: decisionEvents,
};

export const writeResponse: WriteResponse = {
  contractVersion: 1,
  dataMode: "synthetic",
  status: "applied",
  replayed: false,
  decisionId: "88888888-8888-4888-8888-888888888888",
  policyRevision: 8,
  mapRevision: nextMapRevision,
  bindingStatus: "EXACT",
};

export function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

export function payloadForPath(path: string): unknown {
  if (path === "/api/v2/context") return context;
  if (path === "/api/v2/connection") return connection;
  if (path === "/api/v2/sync") return sync;
  if (path === "/api/v2/index") return indexResponse;
  if (path === "/api/v2/map") return mapResponse;
  if (path === "/api/v2/decisions") return decisionsResponse;
  if (path.startsWith("/api/v2/map/sources/")) return sourceDetail;
  if (path === "/api/v2/decisions" || path.endsWith("/undo")) return writeResponse;
  return { error: { code: "invalid_request", message: "Solicitud inválida" } };
}
