import type {
  Confianza,
  PolicyBindingStatus,
  PolicyProtectionReason,
  SyncState,
} from "./types";

export function formatCount(value: number): string {
  return new Intl.NumberFormat("es-AR").format(value);
}

export function formatBytes(value: number): string {
  if (value < 1024) return `${value} B`;
  if (value < 1024 ** 2) return `${(value / 1024).toFixed(1)} KB`;
  if (value < 1024 ** 3) return `${(value / 1024 ** 2).toFixed(1)} MB`;
  return `${(value / 1024 ** 3).toFixed(1)} GB`;
}

export function formatDate(value: string, withTime = false): string {
  return new Intl.DateTimeFormat("es-AR", {
    dateStyle: "medium",
    ...(withTime ? { timeStyle: "short" as const } : {}),
    timeZone: "America/Argentina/Cordoba",
  }).format(new Date(value));
}

export function formatMonth(value: string): string {
  const [year, month] = value.split("-");
  const date = new Date(Date.UTC(Number(year), Number(month) - 1, 1));
  return new Intl.DateTimeFormat("es-AR", {
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(date);
}

export function initials(name: string): string {
  return name
    .split(/\s+/u)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

export function confidenceTone(
  value: Confianza,
): "positive" | "neutral" | "warning" | "critical" {
  if (value === "Alta") return "positive";
  if (value === "Media") return "neutral";
  if (value === "Contradictoria") return "critical";
  return "warning";
}

export const syncLabels: Record<SyncState, string> = {
  not_started: "No iniciado",
  running: "En curso",
  paused: "Pausado",
  completed: "Completado",
  requires_full_resync: "Requiere reconstrucción completa",
  failed: "Fallido",
};

export const bindingLabels: Record<PolicyBindingStatus, string> = {
  EXACT: "Aplicación exacta",
  REBOUND: "Reasignada por identidad estable",
  NEEDS_REVIEW: "Necesita revisión",
  ORPHANED: "Sin objetivo vigente",
  AMBIGUOUS: "Objetivo ambiguo",
  CONFLICT: "En conflicto",
};

export const protectionReasonLabels: Record<PolicyProtectionReason, string> = {
  sent: "Enviado",
  draft: "Borrador",
  trash: "Papelera",
  starred: "Con estrella",
  important: "Marcado importante",
  protected_label: "Etiqueta protegida",
  security: "Seguridad",
  document: "Documento",
  personal: "Comunicación personal",
  low_confidence: "Confianza baja",
  contradiction: "Evidencia contradictoria",
  mixed_conversation: "Conversación mixta",
  manual_policy: "Protección decidida por Joa",
  policy_review: "Política pendiente de revisión",
};

export function shortId(value: string): string {
  if (value.length <= 24) return value;
  return `${value.slice(0, 12)}…${value.slice(-8)}`;
}
