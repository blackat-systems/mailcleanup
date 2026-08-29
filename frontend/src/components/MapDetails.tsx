import type {
  ClassificationEvidence,
  MapEvidence,
  ProtectionProjection,
} from "../types";
import { confidenceTone, protectionReasonLabels } from "../utils";
import { Badge, PublicId } from "./Primitives";
import { Icon } from "./Icon";

export function Comparison({
  label,
  automatic,
  effective,
  changedNote = "Decidido por Joa",
}: {
  label: string;
  automatic: string;
  effective: string;
  changedNote?: string;
}) {
  const changed = automatic !== effective;
  return (
    <div className={`comparison ${changed ? "is-changed" : ""}`}>
      <div>
        <span>Automático · {label}</span>
        <strong>{automatic}</strong>
      </div>
      <div>
        <span>Efectivo · {label}</span>
        <strong>{effective}</strong>
        <small>{changed ? changedNote : "Coincide con el valor automático"}</small>
      </div>
    </div>
  );
}

export function ConfidenceBadge({ value }: { value: Parameters<typeof confidenceTone>[0] }) {
  return <Badge tone={confidenceTone(value)}>Confianza {value.toLocaleLowerCase("es")}</Badge>;
}

export function ProtectionSummary({
  protection,
  compact = false,
}: {
  protection: ProtectionProjection;
  compact?: boolean;
}) {
  return (
    <div className={`protection-summary ${compact ? "is-compact" : ""}`}>
      <div className="badge-row">
        <Badge tone={protection.protected ? "protected" : "neutral"}>
          {protection.protected ? "Protegido" : "Sin protección adicional"}
        </Badge>
        {protection.reviewRequired ? <Badge tone="warning">Revisión obligatoria</Badge> : null}
        {protection.hardExcluded ? <Badge tone="critical">Exclusión dura</Badge> : null}
      </div>
      {!compact ? (
        <>
          <Comparison
            label="protección"
            automatic={protection.automatic}
            effective={protection.effective}
            changedNote="Resultado efectivo de reglas y decisiones locales"
          />
          {protection.reasons.length > 0 ? (
            <ul className="reason-list" aria-label="Razones de protección">
              {protection.reasons.map((reason) => <li key={reason}>{protectionReasonLabels[reason]}</li>)}
            </ul>
          ) : <p className="muted">No hay razones de protección registradas.</p>}
        </>
      ) : null}
    </div>
  );
}

export function AutomaticEvidenceList({ evidence }: { evidence: readonly ClassificationEvidence[] }) {
  if (evidence.length === 0) return <p className="muted">Sin evidencia automática publicada.</p>;
  return (
    <ol className="evidence-list" aria-label="Evidencia automática">
      {evidence.map((item) => (
        <li key={`${item.code}-${item.origin}-${item.detail}`}>
          <span className="evidence-mark"><Icon name="check" /></span>
          <div>
            <strong>{item.label}</strong>
            <p>{item.detail}</p>
            <small>Fuerza {item.strength} · origen {item.origin}</small>
          </div>
        </li>
      ))}
    </ol>
  );
}

export function PolicyEvidenceList({ evidence }: { evidence: readonly MapEvidence[] }) {
  const policies = evidence.filter((item) => item.kind === "policy");
  if (policies.length === 0) return <p className="muted">No hay decisiones de Joa aplicadas aquí.</p>;
  return (
    <ul className="policy-evidence-list" aria-label="Evidencia de decisiones de Joa">
      {policies.map((item) => (
        <li key={`${item.code}-${item.decisionId}`}>
          <Icon name="corrections" />
          <div>
            <strong>{policyEvidenceLabel(item.code)}</strong>
            <PublicId value={item.decisionId} />
          </div>
        </li>
      ))}
    </ul>
  );
}

function policyEvidenceLabel(code: Extract<MapEvidence, { kind: "policy" }>["code"]): string {
  switch (code) {
    case "policy.source_display_name": return "Nombre de fuente decidido por Joa";
    case "policy.source_rubro": return "Rubro decidido por Joa";
    case "policy.flow_display_name": return "Nombre de flujo decidido por Joa";
    case "policy.flow_intention": return "Intención decidida por Joa";
    case "policy.merge_sources": return "Unión manual de fuentes";
    case "policy.partition_source": return "Separación manual de fuente";
    case "policy.protect_target": return "Protección decidida por Joa";
  }
}
