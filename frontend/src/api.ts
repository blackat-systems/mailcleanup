import type {
  AnalysisStatus,
  Configuration,
  Dashboard,
  HistoryPlan,
  PlanPreview,
  PlanRequest,
  SourceRecord,
} from "./types";

class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  if (!response.ok) {
    let message = `La API local respondió ${response.status}.`;
    try {
      const payload = (await response.json()) as { detail?: string | { message?: string } };
      if (typeof payload.detail === "string") message = payload.detail;
      else if (payload.detail?.message) message = payload.detail.message;
    } catch {
      // La respuesta no era JSON: se conserva el mensaje seguro por defecto.
    }
    throw new ApiError(message, response.status);
  }
  return (await response.json()) as T;
}

export const api = {
  dashboard: () => request<Dashboard>("/api/v1/dashboard"),
  analysis: () => request<AnalysisStatus>("/api/v1/analysis"),
  configuration: () => request<Configuration>("/api/v1/configuration"),
  history: () => request<HistoryPlan[]>("/api/v1/history"),
  sources: (view = "all") =>
    request<SourceRecord[]>(`/api/v1/sources?view=${encodeURIComponent(view)}`),
  source: (id: string) => request<SourceRecord>(`/api/v1/sources/${encodeURIComponent(id)}`),
  previewPlan: (payload: PlanRequest) =>
    request<PlanPreview>("/api/v1/plans/preview", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
