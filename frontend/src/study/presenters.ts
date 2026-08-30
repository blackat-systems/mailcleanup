import type {
  Disposition,
  EventType,
  ExclusionReason,
  InventoryState,
  MemberCurrentState,
  MemberFilter,
  MemberInitialState,
  PlanState,
  ReadState,
  StorageEffect,
  WarningCode,
} from "./types";

export const planStateLabels: Record<PlanState, string> = {
  frozen: "Congelado",
  reduced: "Selección reducida",
  invalidated: "Invalidado",
  cancelled: "Cancelado",
  expired: "Vencido",
};

export const inventoryStateLabels: Record<InventoryState, string> = {
  not_started: "No iniciado",
  running: "En curso",
  paused: "Pausado",
  completed: "Completado",
  requires_full_resync: "Requiere reconstrucción completa",
  failed: "Fallido",
};

export const dispositionLabels: Record<Disposition, string> = {
  archive: "Archivo",
  trash: "Papelera",
};

export const readStateLabels: Record<ReadState, string> = {
  any: "Leídos y no leídos",
  read: "Sólo leídos",
  unread: "Sólo no leídos",
};

export const storageEffectLabels: Record<StorageEffect, string> = {
  none: "Archivar no libera almacenamiento.",
  not_guaranteed: "Mover a Papelera no garantiza una liberación inmediata ni definitiva.",
};

export const warningLabels: Record<WarningCode, string> = {
  current_snapshot_unavailable: "La fotografía sintética actual no está disponible.",
  map_changed_since_creation: "El mapa cambió desde la creación.",
  policy_changed_since_creation: "Las decisiones de protección cambiaron desde la creación.",
  selection_reduced: "La selección fue reducida de forma conservadora.",
};

export const exclusionReasonLabels: Record<ExclusionReason, string> = {
  sent: "Enviado",
  draft: "Borrador",
  trash: "Ya estaba en Papelera",
  starred: "Con estrella",
  important: "Marcado importante",
  protected_label: "Etiqueta protegida",
  security: "Seguridad",
  document: "Documento",
  personal: "Comunicación personal",
  low_confidence: "Confianza baja",
  contradiction: "Evidencia contradictoria",
  mixed_conversation: "Conversación mixta",
  manual_policy: "Protección manual",
  policy_review: "Política pendiente de revisión",
  outside_date: "Fuera del período",
  read_state_mismatch: "No coincide con el estado de lectura",
  excluded_label: "Etiqueta excluida",
  keep_latest: "Conservado entre los últimos del flujo",
  missing_after_creation: "Ya no está en la fotografía actual",
  scope_changed: "Dejó de pertenecer al alcance",
  protection_changed: "Quedó protegido después de la creación",
};

export const eventTypeLabels: Record<EventType, string> = {
  created: "Creado",
  revalidated: "Revalidado sin bajas",
  reduced: "Reducido",
  invalidated: "Invalidado",
  cancelled: "Cancelado",
};

export const memberFilterLabels: Record<MemberFilter, string> = {
  all: "Todo el universo inicial",
  selected: "Selección original",
  eligible: "Elegibles actuales",
  excluded: "Excluidos al crear",
  removed: "Retirados después",
};

export const memberInitialLabels: Record<MemberInitialState, string> = {
  selected: "Seleccionado al crear",
  excluded: "Excluido al crear",
};

export const memberCurrentLabels: Record<MemberCurrentState, string> = {
  eligible: "Elegible actualmente",
  excluded: "Excluido desde la creación",
  removed: "Retirado en una revalidación",
};
