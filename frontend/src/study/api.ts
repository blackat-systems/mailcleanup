import {
  decodeStudyError,
  isEventsResponse,
  isPlanId,
  isMessagesResponse,
  isPlanDetail,
  isPlansResponse,
  isStudyContext,
  isTargetsResponse,
} from "./decoders";
import type {
  CancelReceipt,
  CreateReceipt,
  EventsResponse,
  MemberFilter,
  PlanDetail,
  PlanState,
  PlansResponse,
  PreparedCommand,
  RevalidateReceipt,
  StudyClientErrorCode,
  StudyContext,
  TargetKind,
  TargetsResponse,
  MessagesResponse,
} from "./types";

export const STUDY_API_TIMEOUT_MS = 10_000;
export const STUDY_MAX_BODY_BYTES = 64 * 1024;

const LOCAL_MESSAGES: Record<StudyClientErrorCode, string> = {
  invalid_request: "La solicitud local no es válida.",
  invalid_cursor: "El cursor dejó de ser válido. Reiniciá la consulta desde la primera página.",
  invalid_local_origin: "La API rechazó el origen local de la solicitud.",
  route_not_found: "La ruta local solicitada no existe.",
  target_not_found: "Un objetivo ya no existe en el catálogo actual.",
  plan_not_found: "El plan local solicitado ya no está disponible.",
  method_not_allowed: "La API local rechazó el método para esa ruta.",
  map_revision_conflict: "El mapa cambió. Actualizá el catálogo y revisá la selección antes de confirmar otra vez.",
  policy_revision_conflict: "Las decisiones cambiaron. Actualizá el catálogo y revisá la selección antes de confirmar otra vez.",
  plan_revision_conflict: "El plan cambió. Actualizá el detalle antes de tomar otra decisión.",
  command_id_conflict: "Ese identificador ya fue usado con otro pedido. El replay exacto quedó bloqueado.",
  cursor_stale: "La colección cambió. Reiniciala explícitamente desde la primera página.",
  invalid_transition: "El plan ya no admite esa transición. Actualizá su detalle.",
  plan_expired: "El plan venció. Actualizá su detalle; no se puede revalidar ni cancelar.",
  payload_too_large: "La solicitud supera el límite local de 64 KiB.",
  plan_too_large: "El universo del plan supera el límite. Elegí menos objetivos.",
  json_required: "La API local requiere JSON para este comando.",
  unsupported_target: "Ese tipo de objetivo no se puede estudiar.",
  invalid_filter: "El filtro solicitado no pertenece al contrato de Estudio.",
  study_unavailable: "La fotografía sintética actual no está disponible para crear o revalidar.",
  inventory_incomplete: "El inventario sintético todavía no está completo.",
  account_unavailable: "La cuenta sintética de demostración no está disponible.",
  internal_error: "La API local no pudo completar la operación.",
  transport_error: "No pudimos comunicarnos con la API local.",
  invalid_response: "La API local devolvió una respuesta incompatible con el contrato de Estudio.",
};

const POST_PLAN_COMMAND = /^\/api\/v3\/study\/plans\/cleanup-plan-v1-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\/(?:revalidate|cancel)$/u;

function isAllowedPostPath(path: string): boolean {
  return path === "/api/v3/study/plans" || POST_PLAN_COMMAND.test(path);
}

export class StudyApiError extends Error {
  constructor(
    readonly code: StudyClientErrorCode,
    readonly status: number | null,
    readonly uncertainWrite = false,
  ) {
    super(LOCAL_MESSAGES[code]);
    this.name = "StudyApiError";
  }
}

type Decoder<T> = (payload: unknown) => payload is T;

async function readJson(response: Response, uncertainWrite: boolean): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    throw new StudyApiError("invalid_response", response.status, uncertainWrite);
  }
}

async function request<T>(path: string, decoder: Decoder<T>, serializedBody?: string): Promise<T> {
  const isPost = serializedBody !== undefined;
  if (!path.startsWith("/") || path.startsWith("//") || path.includes("://")) {
    throw new StudyApiError("invalid_request", null);
  }
  if (isPost && !isAllowedPostPath(path)) throw new StudyApiError("invalid_request", null);
  if (isPost && new TextEncoder().encode(serializedBody).byteLength > STUDY_MAX_BODY_BYTES) {
    throw new StudyApiError("payload_too_large", null);
  }

  const controller = new AbortController();
  let timeoutId: ReturnType<typeof setTimeout> | undefined;
  let response: Response;
  let payload: unknown;
  try {
    const result = await Promise.race([
      fetch(path, {
        credentials: "omit",
        mode: "same-origin",
        redirect: "error",
        signal: controller.signal,
        ...(isPost
          ? {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: serializedBody,
            }
          : { method: "GET" }),
      }).then(async (received) => ({
        response: received,
        payload: await readJson(received, isPost),
      })),
      new Promise<{ response: Response; payload: unknown }>((_resolve, reject) => {
        timeoutId = setTimeout(() => {
          controller.abort();
          reject(new StudyApiError("transport_error", null, isPost));
        }, STUDY_API_TIMEOUT_MS);
      }),
    ]);
    response = result.response;
    payload = result.payload;
  } catch (reason) {
    if (reason instanceof StudyApiError) throw reason;
    throw new StudyApiError("transport_error", null, isPost);
  } finally {
    if (timeoutId !== undefined) clearTimeout(timeoutId);
  }

  if (!response.ok) {
    const code = decodeStudyError(payload, response.status);
    if (code) throw new StudyApiError(code, response.status);
    throw new StudyApiError("invalid_response", response.status, isPost);
  }
  if (response.status !== 200) throw new StudyApiError("invalid_response", response.status, isPost);
  if (!decoder(payload)) throw new StudyApiError("invalid_response", response.status, isPost);
  return payload;
}

