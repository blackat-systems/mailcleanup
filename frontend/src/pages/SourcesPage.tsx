import { useMemo, useState } from "react";
import { api } from "../api";
import { useResource } from "../hooks";
import { Icon } from "../components/Icon";
import { EmptyState, ErrorState, LoadingState, PageHeader } from "../components/Primitives";
import { SourceCard } from "../components/SourceCard";

type Props = {
  view: string;
  selected: Set<string>;
  onToggle: (id: string) => void;
};

const viewCopy: Record<string, { title: string; description: string }> = {
  all: { title: "Fuentes y flujos", description: "Una fuente puede reunir varios remitentes y actividades sin mezclarlos en una sola etiqueta." },
  subscriptions: { title: "Suscripciones detectadas", description: "Esta es una vista filtrada de las mismas fuentes. La baja y la limpieza del historial siguen siendo decisiones separadas." },
  spam: { title: "Spam y señales sospechosas", description: "Se muestran fuentes aisladas cuando la autenticación o la identidad no alcanzan para agruparlas con seguridad." },
  protected: { title: "Fuentes con protección", description: "Mensajes críticos, documentales, personales o elegidos por vos quedan fuera de los planes ordinarios." },
};

export function SourcesPage({ view, selected, onToggle }: Props) {
  const resource = useResource(() => api.sources(view), [view]);
  const [query, setQuery] = useState("");
  const [rubro, setRubro] = useState("all");
  const copy = viewCopy[view] ?? viewCopy.all!;

  const filtered = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase("es");
    return (resource.data ?? []).filter((source) => {
      const matchesText = !needle || source.name.toLocaleLowerCase("es").includes(needle) || source.senders.some((sender) => sender.includes(needle));
      const matchesRubro = rubro === "all" || source.rubro === rubro;
      return matchesText && matchesRubro;
    });
  }, [query, resource.data, rubro]);

  const rubros = [...new Set((resource.data ?? []).map((source) => source.rubro))].sort();
  return (
    <div className="page">
      <PageHeader eyebrow="Explorador" title={copy.title} description={copy.description} actions={selected.size ? <a className="button button-primary" href="#/plan">Revisar plan ({selected.size}) <Icon name="arrow" /></a> : undefined} />

      <div className="view-tabs" role="navigation" aria-label="Vistas de fuentes">
        <a className={view === "all" ? "active" : undefined} href="#/sources">Todas</a>
        <a className={view === "subscriptions" ? "active" : undefined} href="#/sources?view=subscriptions">Suscripciones</a>
        <a className={view === "spam" ? "active" : undefined} href="#/sources?view=spam">Spam</a>
        <a className={view === "protected" ? "active" : undefined} href="#/sources?view=protected">Protegidas</a>
      </div>

      <section className="filters" aria-label="Filtros">
        <label className="search-field"><Icon name="search" /><span className="sr-only">Buscar fuentes</span><input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar fuente o remitente" /></label>
        <label><span className="sr-only">Filtrar por rubro</span><select value={rubro} onChange={(event) => setRubro(event.target.value)}><option value="all">Todos los rubros</option>{rubros.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
        <span className="result-count">{filtered.length} {filtered.length === 1 ? "fuente" : "fuentes"}</span>
      </section>

      {resource.loading ? <LoadingState /> : null}
      {resource.error ? <ErrorState message={resource.error} retry={resource.reload} /> : null}
      {!resource.loading && !resource.error && filtered.length === 0 ? <EmptyState title="No hay coincidencias" detail="Probá otra búsqueda o quitá algún filtro." /> : null}
      <div className="source-list">{filtered.map((source) => <SourceCard key={source.id} source={source} selected={selected.has(source.id)} onToggle={onToggle} />)}</div>
    </div>
  );
}
