import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, api } from "../api";
import { isCompatibleMapContext } from "../hooks";
import { StudyApiError, studyApi } from "./api";
import type { StudyContext } from "./types";

export type StudyContextState = {
  loading: boolean;
  context: StudyContext | null;
  compatible: boolean;
  error: string | null;
};

const CONTEXT_ERROR = "No pudimos comprobar los contratos locales. Los comandos permanecen bloqueados.";
const CONTEXT_BLOCKED = "Los contratos v2 y v3 no coinciden con la superficie sintética esperada.";

async function readContexts(): Promise<StudyContextState> {
  try {
    const [mapContext, studyContext] = await Promise.all([api.context(), studyApi.context()]);
    if (!isCompatibleMapContext(mapContext)) {
      return { loading: false, context: studyContext, compatible: false, error: CONTEXT_BLOCKED };
    }
    return { loading: false, context: studyContext, compatible: true, error: null };
  } catch (reason) {
    const safe = reason instanceof ApiError || reason instanceof StudyApiError
      ? reason.message
      : CONTEXT_ERROR;
    return { loading: false, context: null, compatible: false, error: safe };
  }
}

export function useStudyContexts() {
  const generation = useRef(0);
  const [state, setState] = useState<StudyContextState>({
    loading: true,
    context: null,
    compatible: false,
    error: null,
  });

  const refresh = useCallback(async () => {
    const requestGeneration = ++generation.current;
    setState((current) => ({ ...current, loading: true, error: null }));
    const next = await readContexts();
    if (requestGeneration === generation.current) setState(next);
    return next;
  }, []);

  useEffect(() => {
    let active = true;
    const requestGeneration = ++generation.current;
    void readContexts().then((next) => {
      if (active && requestGeneration === generation.current) setState(next);
    });
    return () => {
      active = false;
    };
  }, []);

  return { state, refresh };
}
