import { api } from "../api";
import { useResource } from "../hooks";
import { confidenceTone, formatBytes, formatDate, initials } from "../utils";
import { Badge, ErrorState, LoadingState } from "../components/Primitives";
import { Icon } from "../components/Icon";

type Props = { id: string; selected: boolean; onToggle: (id: string) => void };

export function SourceDetailPage({ id, selected, onToggle }: Props) {
  const resource = useResource(() => api.source(id), [id]);
  if (resource.loading) return <LoadingState label="Reconstruyendo la evidencia…" />;
  if (resource.error || !resource.data) return <ErrorState message={resource.error ?? "Fuente no encontrada"} retry={resource.reload} />;
  const source = resource.data;

  return (
    <div className="page detail-page">
      <a className="back-link" href="#/sources">← Volver a fuentes</a>
      <header className="detail-hero">
        <div className="source-avatar source-avatar-large">{initials(source.name)}</div>
        <div className="detail-title"><span className="eyebrow">Fuente sugerida</span><h1>{source.name}</h1><p>{source.rubro} · activa desde {formatDate(source.firstSeen)}</p><div className="badge-row"><Badge tone={confidenceTone(source.confidence)}>Confianza {source.confidence.toLowerCase()}</Badge><Badge tone={source.ambiguous ? "warning" : "positive"}>{source.ambiguous ? "Identidad ambigua" : "Identidad consistente"}</Badge>{source.protectedCount ? <Badge tone="protected">{source.protectedCount} protegidos</Badge> : null}</div></div>
        <button className={`button ${selected ? "button-secondary" : "button-primary"}`} type="button" onClick={() => onToggle(source.id)}>{selected ? "Quitar del plan" : "Sumar al plan"}</button>
      </header>

      <section className="detail-metrics" aria-label="Resumen de la fuente">
        <div><span>Mensajes</span><strong>{source.messageCount}</strong></div><div><span>Flujos</span><strong>{source.flows.length}</strong></div><div><span>Candidatos</span><strong>{source.candidateCount}</strong></div><div><span>Volumen</span><strong>{formatBytes(source.totalBytes)}</strong></div>
      </section>

      <div className="detail-grid">
        <section className="panel"><div className="section-heading"><div><span className="eyebrow">Separación semántica</span><h2>Flujos dentro de la fuente</h2></div></div><div className="flow-list">{source.flows.map((flow) => <article key={flow.id}><div><strong>{flow.name}</strong><span>{flow.subscriptionStates.join(" · ")}</span></div><div><strong>{flow.messageCount}</strong><small>mensajes</small></div>{flow.protectedCount ? <Badge tone="protected">{flow.protectedCount} protegidos</Badge> : null}</article>)}</div></section>
        <section className="panel evidence-panel"><div className="section-heading"><div><span className="eyebrow">Por qué se agrupó</span><h2>Evidencias</h2></div></div><ol>{source.evidence.map((evidence) => <li key={evidence.code}><span className="evidence-mark"><Icon name="check" /></span><div><strong>{evidence.label}</strong><p>{evidence.detail}</p><small>Señal {evidence.strength}</small></div></li>)}</ol></section>
      </div>

      <section className="panel sender-panel"><div className="section-heading"><div><span className="eyebrow">Identidad observada</span><h2>Remitentes y dominios</h2></div></div><div className="identity-columns"><div><h3>Remitentes</h3>{source.senders.map((sender) => <code key={sender}>{sender}</code>)}</div><div><h3>Dominios autenticados</h3>{source.domains.map((domain) => <code key={domain}>{domain}</code>)}</div></div></section>

      <section className="panel message-panel"><div className="section-heading"><div><span className="eyebrow">Muestra segura</span><h2>Metadatos recientes</h2></div><span>Sin cuerpos ni imágenes</span></div><div className="message-table">{source.recentMessages.map((message) => <article key={message.id}><div className="message-main"><strong>{message.subject}</strong><span>{message.senderEmail}</span></div><div><span>{message.intencion}</span><small>{formatDate(message.receivedAt, true)}</small></div><div className="badge-row"><Badge tone={message.protected ? "protected" : "neutral"}>{message.proteccion}</Badge><Badge tone={confidenceTone(message.confianza)}>{message.confianza}</Badge></div></article>)}</div></section>
    </div>
  );
}
