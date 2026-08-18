import { useCallback, useEffect, useState } from "react";

export type ResourceState<T> = {
  data: T | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
};

export function useResource<T>(loader: () => Promise<T>, dependencies: unknown[] = []): ResourceState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);
  const reload = useCallback(() => setVersion((current) => current + 1), []);

  useEffect(() => {
    let active = true;
    const load = async () => {
      await Promise.resolve();
      if (active) {
        setLoading(true);
        setError(null);
      }
      try {
        const result = await loader();
        if (active) setData(result);
      } catch (reason: unknown) {
        if (active) setError(reason instanceof Error ? reason.message : "Falló la API local.");
      } finally {
        if (active) setLoading(false);
      }
    };
    void load();
    return () => {
      active = false;
    };
    // loader se estabiliza desde el llamador; las dependencias expresan cuándo recargar.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [version, ...dependencies]);

  return { data, loading, error, reload };
}
