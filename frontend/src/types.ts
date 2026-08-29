export const RUBROS = [
  "Medios y contenido",
  "Software y servicios digitales",
  "Comercio y compras",
  "Finanzas",
  "Trabajo y educación",
  "Salud y gobierno",
  "Viajes y entretenimiento",
  "Social y comunidades",
  "Servicios domésticos",
  "Personal",
  "Desconocido",
] as const;

export const INTENCIONES = [
  "Seguridad",
  "Documento o comprobante",
  "Operativo o soporte",
  "Notificación",
  "Informativo o editorial",
  "Promocional o venta",
  "Comunicación personal",
  "Sospechoso",
  "Desconocido",
] as const;

export const SUSCRIPCIONES = [
  "Confirmada",
  "Probable",
  "No corresponde",
  "Baja solicitada",
  "Posible incumplimiento",
  "Desconocido",
] as const;

export const CONFIANZAS = ["Alta", "Media", "Baja", "Contradictoria"] as const;

export const PROTECCIONES = [
  "Crítica",
  "Documental",
  "Elegida por el usuario",
  "Ordinaria",
  "Revisión obligatoria",
] as const;

export const SYNC_STATES = [
  "not_started",
  "running",
  "paused",
  "completed",
  "requires_full_resync",
  "failed",
] as const;

export const BINDING_STATES = [
  "EXACT",
  "REBOUND",
  "NEEDS_REVIEW",
  "ORPHANED",
  "AMBIGUOUS",
  "CONFLICT",
] as const;

export const REVIEW_BINDING_STATES = [
  "NEEDS_REVIEW",
  "ORPHANED",
  "AMBIGUOUS",
  "CONFLICT",
] as const;

export const PROTECTION_REASONS = [
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
] as const;

export const POLICY_EVIDENCE_CODES = [
  "policy.source_display_name",
  "policy.source_rubro",
  "policy.flow_display_name",
  "policy.flow_intention",
  "policy.merge_sources",
  "policy.partition_source",
  "policy.protect_target",
] as const;

export type Rubro = (typeof RUBROS)[number];
export type Intencion = (typeof INTENCIONES)[number];
export type Suscripcion = (typeof SUSCRIPCIONES)[number];
export type Confianza = (typeof CONFIANZAS)[number];
export type Proteccion = (typeof PROTECCIONES)[number];
export type SyncState = (typeof SYNC_STATES)[number];
export type SyncMode = "full" | "partial";
export type PolicyBindingStatus = (typeof BINDING_STATES)[number];
export type ReviewBindingStatus = (typeof REVIEW_BINDING_STATES)[number];
export type PolicyProtectionReason = (typeof PROTECTION_REASONS)[number];
export type PolicyEvidenceCode = (typeof POLICY_EVIDENCE_CODES)[number];
export type EvidenceStrength = "strong" | "medium" | "weak";
export type EvidenceOrigin =
  | "record"
  | "sender"
  | "authentication"
  | "subject"
  | "label"
  | "category"
  | "list"
  | "unsubscribe"
  | "aggregation";

export type CapabilitiesProbe = {
  mapRead: boolean;
  policyWrite: boolean;
  policyUndo: boolean;
  gmailConnection: boolean;
  oauth: boolean;
  externalNetwork: boolean;
  realData: boolean;
  syncControl: boolean;
  cleanupPlan: boolean;
  messageMutation: boolean;
  unsubscribe: boolean;
  execute: boolean;
};

export type ContextProbe = {
  contractVersion: number;
  dataMode: string;
  appVersion: string;
  account: { state: string; displayAddress: string | null };
  capabilities: CapabilitiesProbe;
};

export type MapContext = ContextProbe & {
  contractVersion: 1;
  dataMode: "synthetic";
  account: { state: "synthetic"; displayAddress: null };
  capabilities: {
    mapRead: true;
    policyWrite: true;
    policyUndo: true;
    gmailConnection: false;
    oauth: false;
    externalNetwork: false;
    realData: false;
    syncControl: false;
    cleanupPlan: false;
    messageMutation: false;
    unsubscribe: false;
    execute: false;
  };
};

export type ConnectionResponse = {
  contractVersion: 1;
  dataMode: "synthetic";
  state: "synthetic";
  displayAddress: null;
  capabilities: {
    gmailConnection: false;
    oauth: false;
    externalNetwork: false;
    realData: false;
  };
};

export type SyncProjection = {
  state: SyncState;
  mode: SyncMode | null;
  processedCount: number;
  startedAt: string | null;
  updatedAt: string | null;
  errorCode: string | null;
  partial: boolean;
};

