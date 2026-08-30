import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  sendPrepared,
  STUDY_API_TIMEOUT_MS,
  STUDY_MAX_BODY_BYTES,
  studyApi,
} from "./api";
import { prepareCancel, prepareCreate, prepareRevalidate } from "./commands";
import { isCreateReceipt } from "./decoders";
import type { PreparedCommand, StudyErrorCode } from "./types";
import {
  cancelReceipt,
  createReceipt,
  eventsResponse,
  jsonResponse,
  mapRevision,
  messagesResponse,
  planDetail,
  planId,
  plansResponse,
  revalidateReceipt,
  sourceId,
  studyContext,
  studyError,
  targetsResponse,
} from "./test/fixtures";

function installFetch() {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    void init;
    const path = String(input);
    if (path === "/api/v3/study/context") return jsonResponse(studyContext);
    if (path.startsWith("/api/v3/study/targets")) return jsonResponse({ ...targetsResponse, kind: "source", items: [targetsResponse.items[0]] });
    if (path.startsWith("/api/v3/study/plans?")) return jsonResponse({ ...plansResponse, state: "frozen" });
    if (path === "/api/v3/study/plans") return jsonResponse(createReceipt);
    if (path === `/api/v3/study/plans/${planId}`) return jsonResponse(planDetail);
    if (path.startsWith(`/api/v3/study/plans/${planId}/messages`)) return jsonResponse({ ...messagesResponse, state: "removed", items: [] });
    if (path.startsWith(`/api/v3/study/plans/${planId}/events`)) return jsonResponse(eventsResponse);
    if (path === `/api/v3/study/plans/${planId}/revalidate`) return jsonResponse(revalidateReceipt);
    if (path === `/api/v3/study/plans/${planId}/cancel`) return jsonResponse(cancelReceipt);
    return jsonResponse(studyError("route_not_found"), 404);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function createCommand() {
  return prepareCreate({
    expectedMapRevision: mapRevision,
    expectedPolicyRevision: 7,
    disposition: "archive",
    targets: [{ kind: "source" as const, targetId: sourceId }],
    temporalFilter: { kind: "all" },
    readState: "any",
    excludedLabelIds: [],
    keepLatestPerFlow: 0,
  });
}

describe("transporte cerrado /api/v3/study", () => {
  beforeEach(() => {
    vi.stubGlobal("crypto", { randomUUID: vi.fn(() => "12345678-1234-4234-8234-123456789abc") });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("consume exactamente las nueve rutas v3 con métodos, queries y segmentos codificados", async () => {
    const fetchMock = installFetch();
    const create = createCommand();
    const revalidate = prepareRevalidate(planId, {
      expectedPlanRevision: 1,
      expectedMapRevision: mapRevision,
      expectedPolicyRevision: 7,
    });
    const cancel = prepareCancel(planId, { expectedPlanRevision: 1 });

    await studyApi.context();
    await studyApi.targets({ kind: "source", cursor: "objetivos_1", limit: 20 });
    await studyApi.create(create);
    await studyApi.plans({ state: "frozen", cursor: "planes_1", limit: 10 });
    await studyApi.plan(planId);
    await studyApi.messages(planId, { state: "removed", cursor: "miembros_1", limit: 100 });
    await studyApi.events(planId, { cursor: "eventos_1", limit: 50 });
    await studyApi.revalidate(revalidate);
    await studyApi.cancel(cancel);

    expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
      "/api/v3/study/context",
      "/api/v3/study/targets?kind=source&cursor=objetivos_1&limit=20",
      "/api/v3/study/plans",
      "/api/v3/study/plans?state=frozen&cursor=planes_1&limit=10",
      `/api/v3/study/plans/${planId}`,
      `/api/v3/study/plans/${planId}/messages?state=removed&cursor=miembros_1&limit=100`,
      `/api/v3/study/plans/${planId}/events?cursor=eventos_1&limit=50`,
      `/api/v3/study/plans/${planId}/revalidate`,
      `/api/v3/study/plans/${planId}/cancel`,
    ]);
  });

  it("usa paths relativos, omite credenciales, fuerza same-origin y sólo envía JSON en POST", async () => {
    const fetchMock = installFetch();
    await studyApi.context();
    const create = createCommand();
    await studyApi.create(create);

    const getInit = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(getInit).toMatchObject({
      method: "GET",
      credentials: "omit",
      mode: "same-origin",
      redirect: "error",
    });
    expect(getInit.headers).toBeUndefined();
    const postInit = fetchMock.mock.calls[1]?.[1] as RequestInit;
    expect(postInit).toMatchObject({
      method: "POST",
      credentials: "omit",
      mode: "same-origin",
      redirect: "error",
      headers: { "Content-Type": "application/json" },
      body: create.serializedBody,
    });
    expect(JSON.stringify(postInit.headers)).not.toMatch(/authorization|cookie|origin/i);
    expect(String(fetchMock.mock.calls[0]?.[0])).not.toMatch(/^https?:/u);
  });

  it("rechaza identidades de plan inválidas antes de formar una ruta", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      void input;
      void init;
      return jsonResponse(planDetail);
    });
    vi.stubGlobal("fetch", fetchMock);
    for (const invalidPlanId of [`${planId}/otro`, ".", "..", "%2e%2e"]) {
      await expect(studyApi.plan(invalidPlanId)).rejects.toMatchObject({ code: "invalid_request" });
    }
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("rechaza un detalle válido que pertenece a otro plan", async () => {
    const otherPlanId = "cleanup-plan-v1-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
    const fetchMock = vi.fn(async () => jsonResponse({ ...planDetail, planId: otherPlanId }));
    vi.stubGlobal("fetch", fetchMock);
    await expect(studyApi.plan(planId)).rejects.toMatchObject({ code: "invalid_response" });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("mide el cuerpo UTF-8 antes del envío y cierra en 64 KiB", async () => {
    const fetchMock = installFetch();
    const oversized: PreparedCommand<typeof createReceipt> = {
      path: "/api/v3/study/plans",
      serializedBody: `{"value":"${"ñ".repeat(STUDY_MAX_BODY_BYTES)}"}`,
      decode: isCreateReceipt,
    };
    await expect(sendPrepared(oversized)).rejects.toMatchObject({
      code: "payload_too_large",
      uncertainWrite: false,
    });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it.each([
    ["map_revision_conflict", 409],
    ["policy_revision_conflict", 409],
    ["plan_revision_conflict", 409],
    ["cursor_stale", 409],
    ["invalid_cursor", 400],
    ["plan_too_large", 413],
    ["inventory_incomplete", 503],
  ] as const)("interpreta %s sólo desde el sobre cerrado", async (code, status) => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse(studyError(code as StudyErrorCode), status)));
    await expect(studyApi.context()).rejects.toMatchObject({ code, status });
  });

  it("reemplaza errores malformados por un mensaje local seguro", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse({ error: { code: "internal_error", message: "traza privada" } }, 500)));
    await expect(studyApi.context()).rejects.toMatchObject({
      code: "invalid_response",
      message: "La API local devolvió una respuesta incompatible con el contrato de Estudio.",
    });
  });

  it("marca como incierto el fallo de transporte posterior a POST", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new TypeError("fallo crudo"); }));
    await expect(studyApi.context()).rejects.toMatchObject({ code: "transport_error", uncertainWrite: false });
    const command: PreparedCommand<typeof createReceipt> = {
      path: "/api/v3/study/plans",
      serializedBody: "{}",
      decode: isCreateReceipt,
    };
    await expect(sendPrepared(command)).rejects.toMatchObject({ code: "transport_error", uncertainWrite: true });
  });

  it.each([
    ["JSON truncado", () => new Response("{", { status: 200, headers: { "Content-Type": "application/json" } })],
    ["recibo incompatible", () => jsonResponse({ ...createReceipt, extra: true })],
    ["status de éxito no contractual", () => jsonResponse(createReceipt, 201)],
  ])("conserva el POST como incierto ante %s", async (_label, response) => {
    const fetchMock = vi.fn(async (...request: [RequestInfo | URL, RequestInit?]) => {
      void request;
      return response();
    });
    vi.stubGlobal("fetch", fetchMock);
    const command = createCommand();
    await expect(studyApi.create(command)).rejects.toMatchObject({ code: "invalid_response", uncertainWrite: true });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0]?.[0]).toBe(command.path);
    expect(fetchMock.mock.calls[0]?.[1]?.body).toBe(command.serializedBody);
  });

  it("rechaza POST fuera de la allowlist antes de tocar el transporte", async () => {
    const fetchMock = installFetch();
    const command: PreparedCommand<typeof createReceipt> = {
      ...createCommand(),
      path: "/api/v3/study/targets",
    };
    await expect(sendPrepared(command)).rejects.toMatchObject({ code: "invalid_request", uncertainWrite: false });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("rechaza filtros, páginas incompletas y cursores imposibles", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse({
      ...targetsResponse,
      kind: "source",
      items: [targetsResponse.items[0]],
      nextCursor: "faltan_objetivos",
    })));
    await expect(studyApi.targets({ kind: "source", limit: 2 })).rejects.toMatchObject({ code: "invalid_response" });

    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse({ ...plansResponse, state: "reduced" })));
    await expect(studyApi.plans({ state: "frozen" })).rejects.toMatchObject({ code: "invalid_response" });

    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse({
      ...messagesResponse,
      items: [messagesResponse.items[0]],
      nextCursor: "faltan_miembros",
    })));
    await expect(studyApi.messages(planId, { limit: 2 })).rejects.toMatchObject({ code: "invalid_response" });

    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse({ ...eventsResponse, nextCursor: "cursor_fantasma" })));
    await expect(studyApi.events(planId)).rejects.toMatchObject({ code: "invalid_response" });
  });

  it("aplica timeout acotado sin reenviar automáticamente", async () => {
    vi.useFakeTimers();
    const fetchMock = vi.fn(() => new Promise<Response>(() => undefined));
    vi.stubGlobal("fetch", fetchMock);
    const pending = studyApi.context();
    const rejection = expect(pending).rejects.toMatchObject({
      code: "transport_error",
      uncertainWrite: false,
    });
    await vi.advanceTimersByTimeAsync(10_001);
    await rejection;
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  async function expectExactPostAfterTimeout<T>(command: PreparedCommand<T>, receipt: T): Promise<void> {
    vi.useFakeTimers();
    let attempt = 0;
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      void input;
      void init;
      attempt += 1;
      if (attempt === 1) return new Promise<Response>(() => undefined);
      return Promise.resolve(jsonResponse(receipt));
    });
    vi.stubGlobal("fetch", fetchMock);

    const first = sendPrepared(command);
    const rejection = expect(first).rejects.toMatchObject({
      code: "transport_error",
      uncertainWrite: true,
    });
    await vi.advanceTimersByTimeAsync(STUDY_API_TIMEOUT_MS + 1);
    await rejection;
    expect(fetchMock).toHaveBeenCalledTimes(1);

    await sendPrepared(command);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    const firstCall = fetchMock.mock.calls[0]!;
    const secondCall = fetchMock.mock.calls[1]!;
    expect(secondCall[0]).toBe(firstCall[0]);
    expect(secondCall[1]?.body).toBe(firstCall[1]?.body);
    expect(secondCall[1]?.body).toBe(command.serializedBody);
  }

  it.each([
    ["create", () => expectExactPostAfterTimeout(createCommand(), createReceipt)],
    ["revalidate", () => expectExactPostAfterTimeout(prepareRevalidate(planId, {
      expectedPlanRevision: 1,
      expectedMapRevision: mapRevision,
      expectedPolicyRevision: 7,
    }), revalidateReceipt)],
    ["cancel", () => expectExactPostAfterTimeout(
      prepareCancel(planId, { expectedPlanRevision: 1 }),
      cancelReceipt,
    )],
  ] as const)("conserva el replay byte a byte tras timeout real de %s", async (_label, exercise) => {
    await exercise();
  });
});
