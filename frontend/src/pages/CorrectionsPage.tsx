import { useMemo, useState, type FormEvent } from "react";
import { ApiError, api, asApiError } from "../api";
import {
  buildDecisionRequest,
  buildUndoRequest,
  DECISION_LIMITS,
  isStructuralCandidate,
  sameDraft,
  type DecisionDraft,
} from "../decisions";
import { useResource } from "../hooks";
import {
  INTENCIONES,
  RUBROS,
  type DecisionEvent,
  type DecisionListResponse,
  type DecisionRequest,
  type FlowProjection,
  type MapResponse,
  type ProtectionTarget,
  type SourceProjection,
  type UndoRequest,
  type WriteResponse,
} from "../types";
import { bindingLabels, formatDate, shortId } from "../utils";
import { Icon } from "../components/Icon";
import {
  AlertMessage,
  Badge,
  EmptyState,
  LoadingState,
  PageHeader,
  PublicId,
  StatusMessage,
} from "../components/Primitives";

type CorrectionType = DecisionDraft["type"];
type ProtectKind = ProtectionTarget["kind"];
type DraftResult = { ok: true; draft: DecisionDraft } | { ok: false; message: string };
type RetryCandidate =
  | { kind: "decision"; draft: DecisionDraft; body: DecisionRequest }
  | { kind: "undo"; decisionId: string; body: UndoRequest };
type Notice =
  | { kind: "success"; response: WriteResponse; action: "decision" | "undo" }
  | { kind: "error"; error: ApiError; conflict: boolean }
  | { kind: "refresh_error"; error: ApiError; response: WriteResponse };

const correctionLabels: Record<CorrectionType, string> = {
  setSourceDisplayName: "Cambiar nombre de fuente",
  setSourceRubro: "Cambiar rubro de fuente",
  setFlowDisplayName: "Cambiar nombre de flujo",
  setFlowIntention: "Cambiar intención de flujo",
  mergeSources: "Unir fuentes",
  partitionSource: "Separar una fuente",
  protectTarget: "Proteger un objetivo",
};

const conflictCodes = new Set([
  "map_revision_conflict",
  "policy_revision_conflict",
  "command_id_conflict",
  "policy_conflict",
  "invalid_transition",
  "target_not_found",
  "unsupported_target",
  "decision_not_found",
]);

export function CorrectionsPage({
  map,
  decisions,
  initialSourceId,
  refreshProjection,
}: {
  map: MapResponse;
  decisions: DecisionListResponse;
  initialSourceId?: string;
  refreshProjection: () => Promise<void>;
}) {
  return (
    <CorrectionsWorkspace
      map={map}
      decisions={decisions}
      initialSourceId={initialSourceId}
      refreshProjection={refreshProjection}
    />
  );
}

