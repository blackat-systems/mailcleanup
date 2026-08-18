import { useMemo, useState, type FormEvent } from "react";
import { api } from "../api";
import { useResource } from "../hooks";
import type { PlanPreview } from "../types";
import { formatBytes, formatDate, initials } from "../utils";
import { Badge, EmptyState, ErrorState, LoadingState, PageHeader } from "../components/Primitives";
import { Icon } from "../components/Icon";

type Operation = "trash" | "archive" | "unsubscribe";
type Props = { selected: Set<string>; onToggle: (id: string) => void };

export function PlanPage({ selected, onToggle }: Props) {
  const sourcesResource = useResource(() => api.sources());
  const historyResource = useResource(api.history);
  const [beforeDate, setBeforeDate] = useState("");
  const [keepLatest, setKeepLatest] = useState(0);
  const [operations, setOperations] = useState<Set<Operation>>(new Set(["trash"]));
  const [preview, setPreview] = useState<PlanPreview | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const selectedSources = useMemo(() => (sourcesResource.data ?? []).filter((source) => selected.has(source.id)), [selected, sourcesResource.data]);
  const toggleOperation = (operation: Operation) => {
    setPreview(null);
    setOperations((current) => {
      const next = new Set(current);
      if (next.has(operation)) next.delete(operation); else next.add(operation);
      return next;
    });
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!selected.size || !operations.size) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      const result = await api.previewPlan({ sourceIds: [...selected], beforeDate: beforeDate || null, keepLatest, operations: [...operations] });
      setPreview(result);
      historyResource.reload();
    } catch (reason) {
      setSubmitError(reason instanceof Error ? reason.message : "No se pudo preparar el plan.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="page">
      <PageHeader eyebrow="Estudio de Limpieza" title="Decidir con una vista previa" description="Definí alcance, fecha y acciones por separado. La simulación excluye protecciones y nunca puede ejecutarse sobre Gmail." />

      <section className="safety-banner safety-plan"><Icon name="shield" /><div><strong>Simulación sin efectos</strong><p>Preparar este plan sólo guarda un registro local de prueba.</p></div><Badge tone="positive">Ejecución bloqueada</Badge></section>

      {sourcesResource.loading ? <LoadingState /> : null}
      {sourcesResource.error ? <ErrorState message={sourcesResource.error} retry={sourcesResource.reload} /> : null}
      {!sourcesResource.loading && selectedSources.length === 0 ? <EmptyState title="Todavía no elegiste fuentes" detail="Entrá al explorador, revisá la evidencia y sumá al menos una fuente a la simulación." /> : null}

      {selectedSources.length > 0 ? (
        <form className="plan-layout" onSubmit={submit}>
          <div className="plan-builder">
            <section className="panel plan-step"><div className="step-number">1</div><div className="step-content"><div className="section-heading"><div><span className="eyebrow">Alcance</span><h2>{selectedSources.length} {selectedSources.length === 1 ? "fuente elegida" : "fuentes elegidas"}</h2></div><a href="#/sources">Agregar más</a></div><div className="selected-sources">{selectedSources.map((source) => <article key={source.id}><span className="mini-avatar">{initials(source.name)}</span><div><strong>{source.name}</strong><small>{source.messageCount} mensajes · {source.protectedCount} protegidos</small></div><button type="button" onClick={() => { onToggle(source.id); setPreview(null); }} aria-label={`Quitar ${source.name}`}><Icon name="close" /></button></article>)}</div></div></section>

            <section className="panel plan-step"><div className="step-number">2</div><div className="step-content"><span className="eyebrow">Condiciones</span><h2>Qué historial incluir</h2><div className="form-grid"><label><span>Hasta la fecha civil</span><input type="date" value={beforeDate} onChange={(event) => { setBeforeDate(event.target.value); setPreview(null); }} /><small>Incluye todo ese día en horario de Córdoba.</small></label><label><span>Conservar los últimos</span><input type="number" min="0" max="50" value={keepLatest} onChange={(event) => { setKeepLatest(Number(event.target.value)); setPreview(null); }} /><small>Se aplica por cada fuente elegida.</small></label></div></div></section>

            <section className="panel plan-step"><div className="step-number">3</div><div className="step-content"><span className="eyebrow">Decisiones independientes</span><h2>Qué querés simular</h2><div className="operation-grid"><label className={operations.has("trash") ? "checked" : ""}><input type="checkbox" checked={operations.has("trash")} onChange={() => toggleOperation("trash")} /><span><strong>Mover a Papelera</strong><small>Nunca eliminación definitiva</small></span></label><label className={operations.has("archive") ? "checked" : ""}><input type="checkbox" checked={operations.has("archive")} onChange={() => toggleOperation("archive")} /><span><strong>Archivar historial</strong><small>Conserva los mensajes</small></span></label><label className={operations.has("unsubscribe") ? "checked" : ""}><input type="checkbox" checked={operations.has("unsubscribe")} onChange={() => toggleOperation("unsubscribe")} /><span><strong>Solicitar baja</strong><small>Sólo intención simulada</small></span></label></div></div></section>
          </div>

          <aside className="plan-summary panel"><span className="eyebrow">Vista previa</span><h2>Antes de confirmar</h2>{preview ? <PreviewResult preview={preview} /> : <div className="preview-placeholder"><span className="preview-orbit"><Icon name="plan" /></span><p>Calcularemos mensajes incluidos, protecciones excluidas y una muestra segura.</p></div>}{submitError ? <p className="inline-error" role="alert">{submitError}</p> : null}<button className="button button-primary button-wide" type="submit" disabled={submitting || operations.size === 0}>{submitting ? "Calculando…" : preview ? "Recalcular simulación" : "Crear vista previa"}</button><small className="submit-note">Base Segura no contiene un botón de ejecutar.</small></aside>
        </form>
      ) : null}

      <section className="history-section"><div className="section-heading"><div><span className="eyebrow">Registro local</span><h2>Simulaciones recientes</h2></div></div>{historyResource.data?.length ? <div className="history-list">{historyResource.data.slice(0, 4).map((plan) => <article key={plan.id}><Icon name="plan" /><div><strong>{plan.id}</strong><span>{plan.snapshot.messageCount} mensajes · {plan.selection.sourceIds.length} fuentes</span></div><time>{formatDate(plan.createdAt, true)}</time><Badge tone="neutral">Simulado</Badge></article>)}</div> : <p className="muted">Todavía no hay simulaciones guardadas.</p>}</section>
    </div>
  );
}

function PreviewResult({ preview }: { preview: PlanPreview }) {
  return (
    <div className="preview-result">
      <div className="preview-number"><strong>{preview.messageCount}</strong><span>mensajes incluidos</span></div>
      <dl><div><dt>Fuentes</dt><dd>{preview.sourceCount}</dd></div><div><dt>Excluidos</dt><dd>{preview.excludedCount}</dd></div><div><dt>Volumen</dt><dd>{formatBytes(preview.totalBytes)}</dd></div></dl>
      <div className="warning-list">{preview.warnings.map((warning) => <p key={warning}><Icon name="info" />{warning}</p>)}</div>
      {preview.exclusions.length ? <details><summary>Ver por qué se excluyeron {preview.excludedCount}</summary><ul>{preview.exclusions.slice(0, 8).map((item) => <li key={item.messageId}><code>{item.messageId}</code><span>{item.reason}</span></li>)}</ul></details> : null}
    </div>
  );
}