export type SyncResponse = SyncProjection & {
  contractVersion: 1;
  dataMode: "synthetic";
};

export type IndexResponse = {
  contractVersion: 1;
  dataMode: "synthetic";
  state: "synthetic_fixture";
  fixtureVersion: string;
  schemaVersion: number;
  messageCount: number;
  partial: boolean;
  canDelete: false;
};

export type ClassificationEvidence = {
  kind: "classification";
  code: string;
  label: string;
  detail: string;
  strength: EvidenceStrength;
  origin: EvidenceOrigin;
};

export type PolicyEvidence = {
  kind: "policy";
  code: PolicyEvidenceCode;
  decisionId: string;
};

export type MapEvidence = ClassificationEvidence | PolicyEvidence;

export type ProtectionProjection = {
  automatic: Proteccion;
  effective: Proteccion;
  protected: boolean;
  reviewRequired: boolean;
  hardExcluded: boolean;
  reasons: readonly PolicyProtectionReason[];
};

export type MonthlyVolume = {
  month: string;
  messageCount: number;
  totalBytes: number;
};

export type FlowProjection = {
  id: string;
  sourceId: string;
  automaticFlowId: string;
  automaticDisplayName: string;
  effectiveDisplayName: string;
  automaticIntention: Intencion;
  effectiveIntention: Intencion;
  subscription: Suscripcion;
  automaticConfidence: Confianza;
  effectiveConfidence: Confianza;
  messageCount: number;
  protectedMessageCount: number;
  reviewRequiredMessageCount: number;
  hardExcludedMessageCount: number;
  totalBytes: number;
  firstSeen: string;
  lastSeen: string;
  protection: ProtectionProjection;
  automaticEvidence: readonly ClassificationEvidence[];
  effectiveEvidence: readonly MapEvidence[];
  decisionIds: readonly string[];
  structuralDecisionIds: readonly string[];
};

export type SourceProjection = {
  id: string;
  automaticSourceIds: readonly string[];
  automaticDisplayName: string;
  effectiveDisplayName: string;
  automaticRubro: Rubro;
  effectiveRubro: Rubro;
  automaticConfidence: Confianza;
  effectiveConfidence: Confianza;
  messageCount: number;
  flowCount: number;
  protectedMessageCount: number;
  reviewRequiredMessageCount: number;
  hardExcludedMessageCount: number;
  totalBytes: number;
  firstSeen: string;
  lastSeen: string;
  senders: readonly string[];
  domains: readonly string[];
  monthlyVolume: readonly MonthlyVolume[];
  protection: ProtectionProjection;
  automaticEvidence: readonly ClassificationEvidence[];
  effectiveEvidence: readonly MapEvidence[];
  decisionIds: readonly string[];
  structuralDecisionIds: readonly string[];
  flows: readonly FlowProjection[];
};

export type MapSummary = {
  messageCount: number;
  sourceCount: number;
  flowCount: number;
  protectedMessageCount: number;
  reviewRequiredMessageCount: number;
  hardExcludedMessageCount: number;
  totalBytes: number;
  firstSeen: string | null;
  lastSeen: string | null;
};

export type PolicyReviewBinding = {
  decisionId: string;
  status: ReviewBindingStatus;
  currentEffectiveIds: readonly string[];
};

export type MapResponse = {
  contractVersion: 1;
  dataMode: "synthetic";
  mapRevision: string;
  policyRevision: number;
  sync: SyncProjection;
  summary: MapSummary;
  policyReview: {
    total: number;
    bindings: readonly PolicyReviewBinding[];
  };
  sources: readonly SourceProjection[];
};

export type MessageSample = {
  id: string;
  receivedAt: string;
  senderName: string | null;
  senderAddress: string | null;
  subject: string | null;
  labelIds: readonly string[];
  category: string | null;
  sizeEstimateBytes: number;
  sourceId: string;
  flowId: string;
  automaticRubro: Rubro;
  effectiveRubro: Rubro;
  automaticIntention: Intencion;
  effectiveIntention: Intencion;
  subscription: Suscripcion;
  automaticConfidence: Confianza;
  effectiveConfidence: Confianza;
  protection: ProtectionProjection;
};

export type SourceDetailResponse = SourceProjection & {
  contractVersion: 1;
  dataMode: "synthetic";
  recentMessages: readonly MessageSample[];
};

type DecisionEventBase = {
  decisionId: string | null;
  commandId: string;
  revision: number;
  occurredAt: string;
  active: boolean;
  undoable: boolean;
  targetDecisionId: string | null;
  supersedesDecisionIds: readonly string[];
  bindingStatus: PolicyBindingStatus | null;
  currentTargetIds: readonly string[];
};