function CorrectionsWorkspace({
  map,
  decisions,
  initialSourceId,
  refreshProjection,
}: {
  map: MapResponse;
  decisions: DecisionListResponse;
  initialSourceId?: string;
  refreshProjection: () => Promise<void>;
}) {
  const defaultSourceId = initialSourceId === undefined
    ? (map.sources[0]?.id ?? "")
    : map.sources.some((source) => source.id === initialSourceId)
      ? initialSourceId
      : "";
  const flows = useMemo(
    () => map.sources.flatMap((source) => source.flows.map((flow) => ({ source, flow }))),
    [map.sources],
  );
  const structural = useMemo(() => map.sources.filter(isStructuralCandidate), [map.sources]);
  const partitionCandidates = useMemo(
    () => structural.filter((source) =>
      source.flows.length >= 2 && source.flows.length <= DECISION_LIMITS.partitionAnchors),
    [structural],
  );

  const [type, setType] = useState<CorrectionType>("setSourceDisplayName");
  const [sourceId, setSourceId] = useState(defaultSourceId);
  const [sourceName, setSourceName] = useState("");
  const [sourceRubroDraft, setSourceRubroDraft] = useState(() => ({
    sourceId: defaultSourceId,
    value: map.sources.find((source) => source.id === defaultSourceId)?.effectiveRubro ?? RUBROS[0],
  }));
  const [flowId, setFlowId] = useState(flows[0]?.flow.id ?? "");
  const [flowName, setFlowName] = useState("");
  const [flowIntentionDraft, setFlowIntentionDraft] = useState(() => ({
    flowId: flows[0]?.flow.id ?? "",
    value: flows[0]?.flow.effectiveIntention ?? INTENCIONES[0],
  }));
  const [mergeIds, setMergeIds] = useState<readonly string[]>([]);
  const [partitionSourceId, setPartitionSourceId] = useState(partitionCandidates[0]?.id ?? "");
  const [groupCount, setGroupCount] = useState(2);
  const [assignments, setAssignments] = useState<ReadonlyMap<string, number>>(new Map());
  const [protectSourceId, setProtectSourceId] = useState(defaultSourceId);
  const [protectKind, setProtectKind] = useState<ProtectKind>("source");
  const [protectValue, setProtectValue] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);
  const [pending, setPending] = useState<string | null>(null);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [retryCandidate, setRetryCandidate] = useState<RetryCandidate | null>(null);
  const [retryEdited, setRetryEdited] = useState(false);
  const [confirmRetry, setConfirmRetry] = useState(false);
  const writesBlocked = Boolean(pending) ||
    (notice?.kind === "error" && notice.conflict) ||
    notice?.kind === "refresh_error";

  const activeSourceId = map.sources.some((source) => source.id === sourceId) ? sourceId : "";
  const activeFlowId = flows.some(({ flow }) => flow.id === flowId) ? flowId : "";
  const activeSource = map.sources.find((source) => source.id === activeSourceId);
  const activeFlow = flows.find(({ flow }) => flow.id === activeFlowId)?.flow;
  const sourceRubro = sourceRubroDraft.sourceId === activeSourceId
    ? sourceRubroDraft.value
    : (activeSource?.effectiveRubro ?? RUBROS[0]);
  const flowIntention = flowIntentionDraft.flowId === activeFlowId
    ? flowIntentionDraft.value
    : (activeFlow?.effectiveIntention ?? INTENCIONES[0]);
  const activeMergeIds = mergeIds.filter((id) => structural.some((source) => source.id === id));
  const activePartitionSourceId = partitionCandidates.some((source) => source.id === partitionSourceId)
    ? partitionSourceId
    : "";
  const activeProtectSourceId = map.sources.some((source) => source.id === protectSourceId)
    ? protectSourceId
    : "";
  const needsProtectionDetail =
    type === "protectTarget" && (protectKind === "message" || protectKind === "label");

  const detail = useResource(
    () => api.source(activeProtectSourceId),
    [activeProtectSourceId, map.mapRevision],
    Boolean(activeProtectSourceId) && needsProtectionDetail,
  );
  const partitionSource = partitionCandidates.find((source) => source.id === activePartitionSourceId);
  const activeGroupCount = partitionSource
    ? Math.min(
        Math.max(groupCount, 2),
        Math.min(DECISION_LIMITS.partitionGroups, partitionSource.flows.length),
      )
    : 2;
  const protectSource = map.sources.find((source) => source.id === activeProtectSourceId);
  const protectOptions = protectionOptions(protectKind, protectSource, detail.data);

  const markEdited = () => {
    if (retryCandidate) setRetryEdited(true);
    setConfirmRetry(false);
    setValidationError(null);
    if (notice?.kind === "success") setNotice(null);
  };

  const selectSourceTarget = (value: string) => {
    setSourceId(value);
    setSourceName("");
    setSourceRubroDraft({
      sourceId: value,
      value: map.sources.find((source) => source.id === value)?.effectiveRubro ?? RUBROS[0],
    });
    markEdited();
  };

  const selectFlowTarget = (value: string) => {
    setFlowId(value);
    setFlowName("");
    setFlowIntentionDraft({
      flowId: value,
      value: flows.find(({ flow }) => flow.id === value)?.flow.effectiveIntention ?? INTENCIONES[0],
    });
    markEdited();
  };

  const currentDraft = (): DraftResult => {
    switch (type) {
      case "setSourceDisplayName":
        return activeSourceId
          ? { ok: true, draft: { type, sourceId: activeSourceId, displayName: sourceName } }
          : { ok: false, message: "Elegí una fuente." };
      case "setSourceRubro":
        return activeSourceId
          ? { ok: true, draft: { type, sourceId: activeSourceId, rubro: sourceRubro } }
          : { ok: false, message: "Elegí una fuente." };
      case "setFlowDisplayName":
        return activeFlowId
          ? { ok: true, draft: { type, flowId: activeFlowId, displayName: flowName } }
          : { ok: false, message: "Elegí un flujo." };
      case "setFlowIntention":
        return activeFlowId
          ? { ok: true, draft: { type, flowId: activeFlowId, intention: flowIntention } }
          : { ok: false, message: "Elegí un flujo." };
      case "mergeSources":
        return { ok: true, draft: { type, sourceIds: activeMergeIds } };
      case "partitionSource": {
        if (!partitionSource) return { ok: false, message: "Elegí una fuente estructural con al menos dos flujos." };
        const groups = Array.from({ length: activeGroupCount }, (_, index) =>
          partitionSource.flows
            .filter((flow) => assignments.get(flow.id) === index + 1)
            .map((flow) => flow.id),
        );
        return {
          ok: true,
          draft: {
            type,
            sourceId: partitionSource.id,
            groups,
            expectedFlowIds: partitionSource.flows.map((flow) => flow.id),
          },
        };
      }
      case "protectTarget": {
        const publishedValue = protectKind === "source" || protectOptions.some((option) => option.value === protectValue)
          ? protectValue
          : "";
        const target = protectionTarget(protectKind, activeProtectSourceId, publishedValue);
        return target
          ? { ok: true, draft: { type, target } }
          : { ok: false, message: "Elegí un objetivo publicado por la API." };
      }
    }
  };

  const finishWrite = async (response: WriteResponse, action: "decision" | "undo") => {
    try {
      await refreshProjection();
      setNotice({ kind: "success", response, action });
      setRetryCandidate(null);
      setRetryEdited(false);
      setConfirmRetry(false);
    } catch (reason) {
      setNotice({ kind: "refresh_error", error: asApiError(reason), response });
      setRetryCandidate(null);
      setRetryEdited(false);
      setConfirmRetry(false);
    }
  };

  const sendDecision = async (draft: DecisionDraft, body: DecisionRequest) => {
    setPending("decision");
    setNotice(null);
    try {
      const response = await api.recordDecision(body);
      await finishWrite(response, "decision");
    } catch (reason) {
      const error = asApiError(reason);
      if (error.uncertainWrite) {
        setRetryCandidate({ kind: "decision", draft, body });
        setRetryEdited(false);
      }
      setNotice({ kind: "error", error, conflict: conflictCodes.has(error.code) });
    } finally {
      setPending(null);
    }
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (writesBlocked) return;
    const draftResult = currentDraft();
    if (!draftResult.ok) {
      setValidationError(draftResult.message);
      return;
    }
    const built = buildDecisionRequest(draftResult.draft, map);
    if (!built.ok) {
      setValidationError(built.message);
      return;
    }
    setValidationError(null);
    setRetryCandidate(null);
    setRetryEdited(false);
    setConfirmRetry(false);
    void sendDecision(draftResult.draft, built.body);
  };

  const undo = async (decisionId: string) => {
    if (writesBlocked) return;
    const body = buildUndoRequest(map);
    setRetryCandidate(null);
    setRetryEdited(false);
    setConfirmRetry(false);
    setPending(`undo:${decisionId}`);
    setNotice(null);
    try {
      const response = await api.undoDecision(decisionId, body);
      await finishWrite(response, "undo");
    } catch (reason) {
      const error = asApiError(reason);
      if (error.uncertainWrite) {
        setRetryCandidate({ kind: "undo", decisionId, body });
        setRetryEdited(false);
      }
      setNotice({ kind: "error", error, conflict: conflictCodes.has(error.code) });
    } finally {
      setPending(null);
    }
  };

  const retryIsUnchanged = (() => {
    if (!retryCandidate || retryEdited) return false;
    if (retryCandidate.kind === "undo") return true;
    const draft = currentDraft();
    return draft.ok && sameDraft(draft.draft, retryCandidate.draft);
  })();

  const retryExact = async () => {
    if (!retryCandidate || !retryIsUnchanged || !confirmRetry || pending) return;
    setPending("retry");
    setNotice(null);
    try {
      const response = retryCandidate.kind === "decision"
        ? await api.recordDecision(retryCandidate.body)
        : await api.undoDecision(retryCandidate.decisionId, retryCandidate.body);
      await finishWrite(response, retryCandidate.kind === "decision" ? "decision" : "undo");
    } catch (reason) {
      const error = asApiError(reason);
      if (!error.uncertainWrite) {
        setRetryCandidate(null);
        setRetryEdited(false);
        setConfirmRetry(false);
      }
      setNotice({ kind: "error", error, conflict: conflictCodes.has(error.code) });
    } finally {
      setPending(null);
    }
  };

  const refreshAfterNotice = async (
    context: { kind: "conflict" } | { kind: "confirmed_write"; response: WriteResponse },
  ) => {
    if (pending) return;
    setPending("refresh");
    try {
      await refreshProjection();
      setNotice(null);
      setRetryCandidate(null);
      setRetryEdited(false);
      setConfirmRetry(false);
    } catch (reason) {
      const error = asApiError(reason);
      setNotice(context.kind === "confirmed_write"
        ? { kind: "refresh_error", error, response: context.response }
        : { kind: "error", error, conflict: true });
    } finally {
      setPending(null);
    }
  };

  const operationAnnouncement = pending === "decision"
    ? "Registrando corrección."
    : pending?.startsWith("undo:")
      ? "Deshaciendo corrección."
      : pending === "retry"
        ? "Reintentando el mismo envío."
        : pending === "refresh"
          ? "Actualizando la vista sin reenviar."
          : "";

  return (
    <div className="page corrections-page">
      <PageHeader
        eyebrow="Memoria local D5"
        title="Correcciones reversibles"
        description={map.sources.length === 0
          ? "No hay fuentes ni flujos para una decisión nueva. El historial sigue disponible y conserva el undo cuando el contrato lo permite."
          : "Joa puede agregar una decisión sobre la inferencia automática. El servidor conserva ambas capas y valida revisiones antes de escribir."}
      />

      {map.sync.partial ? (
        <AlertMessage><strong>Mapa parcial.</strong> Revisá con especial cuidado los objetivos antes de registrar una decisión.</AlertMessage>
      ) : null}

      <span className="sr-only" role="status" aria-live="polite">{operationAnnouncement}</span>

      <PolicyReview map={map} />

      {map.sources.length === 0 ? (
        <EmptyState
          title="Mapa vacío"
          detail="No hay objetivos públicos para una corrección nueva. Las decisiones anteriores siguen visibles y pueden deshacerse si son undoable."
        />
      ) : (
      <section className="panel correction-editor" aria-labelledby="editor-title">
        <div className="section-heading">
          <div><span className="eyebrow">Nueva decisión</span><h2 id="editor-title">Elegí una corrección explícita</h2></div>
          <Badge tone="positive">Undo disponible según historial</Badge>
        </div>

        <label className="field-stack correction-type">
          <span>Tipo de corrección</span>
           <select
             value={type}
             disabled={Boolean(pending)}
             onChange={(event) => {
              setType(event.target.value as CorrectionType);
              markEdited();
            }}
          >
            {Object.entries(correctionLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </label>

         <form aria-label={correctionLabels[type]} onSubmit={submit} className="correction-form">
           <fieldset className="correction-fields" disabled={Boolean(pending)}>
             <legend className="sr-only">Datos de la corrección</legend>
           {type === "setSourceDisplayName" ? (
             <>
               <SourceSelect sources={map.sources} value={activeSourceId} onChange={selectSourceTarget} />
               <label className="field-stack"><span>Nuevo nombre</span><input value={sourceName} onChange={(event) => { setSourceName(event.target.value); markEdited(); }} /></label>
             </>
           ) : null}
           {type === "setSourceRubro" ? (
             <>
               <SourceSelect sources={map.sources} value={activeSourceId} onChange={selectSourceTarget} />
               <label className="field-stack"><span>Rubro efectivo</span><select value={sourceRubro} onChange={(event) => { setSourceRubroDraft({ sourceId: activeSourceId, value: event.target.value as (typeof RUBROS)[number] }); markEdited(); }}>{RUBROS.map((item) => <option key={item}>{item}</option>)}</select></label>
             </>
           ) : null}
           {type === "setFlowDisplayName" ? (
             <>
               <FlowSelect flows={flows} value={activeFlowId} onChange={selectFlowTarget} />
               <label className="field-stack"><span>Nuevo nombre del flujo</span><input value={flowName} onChange={(event) => { setFlowName(event.target.value); markEdited(); }} /></label>
             </>
           ) : null}
           {type === "setFlowIntention" ? (
             <>
               <FlowSelect flows={flows} value={activeFlowId} onChange={selectFlowTarget} />
               <label className="field-stack"><span>Intención efectiva</span><select value={flowIntention} onChange={(event) => { setFlowIntentionDraft({ flowId: activeFlowId, value: event.target.value as (typeof INTENCIONES)[number] }); markEdited(); }}>{INTENCIONES.map((item) => <option key={item}>{item}</option>)}</select></label>
             </>
          ) : null}
          {type === "mergeSources" ? (
            <fieldset className="choice-grid">
              <legend>Fuentes estructurales para unir</legend>
              {structural.map((source) => (
                <label key={source.id}>
                   <input
                     type="checkbox"
                     checked={activeMergeIds.includes(source.id)}
                     disabled={
                       !activeMergeIds.includes(source.id) &&
                       activeMergeIds.length >= DECISION_LIMITS.mergeSources
                     }
                    onChange={() => {
                      setMergeIds((current) => current.includes(source.id)
                        ? current.filter((id) => id !== source.id)
                        : [...current, source.id]);
                      markEdited();
                    }}
                     aria-label={`Seleccionar ${source.effectiveDisplayName}, ID ${shortId(source.id)}, para unir`}
                  />
                   <span><strong>{source.effectiveDisplayName}</strong><small>ID {shortId(source.id)} · una fuente automática · sin decisión estructural</small></span>
                 </label>
               ))}
               {structural.length < 2 ? <p className="muted">No hay dos fuentes estructurales elegibles.</p> : null}
               {activeMergeIds.length > 0 ? (
                 <div className="selected-id-list" aria-label="IDs públicos seleccionados para unir">
                   {activeMergeIds.map((id) => (
                     <div key={id}>
                       <span>{map.sources.find((source) => source.id === id)?.effectiveDisplayName}</span>
                       <PublicId value={id} />
                     </div>
                   ))}
                 </div>
               ) : null}
             </fieldset>
          ) : null}
          {type === "partitionSource" ? (
            <div className="partition-builder">
               <div className="field-with-id"><label className="field-stack"><span>Fuente estructural para separar</span><select value={activePartitionSourceId} onChange={(event) => { setPartitionSourceId(event.target.value); setGroupCount(2); setAssignments(new Map()); markEdited(); }}><option value="">Elegir fuente</option>{partitionCandidates.map((source) => <option key={source.id} value={source.id}>{source.effectiveDisplayName} · {shortId(source.id)}</option>)}</select></label>{partitionSource ? <PublicId value={partitionSource.id} /> : null}</div>
              {partitionSource ? (
                <>
                  <label className="field-stack"><span>Cantidad de grupos</span><select value={activeGroupCount} onChange={(event) => { setGroupCount(Number(event.target.value)); setAssignments(new Map()); markEdited(); }}>{Array.from({ length: Math.min(DECISION_LIMITS.partitionGroups, partitionSource.flows.length) - 1 }, (_, index) => index + 2).map((count) => <option key={count} value={count}>{count}</option>)}</select></label>
                  <fieldset className="partition-flows">
                    <legend>Asignación manual de cada flujo</legend>
                     {partitionSource.flows.map((flow) => (
                       <div className="partition-flow-row" key={flow.id}>
                         <span><strong>{flow.effectiveDisplayName}</strong><small>{flow.messageCount} mensajes · ID {shortId(flow.id)}</small><PublicId value={flow.id} /></span>
                         <select
                           aria-label={`Grupo para ${flow.effectiveDisplayName}, ID ${shortId(flow.id)}`}
                          value={assignments.get(flow.id) ?? 0}
                          onChange={(event) => {
                            const group = Number(event.target.value);
                            setAssignments((current) => {
                              const next = new Map(current);
                              if (group === 0) next.delete(flow.id); else next.set(flow.id, group);
                              return next;
                            });
                            markEdited();
                          }}
                        >
                          <option value={0}>Sin asignar</option>
                           {Array.from({ length: activeGroupCount }, (_, index) => index + 1).map((group) => <option key={group} value={group}>Grupo {group}</option>)}
                         </select>
                       </div>
                     ))}
                  </fieldset>
                </>
              ) : <p className="muted">No hay una fuente estructural con al menos dos flujos.</p>}
            </div>
          ) : null}
          {type === "protectTarget" ? (
            <div className="protect-builder">
              <SourceSelect label="Fuente de contexto" sources={map.sources} value={activeProtectSourceId} onChange={(value) => { setProtectSourceId(value); setProtectValue(""); markEdited(); }} />
              <label className="field-stack"><span>Tipo de objetivo</span><select value={protectKind} onChange={(event) => { setProtectKind(event.target.value as ProtectKind); setProtectValue(""); markEdited(); }}><option value="source">Fuente</option><option value="flow">Flujo</option><option value="message">Mensaje reciente</option><option value="sender">Remitente</option><option value="label">Etiqueta</option></select></label>
              {protectKind === "source" ? <p className="target-preview"><strong>Objetivo:</strong> {protectSource?.effectiveDisplayName ?? "Sin fuente"}</p> : (
                detail.loading ? <LoadingState label="Leyendo objetivos públicos…" /> : detail.error ? (
                  <AlertMessage>
                    <strong>{detail.error.message}</strong>
                    <button className="button button-secondary" type="button" onClick={detail.reload}>
                      Reintentar lectura de objetivos
                    </button>
                  </AlertMessage>
                 ) : (
                   <div className="field-with-id"><label className="field-stack"><span>Objetivo publicado</span><select value={protectValue} onChange={(event) => { setProtectValue(event.target.value); markEdited(); }}><option value="">Elegir objetivo</option>{protectOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>{protectValue ? <PublicId value={protectValue} /> : null}</div>
                 )
              )}
              <p className="muted">Proteger agrega una capa acumulativa. D6 no ofrece desprotección.</p>
            </div>
           ) : null}
           </fieldset>

           {validationError ? <AlertMessage>{validationError}</AlertMessage> : null}
          <button
            className="button button-primary"
            type="submit"
            aria-busy={pending === "decision" || pending === "retry"}
             disabled={
               writesBlocked ||
               (Boolean(retryCandidate) && retryIsUnchanged)
             }
          >
            {pending === "decision" ? "Registrando…" : "Registrar corrección"}
          </button>
        </form>
      </section>
      )}

      {notice?.kind === "success" ? (
        <StatusMessage>
          <Icon name="check" />
          <strong>{notice.action === "undo" ? "Corrección deshecha" : "Corrección aplicada"}.</strong>
          {notice.response.replayed ? " El servidor confirmó un replay exacto." : " El mapa y el historial fueron releídos."}
        </StatusMessage>
      ) : null}
      {notice?.kind === "error" ? (
        <AlertMessage>
          <strong>{notice.error.message}</strong>
          {notice.conflict ? <p>El formulario se conserva. Actualizá la vista de forma explícita; D6 no reenvía el comando automáticamente.</p> : null}
          {notice.conflict ? <button className="button button-secondary" type="button" onClick={() => void refreshAfterNotice({ kind: "conflict" })} disabled={Boolean(pending)}>Actualizar vista sin reenviar</button> : null}
          {!notice.conflict ? <button className="button button-secondary" type="button" onClick={() => setNotice(null)} disabled={Boolean(pending)}>Volver al formulario</button> : null}
        </AlertMessage>
      ) : null}
      {notice?.kind === "refresh_error" ? (
        <AlertMessage>
          <strong>La escritura fue confirmada, pero no pudimos releer el mapa.</strong>
          <p>{notice.error.message} No vuelvas a enviar la corrección.</p>
          <button className="button button-secondary" type="button" onClick={() => void refreshAfterNotice({ kind: "confirmed_write", response: notice.response })} disabled={Boolean(pending)}>Reintentar sólo la lectura</button>
        </AlertMessage>
      ) : null}

      {retryCandidate ? (
        <section className="panel retry-panel" aria-labelledby="retry-title">
          <span className="eyebrow">Resultado incierto</span>
          <h2 id="retry-title">Retry idempotente, sólo con confirmación</h2>
          <p>{retryIsUnchanged
            ? "Podés repetir exactamente el mismo cuerpo y los mismos identificadores."
            : "El formulario cambió. El intento anterior no puede reutilizarse; un envío nuevo generará identificadores nuevos."}</p>
          {retryIsUnchanged ? (
             <label className="confirm-retry"><input type="checkbox" checked={confirmRetry} disabled={Boolean(pending)} onChange={(event) => setConfirmRetry(event.target.checked)} /><span>Confirmo que no cambié los datos del intento anterior.</span></label>
          ) : null}
          <button className="button button-secondary" type="button" disabled={!retryIsUnchanged || !confirmRetry || Boolean(pending)} onClick={() => void retryExact()}>Reintentar exactamente el mismo envío</button>
        </section>
      ) : null}

      <DecisionHistory
        map={map}
        decisions={decisions}
        pending={pending}
        writesBlocked={writesBlocked}
        onUndo={(decisionId) => void undo(decisionId)}
      />
    </div>
  );
}

function SourceSelect({
  sources,
  value,
  onChange,
  label = "Fuente",
}: {
  sources: readonly SourceProjection[];
  value: string;
  onChange: (value: string) => void;
  label?: string;
}) {
  return (
    <div className="field-with-id">
      <label className="field-stack"><span>{label}</span><select value={value} onChange={(event) => onChange(event.target.value)}><option value="">Elegir fuente</option>{sources.map((source) => <option key={source.id} value={source.id}>{source.effectiveDisplayName} · {shortId(source.id)}</option>)}</select></label>
      {value ? <PublicId value={value} /> : null}
    </div>
  );
}

function FlowSelect({
  flows,
  value,
  onChange,
}: {
  flows: readonly { source: SourceProjection; flow: FlowProjection }[];
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div className="field-with-id">
      <label className="field-stack"><span>Flujo</span><select value={value} onChange={(event) => onChange(event.target.value)}><option value="">Elegir flujo</option>{flows.map(({ source, flow }) => <option key={flow.id} value={flow.id}>{source.effectiveDisplayName} · {flow.effectiveDisplayName} · {shortId(flow.id)}</option>)}</select></label>
      {value ? <PublicId value={value} /> : null}
    </div>
  );
}

function protectionTarget(kind: ProtectKind, sourceId: string, value: string): ProtectionTarget | null {
  if (kind === "source") return sourceId ? { kind, sourceId } : null;
  if (!value) return null;
  if (kind === "flow") return { kind, flowId: value };
  if (kind === "message") return { kind, messageId: value };
  if (kind === "sender") return { kind, senderAddress: value };
  return { kind, labelId: value };
}

function protectionOptions(
  kind: ProtectKind,
  source: SourceProjection | undefined,
  detail: Awaited<ReturnType<typeof api.source>> | null,
): readonly { value: string; label: string }[] {
  if (!source) return [];
  if (kind === "flow") return source.flows.map((flow) => ({
    value: flow.id,
    label: `${flow.effectiveDisplayName} · ${shortId(flow.id)}`,
  }));
  if (kind === "sender") return source.senders.map((sender) => ({ value: sender, label: sender }));
  if (kind === "message") return (detail?.recentMessages ?? []).map((message) => ({
    value: message.id,
    label: `${message.subject ?? "Sin asunto"} · ${formatDate(message.receivedAt)} · ${shortId(message.id)}`,
  }));
  if (kind === "label") {
    return [...new Set((detail?.recentMessages ?? []).flatMap((message) => message.labelIds))]
      .sort()
      .map((label) => ({ value: label, label }));
  }
  return [];
}

function PolicyReview({ map }: { map: MapResponse }) {
  return (
    <details className="panel review-panel disclosure-panel" open={map.policyReview.total > 0}>
      <summary>
        <span className="disclosure-title">
          <span className="eyebrow">Bindings no aplicables</span>
          <span className="disclosure-heading" role="heading" aria-level={2}>Decisiones que requieren revisión</span>
        </span>
        <Badge tone={map.policyReview.total ? "warning" : "positive"}>{map.policyReview.total}</Badge>
      </summary>
      <div className="disclosure-content">
        {map.policyReview.bindings.length === 0 ? <p className="muted">No hay bindings pendientes.</p> : (
          <div className="review-list">
            {map.policyReview.bindings.map((binding) => (
              <article key={binding.decisionId}>
                <Badge tone="warning">{binding.status}</Badge>
                <div><strong>{bindingLabels[binding.status]} · requiere revisión</strong><PublicId value={binding.decisionId} /></div>
                <p>{binding.currentEffectiveIds.length ? `${binding.currentEffectiveIds.length} objetivos efectivos actuales` : "Sin objetivo efectivo actual"}</p>
              </article>
            ))}
          </div>
        )}
      </div>
    </details>
  );
}

function DecisionHistory({
  map,
  decisions,
  pending,
  writesBlocked,
  onUndo,
}: {
  map: MapResponse;
  decisions: DecisionListResponse;
  pending: string | null;
  writesBlocked: boolean;
  onUndo?: (decisionId: string) => void;
}) {
  return (
    <details className="history-section history-disclosure">
      <summary>
        <span>
          <span className="eyebrow">Ledger local</span>
          <span className="history-heading" role="heading" aria-level={2}>Historial de decisiones</span>
        </span>
        <span>{decisions.events.length} eventos · revisión {decisions.policyRevision}</span>
      </summary>
      <div className="history-content">
        {decisions.events.length === 0 ? (
          <EmptyState title="Historial vacío" detail="Todavía no hay decisiones locales ni eventos undo." />
        ) : (
          <div className="decision-history-list" aria-label="Historial de correcciones">
            {decisions.events.map((event) => (
              <article key={`${event.revision}-${event.commandId}`}>
                <div className="history-icon"><Icon name={event.type === "undoPolicy" ? "undo" : "history"} /></div>
                <div className="history-body">
                  <div className="history-title-line">
                    <strong>{decisionDescription(event)}</strong>
                    <Badge tone={event.active ? "positive" : "neutral"}>{event.active ? "Activa" : "Inactiva"}</Badge>
                    {event.bindingStatus ? <Badge tone={event.bindingStatus === "EXACT" || event.bindingStatus === "REBOUND" ? "positive" : "warning"}>{bindingLabels[event.bindingStatus]}</Badge> : null}
                  </div>
                  <span>Revisión {event.revision} · {formatDate(event.occurredAt, true)}</span>
                  <div className="history-record-id">
                    <span>{event.type === "undoPolicy" ? "Decisión deshecha" : "Decisión registrada"}</span>
                    <PublicId value={event.decisionId ?? event.targetDecisionId ?? event.commandId} />
                  </div>
                  <DecisionTargets event={event} map={map} />
                </div>
                {onUndo && event.undoable && event.decisionId ? (
                  <button
                    className="button button-secondary"
                    type="button"
                    aria-label={`${pending === `undo:${event.decisionId}` ? "Deshaciendo" : "Deshacer"} ${decisionDescription(event)}, decisión ${event.decisionId}`}
                    aria-busy={pending === `undo:${event.decisionId}`}
                    onClick={() => onUndo(event.decisionId!)}
                    disabled={writesBlocked}
                  >
                    <Icon name="undo" /> {pending === `undo:${event.decisionId}` ? "Deshaciendo…" : "Deshacer"}
                  </button>
                ) : null}
              </article>
            ))}
          </div>
        )}
      </div>
    </details>
  );
}

function DecisionTargets({ event, map }: { event: DecisionEvent; map: MapResponse }) {
  const targets = publicDecisionTargets(event, map);
  if (targets.length === 0) return null;
  return (
    <div
      className="history-targets"
      aria-label={`Objetivos públicos de ${decisionDescription(event)}`}
    >
      {targets.map((target) => (
        <div key={target.id}>
          <span>{target.label}</span>
          <PublicId value={target.id} />
        </div>
      ))}
    </div>
  );
}

function publicDecisionTargets(
  event: DecisionEvent,
  map: MapResponse,
): readonly { id: string; label: string }[] {
  const targets = new Map<string, string>();
  const add = (id: string | null, fallback: string) => {
    if (!id || targets.has(id)) return;
    const source = map.sources.find((item) => item.id === id);
    if (source) {
      targets.set(id, `Fuente actual: ${source.effectiveDisplayName}`);
      return;
    }
    for (const owner of map.sources) {
      const flow = owner.flows.find((item) => item.id === id);
      if (flow) {
        targets.set(id, `Flujo actual: ${owner.effectiveDisplayName} · ${flow.effectiveDisplayName}`);
        return;
      }
    }
    targets.set(id, fallback);
  };

  switch (event.type) {
    case "setSourceDisplayName":
    case "setSourceRubro":
      add(event.sourceId, "Fuente observada por la decisión");
      break;
    case "setFlowDisplayName":
    case "setFlowIntention":
      add(event.flowId, "Flujo observado por la decisión");
      break;
    case "mergeSources":
      event.sourceIds.forEach((id) => add(id, "Fuente unida por la decisión"));
      break;
    case "partitionSource":
      add(event.sourceId, "Fuente separada por la decisión");
      event.groups.forEach((group) => {
        group.observedSourceIds.forEach((id) => add(id, `Fuente observada en grupo ${group.groupIndex + 1}`));
        group.observedFlowIds.forEach((id) => add(id, `Flujo observado en grupo ${group.groupIndex + 1}`));
      });
      break;
    case "protectTarget":
      add(event.target.observedEffectiveId, `Objetivo efectivo de tipo ${event.target.kind}`);
      event.target.observedSourceIds.forEach((id) => add(id, "Fuente observada por la protección"));
      event.target.observedFlowIds.forEach((id) => add(id, "Flujo observado por la protección"));
      break;
    case "undoPolicy":
      add(event.targetDecisionId, "Decisión objetivo del undo");
      break;
  }
  event.currentTargetIds.forEach((id) => add(id, "Objetivo efectivo actual"));
  return [...targets].map(([id, label]) => ({ id, label }));
}

function decisionDescription(event: DecisionEvent): string {
  switch (event.type) {
    case "setSourceDisplayName": return `Nombre de fuente: ${event.displayName}`;
    case "setSourceRubro": return `Rubro de fuente: ${event.rubro}`;
    case "setFlowDisplayName": return `Nombre de flujo: ${event.displayName}`;
    case "setFlowIntention": return `Intención de flujo: ${event.intention}`;
    case "mergeSources": return `Unión manual de ${event.sourceIds.length} fuentes`;
    case "partitionSource": return `Separación manual en ${event.groupCount} grupos`;
    case "protectTarget": return `Protección manual sobre ${event.target.kind}`;
    case "undoPolicy": return "Undo lógico de una decisión";
  }
}
