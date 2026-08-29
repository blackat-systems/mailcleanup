import {
  isConnectionResponse,
  isContextProbe,
  isDecisionListResponse,
  isIndexResponse,
  isMapResponse,
  isSourceDetailResponse,
  isSyncResponse,
  isWriteResponse,
} from "./decoders";
import type {
  ConnectionResponse,
  ContextProbe,
  DecisionListResponse,
  DecisionRequest,
  IndexResponse,
  MapResponse,
  PublicErrorCode,
  SourceDetailResponse,
  SyncResponse,
  UndoRequest,
  WriteResponse,
} from "./types";

export type ClientErrorCode = PublicErrorCode | "transport_error" | "invalid_response";

const ERROR_MESSAGES: Record<ClientErrorCode, string> = {
  invalid_request: "La solicitud local no es válida.",
  invalid_local_origin: "La API rechazó el origen local de la solicitud.",
  source_not_found: "La fuente ya no existe en la vista actual.",
  decision_not_found: "La decisión ya no existe o dejó de estar activa.",
  map_revision_conflict: "El mapa cambió. Revisá la vista actual antes de volver a enviar.",
  policy_revision_conflict: "Las decisiones cambiaron. Revisá el historial antes de volver a enviar.",
  command_id_conflict: "Ese envío ya fue usado con otros datos. Prepará un comando nuevo.",
  policy_conflict: "La corrección entra en conflicto con otra vigente. Deshacela primero desde el historial.",
  invalid_transition: "La transición ya no está permitida en el estado actual.",
  payload_too_large: "La solicitud supera el tamaño permitido.",
  json_required: "La API local requiere una solicitud JSON.",
  target_not_found: "El objetivo ya no existe en la vista actual.",
  unsupported_target: "Ese objetivo no admite esta corrección.",
  map_unavailable: "El mapa sintético no está disponible.",
  account_unavailable: "La cuenta sintética de demostración no está disponible.",
  internal_error: "La API local no pudo completar la operación.",
  transport_error: "No pudimos comunicarnos con la API local.",
  invalid_response: "La API local devolvió una respuesta que no cumple el contrato.",
};

const PUBLIC_ERROR_CODES = new Set<PublicErrorCode>([
  "invalid_request",
  "invalid_local_origin",
  "source_not_found",
  "decision_not_found",
  "map_revision_conflict",
  "policy_revision_conflict",
  "command_id_conflict",
  "policy_conflict",
  "invalid_transition",
  "payload_too_large",
  "json_required",
  "target_not_found",
  "unsupported_target",
  "map_unavailable",
  "account_unavailable",
  "internal_error",
]);

const ERROR_STATUS: Record<PublicErrorCode, number> = {
  invalid_request: 400,
  invalid_local_origin: 403,
  source_not_found: 404,
  decision_not_found: 404,
  map_revision_conflict: 409,
  policy_revision_conflict: 409,
  command_id_conflict: 409,
  policy_conflict: 409,
  invalid_transition: 409,
  payload_too_large: 413,
  json_required: 415,
  target_not_found: 422,
  unsupported_target: 422,
  map_unavailable: 503,
  account_unavailable: 503,
  internal_error: 500,
};

export const API_TIMEOUT_MS = 10_000;
export const MAX_JSON_BODY_BYTES = 64 * 1024;

export class ApiError extends Error {
  readonly uncertainWrite: boolean;

  constructor(
    readonly code: ClientErrorCode,
    readonly status: number | null,
    options?: { uncertainWrite?: boolean },
  ) {
    super(ERROR_MESSAGES[code]);
    this.name = "ApiError";
    this.uncertainWrite = options?.uncertainWrite ?? false;
  }
}

type Decoder<T> = (payload: unknown) => payload is T;
type PostInit = { method: "POST"; body: string };

