import { afterEach, describe, expect, it, vi } from "vitest";
import { API_TIMEOUT_MS, MAX_JSON_BODY_BYTES, ApiError, api } from "./api";
import type { DecisionRequest, UndoRequest } from "./types";
import {
  connection,
  context,
  decisionsResponse,
  indexResponse,
  jsonResponse,
  mapResponse,
  sourceAId,
  sourceDetail,
  sync,
  writeResponse,
} from "./test/fixtures";

const decisionBody: DecisionRequest = {
  commandId: "11111111-1111-4111-8111-111111111111",
  decisionId: "22222222-2222-4222-8222-222222222222",
  occurredAt: "2026-08-28T12:00:00Z",
  expectedMapRevision: mapResponse.mapRevision,
  expectedPolicyRevision: mapResponse.policyRevision,
  supersedesDecisionIds: [],
  type: "setSourceDisplayName",
  sourceId: sourceAId,
  displayName: "Horizonte",
};

const undoBody: UndoRequest = {
  commandId: "33333333-3333-4333-8333-333333333333",
  occurredAt: "2026-08-28T12:01:00Z",
  expectedMapRevision: mapResponse.mapRevision,
  expectedPolicyRevision: mapResponse.policyRevision,
};

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("transporte cerrado /api/v2", () => {
  it("usa exactamente las nueve rutas del contrato", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (init?.method === "POST") return jsonResponse(writeResponse);
      const payloads: Record<string, unknown> = {
        "/api/v2/context": context,
        "/api/v2/connection": connection,
        "/api/v2/sync": sync,
        "/api/v2/index": indexResponse,
        "/api/v2/map": mapResponse,
        [`/api/v2/map/sources/${sourceAId}`]: sourceDetail,
        "/api/v2/decisions": decisionsResponse,
      };
      return jsonResponse(payloads[path]);
    });
    vi.stubGlobal("fetch", fetchMock);

    await api.context();
    await api.connection();
    await api.sync();
    await api.index();
    await api.map();
    await api.source(sourceAId);
    await api.decisions();
    await api.recordDecision(decisionBody);
    await api.undoDecision(decisionBody.decisionId, undoBody);

    expect(fetchMock.mock.calls.map(([path]) => String(path))).toEqual([
      "/api/v2/context",
      "/api/v2/connection",
      "/api/v2/sync",
      "/api/v2/index",
      "/api/v2/map",
      `/api/v2/map/sources/${sourceAId}`,
      "/api/v2/decisions",
      "/api/v2/decisions",
      `/api/v2/decisions/${decisionBody.decisionId}/undo`,
    ]);
    for (const [, init] of fetchMock.mock.calls) {
      expect(init).toEqual(expect.objectContaining({
        credentials: "omit",
        mode: "same-origin",
        redirect: "error",
      }));
    }
  });

  it("omite credenciales y no agrega Content-Type a GET", async () => {
    const fetchMock = vi.fn(async () => jsonResponse(context));
    vi.stubGlobal("fetch", fetchMock);

    await api.context();

    expect(fetchMock).toHaveBeenCalledWith("/api/v2/context", expect.objectContaining({
      credentials: "omit",
      mode: "same-origin",
      redirect: "error",
      method: "GET",
      signal: expect.anything(),
    }));
  });

  it("envía únicamente JSON en POST y conserva el cuerpo exacto", async () => {
    const fetchMock = vi.fn(async () => jsonResponse(writeResponse));
    vi.stubGlobal("fetch", fetchMock);

    await api.recordDecision(decisionBody);

    expect(fetchMock).toHaveBeenCalledWith("/api/v2/decisions", expect.objectContaining({
      credentials: "omit",
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(decisionBody),
      signal: expect.anything(),
    }));
  });

  it("rechaza localmente un POST mayor a 64 KiB sin tocar el transporte", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const flowIds = Array.from({ length: 1_000 }, (_, index) =>
      `effective-flow-v1-${index.toString(16).padStart(64, "0")}`);
    const oversized: DecisionRequest = {
      ...decisionBody,
      type: "partitionSource",
      sourceId: sourceAId,
      groups: [
        { anchors: flowIds.slice(0, 500).map((flowId) => ({ kind: "flow", flowId })) },
        { anchors: flowIds.slice(500).map((flowId) => ({ kind: "flow", flowId })) },
      ],
    };
    expect(new TextEncoder().encode(JSON.stringify(oversized)).byteLength)
      .toBeGreaterThan(MAX_JSON_BODY_BYTES);

    await expect(api.recordDecision(oversized)).rejects.toMatchObject({
      code: "payload_too_large",
      status: null,
      uncertainWrite: false,
    });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("codifica los IDs usados como segmentos de ruta", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      void input;
      return jsonResponse({ ...sourceDetail, id: "fuente/con espacio" });
    });
    vi.stubGlobal("fetch", fetchMock);

    await api.source("fuente/con espacio");

    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/v2/map/sources/fuente%2Fcon%20espacio");
  });

  it("rechaza un detalle que no corresponde al ID solicitado", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse(sourceDetail)));

    await expect(api.source("otra-fuente")).rejects.toMatchObject({
      code: "invalid_response",
      status: 200,
    });
  });

  it.each([
    "ruta privada C:\\perfil\\correo",
    "x".repeat(129),
  ])("rechaza un errorCode no cerrado sin exponerlo: %s", async (unsafeErrorCode) => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse({
      ...sync,
      state: "failed",
      partial: true,
      errorCode: unsafeErrorCode,
    })));

    await expect(api.sync()).rejects.toMatchObject({
      code: "invalid_response",
      status: 200,
    });
  });

  it("rechaza campos adicionales en respuestas exitosas", async () => {
    const fetchMock = vi.fn(async () => jsonResponse({ ...context, secreto: "no" }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(api.context()).rejects.toMatchObject({ code: "invalid_response", status: 200 });
  });

  it("traduce errores públicos sin mostrar el mensaje arbitrario del servidor", async () => {
    const fetchMock = vi.fn(async () => jsonResponse({
      error: { code: "map_revision_conflict", message: "texto interno que no debe verse" },
    }, 409));
    vi.stubGlobal("fetch", fetchMock);

    await expect(api.recordDecision(decisionBody)).rejects.toMatchObject({
      code: "map_revision_conflict",
      message: "El mapa cambió. Revisá la vista actual antes de volver a enviar.",
      uncertainWrite: false,
    });
  });

  it("marca como incierto sólo un fallo de transporte de escritura", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new TypeError("socket privado"); }));

    await expect(api.context()).rejects.toMatchObject({
      code: "transport_error",
      uncertainWrite: false,
    });
    await expect(api.recordDecision(decisionBody)).rejects.toMatchObject({
      code: "transport_error",
      uncertainWrite: true,
    });
  });

  it("considera inválido un error desconocido o con forma extra", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse({
      error: { code: "detalle_privado", message: "no", trace: "no" },
    }, 500)));

    await expect(api.context()).rejects.toEqual(expect.any(ApiError));
    await expect(api.context()).rejects.toMatchObject({ code: "invalid_response" });
  });

  it("rechaza un código público asociado al status HTTP incorrecto", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse({
      error: { code: "map_revision_conflict", message: "código cruzado" },
    }, 500)));

    await expect(api.recordDecision(decisionBody)).rejects.toMatchObject({
      code: "invalid_response",
      status: 500,
    });
  });

  it("corta una carga que no responde y la convierte en error local", async () => {
    vi.useFakeTimers();
    vi.stubGlobal("fetch", vi.fn(() => new Promise<Response>(() => undefined)));

    const assertion = expect(api.context()).rejects.toMatchObject({
      code: "transport_error",
      uncertainWrite: false,
    });
    await vi.advanceTimersByTimeAsync(API_TIMEOUT_MS);
    await assertion;
  });

  it("corta también un cuerpo JSON que nunca termina", async () => {
    vi.useFakeTimers();
    const stalled = new Response("{}");
    vi.spyOn(stalled, "json").mockImplementation(() => new Promise<unknown>(() => undefined));
    vi.stubGlobal("fetch", vi.fn(async () => stalled));

    const assertion = expect(api.context()).rejects.toMatchObject({ code: "transport_error" });
    await vi.advanceTimersByTimeAsync(API_TIMEOUT_MS);
    await assertion;
  });
});