function queryPath(path: string, values: readonly [string, string | number | null | undefined][]): string {
  const query = new URLSearchParams();
  for (const [key, value] of values) {
    if (value !== null && value !== undefined) query.set(key, String(value));
  }
  const serialized = query.toString();
  const result = serialized ? `${path}?${serialized}` : path;
  if (new TextEncoder().encode(result.slice(result.indexOf("?") + 1)).byteLength > 4096) {
    throw new StudyApiError("invalid_request", null);
  }
  return result;
}

function planPath(planId: string): string {
  if (!isPlanId(planId)) throw new StudyApiError("invalid_request", null);
  return `/api/v3/study/plans/${encodeURIComponent(planId)}`;
}

function pageLimit(value: number | undefined, fallback: number, maximum: number): number {
  const limit = value ?? fallback;
  if (!Number.isSafeInteger(limit) || limit < 1 || limit > maximum) {
    throw new StudyApiError("invalid_request", null);
  }
  return limit;
}

export function asStudyApiError(reason: unknown): StudyApiError {
  return reason instanceof StudyApiError ? reason : new StudyApiError("transport_error", null);
}

export async function sendPrepared<T>(command: PreparedCommand<T>): Promise<T> {
  return request(command.path, command.decode, command.serializedBody);
}

export const studyApi = {
  context: (): Promise<StudyContext> => request("/api/v3/study/context", isStudyContext),
  targets: async (options: {
    kind?: TargetKind;
    cursor?: string;
    limit?: number;
  } = {}): Promise<TargetsResponse> => {
    const limit = pageLimit(options.limit, 50, 100);
    const result = await request(queryPath("/api/v3/study/targets", [
      ["kind", options.kind], ["cursor", options.cursor], ["limit", options.limit],
    ]), isTargetsResponse);
    if (result.kind !== (options.kind ?? null) || result.items.length > limit ||
      (result.nextCursor !== null && result.items.length !== limit)) {
      throw new StudyApiError("invalid_response", 200);
    }
    return result;
  },
  plans: async (options: {
    state?: PlanState;
    cursor?: string;
    limit?: number;
  } = {}): Promise<PlansResponse> => {
    const limit = pageLimit(options.limit, 50, 100);
    const result = await request(queryPath("/api/v3/study/plans", [
      ["state", options.state], ["cursor", options.cursor], ["limit", options.limit],
    ]), isPlansResponse);
    if (result.state !== (options.state ?? null) || result.items.length > limit ||
      (result.nextCursor !== null && result.items.length !== limit)) {
      throw new StudyApiError("invalid_response", 200);
    }
    return result;
  },
  plan: async (planId: string): Promise<PlanDetail> => {
    const detail = await request(planPath(planId), isPlanDetail);
    if (detail.planId !== planId) throw new StudyApiError("invalid_response", 200);
    return detail;
  },
  messages: async (planId: string, options: {
    state?: MemberFilter;
    cursor?: string;
    limit?: number;
  } = {}): Promise<MessagesResponse> => {
    const limit = pageLimit(options.limit, 100, 500);
    const result = await request(queryPath(`${planPath(planId)}/messages`, [
      ["state", options.state], ["cursor", options.cursor], ["limit", options.limit],
    ]), isMessagesResponse);
    if (result.planId !== planId || result.state !== (options.state ?? "all") || result.items.length > limit ||
      (result.nextCursor !== null && result.items.length !== limit)) {
      throw new StudyApiError("invalid_response", 200);
    }
    return result;
  },
  events: async (planId: string, options: {
    cursor?: string;
    limit?: number;
  } = {}): Promise<EventsResponse> => {
    const limit = pageLimit(options.limit, 50, 100);
    const result = await request(queryPath(`${planPath(planId)}/events`, [
      ["cursor", options.cursor], ["limit", options.limit],
    ]), isEventsResponse);
    const firstRevisionValid = options.cursor !== undefined || result.items[0]?.revision === 1;
    const finalRevisionValid = result.nextCursor !== null || result.items.at(-1)?.revision === result.planRevision;
    const cursorHasMore = result.nextCursor === null || result.items.at(-1)!.revision < result.planRevision;
    const completePageBeforeCursor = result.nextCursor === null || result.items.length === limit;
    if (result.planId !== planId || result.items.length > limit || !firstRevisionValid || !finalRevisionValid ||
      !cursorHasMore || !completePageBeforeCursor) {
      throw new StudyApiError("invalid_response", 200);
    }
    return result;
  },
  create: (command: PreparedCommand<CreateReceipt>): Promise<CreateReceipt> => sendPrepared(command),
  revalidate: (command: PreparedCommand<RevalidateReceipt>): Promise<RevalidateReceipt> => sendPrepared(command),
  cancel: (command: PreparedCommand<CancelReceipt>): Promise<CancelReceipt> => sendPrepared(command),
};
