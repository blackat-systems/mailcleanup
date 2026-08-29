import { useMemo, useState } from "react";
import { Badge, EmptyState, PageHeader } from "../components/Primitives";
import { SourceCard } from "../components/SourceCard";
import {
  CONFIANZAS,
  INTENCIONES,
  PROTECCIONES,
  RUBROS,
  SUSCRIPCIONES,
  type MapResponse,
  type SourceProjection,
} from "../types";

export type SourceView = "all" | "subscriptions" | "spam" | "protected";

const subscriptionViewValues = new Set([
  "Confirmada",
  "Probable",
  "Baja solicitada",
  "Posible incumplimiento",
]);

function sourceMatchesView(source: SourceProjection, view: SourceView): boolean {
  if (view === "subscriptions") {
    return source.flows.some((flow) => subscriptionViewValues.has(flow.subscription));
  }
  if (view === "spam") {
    return source.flows.some((flow) => flow.effectiveIntention === "Sospechoso");
  }
  if (view === "protected") return source.protectedMessageCount > 0;
  return true;
}

const viewCopy: Record<SourceView, { title: string; description: string }> = {
  all: {
    title: "Fuentes y flujos",
    description: "Fuente y flujo permanecen separados. Los filtros sólo usan campos publicados por el mapa.",
  },
  subscriptions: {
    title: "Suscripciones",
    description: "Vista de fuentes con al menos un flujo confirmado, probable, con baja solicitada o posible incumplimiento.",
  },
  spam: {
    title: "Spam",
    description: "Vista de fuentes con al menos un flujo cuya intención efectiva es exactamente Sospechoso.",
  },
  protected: {
    title: "Fuentes protegidas",
    description: "Vista de las mismas fuentes cuando contienen al menos un mensaje protegido.",
  },
};

export function SourcesPage({ map, view }: { map: MapResponse; view: SourceView }) {
  const [query, setQuery] = useState("");
  const [rubro, setRubro] = useState("");
  const [intention, setIntention] = useState("");
  const [subscription, setSubscription] = useState("");
  const [confidence, setConfidence] = useState("");
  const [protection, setProtection] = useState("");
  const copy = viewCopy[view];
  const activeAdvancedFilters = [rubro, intention, subscription, confidence, protection]
    .filter(Boolean).length;

  const filtered = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase("es");
    return map.sources.filter((source) => {
      if (!sourceMatchesView(source, view)) return false;
      const searchable = [
        source.effectiveDisplayName,
        source.automaticDisplayName,
        ...source.senders,
        ...source.domains,
      ];
      const matchesText = !needle || searchable.some((value) =>
        value.toLocaleLowerCase("es").includes(needle));
      const matchesRubro = !rubro || source.effectiveRubro === rubro;
      const matchesIntention = !intention || source.flows.some((flow) =>
        flow.effectiveIntention === intention);
      const matchesSubscription = !subscription || source.flows.some((flow) =>
        flow.subscription === subscription);
      const matchesConfidence = !confidence || source.effectiveConfidence === confidence;
      const matchesProtection = !protection || source.protection.effective === protection;
      return matchesText && matchesRubro && matchesIntention && matchesSubscription &&
        matchesConfidence && matchesProtection;
    });
  }, [confidence, intention, map.sources, protection, query, rubro, subscription, view]);

  return (
    <div className="page">
      <PageHeader eyebrow="Explorador sintético" title={copy.title} description={copy.description} />

      {map.sync.partial ? (
        <div className="partial-banner" role="status">
          <strong>Mapa parcial.</strong> La fotografía no está completada; los conteos y pertenencias pueden cambiar.
        </div>
      ) : null}

      <nav className="view-tabs" aria-label="Vistas de fuentes">
        <a aria-current={view === "all" ? "page" : undefined} className={view === "all" ? "active" : undefined} href="#/sources">Todas</a>
        <a aria-current={view === "subscriptions" ? "page" : undefined} className={view === "subscriptions" ? "active" : undefined} href="#/sources?view=subscriptions">Suscripciones</a>
        <a aria-current={view === "spam" ? "page" : undefined} className={view === "spam" ? "active" : undefined} href="#/sources?view=spam">Spam</a>
        <a aria-current={view === "protected" ? "page" : undefined} className={view === "protected" ? "active" : undefined} href="#/sources?view=protected">Protegidas</a>
      </nav>

      <section className="filters" aria-label="Filtros de fuentes">
        <div className="filter-primary">
          <label className="search-field">
            <span>Buscar fuente, remitente o dominio</span>
            <input type="search" value={query} onChange={(event) => setQuery(event.target.value)} />
          </label>
          <span className="result-count" role="status">{filtered.length} {filtered.length === 1 ? "fuente" : "fuentes"}</span>
        </div>
        <details className="advanced-filters">
          <summary>
            <span>Más filtros</span>
            {activeAdvancedFilters > 0 ? (
              <Badge tone="positive">{activeAdvancedFilters} activos</Badge>
            ) : <span className="filter-optional">Opcional</span>}
          </summary>
          <div className="advanced-filter-grid">
            <FilterSelect label="Rubro efectivo" value={rubro} onChange={setRubro} options={RUBROS} />
            <FilterSelect label="Intención efectiva de flujo" value={intention} onChange={setIntention} options={INTENCIONES} />
            <FilterSelect label="Suscripción de flujo" value={subscription} onChange={setSubscription} options={SUSCRIPCIONES} />
            <FilterSelect label="Confianza efectiva" value={confidence} onChange={setConfidence} options={CONFIANZAS} />
            <FilterSelect label="Protección efectiva" value={protection} onChange={setProtection} options={PROTECCIONES} />
          </div>
        </details>
      </section>

      {filtered.length === 0 ? (
        <EmptyState
          title={map.sources.length === 0 ? "El mapa no contiene fuentes" : "No hay coincidencias"}
          detail={map.sources.length === 0
            ? "La fotografía sintética está disponible y vacía."
            : "Probá otra búsqueda o quitá algún filtro presentacional."}
        />
      ) : (
        <div className="source-list" aria-label="Fuentes del mapa">
          {filtered.map((source) => <SourceCard key={source.id} source={source} />)}
        </div>
      )}
    </div>
  );
}

function FilterSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: readonly string[];
}) {
  return (
    <label>
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">Todos</option>
        {options.map((option) => <option key={option} value={option}>{option}</option>)}
      </select>
    </label>
  );
}
