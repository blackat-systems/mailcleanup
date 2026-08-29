import type { SourceProjection } from "../types";
import { formatBytes, formatCount, formatDate, initials } from "../utils";
import { ConfidenceBadge, ProtectionSummary } from "./MapDetails";
import { Badge } from "./Primitives";
import { Icon } from "./Icon";

export function SourceCard({
  source,
  headingLevel = 2,
}: {
  source: SourceProjection;
  headingLevel?: 2 | 3;
}) {
  const renamed = source.automaticDisplayName !== source.effectiveDisplayName;
  const recategorized = source.automaticRubro !== source.effectiveRubro;
  return (
    <article className="source-card" aria-labelledby={`source-${source.id}`}>
      <div className="source-card-main">
        <div className="source-avatar" aria-hidden="true">{initials(source.effectiveDisplayName)}</div>
        <div className="source-identity">
          <div className="source-title-line">
            {headingLevel === 3 ? (
              <h3 id={`source-${source.id}`}>
                <a href={`#/source/${encodeURIComponent(source.id)}`}>{source.effectiveDisplayName}</a>
              </h3>
            ) : (
              <h2 id={`source-${source.id}`}>
                <a href={`#/source/${encodeURIComponent(source.id)}`}>{source.effectiveDisplayName}</a>
              </h2>
            )}
            {renamed || recategorized ? <Badge tone="positive">Decidido por Joa</Badge> : null}
          </div>
          <p>{source.effectiveRubro}</p>
          <div className="source-meta">
            <span>{formatCount(source.messageCount)} mensajes</span>
            <span>{formatCount(source.flowCount)} flujos</span>
            <span>Última aparición: {formatDate(source.lastSeen)}</span>
            <ConfidenceBadge value={source.effectiveConfidence} />
          </div>
          <ProtectionSummary protection={source.protection} compact />
          <details className="source-card-details">
            <summary>Más contexto</summary>
            <div>
              <span>{formatBytes(source.totalBytes)} indexados</span>
              {renamed ? <span>Nombre automático: {source.automaticDisplayName}</span> : null}
              {recategorized ? <span>Rubro automático: {source.automaticRubro}</span> : null}
            </div>
          </details>
        </div>
      </div>
      <div className="source-card-side">
        {source.reviewRequiredMessageCount > 0 ? (
          <Badge tone="warning">{source.reviewRequiredMessageCount} requieren revisión</Badge>
        ) : null}
        {source.hardExcludedMessageCount > 0 ? (
          <Badge tone="critical">{source.hardExcludedMessageCount} con exclusión dura</Badge>
        ) : null}
        <a className="detail-link" href={`#/source/${encodeURIComponent(source.id)}`}>
          Abrir fuente <Icon name="arrow" />
        </a>
      </div>
    </article>
  );
}
