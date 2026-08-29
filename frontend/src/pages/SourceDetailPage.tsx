import { api } from "../api";
import { useResource } from "../hooks";
import { formatBytes, formatCount, formatDate, initials } from "../utils";
import { Badge, DisclosurePanel, ErrorState, LoadingState } from "../components/Primitives";
import {
  AutomaticEvidenceList,
  Comparison,
  ConfidenceBadge,
  PolicyEvidenceList,
  ProtectionSummary,
} from "../components/MapDetails";

export function SourceDetailPage({
  id,
  mapRevision,
  partial,
}: {
  id: string;
  mapRevision: string;
  partial: boolean;
}) {
  const resource = useResource(() => api.source(id), [id, mapRevision]);
  if (resource.loading) {
    return (
      <div className="page">
        <h1 className="sr-only">Detalle de fuente</h1>
        <PartialNotice partial={partial} />
        <LoadingState label="Leyendo fuente, flujos y evidencia…" />
      </div>
    );
  }
  if (resource.error || !resource.data) {
    const missing = resource.error?.code === "source_not_found";
    return (
      <div className="page">
        <h1 className="sr-only">Detalle de fuente</h1>
        <PartialNotice partial={partial} />
        <ErrorState
          title={missing ? "Fuente inexistente" : undefined}
          message={resource.error?.message ?? "No hay un detalle válido para esta fuente."}
          retry={missing ? undefined : resource.reload}
          backHref="#/sources"
        />
      </div>
    );
  }
  const source = resource.data;

  return (
    <div className="page detail-page">
      <a className="back-link" href="#/sources">← Volver a fuentes</a>
      <PartialNotice partial={partial} />
      <header className="detail-hero">
        <div className="source-avatar source-avatar-large" aria-hidden="true">
          {initials(source.effectiveDisplayName)}
        </div>
        <div className="detail-title">
          <span className="eyebrow">Fuente efectiva</span>
          <h1>{source.effectiveDisplayName}</h1>
          <p>Primera aparición {formatDate(source.firstSeen)} · última {formatDate(source.lastSeen)}</p>
          <div className="badge-row">
            <ConfidenceBadge value={source.effectiveConfidence} />
            {source.automaticConfidence !== source.effectiveConfidence ? (
              <Badge tone="warning">Automática: {source.automaticConfidence}</Badge>
            ) : null}
            {source.reviewRequiredMessageCount > 0 ? <Badge tone="warning">Revisión obligatoria</Badge> : null}
            {source.hardExcludedMessageCount > 0 ? <Badge tone="critical">Exclusión dura</Badge> : null}
          </div>
        </div>
        <a className="button button-primary" href={`#/corrections?sourceId=${encodeURIComponent(source.id)}`}>
          Corregir esta fuente
        </a>
      </header>

      <section className="detail-metrics" aria-label="Resumen de la fuente">
        <div><span>Mensajes</span><strong>{formatCount(source.messageCount)}</strong></div>
        <div><span>Flujos</span><strong>{formatCount(source.flowCount)}</strong></div>
        <div><span>Protegidos</span><strong>{formatCount(source.protectedMessageCount)}</strong></div>
        <div><span>Volumen indexado estimado</span><strong>{formatBytes(source.totalBytes)}</strong></div>
      </section>

      <DisclosurePanel
        eyebrow="Inferencia y decisión"
        title="Valores automáticos y efectivos"
        summary="3 campos comparados"
        className="comparison-panel"
      >
        <div className="comparison-grid">
          <Comparison label="nombre" automatic={source.automaticDisplayName} effective={source.effectiveDisplayName} />
          <Comparison label="rubro" automatic={source.automaticRubro} effective={source.effectiveRubro} />
          <Comparison label="confianza" automatic={source.automaticConfidence} effective={source.effectiveConfidence} />
        </div>
      </DisclosurePanel>

      <DisclosurePanel
        eyebrow="Conservación"
        title="Protección de la fuente"
        summary={source.protection.protected ? "Protegida" : "Sin protección adicional"}
        className="protection-panel"
      >
        <ProtectionSummary protection={source.protection} />
      </DisclosurePanel>

      <section className="panel flow-panel" aria-labelledby="flows-title">
        <div className="section-heading">
          <div><span className="eyebrow">Fuente ≠ flujo</span><h2 id="flows-title">Flujos dentro de la fuente</h2></div>
        </div>
        <div className="flow-card-list">
          {source.flows.map((flow) => (
            <article key={flow.id} className="flow-card" aria-labelledby={`flow-${flow.id}`}>
              <div className="flow-card-heading">
                <div>
                  <h3 id={`flow-${flow.id}`}>{flow.effectiveDisplayName}</h3>
                </div>
                <div className="badge-row">
                  <Badge>{flow.effectiveIntention}</Badge>
                  <Badge>{flow.subscription}</Badge>
                  <ConfidenceBadge value={flow.effectiveConfidence} />
                  {flow.protection.protected ? <Badge tone="protected">Protegido</Badge> : null}
                  {flow.protection.reviewRequired || flow.reviewRequiredMessageCount > 0 ? (
                    <Badge tone="warning">Revisión obligatoria</Badge>
                  ) : null}
                  {flow.protection.hardExcluded || flow.hardExcludedMessageCount > 0 ? (
                    <Badge tone="critical">Exclusión dura</Badge>
                  ) : null}
                </div>
              </div>
              <div className="flow-counts">
                <span>{formatCount(flow.messageCount)} mensajes</span>
                <span>{formatBytes(flow.totalBytes)} indexados</span>
                <span>{formatCount(flow.protectedMessageCount)} protegidos</span>
              </div>
              <details className="flow-details">
                <summary>Clasificación, protección y evidencia</summary>
                <div className="flow-details-content">
                  <div className="comparison-grid">
                    <Comparison label="nombre" automatic={flow.automaticDisplayName} effective={flow.effectiveDisplayName} />
                    <Comparison label="intención" automatic={flow.automaticIntention} effective={flow.effectiveIntention} />
                    <Comparison label="confianza" automatic={flow.automaticConfidence} effective={flow.effectiveConfidence} />
                  </div>
                  <ProtectionSummary protection={flow.protection} />
                  <div className="evidence-columns">
                    <div><h4>Automática</h4><AutomaticEvidenceList evidence={flow.automaticEvidence} /></div>
                    <div><h4>Decisiones de Joa</h4><PolicyEvidenceList evidence={flow.effectiveEvidence} /></div>
                  </div>
                </div>
              </details>
            </article>
          ))}
        </div>
      </section>

      <DisclosurePanel
        eyebrow="Explicación"
        title="Cómo se clasificó esta fuente"
        summary={`${source.automaticEvidence.length} señales automáticas`}
        className="evidence-panel"
      >
        <div className="detail-grid">
          <section className="evidence-section" aria-labelledby="automatic-evidence-title">
            <h3 id="automatic-evidence-title">Evidencia automática</h3>
            <AutomaticEvidenceList evidence={source.automaticEvidence} />
          </section>
          <section className="evidence-section" aria-labelledby="policy-evidence-title">
            <h3 id="policy-evidence-title">Decisiones de Joa</h3>
            <PolicyEvidenceList evidence={source.effectiveEvidence} />
          </section>
        </div>
      </DisclosurePanel>

      <DisclosurePanel
        eyebrow="Detalles técnicos"
        title="Remitentes y dominios"
        summary={`${source.senders.length} remitentes · ${source.domains.length} dominios`}
        className="sender-panel"
      >
        <div className="identity-columns">
          <div><h3>Remitentes</h3>{source.senders.map((sender) => <code key={sender}>{sender}</code>)}</div>
          <div><h3>Dominios</h3>{source.domains.map((domain) => <code key={domain}>{domain}</code>)}</div>
        </div>
      </DisclosurePanel>

      <section className="panel message-panel" aria-labelledby="message-samples-title">
        <div className="section-heading">
          <div>
            <span className="eyebrow">Máximo cinco muestras</span>
            <h2 id="message-samples-title">Metadatos recientes permitidos</h2>
          </div>
          <span>{source.recentMessages.length} muestras · sin contenido</span>
        </div>
        <p className="muted privacy-note">Sin contenido ni recursos remotos.</p>
        {source.recentMessages.length === 0 ? <p className="muted">No hay muestras recientes.</p> : (
          <div className="message-card-list">
            {source.recentMessages.map((message) => (
              <details key={message.id} className="message-card">
                <summary className="message-main">
                  <strong>{message.subject ?? "Sin asunto publicado"}</strong>
                  <span>{message.senderName ?? "Sin nombre publicado"} · {message.senderAddress ?? "Sin dirección publicada"}</span>
                  <small>{formatDate(message.receivedAt, true)} · {formatBytes(message.sizeEstimateBytes)} · ver clasificación</small>
                  <span className="badge-row message-alerts">
                    {message.effectiveConfidence === "Contradictoria" ? (
                      <ConfidenceBadge value={message.effectiveConfidence} />
                    ) : null}
                    {message.protection.protected ? <Badge tone="protected">Protegido</Badge> : null}
                    {message.protection.reviewRequired ? <Badge tone="warning">Revisión obligatoria</Badge> : null}
                    {message.protection.hardExcluded ? <Badge tone="critical">Exclusión dura</Badge> : null}
                  </span>
                </summary>
                <div className="message-details">
                  <div className="comparison-grid">
                    <Comparison label="rubro" automatic={message.automaticRubro} effective={message.effectiveRubro} />
                    <Comparison label="intención" automatic={message.automaticIntention} effective={message.effectiveIntention} />
                    <Comparison label="confianza" automatic={message.automaticConfidence} effective={message.effectiveConfidence} />
                  </div>
                  <div className="message-labels" aria-label="Etiquetas publicadas">
                    {message.labelIds.map((label) => <code key={label}>{label}</code>)}
                  </div>
                  <ProtectionSummary protection={message.protection} />
                </div>
              </details>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function PartialNotice({ partial }: { partial: boolean }) {
  return partial ? (
    <div className="partial-banner" role="status">
      <strong>Mapa parcial.</strong> La pertenencia de esta fuente y sus conteos pueden cambiar.
    </div>
  ) : null;
}
