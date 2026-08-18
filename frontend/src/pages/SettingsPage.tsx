import { api } from "../api";
import { useResource } from "../hooks";
import { Badge, ErrorState, LoadingState, PageHeader } from "../components/Primitives";
import { Icon } from "../components/Icon";

export function SettingsPage() {
  const configuration = useResource(api.configuration);
  const analysis = useResource(api.analysis);
  if (configuration.loading || analysis.loading) return <LoadingState label="Revisando el entorno local…" />;
  if (configuration.error || analysis.error || !configuration.data || !analysis.data) return <ErrorState message={configuration.error ?? analysis.error ?? "Sin estado"} retry={() => { configuration.reload(); analysis.reload(); }} />;
  const config = configuration.data;

  return (
    <div className="page">
      <PageHeader eyebrow="Estado y configuración" title="Límites visibles, no promesas" description="Este tablero muestra qué puede y qué no puede hacer Base Segura." />
      <div className="settings-grid">
        <section className="panel environment-card"><span className="eyebrow">Entorno</span><h2>Aplicación local</h2><dl><div><dt>Plataforma</dt><dd>{config.platform}</dd></div><div><dt>Experiencia</dt><dd>{config.experience}</dd></div><div><dt>Zona civil</dt><dd>{config.timezone}</dd></div><div><dt>Esquema local</dt><dd>Versión {config.schemaVersion}</dd></div></dl></section>
        <section className="panel safety-card"><span className="eyebrow">Capacidades bloqueadas</span><h2>Puertas de seguridad</h2><ul><SafetyItem label="Conexión a Gmail" enabled={config.gmailConnected} /><SafetyItem label="OAuth disponible" enabled={config.oauthAvailable} /><SafetyItem label="IA remota" enabled={config.remoteAi} /><SafetyItem label="Eliminación definitiva" enabled={config.permanentDelete} /></ul></section>
      </div>

      <section className="panel protection-card"><div className="section-heading"><div><span className="eyebrow">Exclusión por defecto</span><h2>Protecciones activas</h2></div><Badge tone="protected">{config.protectedLabels.length} reglas</Badge></div><div className="protection-labels">{config.protectedLabels.map((label) => <span key={label}><Icon name="shield" />{label}</span>)}</div><p>Además se protegen seguridad, documentos, comunicación personal, confianza baja y contradicciones.</p></section>

      <section className="panel analysis-card"><div className="section-heading"><div><span className="eyebrow">Ingesta sintética</span><h2>Recorrido y fallos parciales</h2></div><Badge tone={analysis.data.incidents.length ? "warning" : "positive"}>{analysis.data.incidents.length ? "Completado con advertencias" : "Completado"}</Badge></div><div className="phase-list">{analysis.data.phases.map((phase) => <div key={phase.name}><span><Icon name="check" /></span><strong>{phase.name}</strong><small>{phase.state === "completed" ? "Completado" : phase.state}</small></div>)}</div>{analysis.data.incidents.length ? <div className="incident-list">{analysis.data.incidents.map((incident) => <article key={incident.messageId}><Icon name="info" /><div><strong>{incident.state.replaceAll("_", " ")}</strong><p>{incident.resolution}</p><code>{incident.messageId}</code></div></article>)}</div> : null}</section>
    </div>
  );
}

function SafetyItem({ label, enabled }: { label: string; enabled: boolean }) {
  return <li><span className={enabled ? "status-on" : "status-off"}>{enabled ? "Activa" : "Bloqueada"}</span><strong>{label}</strong></li>;
}
