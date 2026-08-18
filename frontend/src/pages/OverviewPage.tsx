import { api } from "../api";
import { useResource } from "../hooks";
import type { SourceRecord } from "../types";
import { formatBytes, formatCount } from "../utils";
import { Icon } from "../components/Icon";
import { ErrorState, LoadingState, PageHeader, StatCard } from "../components/Primitives";
import { SourceCard } from "../components/SourceCard";

type Props = {
  selected: Set<string>;
  onToggle: (id: string) => void;
};

export function OverviewPage({ selected, onToggle }: Props) {
  const dashboard = useResource(api.dashboard);
  if (dashboard.loading) return <LoadingState label="Construyendo el panorama sintético…" />;
  if (dashboard.error || !dashboard.data) {
    return <ErrorState message={dashboard.error ?? "Sin datos"} retry={dashboard.reload} />;
  }

  const data = dashboard.data;
  const maxRubro = Math.max(...data.rubros.map((item) => item.count), 1);
  return (
    <div className="page">
      <PageHeader
        eyebrow="Panorama sintético"
        title="Tu casilla, convertida en un mapa"
        description="Fuentes, flujos y protecciones visibles antes de tomar cualquier decisión. Estos datos son ficticios y sirven para probar el modelo."
        actions={<a className="button button-primary" href="#/sources">Explorar fuentes <Icon name="arrow" /></a>}
      />

      <section className="safety-banner" aria-label="Estado de seguridad">
        <Icon name="shield" />
        <div><strong>Entorno de demostración seguro</strong><p>0 credenciales · 0 conexiones externas · 0 acciones sobre correos</p></div>
        <span>{data.fixtureCoverage.covered}/{data.fixtureCoverage.required} casos cubiertos</span>
      </section>

      <section className="stats-grid" aria-label="Resumen de volumen">
        <StatCard label="Mensajes analizados" value={formatCount(data.totalMessages)} note={`${formatBytes(data.totalBytes)} de metadatos simulados`} tone="ink" />
        <StatCard label="Fuentes sugeridas" value={formatCount(data.totalSources)} note="Agrupadas con evidencia" tone="blue" />
        <StatCard label="Suscripciones" value={formatCount(data.subscriptionSources)} note="Confirmadas o probables" tone="green" />
        <StatCard label="Protegidos" value={formatCount(data.protectedMessages)} note="Excluidos por defecto" tone="gold" />
      </section>

      <div className="overview-grid">
        <section className="panel panel-volume">
          <div className="section-heading"><div><span className="eyebrow">Distribución</span><h2>Qué actividad ocupa la bandeja</h2></div><a href="#/sources">Ver todo</a></div>
          <div className="bar-list">
            {data.rubros.map((item, index) => (
              <div className="bar-row" key={item.name}>
                <div><span>{item.name}</span><strong>{item.count}</strong></div>
                <div className="bar-track"><span style={{ width: `${(item.count / maxRubro) * 100}%`, "--bar-index": index } as React.CSSProperties} /></div>
              </div>
            ))}
          </div>
        </section>

        <section className="panel decision-panel">
          <span className="eyebrow">Lectura inicial</span>
          <h2>{data.candidateMessages} mensajes podrían ordenarse</h2>
          <p>Es una sugerencia, no una orden. Hay {data.protectedMessages} mensajes que el sistema apartó antes de preparar cualquier plan.</p>
          <dl>
            <div><dt>Candidatos</dt><dd>{data.candidateMessages}</dd></div>
            <div><dt>Spam visible</dt><dd>{data.spamMessages}</dd></div>
            <div><dt>Protegidos</dt><dd>{data.protectedMessages}</dd></div>
          </dl>
          <a className="text-button" href="#/plan">Preparar una simulación <Icon name="arrow" /></a>
        </section>
      </div>

      <section className="sources-section">
        <div className="section-heading"><div><span className="eyebrow">Mayor volumen</span><h2>Fuentes para mirar primero</h2></div></div>
        <div className="source-list">
          {data.topSources.map((source: SourceRecord) => (
            <SourceCard key={source.id} source={source} selected={selected.has(source.id)} onToggle={onToggle} />
          ))}
        </div>
      </section>
    </div>
  );
}
