import { useCallback, useEffect, useState } from "react";
import { ApiError, api, asApiError } from "./api";
import type { ContextProbe, MapContext, WorkspaceData } from "./types";

export type WorkspaceState =
  | { kind: "loading" }
  | { kind: "blocked"; reason: string }
  | { kind: "error"; error: ApiError }
  | { kind: "ready"; data: WorkspaceData };

export function isCompatibleMapContext(context: ContextProbe): context is MapContext {
  const capabilities = context.capabilities;
  return (
    context.contractVersion === 1 &&
    context.dataMode === "synthetic" &&
    context.account.state === "synthetic" &&
    context.account.displayAddress === null &&
    capabilities.mapRead === true &&
    capabilities.policyWrite === true &&
    capabilities.policyUndo === true &&
    capabilities.gmailConnection === false &&
    capabilities.oauth === false &&
    capabilities.externalNetwork === false &&
    capabilities.realData === false &&
    capabilities.syncControl === false &&
    capabilities.cleanupPlan === false &&
    capabilities.messageMutation === false &&
    capabilities.unsubscribe === false &&
    capabilities.execute === false
  );
}

async function loadWorkspace(): Promise<WorkspaceState> {
  try {
    const context = await api.context();
    if (!isCompatibleMapContext(context)) {
      return {
        kind: "blocked",
        reason:
          "El contrato, el modo de datos o las capacidades no coinciden con la superficie sintética D6.",
      };
    }
    const [connection, sync, index, map, decisions] = await Promise.all([
      api.connection(),
      api.sync(),
      api.index(),
      api.map(),
      api.decisions(),
    ]);
    const syncMatchesMap =
      map.sync.state === sync.state &&
      map.sync.mode === sync.mode &&
      map.sync.processedCount === sync.processedCount &&
      map.sync.startedAt === sync.startedAt &&
      map.sync.updatedAt === sync.updatedAt &&
      map.sync.errorCode === sync.errorCode &&
      map.sync.partial === sync.partial;
    if (
      map.policyRevision !== decisions.policyRevision ||
      map.sync.partial !== index.partial ||
      !syncMatchesMap
    ) {
      return { kind: "error", error: new ApiError("invalid_response", 200) };
    }
    return {
      kind: "ready",
      data: { context, connection, sync, index, map, decisions },
    };
  } catch (reason) {
    return { kind: "error", error: asApiError(reason) };
  }
}

export function useMapWorkspace() {
  const [state, setState] = useState<WorkspaceState>({ kind: "loading" });
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let active = true;
    void loadWorkspace().then((next) => {
      if (active) setState(next);
    });
    return () => {
      active = false;
    };
  }, [version]);

  const reload = useCallback(() => {
    setState({ kind: "loading" });
    setVersion((current) => current + 1);
  }, []);

  const refreshProjection = useCallback(async () => {
    const next = await loadWorkspace();
    if (next.kind === "ready") {
      setState(next);
      return;
    }
    if (next.kind === "blocked") {
      setState(next);
      throw new ApiError("invalid_response", 200);
    }
    if (next.kind === "error") throw next.error;
    throw new ApiError("invalid_response", 200);
  }, []);

  return { state, reload, refreshProjection };
}

export type ResourceState<T> = {
  data: T | null;
  loading: boolean;
  error: ApiError | null;
  reload: () => void;
};

export function useResource<T>(
  loader: () => Promise<T>,
  dependencies: readonly (string | number | boolean | null)[] = [],
  enabled = true,
): ResourceState<T> {
  type Snapshot = {
    key: string;
    data: T | null;
    loading: boolean;
    error: ApiError | null;
  };
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [version, setVersion] = useState(0);
  const reload = useCallback(() => setVersion((current) => current + 1), []);
  const requestKey = JSON.stringify([version, ...dependencies]);

  useEffect(() => {
    if (!enabled) return;
    let active = true;
    queueMicrotask(() => {
      if (!active) return;
      setSnapshot({ key: requestKey, data: null, loading: true, error: null });
      void loader()
        .then((result) => {
          if (active) {
            setSnapshot({ key: requestKey, data: result, loading: false, error: null });
          }
        })
        .catch((reason: unknown) => {
          if (active) {
            setSnapshot({
              key: requestKey,
              data: null,
              loading: false,
              error: asApiError(reason),
            });
          }
        });
    });
    return () => {
      active = false;
    };
    // El llamador declara de forma explícita qué revisión vuelve obsoleto el recurso.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, requestKey]);

  if (!enabled) return { data: null, loading: false, error: null, reload };
  if (!snapshot || snapshot.key !== requestKey) {
    return { data: null, loading: true, error: null, reload };
  }
  return { data: snapshot.data, loading: snapshot.loading, error: snapshot.error, reload };
}
