import type { SourceRecord } from "../types";
import { confidenceTone, formatCount, formatDate, initials } from "../utils";
import { Badge } from "./Primitives";
import { Icon } from "./Icon";

type Props = {
  source: SourceRecord;
  selected: boolean;
  onToggle: (id: string) => void;
};

export function SourceCard({ source, selected, onToggle }: Props) {
  return (
    <article className={`source-card ${selected ? "is-selected" : ""}`}>
      <div className="source-card-main">
        <div className="source-avatar">{initials(source.name)}</div>
        <div className="source-identity">
          <div className="source-title-line">
            <h3><a href={`#/source/${source.id}`}>{source.name}</a></h3>
            {source.protectedCount > 0 ? <Badge tone="protected">{source.protectedCount} protegidos</Badge> : null}
          </div>
          <p>{source.rubro} · {source.dominantIntent}</p>
          <div className="source-meta">
            <span>{formatCount(source.messageCount)} mensajes</span>
            <span>Último: {formatDate(source.lastSeen)}</span>
            <Badge tone={confidenceTone(source.confidence)}>Confianza {source.confidence.toLowerCase()}</Badge>
          </div>
        </div>
      </div>
      <div className="source-card-side">
        <span className="recommendation">{source.recommendation}</span>
        <label className="select-control">
          <input type="checkbox" checked={selected} onChange={() => onToggle(source.id)} />
          <span>{selected ? "En el plan" : "Sumar al plan"}</span>
        </label>
        <a className="detail-link" href={`#/source/${source.id}`}>Ver evidencia <Icon name="arrow" /></a>
      </div>
    </article>
  );
}