export type TargetSummary = {
  kind: "source" | "flow" | "message" | "sender" | "label";
  observedEffectiveId: string | null;
  observedSourceIds: readonly string[];
  observedFlowIds: readonly string[];
};

export type PartitionGroupSummary = {
  groupIndex: number;
  anchorCount: number;
  anchorKinds: readonly ("flow" | "message" | "sender")[];
  observedSourceIds: readonly string[];
  observedFlowIds: readonly string[];
};

export type DecisionEvent =
  | (DecisionEventBase & {
      type: "setSourceDisplayName";
      decisionId: string;
      sourceId: string;
      displayName: string;
    })
  | (DecisionEventBase & {
      type: "setSourceRubro";
      decisionId: string;
      sourceId: string;
      rubro: Rubro;
    })
  | (DecisionEventBase & {
      type: "setFlowDisplayName";
      decisionId: string;
      flowId: string;
      displayName: string;
    })
  | (DecisionEventBase & {
      type: "setFlowIntention";
      decisionId: string;
      flowId: string;
      intention: Intencion;
    })
  | (DecisionEventBase & {
      type: "mergeSources";
      decisionId: string;
      sourceIds: readonly string[];
    })
  | (DecisionEventBase & {
      type: "partitionSource";
      decisionId: string;
      sourceId: string;
      groupCount: number;
      groups: readonly PartitionGroupSummary[];
    })
  | (DecisionEventBase & {
      type: "protectTarget";
      decisionId: string;
      target: TargetSummary;
    })
  | (DecisionEventBase & {
      type: "undoPolicy";
      decisionId: null;
      targetDecisionId: string;
    });

export type DecisionListResponse = {
  contractVersion: 1;
  dataMode: "synthetic";
  policyRevision: number;
  events: readonly DecisionEvent[];
};

type CommandMetadata = {
  commandId: string;
  occurredAt: string;
  expectedMapRevision: string;
  expectedPolicyRevision: number;
};

type DecisionMetadata = CommandMetadata & {
  decisionId: string;
  supersedesDecisionIds: readonly string[];
};

export type SourceTarget = { kind: "source"; sourceId: string };
export type FlowTarget = { kind: "flow"; flowId: string };
export type MessageTarget = { kind: "message"; messageId: string };
export type SenderTarget = { kind: "sender"; senderAddress: string };
export type LabelTarget = { kind: "label"; labelId: string };
export type ProtectionTarget =
  | SourceTarget
  | FlowTarget
  | MessageTarget
  | SenderTarget
  | LabelTarget;

export type FlowPartitionAnchor = { kind: "flow"; flowId: string };

export type DecisionRequest =
  | (DecisionMetadata & {
      type: "setSourceDisplayName";
      sourceId: string;
      displayName: string;
    })
  | (DecisionMetadata & { type: "setSourceRubro"; sourceId: string; rubro: Rubro })
  | (DecisionMetadata & {
      type: "setFlowDisplayName";
      flowId: string;
      displayName: string;
    })
  | (DecisionMetadata & {
      type: "setFlowIntention";
      flowId: string;
      intention: Intencion;
    })
  | (DecisionMetadata & { type: "mergeSources"; sourceIds: readonly string[] })
  | (DecisionMetadata & {
      type: "partitionSource";
      sourceId: string;
      groups: readonly { anchors: readonly FlowPartitionAnchor[] }[];
    })
  | (DecisionMetadata & { type: "protectTarget"; target: ProtectionTarget });

export type UndoRequest = CommandMetadata;

export type WriteResponse = {
  contractVersion: 1;
  dataMode: "synthetic";
  status: "applied";
  replayed: boolean;
  decisionId: string;
  policyRevision: number;
  mapRevision: string;
  bindingStatus: PolicyBindingStatus | null;
};

export type PublicErrorCode =
  | "invalid_request"
  | "invalid_local_origin"
  | "source_not_found"
  | "decision_not_found"
  | "map_revision_conflict"
  | "policy_revision_conflict"
  | "command_id_conflict"
  | "policy_conflict"
  | "invalid_transition"
  | "payload_too_large"
  | "json_required"
  | "target_not_found"
  | "unsupported_target"
  | "map_unavailable"
  | "account_unavailable"
  | "internal_error";

export type WorkspaceData = {
  context: MapContext;
  connection: ConnectionResponse;
  sync: SyncResponse;
  index: IndexResponse;
  map: MapResponse;
  decisions: DecisionListResponse;
};
