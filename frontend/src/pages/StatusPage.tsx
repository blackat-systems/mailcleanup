import { Badge, DisclosurePanel, PageHeader } from "../components/Primitives";
import type { CapabilitiesProbe, WorkspaceData } from "../types";
import { formatCount, formatDate, syncLabels } from "../utils";

const capabilityCopy: readonly [keyof CapabilitiesProbe, string][] = [
  ["mapRead", "Lectura del mapa"],
  ["policyWrite", "Registrar correcciones locales"],
  ["policyUndo", "Deshacer correcciones locales"],
  ["gmailConnection", "Conexión a Gmail"],
  ["oauth", "OAuth"],
  ["externalNetwork", "Red externa"],
  ["realData", "Datos reales"],
  ["syncControl", "Controles de sincronización"],
  ["cleanupPlan", "Plan de limpieza"],
  ["messageMutation", "Modificación de mensajes"],
  ["unsubscribe", "Desuscripción"],
  ["execute", "Ejecución"],
];

export function StatusPage({ data }: { data: WorkspaceData }) {
  const { context, connection, index, sync } = data;
  const availableCount = capabilityCopy.filter(([key]) => context.capabilities[key]).length;
  const blockedCount = capabilityCopy.length - availableCount;
  return (
    <div className="page">
      <PageHeader
        eyebrow="Estado de sólo lectura"
        title="Lo disponible y lo bloqueado"
        description="Contexto, conexión, índice y sincronización publicados por C5. Esta pantalla informa estados; no controla ninguno."
      />

      {sync.partial ? (
        <div className="partial-banner" role="status">
          <strong>Mapa parcial.</strong> El estado de sincronización no está completado.
        </div>
      ) : null}

      <section className="status-summary" aria-label="Resumen operativo">
        <div><span>Datos</span><strong>Demo local</strong></div>
        <div><span>Cuenta</span><strong>Sin conectar</strong></div>
        <div><span>Mapa</span><strong>{sync.partial ? "Parcial" : "Completo"}</strong></div>
        <div><span>Capacidades</span><strong>{availableCount} disponibles</strong></div>
      </section>

      <DisclosurePanel
        eyebrow="Diagnóstico local"
        title="Contexto, índice y sincronización"
        summary={syncLabels[sync.state]}
        className="status-diagnostics"
      >
        <div className="status-grid">
          <section className="status-card" aria-labelledby="context-title">
            <h3 id="context-title">Contrato sintético</h3>
            <dl>
              <div><dt>Contrato</dt><dd>v{context.contractVersion}</dd></div>
              <div><dt>Modo de datos</dt><dd>Demostración sintética</dd></div>
              <div><dt>Aplicación</dt><dd>{context.appVersion}</dd></div>
              <div><dt>Cuenta visible</dt><dd>Ninguna</dd></div>
            </dl>
          </section>

          <section className="status-card" aria-labelledby="connection-title">
            <h3 id="connection-title">Sin cuenta conectada</h3>
            <dl>
              <div><dt>Estado</dt><dd>{connection.state === "synthetic" ? "Sintético" : connection.state}</dd></div>
              <div><dt>Dirección</dt><dd>No publicada</dd></div>
              <div><dt>OAuth</dt><dd>Bloqueado</dd></div>
              <div><dt>Red externa</dt><dd>Bloqueada</dd></div>
            </dl>
          </section>

          <section className="status-card" aria-labelledby="index-title">
            <h3 id="index-title">Fixture sintético</h3>
            <dl>
              <div><dt>Estado</dt><dd>Demostración versionada</dd></div>
              <div><dt>Fixture</dt><dd><code>{index.fixtureVersion}</code></dd></div>
              <div><dt>Esquema</dt><dd>v{index.schemaVersion}</dd></div>
              <div><dt>Mensajes</dt><dd>{formatCount(index.messageCount)}</dd></div>
              <div><dt>Borrado desde D6</dt><dd>No disponible</dd></div>
            </dl>
          </section>

          <section className="status-card sync-card" aria-labelledby="sync-title">
            <h3 id="sync-title">{syncLabels[sync.state]}</h3>
            <div className="badge-row">
              <Badge tone={sync.state === "completed" ? "positive" : sync.state === "failed" ? "critical" : "warning"}>
                {syncLabels[sync.state]}
              </Badge>
              <Badge tone={sync.partial ? "warning" : "positive"}>{sync.partial ? "Mapa parcial" : "Mapa completo"}</Badge>
            </div>
            <dl>
              <div><dt>Modo</dt><dd>{sync.mode === "full" ? "Completo" : sync.mode === "partial" ? "Parcial" : "Sin modo"}</dd></div>
              <div><dt>Procesados</dt><dd>{formatCount(sync.processedCount)}</dd></div>
              <div><dt>Inicio</dt><dd>{sync.startedAt ? formatDate(sync.startedAt, true) : "No disponible"}</dd></div>
              <div><dt>Actualización</dt><dd>{sync.updatedAt ? formatDate(sync.updatedAt, true) : "No disponible"}</dd></div>
              <div><dt>Código de estado</dt><dd><code>{sync.errorCode ?? "Sin error"}</code></dd></div>
            </dl>
            <p className="muted">No hay botones para iniciar, pausar, reanudar o reconstruir la sincronización.</p>
          </section>
        </div>
      </DisclosurePanel>

      <DisclosurePanel
        eyebrow="Capacidades efectivas"
        title="Puertas publicadas por C5"
        summary={`${availableCount} disponibles · ${blockedCount} bloqueadas`}
        className="capabilities-card"
      >
        <ul aria-label="Capacidades del contexto">
          {capabilityCopy.map(([key, label]) => (
            <li key={key}>
              <span className={context.capabilities[key] ? "status-on" : "status-off"}>
                {context.capabilities[key] ? "Disponible" : "Bloqueada"}
              </span>
              <strong>{label}</strong>
            </li>
          ))}
        </ul>
      </DisclosurePanel>
    </div>
  );
}