function isObject(value: unknown): value is object {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function errorCode(payload: unknown, status: number): PublicErrorCode | null {
  if (!isObject(payload) || Object.keys(payload).length !== 1) return null;
  const error = Reflect.get(payload, "error");
  if (!isObject(error) || Object.keys(error).sort().join("|") !== "code|message") return null;
  const code = Reflect.get(error, "code");
  const message = Reflect.get(error, "message");
  if (typeof code !== "string" || typeof message !== "string") return null;
  if (!PUBLIC_ERROR_CODES.has(code as PublicErrorCode)) return null;
  const publicCode = code as PublicErrorCode;
  return ERROR_STATUS[publicCode] === status ? publicCode : null;
}

async function readJson(response: Response, uncertainWrite: boolean): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    throw new ApiError("invalid_response", response.status, { uncertainWrite });
  }
}

async function request<T>(
  path: string,
  decoder: Decoder<T>,
  post?: PostInit,
): Promise<T> {
  if (post && new TextEncoder().encode(post.body).byteLength > MAX_JSON_BODY_BYTES) {
    throw new ApiError("payload_too_large", null);
  }
  let response: Response;
  let payload: unknown;
  const controller = new AbortController();
  let timeoutId: ReturnType<typeof setTimeout> | undefined;
  try {
    const result = await Promise.race([
      fetch(path, {
        credentials: "omit",
        mode: "same-origin",
        redirect: "error",
        signal: controller.signal,
        ...(post
          ? {
              method: post.method,
              headers: { "Content-Type": "application/json" },
              body: post.body,
            }
          : { method: "GET" }),
      }).then(async (received) => ({
        response: received,
        payload: await readJson(received, Boolean(post)),
      })),
      new Promise<{ response: Response; payload: unknown }>((_resolve, reject) => {
        timeoutId = setTimeout(() => {
          controller.abort();
          reject(new ApiError("transport_error", null, { uncertainWrite: Boolean(post) }));
        }, API_TIMEOUT_MS);
      }),
    ]);
    response = result.response;
    payload = result.payload;
  } catch (reason) {
    if (reason instanceof ApiError) throw reason;
    throw new ApiError("transport_error", null, { uncertainWrite: Boolean(post) });
  } finally {
    if (timeoutId !== undefined) clearTimeout(timeoutId);
  }

  if (!response.ok) {
    const code = errorCode(payload, response.status);
    if (code) throw new ApiError(code, response.status);
    throw new ApiError("invalid_response", response.status, { uncertainWrite: Boolean(post) });
  }
  if (!decoder(payload)) {
    throw new ApiError("invalid_response", response.status, { uncertainWrite: Boolean(post) });
  }
  return payload;
}

export function asApiError(reason: unknown): ApiError {
  return reason instanceof ApiError ? reason : new ApiError("transport_error", null);
}

export const api = {
  context: (): Promise<ContextProbe> => request("/api/v2/context", isContextProbe),
  connection: (): Promise<ConnectionResponse> =>
    request("/api/v2/connection", isConnectionResponse),
  sync: (): Promise<SyncResponse> => request("/api/v2/sync", isSyncResponse),
  index: (): Promise<IndexResponse> => request("/api/v2/index", isIndexResponse),
  map: (): Promise<MapResponse> => request("/api/v2/map", isMapResponse),
  source: async (sourceId: string): Promise<SourceDetailResponse> => {
    const source = await request(
      `/api/v2/map/sources/${encodeURIComponent(sourceId)}`,
      isSourceDetailResponse,
    );
    if (source.id !== sourceId) throw new ApiError("invalid_response", 200);
    return source;
  },
  decisions: (): Promise<DecisionListResponse> =>
    request("/api/v2/decisions", isDecisionListResponse),
  recordDecision: (body: DecisionRequest): Promise<WriteResponse> =>
    request("/api/v2/decisions", isWriteResponse, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  undoDecision: (decisionId: string, body: UndoRequest): Promise<WriteResponse> =>
    request(`/api/v2/decisions/${encodeURIComponent(decisionId)}/undo`, isWriteResponse, {
      method: "POST",
      body: JSON.stringify(body),
    }),
};
