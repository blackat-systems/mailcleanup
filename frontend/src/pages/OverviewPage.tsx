import type { MapResponse, MonthlyVolume } from "../types";
import { formatBytes, formatCount, formatDate, formatMonth } from "../utils";
import { Icon } from "../components/Icon";
import { Badge, DisclosurePanel, EmptyState, PageHeader, StatCard } from "../components/Primitives";
import { SourceCard } from "../components/SourceCard";

function aggregateMonthlyVolume(map: MapResponse): MonthlyVolume[] {
  const totals = new Map<string, { messageCount: number; totalBytes: number }>();
  for (const source of map.sources) {
    for (const item of source.monthlyVolume) {
      const current = totals.get(item.month) ?? { messageCount: 0, totalBytes: 0 };
      totals.set(item.month, {
        messageCount: current.messageCount + item.messageCount,
        totalBytes: current.totalBytes + item.totalBytes,
      });
    }
  }
  return [...totals.entries()]
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([month, values]) => ({ month, ...values }));
}

export function OverviewPage({ map }: { map: MapResponse }) {
  const monthly = aggregateMonthlyVolume(map);
  const maxMonthly = Math.max(...monthly.map((item) => item.messageCount), 1);
  const period = map.summary.firstSeen && map.summary.lastSeen
    ? `${formatDate(map.summary.firstSeen)} — ${formatDate(map.summary.lastSeen)}`
    : "Sin apariciones registradas";

  return (
    <div className="page">
      <PageHeader
        eyebrow="Panorama sintético"
        title="Mapa Total con datos de demostración"
        description="Una lectura explicable de fuentes, flujos, evidencia y protecciones. No representa una cuenta conectada ni correos reales."
        actions={<a className="button button-primary" href="#/sources">Explorar fuentes <Icon name="arrow" /></a>}
      />

      <section className="safety-banner" aria-label="Estado de seguridad">
        <Icon name="shield" />
        <div>
          <strong>Demostración local sin acceso externo</strong>
          <p>Sin credenciales · sin conexión a Gmail · sin acciones sobre mensajes</p>
        </div>
        <Badge tone={map.sync.partial ? "warning" : "positive"}>
          {map.sync.partial ? "Mapa parcial" : "Fotografía completada"}
        </Badge>
      </section>

      <section className="stats-grid" aria-label="Resumen del mapa">
        <StatCard
          label="Mensajes indexados"
          value={formatCount(map.summary.messageCount)}
          note={`Período: ${period}`}
          tone="ink"
        />
        <StatCard
          label="Fuentes efectivas"
          value={formatCount(map.summary.sourceCount)}
          note={`${formatCount(map.summary.flowCount)} flujos separados`}
          tone="blue"
        />
        <StatCard
          label="Volumen indexado estimado"
          value={formatBytes(map.summary.totalBytes)}
          note="No representa espacio liberable"
          tone="green"
        />
        <StatCard
          label="Protegidos"
          value={formatCount(map.summary.protectedMessageCount)}
          note={`${formatCount(map.summary.reviewRequiredMessageCount)} requieren revisión`}
          tone="gold"
        />
      </section>

      {map.summary.messageCount === 0 ? (
        <EmptyState
          title="El mapa está disponible, pero vacío"
          detail="La fotografía sintética no contiene mensajes, fuentes ni flujos para mostrar."
        />
      ) : (
        <>
          <div className="overview-disclosures">
            <DisclosurePanel
              eyebrow="Volumen observado"
              title="Actividad mensual"
              summary={period}
              className="panel-volume"
            >
              <div className="bar-list">
                {monthly.map((item) => (
                  <div className="bar-row" key={item.month}>
                    <div>
                      <span>{formatMonth(item.month)}</span>
                      <strong>{formatCount(item.messageCount)} · {formatBytes(item.totalBytes)}</strong>
                    </div>
                    <div className="bar-track" aria-hidden="true">
                      <span style={{ width: `${(item.messageCount / maxMonthly) * 100}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </DisclosurePanel>

            <DisclosurePanel
              eyebrow="Memoria local"
              title={`${map.policyReview.total} decisiones necesitan atención`}
              summary={map.policyReview.total > 0 ? "Revisar antes de continuar" : "Sin pendientes"}
              className={map.policyReview.total > 0 ? "decision-disclosure has-attention" : "decision-disclosure"}
            >
              <p>
                Las decisiones de Joa se muestran como una capa separada. Ninguna corrección cambia ni oculta la evidencia automática.
              </p>
              <dl>
                <div><dt>Revisión</dt><dd>{map.policyReview.total}</dd></div>
                <div><dt>Exclusión dura</dt><dd>{map.summary.hardExcludedMessageCount}</dd></div>
                <div><dt>Parcial</dt><dd>{map.sync.partial ? "Sí" : "No"}</dd></div>
              </dl>
              <a className="text-button" href="#/corrections">Revisar correcciones <Icon name="arrow" /></a>
            </DisclosurePanel>
          </div>

          <section className="sources-section" aria-labelledby="top-sources-title">
            <div className="section-heading">
              <div><span className="eyebrow">Mayor volumen observado</span><h2 id="top-sources-title">Fuentes para comprender primero</h2></div>
              <a href="#/sources">Ver todas</a>
            </div>
            <div className="source-list">
              {map.sources.slice(0, 3).map((source) => <SourceCard key={source.id} source={source} headingLevel={3} />)}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
