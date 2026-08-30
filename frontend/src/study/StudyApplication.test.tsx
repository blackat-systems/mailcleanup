import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import { context as mapContext } from "../test/fixtures";
import { isSafePlanProgression } from "./decoders";
import { inventoryStateLabels } from "./presenters";
import { INVENTORY_STATES, type MemberFilter, type PlanDetail, type PlanMember, type PlanState, type PlanSummary, type PublicTarget, type StudyContext } from "./types";
import {
  cancelReceipt,
  cancelledAfterRevalidationDetail,
  createReceipt,
  detailAfterRevalidation,
  detailForState,
  eventsResponse,
  frozenTwoDetail,
  jsonResponse,
  messagesResponse,
  planDetail,
  planId,
  plansResponse,
  revalidateReceipt,
  studyContext,
  studyError,
  targetsResponse,
  nextMapRevision,
} from "./test/fixtures";

type ApiOptions = {
  mapContext?: unknown;
  context?: StudyContext;
  contextResponse?: () => Promise<Response>;
  detail?: PlanDetail;
  detailResponse?: () => Promise<Response>;
  plans?: unknown;
  targets?: unknown;
  messages?: unknown;
  messagesResponse?: (path: string) => Promise<Response>;
  events?: unknown;
  eventsResponse?: (path: string) => Promise<Response>;
  post?: (path: string, body: string) => Promise<Response>;
};

function installStudyApi(options: ApiOptions = {}) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path === "/api/v2/context") return jsonResponse(options.mapContext ?? mapContext);
    if (path === "/api/v3/study/context") {
      return options.contextResponse ? options.contextResponse() : jsonResponse(options.context ?? studyContext);
    }
    if (path.startsWith("/api/v3/study/targets")) return jsonResponse(options.targets ?? targetsResponse);
    if (path === "/api/v3/study/plans" && init?.method === "POST") {
      if (options.post) return options.post(path, String(init.body));
      return jsonResponse(createReceipt);
    }
    if (path.startsWith("/api/v3/study/plans?") || path === "/api/v3/study/plans") {
      return jsonResponse(options.plans ?? plansResponse);
    }
    if (path === `/api/v3/study/plans/${planId}`) {
      return options.detailResponse ? options.detailResponse() : jsonResponse(options.detail ?? planDetail);
    }
    if (path.startsWith(`/api/v3/study/plans/${planId}/messages`)) {
      return options.messagesResponse ? options.messagesResponse(path) : jsonResponse(options.messages ?? messagesResponse);
    }
    if (path.startsWith(`/api/v3/study/plans/${planId}/events`)) {
      return options.eventsResponse ? options.eventsResponse(path) : jsonResponse(options.events ?? eventsResponse);
    }
    if (path === `/api/v3/study/plans/${planId}/revalidate` && init?.method === "POST") {
      if (options.post) return options.post(path, String(init.body));
      return jsonResponse(revalidateReceipt);
    }
    if (path === `/api/v3/study/plans/${planId}/cancel` && init?.method === "POST") {
      if (options.post) return options.post(path, String(init.body));
      return jsonResponse(cancelReceipt);
    }
    return jsonResponse(studyError("route_not_found"), 404);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function fullHistoryPage(): PlanSummary[] {
  const base = plansResponse.items[0]!;
  return Array.from({ length: 10 }, (_value, index) => {
    const createdAt = new Date(Date.parse(base.createdAt) - index * 60_000).toISOString();
    const expiresAt = new Date(Date.parse(createdAt) + 86_400_000).toISOString();
    return {
      ...base,
      planId: index === 0 ? base.planId : `cleanup-plan-v1-12345678-1234-4234-8234-${index.toString(16).padStart(12, "0")}`,
      createdAt,
      expiresAt,
    };
  });
}

function fullTargetPage(): PublicTarget[] {
  const base = targetsResponse.items[0]!;
  if (base.kind !== "source") throw new Error("fixture source expected");
  return Array.from({ length: 50 }, (_value, index) => index === 0 ? base : {
    ...base,
    targetId: `effective-source-v1-${index.toString(16).padStart(24, "0")}`,
    displayName: `Fuente ${index.toString().padStart(2, "0")}`,
  });
}

function fullMemberPage(): PlanMember[] {
  const base = messagesResponse.items[0]!;
  return Array.from({ length: 100 }, (_value, index) => ({
    ...base,
    messageId: index === 0 ? base.messageId : `message-v1-${index.toString(16).padStart(64, "0")}`,
    receivedAt: new Date(Date.parse(base.receivedAt) - index * 60_000).toISOString(),
  }));
}

function historyPage(start: number, count: number): PlanSummary[] {
  const base = plansResponse.items[0]!;
  return Array.from({ length: count }, (_value, offset) => {
    const index = start + offset;
    const createdAt = new Date(Date.parse(base.createdAt) - index * 60_000).toISOString();
    return {
      ...base,
      planId: `cleanup-plan-v1-87654321-4321-4321-8321-${index.toString(16).padStart(12, "0")}`,
      createdAt,
      expiresAt: new Date(Date.parse(createdAt) + 86_400_000).toISOString(),
    };
  });
}

function targetPage(start: number, count: number): PublicTarget[] {
  const base = targetsResponse.items[0]!;
  if (base.kind !== "source") throw new Error("fixture source expected");
  return Array.from({ length: count }, (_value, offset) => {
    const index = start + offset;
    return {
      ...base,
      targetId: `effective-source-v1-${index.toString(16).padStart(24, "0")}`,
      displayName: `Z Fuente ${index.toString().padStart(3, "0")}`,
    };
  });
}

function memberPage(start: number, count: number): PlanMember[] {
  const base = messagesResponse.items[0]!;
  return Array.from({ length: count }, (_value, offset) => {
    const index = start + offset;
    return {
      ...base,
      messageId: `message-v1-${index.toString(16).padStart(64, "0")}`,
      receivedAt: new Date(Date.parse(base.receivedAt) - index * 60_000).toISOString(),
    };
  });
}

function detailAfterSecondRevalidation(): PlanDetail {
  const revisionTwo = detailAfterRevalidation("frozen");
  return {
    ...revisionTwo,
    planRevision: 3,
    lastRevalidatedAt: "2026-08-29T14:00:00Z",
    eventCount: 3,
    recentEvents: [{
      revision: 3,
      type: "revalidated",
      recordedAt: "2026-08-29T14:00:00Z",
      state: "frozen",
      observedMapRevision: studyContext.availability.currentMapRevision,
      observedPolicyRevision: 7,
      removedCount: 0,
      remainingCount: 1,
    }, ...revisionTwo.recentEvents],
  };
}

const MEMBER_FILTER_CASES = [
  ["all", "Todo el universo inicial"],
  ["selected", "Selección original"],
  ["eligible", "Elegibles actuales"],
  ["excluded", "Excluidos al crear"],
  ["removed", "Retirados después"],
] as const satisfies readonly (readonly [MemberFilter, string])[];

function coherentMemberRows(): Record<MemberFilter, PlanMember[]> {
  const eligible = messagesResponse.items[0]!;
  const excluded = messagesResponse.items[1]!;
  const removed: PlanMember = {
    ...eligible,
    messageId: `message-v1-${"d".repeat(64)}`,
    currentState: "removed",
    receivedAt: "2026-08-18T12:00:00Z",
    reasonCodes: ["missing_after_creation"],
  };
  return {
    all: [eligible, excluded, removed],
    selected: [eligible, removed],
    eligible: [eligible],
    excluded: [excluded],
    removed: [removed],
  };
}

function contradictoryMemberRows(
  items: readonly PlanMember[],
  mismatch: "n-1" | "n+1" | "wrong-size",
): PlanMember[] {
  if (mismatch === "n-1") return items.slice(0, -1);
  if (mismatch === "wrong-size") {
    return items.map((item, index) => index === 0 ? { ...item, sizeEstimateBytes: item.sizeEstimateBytes + 1 } : item);
  }
  const template = items[0]!;
  return [...items, {
    ...template,
    messageId: `message-v1-${"c".repeat(64)}`,
    receivedAt: "2026-08-01T12:00:00Z",
  }];
}

function partitionContradiction(state: "all" | "selected", rows: Record<MemberFilter, PlanMember[]>): PlanMember[] {
  if (state === "selected") {
    return rows.selected.map((item) => item.currentState === "removed"
      ? { ...item, currentState: "eligible", reasonCodes: [] }
      : item);
  }
  return rows.all.map((item) => item.currentState === "removed"
    ? { ...item, initialState: "excluded", currentState: "excluded", reasonCodes: ["starred"] }
    : item);
}

function eventLedger(count = 51): PlanDetail["recentEvents"] {
  return Array.from({ length: count }, (_value, index) => ({
    revision: index + 1,
    type: index === 0 ? "created" : "revalidated",
    recordedAt: new Date(Date.parse("2026-08-29T12:00:00Z") + index * 60_000).toISOString(),
    state: "frozen",
    observedMapRevision: studyContext.availability.currentMapRevision,
    observedPolicyRevision: 7,
    removedCount: 0,
    remainingCount: 1,
  }));
}

function detailForLedger(events: PlanDetail["recentEvents"]): PlanDetail {
  return {
    ...planDetail,
    planRevision: events.length,
    lastRevalidatedAt: events.at(-1)!.recordedAt,
    eventCount: events.length,
    recentEvents: events.slice(-10).reverse(),
  };
}

function detailForMemberPagination(events: PlanDetail["recentEvents"]): PlanDetail {
  return {
    ...detailForLedger(events),
    selectedAtCreationCount: 101,
    selectedAtCreationSizeEstimateBytes: 206_848,
    excludedAtCreationCount: 0,
    excludedAtCreationSizeEstimateBytes: 0,
    currentEligibleCount: 101,
    currentEligibleSizeEstimateBytes: 206_848,
    excludedSamples: [],
  };
}

function detailAfterImpossibleTerminalRevision(previous: PlanDetail): PlanDetail {
  const planRevision = previous.planRevision + 11;
  const firstRevision = planRevision - 9;
  const eligibleBeforeTerminal = previous.state === "invalidated"
    ? previous.selectedAtCreationCount
    : previous.currentEligibleCount;
  const ascendingEvents: PlanDetail["recentEvents"] = Array.from({ length: 10 }, (_value, index) => {
    const revision = firstRevision + index;
    const recordedAt = new Date(Date.parse("2026-08-29T15:00:00Z") + index * 60_000).toISOString();
    if (revision === planRevision && previous.state === "cancelled") {
      return {
        revision,
        type: "cancelled",
        recordedAt,
        state: "cancelled",
        observedMapRevision: null,
        observedPolicyRevision: null,
        removedCount: 0,
        remainingCount: eligibleBeforeTerminal,
      };
    }
    if (revision === planRevision && previous.state === "invalidated") {
      return {
        revision,
        type: "invalidated",
        recordedAt,
        state: "invalidated",
        observedMapRevision: studyContext.availability.currentMapRevision,
        observedPolicyRevision: 7,
        removedCount: eligibleBeforeTerminal,
        remainingCount: 0,
      };
    }
    return {
      revision,
      type: "revalidated",
      recordedAt,
      state: "frozen",
      observedMapRevision: studyContext.availability.currentMapRevision,
      observedPolicyRevision: 7,
      removedCount: 0,
      remainingCount: eligibleBeforeTerminal,
    };
  });
  const recentEvents = [...ascendingEvents].reverse();
  const latestRevalidation = recentEvents.find((event) => event.type !== "cancelled")!;
  return {
    ...previous,
    planRevision,
    lastRevalidatedAt: latestRevalidation.recordedAt,
    eventCount: planRevision,
    recentEvents,
  };
}

function deferredResponse() {
  let resolve!: (response: Response) => void;
  const promise = new Promise<Response>((next) => {
    resolve = next;
  });
  return { promise, resolve };
}

function incompatibleStudyContext(): unknown {
  return {
    ...studyContext,
    capabilities: { ...studyContext.capabilities, execute: true },
  };
}

function dynamicallyBlockedStudyContext(): StudyContext {
  return {
    ...studyContext,
    availability: {
      ...studyContext.availability,
      inventoryState: "running",
      completeSnapshotAvailable: false,
      currentMapRevision: null,
      currentPolicyRevision: null,
      targetReadAvailable: false,
      planCreateAvailable: false,
      planRevalidateAvailable: false,
      blockerCodes: ["inventory_incomplete"],
    },
  };
}

async function reachReview(user: ReturnType<typeof userEvent.setup>) {
  await user.click(await screen.findByRole("button", { name: "Crear estudio" }));
  await user.click(await screen.findByRole("checkbox", { name: /Boletines Example/u }));
  await user.click(screen.getByRole("button", { name: "Continuar al paso 2" }));
  await user.click(screen.getByRole("button", { name: "Continuar al paso 3" }));
  await user.click(screen.getByRole("button", { name: "Continuar al paso 4" }));
  await user.click(screen.getByRole("button", { name: "Continuar al paso 5" }));
}

describe("subaplicación route-aware de Estudio", () => {
  beforeEach(() => {
    vi.stubGlobal("crypto", { randomUUID: vi.fn(() => "12345678-1234-4234-8234-123456789abc") });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("compone sólo contextos v2/v3, historia v3 y nunca carga el mapa", async () => {
    window.location.hash = "#/study";
    const fetchMock = installStudyApi();
    render(<App />);

    expect(await screen.findByRole("heading", { name: "Estudio de Limpieza", level: 1 })).toBeVisible();
    expect(await screen.findByRole("heading", { name: "Archivo", level: 3 })).toBeVisible();
    const paths = fetchMock.mock.calls.map((call) => String(call[0]));
    expect(paths).toContain("/api/v2/context");
    expect(paths).toContain("/api/v3/study/context");
    expect(paths).toContain("/api/v3/study/plans?limit=10");
    expect(paths.some((path) => path === "/api/v2/map" || path.startsWith("/api/v2/map/"))).toBe(false);
    expect(paths.filter((path) => path.startsWith("/api/v2/"))).toEqual(["/api/v2/context"]);
    expect(screen.getByText("Vista previa sin efectos; no modifica Gmail.")).toBeVisible();
    expect(screen.getByRole("link", { name: "Estudio de Limpieza" })).toHaveAttribute("aria-current", "page");
  });

  it("bloquea comandos ante contexto v2 incompatible sin ocultar historia", async () => {
    window.location.hash = "#/study";
    installStudyApi({
      mapContext: {
        ...mapContext,
        capabilities: { ...mapContext.capabilities, cleanupPlan: true },
      },
    });
    render(<App />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Comandos bloqueados");
    expect(await screen.findByRole("heading", { name: "Archivo", level: 3 })).toBeVisible();
    expect(screen.getByRole("button", { name: "Crear estudio" })).toBeDisabled();
  });

  it("presenta cuenta ausente e inventario bloqueado sin perder planes", async () => {
    window.location.hash = "#/study";
    installStudyApi({
      context: {
        ...studyContext,
        availability: {
          accountAvailable: false,
          inventoryState: null,
          completeSnapshotAvailable: false,
          currentMapRevision: null,
          currentPolicyRevision: null,
          targetReadAvailable: false,
          planCreateAvailable: false,
          planRevalidateAvailable: false,
          blockerCodes: ["account_unavailable"],
        },
      },
    });
    render(<App />);

    expect(await screen.findByText("La cuenta sintética de demostración está ausente.")).toBeVisible();
    expect(await screen.findByRole("link", { name: /Ver detalle/u })).toBeVisible();
    expect(screen.getByRole("button", { name: "Crear estudio" })).toBeDisabled();
  });

  it.each(INVENTORY_STATES)("representa el inventario %s sin habilitar comandos antes de completed", async (inventoryState) => {
    window.location.hash = "#/study";
    const available = inventoryState === "completed";
    installStudyApi({
      context: available ? studyContext : {
        ...studyContext,
        availability: {
          accountAvailable: true,
          inventoryState,
          completeSnapshotAvailable: false,
          currentMapRevision: null,
          currentPolicyRevision: null,
          targetReadAvailable: false,
          planCreateAvailable: false,
          planRevalidateAvailable: false,
          blockerCodes: ["inventory_incomplete"],
        },
      },
    });
    render(<App />);

    const create = await screen.findByRole("button", { name: "Crear estudio" });
    expect(screen.getByText(inventoryStateLabels[inventoryState])).toBeVisible();
    if (available) expect(create).toBeEnabled();
    else expect(create).toBeDisabled();
  });

  it("muestra historia y catálogo vacíos sin inventar objetivos", async () => {
    window.location.hash = "#/study";
    installStudyApi({
      plans: { ...plansResponse, items: [], nextCursor: null },
      targets: { ...targetsResponse, items: [], nextCursor: null },
    });
    const user = userEvent.setup();
    render(<App />);

    expect(await screen.findByText("Todavía no hay planes")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Crear estudio" }));
    expect(await screen.findByText("Catálogo vacío")).toBeVisible();
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
  });

  it("mantiene comandos bloqueados durante la carga inicial y sale del estado vivo al completar ambos contextos", async () => {
    window.location.hash = "#/study";
    let releaseMap!: (response: Response) => void;
    const pendingMap = new Promise<Response>((resolve) => { releaseMap = resolve; });
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path === "/api/v2/context") return pendingMap;
      if (path === "/api/v3/study/context") return jsonResponse(studyContext);
      if (path === "/api/v3/study/plans?limit=10") return jsonResponse(plansResponse);
      return jsonResponse(studyError("route_not_found"), 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    expect(await screen.findByText("Comprobando los contratos sintéticos v2 y v3…")).toBeVisible();
    expect(screen.getByRole("button", { name: "Crear estudio" })).toBeDisabled();
    releaseMap(jsonResponse(mapContext));
    await waitFor(() => expect(screen.queryByText("Comprobando los contratos sintéticos v2 y v3…")).not.toBeInTheDocument());
    expect(screen.getByRole("button", { name: "Crear estudio" })).toBeEnabled();
  });

  it.each([
    ["fallo local", async () => { throw new TypeError("detalle privado"); }, "No pudimos comunicarnos con la API local"],
    ["respuesta inválida", async () => jsonResponse({ contractVersion: 1 }), "respuesta incompatible con el contrato"],
  ] as const)("cierra comandos ante %s sin ocultar historia ni quedar cargando", async (_case, contextResponse, message) => {
    window.location.hash = "#/study";
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path === "/api/v2/context") return jsonResponse(mapContext);
      if (path === "/api/v3/study/context") return contextResponse();
      if (path === "/api/v3/study/plans?limit=10") return jsonResponse(plansResponse);
      return jsonResponse(studyError("route_not_found"), 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    expect(await screen.findByText(new RegExp(message, "u"))).toBeVisible();
    expect(screen.getByRole("button", { name: "Crear estudio" })).toBeDisabled();
    expect(await screen.findByRole("heading", { name: "Archivo", level: 3 })).toBeVisible();
    expect(screen.queryByText("Comprobando los contratos sintéticos v2 y v3…")).not.toBeInTheDocument();
    expect(screen.queryByText("detalle privado")).not.toBeInTheDocument();
  });

  it("lleva el foco al constructor y lo devuelve a la acción principal al cerrarlo", async () => {
    window.location.hash = "#/study";
    installStudyApi();
    const user = userEvent.setup();
    render(<App />);

    const create = await screen.findByRole("button", { name: "Crear estudio" });
    await user.click(create);
    const builderHeading = await screen.findByRole("heading", { name: "Preparar un estudio", level: 2 });
    await waitFor(() => expect(builderHeading).toHaveFocus());
    await user.click(screen.getByRole("button", { name: "Cerrar constructor" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Crear estudio" })).toHaveFocus());
  });

  it("no roba foco cuando terminan las cargas automáticas de historia y catálogo", async () => {
    window.location.hash = "#/study";
    const historyResponse = deferredResponse();
    const catalogResponse = deferredResponse();
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path === "/api/v2/context") return jsonResponse(mapContext);
      if (path === "/api/v3/study/context") return jsonResponse(studyContext);
      if (path === "/api/v3/study/plans?limit=10") return historyResponse.promise;
      if (path === "/api/v3/study/targets?limit=50") return catalogResponse.promise;
      return jsonResponse(studyError("route_not_found"), 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<App />);

    const create = await screen.findByRole("button", { name: "Crear estudio" });
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/v3/study/plans?limit=10",
      expect.objectContaining({ method: "GET" }),
    ));
    create.focus();
    await act(async () => historyResponse.resolve(jsonResponse(plansResponse)));
    expect(await screen.findByRole("heading", { name: "Archivo", level: 3 })).toBeVisible();
    expect(create).toHaveFocus();

    await user.click(create);
    const builderHeading = await screen.findByRole("heading", { name: "Preparar un estudio", level: 2 });
    await waitFor(() => expect(builderHeading).toHaveFocus());
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/v3/study/targets?limit=50",
      expect.objectContaining({ method: "GET" }),
    ));
    await act(async () => catalogResponse.resolve(jsonResponse(targetsResponse)));
    expect(await screen.findByRole("checkbox", { name: /Boletines Example/u })).toBeVisible();
    expect(builderHeading).toHaveFocus();
  });

  it.each([
    ["Miembros y razones", "members", "2 miembros cargados"],
    ["Eventos completos", "events", "1 eventos cargados"],
  ] as const)("no roba foco cuando termina la carga automática de %s", async (panelTitle, surface, loadedText) => {
    window.location.hash = `#/study/plans/${planId}`;
    const collectionResponse = deferredResponse();
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path === "/api/v2/context") return jsonResponse(mapContext);
      if (path === "/api/v3/study/context") return jsonResponse(studyContext);
      if (path === "/api/v3/study/plans?limit=10") return jsonResponse(plansResponse);
      if (path === `/api/v3/study/plans/${planId}`) return jsonResponse(planDetail);
      if (path === `/api/v3/study/plans/${planId}/messages?state=all&limit=100`) {
        return surface === "members" ? collectionResponse.promise : jsonResponse(messagesResponse);
      }
      if (path === `/api/v3/study/plans/${planId}/events?limit=50`) {
        return surface === "events" ? collectionResponse.promise : jsonResponse(eventsResponse);
      }
      return jsonResponse(studyError("route_not_found"), 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<App />);

    await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });
    const summary = screen.getByText(panelTitle).closest("summary")!;
    await user.click(summary);
    expect(summary).toHaveFocus();
    const expectedPath = surface === "members"
      ? `/api/v3/study/plans/${planId}/messages?state=all&limit=100`
      : `/api/v3/study/plans/${planId}/events?limit=50`;
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      expectedPath,
      expect.objectContaining({ method: "GET" }),
    ));
    await act(async () => collectionResponse.resolve(jsonResponse(surface === "members" ? messagesResponse : eventsResponse)));

    expect(await screen.findByText(loadedText)).toBeVisible();
    expect(summary).toHaveFocus();
  });

  it("completa el constructor por etapas con fechas civiles, etiquetas sólo como exclusión y límites", async () => {
    window.location.hash = "#/study";
    installStudyApi();
    const user = userEvent.setup();
    render(<App />);

    await user.click(await screen.findByRole("button", { name: "Crear estudio" }));
    expect(await screen.findByRole("group", { name: "Qué estudiar" })).toBeVisible();
    expect(screen.queryByRole("checkbox", { name: /Recibidos/u })).not.toBeInTheDocument();
    await user.click(screen.getByRole("checkbox", { name: /Boletines Example/u }));
    await user.click(screen.getByRole("button", { name: "Continuar al paso 2" }));
    expect(screen.getByRole("group", { name: "Intención" })).toBeVisible();
    await user.click(screen.getByRole("radio", { name: /Papelera/u }));
    await user.click(screen.getByRole("button", { name: "Continuar al paso 3" }));
    await user.click(screen.getByRole("radio", { name: "Antes de una fecha" }));
    fireEvent.change(screen.getByLabelText("Fecha final exclusiva"), { target: { value: "2026-08-20" } });
    await user.click(screen.getByRole("radio", { name: "Sólo no leídos" }));
    expect(screen.getByText(/America\/Argentina\/Cordoba/u)).toBeVisible();
    expect(screen.getByText(/fecha indicada queda afuera/u)).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Continuar al paso 4" }));
    expect(screen.getByRole("checkbox", { name: /Recibidos/u })).toBeVisible();
    await user.click(screen.getByRole("checkbox", { name: /Recibidos/u }));
    fireEvent.change(screen.getByLabelText("Conservar los últimos N por flujo"), { target: { value: "2" } });
    await user.click(screen.getByRole("button", { name: "Continuar al paso 5" }));
    expect(screen.getByRole("group", { name: "Revisión final" })).toHaveTextContent("Papelera");
    expect(screen.getByRole("group", { name: "Revisión final" })).toHaveTextContent("Antes del 2026-08-20");
    expect(screen.queryByRole("button", { name: /Aprobar|Ejecutar|Archivar ahora|Mover a Papelera ahora|Desuscribir/u })).not.toBeInTheDocument();
  });

  it.each([
    ["Entre dos fechas", "Ingresá un rango válido cuyo inicio sea anterior al final.", "Inicio incluido", "Final excluido"],
    ["Más antiguos que N días", "Ingresá entre 1 y 36.500 días civiles completos.", "Días civiles completos", null],
  ] as const)("valida la variante temporal %s antes de avanzar", async (variant, errorText, firstLabel, secondLabel) => {
    window.location.hash = "#/study";
    installStudyApi();
    const user = userEvent.setup();
    render(<App />);
    await user.click(await screen.findByRole("button", { name: "Crear estudio" }));
    await user.click(await screen.findByRole("checkbox", { name: /Boletines Example/u }));
    await user.click(screen.getByRole("button", { name: "Continuar al paso 2" }));
    await user.click(screen.getByRole("button", { name: "Continuar al paso 3" }));
    await user.click(screen.getByRole("radio", { name: variant }));
    if (secondLabel) {
      fireEvent.change(screen.getByLabelText(firstLabel), { target: { value: "2026-08-20" } });
      fireEvent.change(screen.getByLabelText(secondLabel), { target: { value: "2026-08-20" } });
    } else {
      fireEvent.change(screen.getByLabelText(firstLabel), { target: { value: "0" } });
    }
    await user.click(screen.getByRole("button", { name: "Continuar al paso 4" }));
    expect(await screen.findByText(errorText)).toBeVisible();
    expect(screen.getByRole("group", { name: "Período civil de Córdoba" })).toBeVisible();
    if (secondLabel) {
      fireEvent.change(screen.getByLabelText(secondLabel), { target: { value: "2026-08-21" } });
    } else {
      fireEvent.change(screen.getByLabelText(firstLabel), { target: { value: "30" } });
    }
    await user.click(screen.getByRole("button", { name: "Continuar al paso 4" }));
    expect(screen.getByRole("group", { name: "Exclusiones" })).toBeVisible();
  });

  it("rechaza keepLatestPerFlow vacío en vez de convertirlo silenciosamente a cero", async () => {
    window.location.hash = "#/study";
    installStudyApi();
    const user = userEvent.setup();
    render(<App />);
    await user.click(await screen.findByRole("button", { name: "Crear estudio" }));
    await user.click(await screen.findByRole("checkbox", { name: /Boletines Example/u }));
    await user.click(screen.getByRole("button", { name: "Continuar al paso 2" }));
    await user.click(screen.getByRole("button", { name: "Continuar al paso 3" }));
    await user.click(screen.getByRole("button", { name: "Continuar al paso 4" }));
    fireEvent.change(screen.getByLabelText("Conservar los últimos N por flujo"), { target: { value: "" } });
    await user.click(screen.getByRole("button", { name: "Continuar al paso 5" }));
    expect(await screen.findByText("Ingresá un entero entre 0 y 10.000.")).toBeVisible();
    expect(screen.getByRole("group", { name: "Exclusiones" })).toBeVisible();
  });

  it("crea con CAS, relee detalle/contexto/historia y recién entonces navega", async () => {
    window.location.hash = "#/study";
    const delayedConfirmation = deferredResponse();
    let detailReads = 0;
    const fetchMock = installStudyApi({
      detailResponse: async () => {
        detailReads += 1;
        return detailReads === 1 ? delayedConfirmation.promise : jsonResponse(planDetail);
      },
    });
    const user = userEvent.setup();
    render(<App />);
    await reachReview(user);
    await user.click(screen.getByRole("button", { name: "Crear estudio" }));

    await waitFor(() => expect(detailReads).toBe(1));
    expect(window.location.hash).toBe("#/study");
    expect(screen.getByRole("button", { name: "Creando estudio…" })).toBeDisabled();
    await act(async () => delayedConfirmation.resolve(jsonResponse(planDetail)));
    await screen.findByText("Leé el alcance histórico y su estado efectivo sin reconstruirlo desde el mapa actual.");
    expect(screen.getByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 })).toBeVisible();
    const createCall = fetchMock.mock.calls.find((call) => call[0] === "/api/v3/study/plans" && call[1]?.method === "POST");
    expect(JSON.parse(String(createCall?.[1]?.body))).toMatchObject({
      expectedMapRevision: studyContext.availability.currentMapRevision,
      expectedPolicyRevision: studyContext.availability.currentPolicyRevision,
      targets: [{ kind: "source", targetId: targetsResponse.items[0]?.targetId }],
    });
    expect(fetchMock.mock.calls.filter((call) => call[0] === `/api/v3/study/plans/${planId}`).length).toBeGreaterThanOrEqual(2);
    expect(fetchMock.mock.calls.filter((call) => call[0] === "/api/v3/study/context").length).toBeGreaterThanOrEqual(2);
  });

  it.each([
    ["idéntica", false],
    ["con identidad congelada reescrita", true],
  ] as const)("ancla la fotografía confirmada y trata como %s la siguiente lectura r1", async (_case, rewritten) => {
    window.location.hash = "#/study";
    const rewrittenDetail: PlanDetail = {
      ...planDetail,
      includedSamples: planDetail.includedSamples.map((sample) => ({
        ...sample,
        subject: "Asunto sintético reescrito",
      })),
    };
    let detailReads = 0;
    const fetchMock = installStudyApi({
      detailResponse: async () => {
        detailReads += 1;
        return jsonResponse(detailReads === 1 || !rewritten ? planDetail : rewrittenDetail);
      },
    });
    const user = userEvent.setup();
    render(<App />);
    await reachReview(user);
    await user.click(screen.getByRole("button", { name: "Crear estudio" }));

    if (rewritten) {
      expect(await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza no disponible", level: 1 })).toBeVisible();
      expect(screen.queryByText("Asunto sintético reescrito")).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Revalidar alcance" })).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Cancelar plan" })).not.toBeInTheDocument();
    } else {
      expect(await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 })).toBeVisible();
      expect(screen.getByText("Plan r1")).toBeVisible();
      expect(screen.getByRole("button", { name: "Revalidar alcance" })).toBeEnabled();
      expect(screen.getByRole("button", { name: "Cancelar plan" })).toBeEnabled();
    }
    expect(detailReads).toBe(2);
    expect(fetchMock.mock.calls.filter((call) => call[1]?.method === "POST")).toHaveLength(1);
  });

  it("ancla r2 al recuperar un create sin confirmar y rechaza otra variante válida de esa revisión", async () => {
    window.location.hash = `#/study/plans/${planId}`;
    const confirmedR2 = detailAfterRevalidation("frozen");
    const rewrittenR2: PlanDetail = {
      ...confirmedR2,
      currentPolicyRevision: 8,
      recentEvents: [{
        ...confirmedR2.recentEvents[0]!,
        observedPolicyRevision: 8,
      }, confirmedR2.recentEvents[1]!],
      warnings: ["policy_changed_since_creation"],
    };
    expect(isSafePlanProgression(planDetail, rewrittenR2)).toBe(true);
    expect(isSafePlanProgression(confirmedR2, rewrittenR2)).toBe(false);
    let detailReads = 0;
    const fetchMock = installStudyApi({
      detailResponse: async () => {
        detailReads += 1;
        if (detailReads === 1) return jsonResponse(planDetail);
        if (detailReads === 2) throw new TypeError("lectura interrumpida");
        return jsonResponse(detailReads === 3 ? confirmedR2 : rewrittenR2);
      },
    });
    const user = userEvent.setup();
    render(<App />);
    await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });
    await user.click(screen.getByRole("link", { name: "Volver a planes" }));
    await screen.findByRole("heading", { name: "Estudio de Limpieza", level: 1 });
    await reachReview(user);
    await user.click(screen.getByRole("button", { name: "Crear estudio" }));
    await user.click(await screen.findByRole("button", { name: "Confirmar el estado del estudio aceptado" }));

    expect(await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza no disponible", level: 1 })).toBeVisible();
    expect(screen.queryByRole("button", { name: "Revalidar alcance" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Cancelar plan" })).not.toBeInTheDocument();
    expect(detailReads).toBe(4);
    expect(fetchMock.mock.calls.filter((call) => call[1]?.method === "POST")).toHaveLength(1);
  });

  it.each([
    ["create", false],
    ["replay", true],
  ] as const)("mantiene sin confirmar un %s cuya confirmación r4 termina después de desmontar StudyPage", async (_case, replayed) => {
    window.location.hash = "#/study";
    const delayedConfirmation = deferredResponse();
    const visibleDetail = detailForLedger(eventLedger(3));
    const confirmedDetail = detailForLedger(eventLedger(4));
    let detailReads = 0;
    const postBodies: string[] = [];
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path === "/api/v2/context") return jsonResponse(mapContext);
      if (path === "/api/v3/study/context") return jsonResponse(studyContext);
      if (path === "/api/v3/study/targets?limit=50") return jsonResponse(targetsResponse);
      if (path === "/api/v3/study/plans" && init?.method === "POST") {
        postBodies.push(String(init.body));
        if (replayed && postBodies.length === 1) throw new TypeError("resultado incierto");
        return jsonResponse({ ...createReceipt, replayed });
      }
      if (path === "/api/v3/study/plans?limit=10") return jsonResponse(plansResponse);
      if (path === `/api/v3/study/plans/${planId}`) {
        detailReads += 1;
        if (detailReads === 1) return delayedConfirmation.promise;
        return jsonResponse(detailReads === 2 ? visibleDetail : confirmedDetail);
      }
      return jsonResponse(studyError("route_not_found"), 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<App />);
    await reachReview(user);
    await user.click(screen.getByRole("button", { name: "Crear estudio" }));
    if (replayed) {
      await user.click(await screen.findByRole("button", { name: "Repetir exactamente el mismo envío" }));
      expect(postBodies[1]).toBe(postBodies[0]);
    }
    await waitFor(() => expect(detailReads).toBe(1));

    await user.click(await screen.findByRole("link", { name: /Ver detalle del plan/u }));
    await screen.findByText("Plan r3");
    expect(detailReads).toBe(2);

    await act(async () => delayedConfirmation.resolve(jsonResponse(confirmedDetail)));

    expect(await screen.findByText(/estado actual todavía no pudo confirmarse/u)).toBeVisible();
    expect(screen.getByText("Plan r3")).toBeVisible();
    expect(screen.queryByText("Plan r4")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Revalidar alcance" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Cancelar plan" })).toBeDisabled();
    expect(fetchMock.mock.calls.filter((call) => call[1]?.method === "POST")).toHaveLength(replayed ? 2 : 1);

    await user.click(screen.getByRole("button", { name: "Actualizar detalle y contrato" }));
    expect(await screen.findByText("Plan r4")).toBeVisible();
    expect(await screen.findByText("El estado actual del comando aceptado quedó confirmado.")).toBeVisible();
    expect(screen.getByRole("button", { name: "Revalidar alcance" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Cancelar plan" })).toBeEnabled();
    expect(detailReads).toBe(3);
    expect(fetchMock.mock.calls.filter((call) => call[1]?.method === "POST")).toHaveLength(replayed ? 2 : 1);
  });

  it("no secuestra otra ruta cuando la confirmación aceptada termina después de desmontar StudyPage", async () => {
    window.location.hash = "#/study";
    const delayedConfirmation = deferredResponse();
    let detailReads = 0;
    const fetchMock = installStudyApi({
      detailResponse: async () => {
        detailReads += 1;
        return delayedConfirmation.promise;
      },
    });
    const user = userEvent.setup();
    render(<App />);
    await reachReview(user);
    await user.click(screen.getByRole("button", { name: "Crear estudio" }));
    await waitFor(() => expect(detailReads).toBe(1));

    await act(async () => {
      window.history.replaceState(null, "", "#/ruta-inexistente");
      window.dispatchEvent(new HashChangeEvent("hashchange"));
    });
    await screen.findByRole("heading", { name: "Esta sección no existe", level: 1 });
    await act(async () => delayedConfirmation.resolve(jsonResponse(detailForLedger(eventLedger(4)))));

    expect(window.location.hash).toBe("#/ruta-inexistente");
    expect(screen.getByRole("heading", { name: "Esta sección no existe", level: 1 })).toBeVisible();
    expect(fetchMock.mock.calls.filter((call) => call[1]?.method === "POST")).toHaveLength(1);

    await act(async () => {
      window.history.replaceState(null, "", "#/study");
      window.dispatchEvent(new HashChangeEvent("hashchange"));
    });
    expect(await screen.findByRole("button", { name: "Confirmar el estado del estudio aceptado" })).toBeVisible();
  });

  it("preserva unconfirmed si confirmAcceptedState termina desmontado y sólo lo limpia al recuperar montado", async () => {
    window.location.hash = "#/study";
    const delayedRecovery = deferredResponse();
    let detailReads = 0;
    const fetchMock = installStudyApi({
      detailResponse: async () => {
        detailReads += 1;
        if (detailReads === 1) throw new TypeError("lectura interrumpida");
        if (detailReads === 2) return delayedRecovery.promise;
        return jsonResponse(planDetail);
      },
    });
    const user = userEvent.setup();
    render(<App />);
    await reachReview(user);
    await user.click(screen.getByRole("button", { name: "Crear estudio" }));
    const confirm = await screen.findByRole("button", { name: "Confirmar el estado del estudio aceptado" });
    await user.click(confirm);
    await waitFor(() => expect(detailReads).toBe(2));

    await act(async () => {
      window.history.replaceState(null, "", "#/ruta-inexistente");
      window.dispatchEvent(new HashChangeEvent("hashchange"));
    });
    await screen.findByRole("heading", { name: "Esta sección no existe", level: 1 });
    await act(async () => delayedRecovery.resolve(jsonResponse(planDetail)));
    expect(window.location.hash).toBe("#/ruta-inexistente");

    await act(async () => {
      window.history.replaceState(null, "", "#/study");
      window.dispatchEvent(new HashChangeEvent("hashchange"));
    });
    const resumedConfirm = await screen.findByRole("button", { name: "Confirmar el estado del estudio aceptado" });
    await user.click(resumedConfirm);
    expect(await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 })).toBeVisible();
    expect(fetchMock.mock.calls.filter((call) => call[1]?.method === "POST")).toHaveLength(1);
  });

  it.each([
    ["puente r11…r2", 11, true],
    ["hueco r12…r3", 12, false],
  ] as const)("exige continuidad demostrable del ledger para %s", async (_case, revision, accepted) => {
    window.location.hash = `#/study/plans/${planId}`;
    const advanced = detailForLedger(eventLedger(revision));
    let detailReads = 0;
    const fetchMock = installStudyApi({
      detailResponse: async () => {
        detailReads += 1;
        return jsonResponse(detailReads === 1 ? planDetail : advanced);
      },
      post: async () => jsonResponse(revalidateReceipt),
    });
    const user = userEvent.setup();
    render(<App />);
    await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });
    await user.click(screen.getByRole("button", { name: "Revalidar alcance" }));

    if (accepted) {
      expect(await screen.findByText(`Plan r${revision}`)).toBeVisible();
      expect(screen.getByText(/Alcance revalidado; estado actual confirmado/u)).toBeVisible();
      expect(screen.getByRole("button", { name: "Revalidar alcance" })).toBeEnabled();
    } else {
      expect(await screen.findByText(/no pudimos confirmar el estado actual/u)).toBeVisible();
      expect(screen.getByText("Plan r1")).toBeVisible();
      expect(screen.queryByText(`Plan r${revision}`)).not.toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Revalidar alcance" })).toBeDisabled();
      expect(screen.getByRole("button", { name: "Cancelar plan" })).toBeDisabled();
    }
    expect(fetchMock.mock.calls.filter((call) => call[1]?.method === "POST")).toHaveLength(1);
  });

  it("aísla la continuidad del ledger sin depender de un recibo de comando", () => {
    const bridge = detailForLedger(eventLedger(11));
    const gap = detailForLedger(eventLedger(12));

    expect(bridge.recentEvents.at(-1)?.revision).toBe(2);
    expect(gap.recentEvents.at(-1)?.revision).toBe(3);
    expect(isSafePlanProgression(planDetail, bridge)).toBe(true);
    expect(isSafePlanProgression(planDetail, gap)).toBe(false);
  });

  it("no limpia un revalidate sin el evento exacto del recibo ni durante recuperación explícita", async () => {
    window.location.hash = `#/study/plans/${planId}`;
    const bridge = detailForLedger(eventLedger(11));
    const withoutReceipt = detailForLedger(eventLedger(12));
    let detailReads = 0;
    const fetchMock = installStudyApi({
      detailResponse: async () => {
        detailReads += 1;
        if (detailReads === 1) return jsonResponse(planDetail);
        if (detailReads === 2) return jsonResponse(withoutReceipt);
        if (detailReads === 3) return jsonResponse(bridge);
        return jsonResponse(withoutReceipt);
      },
      post: async () => jsonResponse(revalidateReceipt),
    });
    const user = userEvent.setup();
    render(<App />);
    await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });
    await user.click(screen.getByRole("button", { name: "Revalidar alcance" }));
    expect(await screen.findByText(/no pudimos confirmar el estado actual/u)).toBeVisible();
    expect(screen.getByText("Plan r1")).toBeVisible();

    await user.click(screen.getByRole("link", { name: "Volver a planes" }));
    await screen.findByRole("heading", { name: "Estudio de Limpieza", level: 1 });
    await user.click(await screen.findByRole("link", { name: /Ver detalle del plan/u }));
    expect(await screen.findByText("Plan r11")).toBeVisible();
    expect(screen.getByText(/estado actual todavía no pudo confirmarse/u)).toBeVisible();

    await user.click(screen.getByRole("button", { name: "Actualizar detalle y contrato" }));
    expect(await screen.findByText("Plan r12")).toBeVisible();
    expect(screen.getByText(/estado actual todavía no pudo confirmarse/u)).toBeVisible();
    expect(screen.queryByText("El estado actual del comando aceptado quedó confirmado.")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Revalidar alcance" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Cancelar plan" })).toBeDisabled();
    expect(detailReads).toBe(4);
    expect(fetchMock.mock.calls.filter((call) => call[1]?.method === "POST")).toHaveLength(1);
  });

  it("bloquea paginación de miembros y eventos mientras el POST está pendiente y conserva foco de recuperación", async () => {
    window.location.hash = `#/study/plans/${planId}`;
    const initialLedger = eventLedger(51).map((event) => ({ ...event, remainingCount: 101 }));
    const confirmedLedger = eventLedger(52).map((event) => ({ ...event, remainingCount: 101 }));
    const initialDetail = detailForMemberPagination(initialLedger);
    const confirmedDetail = detailForMemberPagination(confirmedLedger);
    const delayedPost = deferredResponse();
    let detailReads = 0;
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path === "/api/v2/context") return jsonResponse(mapContext);
      if (path === "/api/v3/study/context") return jsonResponse(studyContext);
      if (path === "/api/v3/study/plans?limit=10") return jsonResponse(plansResponse);
      if (path === `/api/v3/study/plans/${planId}`) {
        detailReads += 1;
        return jsonResponse(detailReads === 1 ? initialDetail : confirmedDetail);
      }
      if (path === `/api/v3/study/plans/${planId}/messages?state=all&limit=100`) {
        return jsonResponse({ ...messagesResponse, planRevision: 51, items: fullMemberPage(), nextCursor: "miembros_siguiente" });
      }
      if (path === `/api/v3/study/plans/${planId}/events?limit=50`) {
        return jsonResponse({ ...eventsResponse, planRevision: 51, items: initialLedger.slice(0, 50), nextCursor: "eventos_siguiente" });
      }
      if (path === `/api/v3/study/plans/${planId}/revalidate` && init?.method === "POST") return delayedPost.promise;
      if (path.includes("cursor=miembros_siguiente") || path.includes("cursor=eventos_siguiente")) {
        throw new Error("la paginación no debía iniciarse");
      }
      return jsonResponse(studyError("route_not_found"), 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<App />);
    await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });
    await user.click(screen.getByText("Miembros y razones"));
    const moreMembers = await screen.findByRole("button", { name: /Cargar la siguiente página de todo el universo inicial/u });
    await user.click(screen.getByText("Eventos completos"));
    const moreEvents = await screen.findByRole("button", { name: "Cargar la siguiente página de eventos" });

    await user.click(screen.getByRole("button", { name: "Revalidar alcance" }));
    expect(moreMembers).toBeDisabled();
    expect(moreEvents).toBeDisabled();
    fireEvent.click(moreMembers);
    fireEvent.click(moreEvents);
    expect(fetchMock.mock.calls.filter((call) => String(call[0]).includes("cursor=miembros_siguiente"))).toHaveLength(0);
    expect(fetchMock.mock.calls.filter((call) => String(call[0]).includes("cursor=eventos_siguiente"))).toHaveLength(0);

    await act(async () => delayedPost.resolve(jsonResponse({ ...revalidateReceipt, commandRevision: 52 })));
    const memberRestart = await screen.findByRole("button", { name: "Reiniciar miembros desde la primera página" });
    expect(memberRestart).toHaveFocus();
    expect(screen.getByRole("button", { name: "Reiniciar eventos desde la primera página" })).toBeVisible();
    expect(fetchMock.mock.calls.filter((call) => String(call[0]).includes("cursor=miembros_siguiente"))).toHaveLength(0);
    expect(fetchMock.mock.calls.filter((call) => String(call[0]).includes("cursor=eventos_siguiente"))).toHaveLength(0);
    expect(fetchMock.mock.calls.filter((call) => call[1]?.method === "POST")).toHaveLength(1);
  });

  it("conserva y repite exactamente el mismo envío incierto sólo por acción explícita", async () => {
    window.location.hash = "#/study";
    const postBodies: string[] = [];
    let attempts = 0;
    const fetchMock = installStudyApi({
      post: async (_path, body) => {
        postBodies.push(body);
        attempts += 1;
        if (attempts === 1) throw new TypeError("corte local");
        return jsonResponse(createReceipt);
      },
    });
    const user = userEvent.setup();
    render(<App />);
    await reachReview(user);
    await user.click(screen.getByRole("button", { name: "Crear estudio" }));

    expect(await screen.findByText(/Resultado incierto/u)).toBeVisible();
    expect(postBodies).toHaveLength(1);
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(postBodies).toHaveLength(1);
    await user.click(screen.getByRole("link", { name: /Ver detalle del plan/u }));
    await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });
    await user.click(screen.getByRole("link", { name: "Estudio de Limpieza" }));
    expect(await screen.findByRole("button", { name: "Repetir exactamente el mismo envío" })).toBeVisible();
    expect(screen.getByRole("group", { name: "Revisión final" })).toHaveTextContent("Boletines Example");
    await user.click(screen.getByRole("button", { name: "Repetir exactamente el mismo envío" }));
    await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });
    expect(postBodies).toHaveLength(2);
    expect(postBodies[1]).toBe(postBodies[0]);
    expect(fetchMock.mock.calls.filter((call) => call[1]?.method === "POST")).toHaveLength(2);
  });

  it("cierra el retry de creación con contexto incompatible y conserva el envío exacto al recuperar un contrato compatible", async () => {
    window.location.hash = "#/study";
    const randomUUID = vi.mocked(crypto.randomUUID);
    let contextPayload: unknown = studyContext;
    const postBodies: string[] = [];
    let attempts = 0;
    const fetchMock = installStudyApi({
      contextResponse: async () => jsonResponse(contextPayload),
      post: async (_path, body) => {
        postBodies.push(body);
        attempts += 1;
        if (attempts === 1) throw new TypeError("corte local");
        return jsonResponse(createReceipt);
      },
    });
    const user = userEvent.setup();
    render(<App />);
    await reachReview(user);
    await user.click(screen.getByRole("button", { name: "Crear estudio" }));
    const retry = await screen.findByRole("button", { name: "Repetir exactamente el mismo envío" });

    contextPayload = incompatibleStudyContext();
    await user.click(screen.getByRole("button", { name: "Actualizar contexto y catálogo para revisar" }));
    await waitFor(() => expect(retry).toBeDisabled());
    fireEvent.click(retry);
    expect(postBodies).toHaveLength(1);

    contextPayload = dynamicallyBlockedStudyContext();
    await user.click(screen.getByRole("button", { name: "Actualizar contexto y catálogo para revisar" }));
    await waitFor(() => expect(retry).toBeEnabled());
    await user.click(retry);
    await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });

    expect(postBodies).toHaveLength(2);
    expect(postBodies[1]).toBe(postBodies[0]);
    expect(JSON.parse(postBodies[1]!).commandId).toBe(JSON.parse(postBodies[0]!).commandId);
    expect(fetchMock.mock.calls.filter((call) => call[1]?.method === "POST")).toHaveLength(2);
    expect(randomUUID).toHaveBeenCalledTimes(1);
  });

  it.each(["revalidate", "cancel"] as const)(
    "cierra el retry de %s con contexto incompatible y lo reabre sin depender del inventario",
    async (kind) => {
      window.location.hash = `#/study/plans/${planId}`;
      const randomUUID = vi.mocked(crypto.randomUUID);
      let contextPayload: unknown = studyContext;
      const options: ApiOptions = {
        contextResponse: async () => jsonResponse(contextPayload),
      };
      const postPaths: string[] = [];
      const postBodies: string[] = [];
      let attempts = 0;
      options.post = async (path, body) => {
        postPaths.push(path);
        postBodies.push(body);
        attempts += 1;
        if (attempts === 1) throw new TypeError("corte local");
        options.detail = kind === "revalidate" ? detailAfterRevalidation("frozen") : detailForState("cancelled");
        return jsonResponse(kind === "revalidate" ? revalidateReceipt : cancelReceipt);
      };
      const fetchMock = installStudyApi(options);
      const user = userEvent.setup();
      render(<App />);
      await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });
      await user.click(screen.getByRole("button", { name: kind === "revalidate" ? "Revalidar alcance" : "Cancelar plan" }));
      const retry = await screen.findByRole("button", { name: "Repetir exactamente el mismo envío" });

      contextPayload = incompatibleStudyContext();
      await user.click(screen.getByRole("button", { name: "Actualizar detalle y contrato" }));
      await waitFor(() => expect(retry).toBeDisabled());
      fireEvent.click(retry);
      expect(postBodies).toHaveLength(1);

      contextPayload = dynamicallyBlockedStudyContext();
      await user.click(screen.getByRole("button", { name: "Actualizar detalle y contrato" }));
      await waitFor(() => expect(retry).toBeEnabled());
      await user.click(retry);
      await waitFor(() => expect(postBodies).toHaveLength(2));

      expect(postPaths[1]).toBe(postPaths[0]);
      expect(postBodies[1]).toBe(postBodies[0]);
      expect(JSON.parse(postBodies[1]!).commandId).toBe(JSON.parse(postBodies[0]!).commandId);
      expect(fetchMock.mock.calls.filter((call) => call[1]?.method === "POST")).toHaveLength(2);
      expect(randomUUID).toHaveBeenCalledTimes(1);
    },
  );

  it("mantiene una creación con JSON 200 malformado cerrada hasta recuperar y conserva la misma clave incluso al navegar", async () => {
    window.location.hash = "#/study";
    const randomUUID = vi.mocked(crypto.randomUUID);
    const postPaths: string[] = [];
    const postBodies: string[] = [];
    let attempts = 0;
    const fetchMock = installStudyApi({
      post: async (path, body) => {
        postPaths.push(path);
        postBodies.push(body);
        attempts += 1;
        return attempts === 1
          ? new Response("{", { status: 200, headers: { "Content-Type": "application/json" } })
          : jsonResponse(createReceipt);
      },
    });
    const user = userEvent.setup();
    render(<App />);
    await reachReview(user);
    await user.click(screen.getByRole("button", { name: "Crear estudio" }));
    let retry = await screen.findByRole("button", { name: "Repetir exactamente el mismo envío" });
    expect(retry).toBeDisabled();
    fireEvent.click(retry);
    expect(postBodies).toHaveLength(1);

    await user.click(screen.getByRole("link", { name: /Ver detalle del plan/u }));
    await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });
    await user.click(screen.getByRole("link", { name: "Estudio de Limpieza" }));
    retry = await screen.findByRole("button", { name: "Repetir exactamente el mismo envío" });
    expect(retry).toBeDisabled();
    fireEvent.click(retry);
    expect(postBodies).toHaveLength(1);

    await user.click(screen.getByRole("button", { name: "Actualizar contexto y catálogo para revisar" }));
    await waitFor(() => expect(retry).toBeEnabled());
    await user.click(retry);
    await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });

    expect(postPaths[1]).toBe(postPaths[0]);
    expect(postBodies[1]).toBe(postBodies[0]);
    expect(JSON.parse(postBodies[1]!).commandId).toBe(JSON.parse(postBodies[0]!).commandId);
    expect(fetchMock.mock.calls.filter((call) => call[1]?.method === "POST")).toHaveLength(2);
    expect(randomUUID).toHaveBeenCalledTimes(1);
  });

  it("mantiene durable el cierre de una respuesta malformada editada y exige recuperar antes de otra clave", async () => {
    window.location.hash = "#/study";
    const firstId = "12345678-1234-4234-8234-123456789abc";
    const secondId = "abcdefab-cdef-4abc-8def-abcdefabcdef";
    const randomUUID = vi.fn().mockReturnValueOnce(firstId).mockReturnValueOnce(secondId);
    vi.stubGlobal("crypto", { randomUUID });
    const postBodies: string[] = [];
    let attempts = 0;
    installStudyApi({
      post: async (_path, body) => {
        postBodies.push(body);
        attempts += 1;
        return attempts === 1
          ? new Response("{", { status: 200, headers: { "Content-Type": "application/json" } })
          : jsonResponse(createReceipt);
      },
    });
    const user = userEvent.setup();
    render(<App />);
    await reachReview(user);
    await user.click(screen.getByRole("button", { name: "Crear estudio" }));
    expect(await screen.findByRole("button", { name: "Repetir exactamente el mismo envío" })).toBeDisabled();

    await user.click(screen.getByRole("button", { name: "Paso anterior" }));
    fireEvent.change(screen.getByLabelText("Conservar los últimos N por flujo"), { target: { value: "3" } });
    expect(randomUUID).toHaveBeenCalledTimes(1);
    expect(postBodies).toHaveLength(1);

    await user.click(screen.getByRole("link", { name: /Ver detalle del plan/u }));
    await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });
    await user.click(screen.getByRole("link", { name: "Estudio de Limpieza" }));
    expect(await screen.findByRole("button", { name: "Repetir exactamente el mismo envío" })).toBeDisabled();
    expect(randomUUID).toHaveBeenCalledTimes(1);
    expect(postBodies).toHaveLength(1);

    await user.click(screen.getByRole("button", { name: "Actualizar contexto y catálogo para revisar" }));
    const confirmNewDecision = await screen.findByRole("button", { name: "Confirmar una decisión nueva con este formulario" });
    expect(randomUUID).toHaveBeenCalledTimes(1);
    expect(postBodies).toHaveLength(1);
    await user.click(confirmNewDecision);
    const create = screen.getByRole("button", { name: "Crear estudio" });
    await waitFor(() => expect(create).toBeEnabled());
    await user.click(create);
    await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });

    expect(randomUUID).toHaveBeenCalledTimes(2);
    expect(postBodies).toHaveLength(2);
    expect(JSON.parse(postBodies[0]!).commandId).toBe(firstId);
    expect(JSON.parse(postBodies[1]!).commandId).toBe(secondId);
  });

  it("mantiene un recibo cerrado incompatible sin retry hasta releer detalle y contrato", async () => {
    window.location.hash = `#/study/plans/${planId}`;
    const randomUUID = vi.mocked(crypto.randomUUID);
    const options: ApiOptions = {};
    const postPaths: string[] = [];
    const postBodies: string[] = [];
    let attempts = 0;
    options.post = async (path, body) => {
      postPaths.push(path);
      postBodies.push(body);
      attempts += 1;
      if (attempts === 1) return jsonResponse({ ...revalidateReceipt, canExecute: true });
      options.detail = detailAfterRevalidation("frozen");
      return jsonResponse(revalidateReceipt);
    };
    const fetchMock = installStudyApi(options);
    const user = userEvent.setup();
    render(<App />);
    await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });
    await user.click(screen.getByRole("button", { name: "Revalidar alcance" }));
    const retry = await screen.findByRole("button", { name: "Repetir exactamente el mismo envío" });
    expect(retry).toBeDisabled();
    expect(screen.getByRole("button", { name: "Revalidar alcance" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Cancelar plan" })).toBeDisabled();
    fireEvent.click(retry);
    expect(postBodies).toHaveLength(1);

    await user.click(screen.getByRole("button", { name: "Actualizar detalle y contrato" }));
    await waitFor(() => expect(retry).toBeEnabled());
    expect(postBodies).toHaveLength(1);
    await user.click(retry);
    await screen.findByText(/Alcance revalidado/u);

    expect(postPaths[1]).toBe(postPaths[0]);
    expect(postBodies[1]).toBe(postBodies[0]);
    expect(JSON.parse(postBodies[1]!).commandId).toBe(JSON.parse(postBodies[0]!).commandId);
    expect(fetchMock.mock.calls.filter((call) => call[1]?.method === "POST")).toHaveLength(2);
    expect(randomUUID).toHaveBeenCalledTimes(1);
  });

  it("permite cerrar y retomar un constructor bloqueado sin perder el retry exacto", async () => {
    window.location.hash = "#/study";
    const fetchMock = installStudyApi({ post: async () => { throw new TypeError("corte local"); } });
    const user = userEvent.setup();
    render(<App />);
    await reachReview(user);
    await user.click(screen.getByRole("button", { name: "Crear estudio" }));
    await screen.findByRole("button", { name: "Repetir exactamente el mismo envío" });
    await user.click(screen.getByRole("button", { name: "Cerrar constructor" }));
    const resume = screen.getByRole("button", { name: "Retomar estudio pendiente" });
    expect(resume).toBeEnabled();
    await user.click(resume);
    expect(screen.getByRole("group", { name: "Revisión final" })).toHaveTextContent("Boletines Example");
    expect(screen.getByRole("button", { name: "Repetir exactamente el mismo envío" })).toBeVisible();
    expect(fetchMock.mock.calls.filter((call) => call[1]?.method === "POST")).toHaveLength(1);
  });

  it("invalida el retry incierto cuando se edita el formulario", async () => {
    window.location.hash = "#/study";
    installStudyApi({ post: async () => { throw new TypeError("corte local"); } });
    const user = userEvent.setup();
    render(<App />);
    await reachReview(user);
    await user.click(screen.getByRole("button", { name: "Crear estudio" }));
    await screen.findByRole("button", { name: "Repetir exactamente el mismo envío" });
    await user.click(screen.getByRole("button", { name: "Paso anterior" }));
    fireEvent.change(screen.getByLabelText("Conservar los últimos N por flujo"), { target: { value: "3" } });
    expect(screen.queryByRole("button", { name: "Repetir exactamente el mismo envío" })).not.toBeInTheDocument();
    expect(screen.getByText(/El formulario cambió/u)).toBeVisible();
  });

  it("bloquea doble envío y marca el formulario ocupado mientras el POST sigue pendiente", async () => {
    window.location.hash = "#/study";
    let release!: (response: Response) => void;
    const pendingResponse = new Promise<Response>((resolve) => { release = resolve; });
    const fetchMock = installStudyApi({ post: async () => pendingResponse });
    const user = userEvent.setup();
    render(<App />);
    await reachReview(user);
    const submit = screen.getByRole("button", { name: "Crear estudio" });
    fireEvent.click(submit);
    fireEvent.click(submit);
    await waitFor(() => expect(fetchMock.mock.calls.filter((call) => call[1]?.method === "POST")).toHaveLength(1));
    expect(screen.getByRole("group", { name: "Revisión final" }).closest("form")).toHaveAttribute("aria-busy", "true");
    expect(submit).toBeDisabled();
    release(jsonResponse(createReceipt));
    await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });
  });

  it("conserva un comando aceptado sin confirmar y lo resuelve sólo con lecturas explícitas", async () => {
    window.location.hash = "#/study";
    let detailReads = 0;
    const fetchMock = installStudyApi({
      detailResponse: async () => {
        detailReads += 1;
        if (detailReads === 1) throw new TypeError("lectura interrumpida");
        return jsonResponse(planDetail);
      },
    });
    const user = userEvent.setup();
    render(<App />);
    await reachReview(user);
    await user.click(screen.getByRole("button", { name: "Crear estudio" }));
    expect(await screen.findByText(/no pudimos confirmar el estado actual/u)).toBeVisible();
    expect(fetchMock.mock.calls.filter((call) => call[1]?.method === "POST")).toHaveLength(1);
    await user.click(screen.getByRole("button", { name: "Confirmar el estado del estudio aceptado" }));
    await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });
    expect(fetchMock.mock.calls.filter((call) => call[1]?.method === "POST")).toHaveLength(1);
    expect(detailReads).toBe(3);
  });

  it("confirma con anuncio vivo una creación aceptada al recuperarla desde el detalle", async () => {
    window.location.hash = "#/study";
    let detailReads = 0;
    const fetchMock = installStudyApi({
      detailResponse: async () => {
        detailReads += 1;
        if (detailReads === 1) throw new TypeError("lectura interrumpida");
        return jsonResponse(planDetail);
      },
    });
    const user = userEvent.setup();
    render(<App />);
    await reachReview(user);
    await user.click(screen.getByRole("button", { name: "Crear estudio" }));
    await screen.findByText(/no pudimos confirmar el estado actual/u);
    await user.click(screen.getByRole("link", { name: /Ver detalle del plan/u }));
    await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });
    expect(screen.getByText(/estado actual todavía no pudo confirmarse/u)).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Actualizar detalle y contrato" }));
    const confirmed = await screen.findByText("El estado actual del comando aceptado quedó confirmado.");
    expect(confirmed.closest('[role="status"]')).not.toBeNull();
    expect(screen.getByRole("button", { name: "Cancelar plan" })).toBeEnabled();
    expect(fetchMock.mock.calls.filter((call) => call[1]?.method === "POST")).toHaveLength(1);
    expect(detailReads).toBe(3);
  });

  it.each(["map_revision_conflict", "policy_revision_conflict", "target_not_found"] as const)(
    "conserva el formulario y actualiza explícitamente ante %s",
    async (code) => {
      window.location.hash = "#/study";
      const fetchMock = installStudyApi({ post: async () => jsonResponse(studyError(code), code === "target_not_found" ? 404 : 409) });
      const user = userEvent.setup();
      render(<App />);
      await reachReview(user);
      await user.click(screen.getByRole("button", { name: "Crear estudio" }));
      const alertPattern = code === "map_revision_conflict"
        ? /El mapa cambió\. Actualizá/u
        : code === "policy_revision_conflict"
          ? /Las decisiones cambiaron\. Actualizá/u
          : /Un objetivo ya no existe/u;
      expect(await screen.findByText(alertPattern)).toBeVisible();
      expect(screen.getByRole("group", { name: "Revisión final" })).toHaveTextContent("Boletines Example");
      const contextReads = fetchMock.mock.calls.filter((call) => call[0] === "/api/v3/study/context").length;
      await user.click(screen.getByRole("button", { name: "Actualizar contexto y catálogo para revisar" }));
      await waitFor(() => expect(fetchMock.mock.calls.filter((call) => call[0] === "/api/v3/study/context").length).toBeGreaterThan(contextReads));
      expect(fetchMock.mock.calls.filter((call) => call[1]?.method === "POST")).toHaveLength(1);
      expect(screen.getByRole("group", { name: "Revisión final" })).toHaveTextContent("Boletines Example");
    },
  );

  it("bloquea command_id_conflict hasta una decisión explícita y recién entonces usa otro UUID", async () => {
    window.location.hash = "#/study";
    const firstId = "12345678-1234-4234-8234-123456789abc";
    const secondId = "87654321-4321-4321-8321-cba987654321";
    vi.stubGlobal("crypto", {
      randomUUID: vi.fn().mockReturnValueOnce(firstId).mockReturnValueOnce(secondId),
    });
    const postBodies: string[] = [];
    const fetchMock = installStudyApi({
      post: async (_path, body) => {
        postBodies.push(body);
        return postBodies.length === 1
          ? jsonResponse(studyError("command_id_conflict"), 409)
          : jsonResponse(createReceipt);
      },
    });
    const user = userEvent.setup();
    render(<App />);
    await reachReview(user);

    await user.click(screen.getByRole("button", { name: "Crear estudio" }));
    expect(await screen.findByText(/Ese identificador ya fue usado/u)).toBeVisible();
    expect(postBodies).toHaveLength(1);
    expect(screen.getByRole("button", { name: "Crear estudio" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Confirmar una decisión nueva con este formulario" }));
    expect(fetchMock.mock.calls.filter((call) => call[1]?.method === "POST")).toHaveLength(1);
    await user.click(screen.getByRole("button", { name: "Crear estudio" }));
    await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });

    expect(postBodies).toHaveLength(2);
    expect(JSON.parse(postBodies[0]!).commandId).toBe(firstId);
    expect(JSON.parse(postBodies[1]!).commandId).toBe(secondId);
  });

  it.each([
    ["inventory_incomplete", "El inventario sintético todavía no está completo."],
    ["account_unavailable", "La cuenta sintética de demostración no está disponible."],
    ["study_unavailable", "La fotografía sintética actual no está disponible para crear o revalidar."],
  ] as const)("bloquea creación ante %s y conserva la historia legible", async (code, message) => {
    window.location.hash = "#/study";
    const fetchMock = installStudyApi({ post: async () => jsonResponse(studyError(code), 503) });
    const user = userEvent.setup();
    render(<App />);
    await reachReview(user);
    await user.click(screen.getByRole("button", { name: "Crear estudio" }));

    expect(await screen.findByText(message)).toBeVisible();
    expect(screen.getByRole("button", { name: "Crear estudio" })).toBeDisabled();
    expect(screen.getByRole("group", { name: "Revisión final" })).toHaveTextContent("Boletines Example");
    expect(screen.getByRole("heading", { name: "Archivo", level: 3 })).toBeVisible();
    expect(fetchMock.mock.calls.filter((call) => call[1]?.method === "POST")).toHaveLength(1);
  });

  it.each([
    ["plan_too_large", "El universo del plan supera el límite. Elegí menos objetivos."],
    ["payload_too_large", "La solicitud supera el límite local de 64 KiB."],
  ] as const)("exige una decisión nueva ante %s sin sugerir eludir el límite", async (code, message) => {
    window.location.hash = "#/study";
    const fetchMock = installStudyApi({ post: async () => jsonResponse(studyError(code), 413) });
    const user = userEvent.setup();
    render(<App />);
    await reachReview(user);
    await user.click(screen.getByRole("button", { name: "Crear estudio" }));

    expect(await screen.findByText(message)).toBeVisible();
    expect(screen.getByRole("button", { name: "Confirmar una decisión nueva con este formulario" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Crear estudio" })).toBeDisabled();
    expect(screen.queryByText(/filtros posteriores|eludir/iu)).not.toBeInTheDocument();
    expect(fetchMock.mock.calls.filter((call) => call[1]?.method === "POST")).toHaveLength(1);
  });

  it("mantiene el detalle activo en navegación y carga miembros/eventos sólo al abrirlos", async () => {
    window.location.hash = `#/study/plans/${planId}`;
    const fetchMock = installStudyApi();
    const user = userEvent.setup();
    render(<App />);

    await screen.findByText("Leé el alcance histórico y su estado efectivo sin reconstruirlo desde el mapa actual.");
    expect(screen.getByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 })).toBeVisible();
    expect(screen.getByRole("link", { name: "Estudio de Limpieza" })).toHaveAttribute("aria-current", "page");
    expect(screen.getAllByText("Vista previa sin efectos; no modifica Gmail.", { exact: false }).length).toBeGreaterThanOrEqual(2);
    expect(fetchMock.mock.calls.some((call) => String(call[0]).includes("/messages"))).toBe(false);
    expect(fetchMock.mock.calls.some((call) => String(call[0]).includes("/events"))).toBe(false);

    await user.click(screen.getByText("Miembros y razones"));
    expect(await screen.findByText("Elegible actualmente")).toBeVisible();
    const memberSelect = screen.getByLabelText("Filtrar miembros");
    expect(within(memberSelect).getAllByRole("option")).toHaveLength(5);
    expect(screen.getByText(/retirado sigue perteneciendo a la selección original/u)).toBeVisible();
    await user.click(screen.getByText("Eventos completos"));
    expect((await screen.findAllByText("Creado")).length).toBeGreaterThanOrEqual(2);
  });

  it("actualiza el detalle explícitamente antes de reiniciar colecciones de una revisión concurrente", async () => {
    window.location.hash = `#/study/plans/${planId}`;
    const revisionTwo = detailAfterRevalidation("frozen");
    const revisionThree: PlanDetail = {
      ...revisionTwo,
      planRevision: 3,
      lastRevalidatedAt: "2026-08-29T13:00:00Z",
      eventCount: 3,
      recentEvents: [{
        revision: 3,
        type: "revalidated",
        recordedAt: "2026-08-29T13:00:00Z",
        state: "frozen",
        observedMapRevision: studyContext.availability.currentMapRevision,
        observedPolicyRevision: 7,
        removedCount: 0,
        remainingCount: 1,
      }, ...revisionTwo.recentEvents],
    };
    let detailReads = 0;
    let memberReads = 0;
    let eventReads = 0;
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path === "/api/v2/context") return jsonResponse(mapContext);
      if (path === "/api/v3/study/context") return jsonResponse(studyContext);
      if (path === "/api/v3/study/plans?limit=10") return jsonResponse(plansResponse);
      if (path === `/api/v3/study/plans/${planId}`) {
        detailReads += 1;
        return jsonResponse(detailReads === 1 ? planDetail : detailReads === 2 ? revisionTwo : revisionThree);
      }
      if (path === `/api/v3/study/plans/${planId}/messages?state=all&limit=100`) {
        memberReads += 1;
        return jsonResponse({ ...messagesResponse, planRevision: 2 });
      }
      if (path === `/api/v3/study/plans/${planId}/events?limit=50`) {
        eventReads += 1;
        return jsonResponse({
          ...eventsResponse,
          planRevision: 3,
          items: [...revisionThree.recentEvents].reverse(),
        });
      }
      return jsonResponse(studyError("route_not_found"), 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<App />);

    await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });
    await user.click(screen.getByText("Miembros y razones"));
    await user.click(await screen.findByRole("button", { name: "Actualizar detalle y reiniciar miembros" }));
    expect(await screen.findByText("Elegible actualmente")).toBeVisible();
    expect(screen.getByText("2 miembros cargados")).toBeVisible();
    expect(detailReads).toBe(2);
    expect(memberReads).toBe(2);

    await user.click(screen.getByText("Eventos completos"));
    await user.click(await screen.findByRole("button", { name: "Actualizar detalle y reiniciar eventos" }));
    expect(await screen.findByText("3 eventos cargados")).toBeVisible();
    expect(detailReads).toBe(3);
    expect(eventReads).toBe(2);
  });

  it("rechaza un evento reescrito entre dos detalles con la misma revisión", async () => {
    window.location.hash = `#/study/plans/${planId}`;
    const stable = detailAfterRevalidation("frozen");
    const rewritten: PlanDetail = {
      ...stable,
      recentEvents: [
        { ...stable.recentEvents[0]!, observedPolicyRevision: 8 },
        stable.recentEvents[1]!,
      ],
    };
    let detailReads = 0;
    const fetchMock = installStudyApi({
      detailResponse: async () => {
        detailReads += 1;
        return jsonResponse(detailReads === 1 ? stable : rewritten);
      },
      post: async () => jsonResponse(studyError("plan_revision_conflict"), 409),
    });
    const user = userEvent.setup();
    render(<App />);
    await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });
    await user.click(screen.getByRole("button", { name: "Revalidar alcance" }));
    await screen.findByText(/El plan cambió/u);
    await user.click(screen.getByRole("button", { name: "Actualizar detalle y contrato" }));

    expect(await screen.findByText(/respuesta incompatible con el contrato/u)).toBeVisible();
    expect(screen.getByRole("button", { name: "Revalidar alcance" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Cancelar plan" })).toBeDisabled();
    expect(detailReads).toBe(2);
    expect(fetchMock.mock.calls.filter((call) => call[1]?.method === "POST")).toHaveLength(1);
  });

  it("conserva la identidad del ledger visto al salir del detalle y volver", async () => {
    window.location.hash = `#/study/plans/${planId}`;
    const stable = detailAfterRevalidation("frozen");
    const rewritten: PlanDetail = {
      ...stable,
      recentEvents: [
        { ...stable.recentEvents[0]!, observedPolicyRevision: 8 },
        stable.recentEvents[1]!,
      ],
    };
    let detailReads = 0;
    installStudyApi({
      detailResponse: async () => {
        detailReads += 1;
        return jsonResponse(detailReads === 1 ? stable : rewritten);
      },
    });
    const user = userEvent.setup();
    render(<App />);
    await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });

    await user.click(screen.getByRole("link", { name: "Volver a planes" }));
    await screen.findByRole("heading", { name: "Estudio de Limpieza", level: 1 });
    await user.click(screen.getByRole("link", { name: /Ver detalle del plan/u }));

    expect(await screen.findByText(/respuesta incompatible con el contrato/u)).toBeVisible();
    expect(screen.getByRole("heading", { name: "Detalle del Estudio de Limpieza no disponible", level: 1 })).toBeVisible();
    expect(detailReads).toBe(2);
  });

  it("rechaza una página de eventos que reescribe una revisión visible del detalle", async () => {
    window.location.hash = `#/study/plans/${planId}`;
    const detail = detailAfterRevalidation("frozen");
    const rewrittenLatest = { ...detail.recentEvents[0]!, observedPolicyRevision: 8 };
    installStudyApi({
      detail,
      events: {
        ...eventsResponse,
        planRevision: detail.planRevision,
        items: [detail.recentEvents[1]!, rewrittenLatest],
      },
    });
    const user = userEvent.setup();
    const { container } = render(<App />);
    await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });
    await user.click(screen.getByText("Eventos completos"));

    expect(await screen.findByText(/respuesta incompatible con el contrato/u)).toBeVisible();
    expect(container.querySelectorAll(".study-event-list li")).toHaveLength(0);
    expect(screen.getByRole("button", { name: "Revalidar alcance" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Cancelar plan" })).toBeDisabled();
  });

  it("descarta miembros y eventos cargados cuando una recuperación avanza la revisión", async () => {
    window.location.hash = `#/study/plans/${planId}`;
    let detailReads = 0;
    const nextDetail = detailAfterRevalidation("frozen");
    const fetchMock = installStudyApi({
      detailResponse: async () => {
        detailReads += 1;
        return jsonResponse(detailReads === 1 ? planDetail : nextDetail);
      },
      post: async () => jsonResponse(studyError("plan_revision_conflict"), 409),
    });
    const user = userEvent.setup();
    const { container } = render(<App />);
    await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });
    await user.click(screen.getByText("Miembros y razones"));
    await waitFor(() => expect(container.querySelectorAll(".study-member-list li")).toHaveLength(2));
    await user.click(screen.getByText("Eventos completos"));
    await waitFor(() => expect(container.querySelectorAll(".study-event-list li")).toHaveLength(1));

    await user.click(screen.getByRole("button", { name: "Revalidar alcance" }));
    await screen.findByText(/El plan cambió/u);
    await user.click(screen.getByRole("button", { name: "Actualizar detalle y contrato" }));

    expect(await screen.findByRole("button", { name: "Reiniciar miembros desde la primera página" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Reiniciar eventos desde la primera página" })).toBeVisible();
    expect(container.querySelectorAll(".study-member-list li")).toHaveLength(0);
    expect(container.querySelectorAll(".study-event-list li")).toHaveLength(0);
    expect(screen.getByText("Plan r2")).toBeVisible();
    expect(fetchMock.mock.calls.filter((call) => call[1]?.method === "POST")).toHaveLength(1);
  });

  it.each([
    ["revalidación", "revalidate", false],
    ["cancelación", "cancel", false],
    ["replay", "revalidate", true],
  ] as const)(
    "mantiene paneles abiertos recuperables después de %s exitosa",
    async (_label, commandKind, replay) => {
      window.location.hash = `#/study/plans/${planId}`;
      const confirmed = commandKind === "cancel" ? detailForState("cancelled") : detailAfterRevalidation("frozen");
      const options: ApiOptions = {};
      let memberReads = 0;
      let eventReads = 0;
      let postAttempts = 0;
      options.messagesResponse = async () => {
        memberReads += 1;
        const activeDetail = options.detail ?? planDetail;
        return jsonResponse({ ...messagesResponse, planRevision: activeDetail.planRevision });
      };
      options.eventsResponse = async () => {
        eventReads += 1;
        const activeDetail = options.detail ?? planDetail;
        return jsonResponse({
          ...eventsResponse,
          planRevision: activeDetail.planRevision,
          items: [...activeDetail.recentEvents].reverse(),
        });
      };
      options.post = async () => {
        postAttempts += 1;
        if (replay && postAttempts === 1) throw new TypeError("resultado incierto sintético");
        options.detail = confirmed;
        return commandKind === "cancel"
          ? jsonResponse(cancelReceipt)
          : jsonResponse({ ...revalidateReceipt, replayed: replay });
      };
      installStudyApi(options);
      const user = userEvent.setup();
      const { container } = render(<App />);

      await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });
      const memberPanel = screen.getByText("Miembros y razones").closest("details") as HTMLDetailsElement;
      const eventPanel = screen.getByText("Eventos completos").closest("details") as HTMLDetailsElement;
      await user.click(screen.getByText("Miembros y razones"));
      await waitFor(() => expect(container.querySelectorAll(".study-member-list li")).toHaveLength(2));
      await user.click(screen.getByText("Eventos completos"));
      await waitFor(() => expect(container.querySelectorAll(".study-event-list li")).toHaveLength(1));

      await user.click(screen.getByRole("button", {
        name: commandKind === "cancel" ? "Cancelar plan" : "Revalidar alcance",
      }));
      if (replay) {
        await screen.findByText(/Resultado incierto/u);
        expect(container.querySelectorAll(".study-member-list li")).toHaveLength(2);
        expect(container.querySelectorAll(".study-event-list li")).toHaveLength(1);
        await user.click(screen.getByRole("button", { name: "Repetir exactamente el mismo envío" }));
      }

      if (commandKind === "cancel") await screen.findByRole("heading", { name: "Cancelado", level: 2 });
      else await screen.findByText(replay ? /Replay confirmado/u : /Alcance revalidado/u);
      const restartMembers = await screen.findByRole("button", { name: "Reiniciar miembros desde la primera página" });
      const restartEvents = screen.getByRole("button", { name: "Reiniciar eventos desde la primera página" });
      expect(memberPanel.open).toBe(true);
      expect(eventPanel.open).toBe(true);
      expect(restartMembers).toBeVisible();
      expect(restartMembers).toHaveFocus();
      expect(restartEvents).toBeVisible();
      expect(container.querySelectorAll(".study-member-list li")).toHaveLength(0);
      expect(container.querySelectorAll(".study-event-list li")).toHaveLength(0);
      expect(memberReads).toBe(1);
      expect(eventReads).toBe(1);

      await user.click(restartMembers);
      await waitFor(() => expect(container.querySelectorAll(".study-member-list li")).toHaveLength(2));
      expect(screen.getByText("2 miembros cargados")).toBeVisible();
      await user.click(restartEvents);
      await waitFor(() => expect(container.querySelectorAll(".study-event-list li")).toHaveLength(2));
      expect(screen.getByText("2 eventos cargados")).toBeVisible();
      expect(screen.getByText("Plan r2")).toBeVisible();
      expect(memberReads).toBe(2);
      expect(eventReads).toBe(2);
      expect(postAttempts).toBe(replay ? 2 : 1);
    },
  );

  it("usa el estado actual de los paneles cuando el comando termina", async () => {
    window.location.hash = `#/study/plans/${planId}`;
    const confirmed = detailAfterRevalidation("frozen");
    const options: ApiOptions = {};
    let releasePost!: (response: Response) => void;
    const pendingPost = new Promise<Response>((resolve) => { releasePost = resolve; });
    options.post = async () => pendingPost;
    options.messagesResponse = async () => jsonResponse({
      ...messagesResponse,
      planRevision: (options.detail ?? planDetail).planRevision,
    });
    options.eventsResponse = async () => {
      const activeDetail = options.detail ?? planDetail;
      return jsonResponse({
        ...eventsResponse,
        planRevision: activeDetail.planRevision,
        items: [...activeDetail.recentEvents].reverse(),
      });
    };
    installStudyApi(options);
    const user = userEvent.setup();
    const { container } = render(<App />);

    await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });
    const memberSummary = screen.getByText("Miembros y razones");
    const eventSummary = screen.getByText("Eventos completos");
    const memberPanel = memberSummary.closest("details") as HTMLDetailsElement;
    const eventPanel = eventSummary.closest("details") as HTMLDetailsElement;
    await user.click(memberSummary);
    await waitFor(() => expect(container.querySelectorAll(".study-member-list li")).toHaveLength(2));
    fireEvent.click(screen.getByRole("button", { name: "Revalidar alcance" }));
    await user.click(memberSummary);
    await user.click(eventSummary);
    await waitFor(() => expect(container.querySelectorAll(".study-event-list li")).toHaveLength(1));

    options.detail = confirmed;
    releasePost(jsonResponse(revalidateReceipt));

    await screen.findByText(/Alcance revalidado/u);
    const restartEvents = await screen.findByRole("button", { name: "Reiniciar eventos desde la primera página" });
    expect(memberPanel.open).toBe(false);
    expect(eventPanel.open).toBe(true);
    expect(eventSummary.closest("summary")).toHaveFocus();
    expect(restartEvents).toBeVisible();
    expect(container.querySelectorAll(".study-member-list li")).toHaveLength(0);
    expect(container.querySelectorAll(".study-event-list li")).toHaveLength(0);
    await user.click(restartEvents);
    await waitFor(() => expect(container.querySelectorAll(".study-event-list li")).toHaveLength(2));
  });

  it("envía los cinco filtros de miembros y conserva la superposición selected/removed", async () => {
    window.location.hash = `#/study/plans/${planId}`;
    const detail = detailForState("reduced");
    const rows = coherentMemberRows();
    const memberPaths: string[] = [];
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path === "/api/v2/context") return jsonResponse(mapContext);
      if (path === "/api/v3/study/context") return jsonResponse(studyContext);
      if (path === "/api/v3/study/plans?limit=10") return jsonResponse(plansResponse);
      if (path === `/api/v3/study/plans/${planId}`) return jsonResponse(detail);
      if (path.startsWith(`/api/v3/study/plans/${planId}/messages?`)) {
        memberPaths.push(path);
        const state = new URLSearchParams(path.split("?")[1] ?? "").get("state") as MemberFilter;
        return jsonResponse({ ...messagesResponse, planRevision: detail.planRevision, state, items: rows[state] });
      }
      return jsonResponse(studyError("route_not_found"), 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<App />);

    await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });
    await user.click(screen.getByText("Miembros y razones"));
    const filter = screen.getByLabelText("Filtrar miembros");
    await screen.findByText("Elegible actualmente");
    expect(screen.getByText("3 miembros cargados")).toBeVisible();
    for (const state of ["selected", "eligible", "excluded", "removed"] as const) {
      await user.selectOptions(filter, state);
      await waitFor(() => expect(memberPaths).toContain(`/api/v3/study/plans/${planId}/messages?state=${state}&limit=100`));
      await waitFor(() => expect(screen.getByText(`${rows[state].length} miembros cargados`)).toBeVisible());
    }
    expect(memberPaths[0]).toBe(`/api/v3/study/plans/${planId}/messages?state=all&limit=100`);
    expect(screen.getByText("Seleccionado al crear")).toBeVisible();
    expect(screen.getByText("Retirado en una revalidación")).toBeVisible();
  });

  it.each(MEMBER_FILTER_CASES)("acepta el cierre terminal coherente del filtro %s", async (state, optionLabel) => {
    window.location.hash = `#/study/plans/${planId}`;
    const detail = detailForState("reduced");
    const rows = coherentMemberRows();
    installStudyApi({
      detail,
      messagesResponse: async (path) => {
        const requested = new URLSearchParams(path.split("?")[1] ?? "").get("state") as MemberFilter;
        return jsonResponse({
          ...messagesResponse,
          planRevision: detail.planRevision,
          state: requested,
          items: rows[requested],
        });
      },
    });
    const user = userEvent.setup();
    const { container } = render(<App />);

    await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });
    await user.click(screen.getByText("Miembros y razones"));
    if (state !== "all") await user.selectOptions(screen.getByLabelText("Filtrar miembros"), optionLabel);

    await waitFor(() => expect(container.querySelectorAll(".study-member-list li")).toHaveLength(rows[state].length));
    expect(screen.getByText(`${rows[state].length} miembros cargados`)).toBeVisible();
    expect(screen.queryByText(/respuesta incompatible con el contrato/u)).not.toBeInTheDocument();
  });

  it.each(MEMBER_FILTER_CASES.flatMap(([state, optionLabel]) => ([
    [state, optionLabel, "n-1"],
    [state, optionLabel, "n+1"],
    [state, optionLabel, "wrong-size"],
  ] as const)))(
    "rechaza el cierre terminal %s (%s) con contradicción %s",
    async (state, optionLabel, mismatch) => {
      window.location.hash = `#/study/plans/${planId}`;
      const detail = detailForState("reduced");
      const rows = coherentMemberRows();
      installStudyApi({
        detail,
        messagesResponse: async (path) => {
          const requested = new URLSearchParams(path.split("?")[1] ?? "").get("state") as MemberFilter;
          const items = requested === state
            ? contradictoryMemberRows(rows[requested], mismatch)
            : rows[requested];
          return jsonResponse({
            ...messagesResponse,
            planRevision: detail.planRevision,
            state: requested,
            items,
          });
        },
      });
      const user = userEvent.setup();
      const { container } = render(<App />);

      await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });
      await user.click(screen.getByText("Miembros y razones"));
      if (state !== "all") {
        await screen.findByText("3 miembros cargados");
        await user.selectOptions(screen.getByLabelText("Filtrar miembros"), optionLabel);
      }

      expect(await screen.findByText(/respuesta incompatible con el contrato/u)).toBeVisible();
      expect(container.querySelectorAll(".study-member-list li")).toHaveLength(0);
      expect(screen.queryByText(`${rows[state].length} miembros cargados`)).not.toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Revalidar alcance" })).toBeDisabled();
      expect(screen.getByRole("button", { name: "Cancelar plan" })).toBeDisabled();
    },
  );

  it.each([
    ["all", "Todo el universo inicial"],
    ["selected", "Selección original"],
  ] as const)("rechaza el filtro %s con total correcto y partición interna falsa", async (state, optionLabel) => {
    window.location.hash = `#/study/plans/${planId}`;
    const detail = detailForState("reduced");
    const rows = coherentMemberRows();
    const contradictory = partitionContradiction(state, rows);
    expect(contradictory).toHaveLength(rows[state].length);
    expect(contradictory.reduce((total, item) => total + item.sizeEstimateBytes, 0)).toBe(
      rows[state].reduce((total, item) => total + item.sizeEstimateBytes, 0),
    );
    installStudyApi({
      detail,
      messagesResponse: async (path) => {
        const requested = new URLSearchParams(path.split("?")[1] ?? "").get("state") as MemberFilter;
        return jsonResponse({
          ...messagesResponse,
          planRevision: detail.planRevision,
          state: requested,
          items: requested === state ? contradictory : rows[requested],
        });
      },
    });
    const user = userEvent.setup();
    const { container } = render(<App />);

    await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });
    await user.click(screen.getByText("Miembros y razones"));
    if (state === "selected") {
      await screen.findByText("3 miembros cargados");
      await user.selectOptions(screen.getByLabelText("Filtrar miembros"), optionLabel);
    }

    expect(await screen.findByText(/respuesta incompatible con el contrato/u)).toBeVisible();
    expect(container.querySelectorAll(".study-member-list li")).toHaveLength(0);
    expect(screen.getByRole("button", { name: "Revalidar alcance" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Cancelar plan" })).toBeDisabled();
  });

  it("rechaza una página parcial que ya supera el agregado congelado", async () => {
    window.location.hash = `#/study/plans/${planId}`;
    installStudyApi({
      messages: {
        ...messagesResponse,
        items: fullMemberPage(),
        nextCursor: "miembros_imposibles",
      },
    });
    const user = userEvent.setup();
    const { container } = render(<App />);

    await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });
    await user.click(screen.getByText("Miembros y razones"));

    expect(await screen.findByText(/respuesta incompatible con el contrato/u)).toBeVisible();
    expect(container.querySelectorAll(".study-member-list li")).toHaveLength(0);
    expect(screen.queryByRole("button", { name: /Cargar la siguiente página de todo el universo inicial/u })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Revalidar alcance" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Cancelar plan" })).toBeDisabled();
  });

  it.each([
    ["frozen", "Congelado"],
    ["reduced", "Selección reducida"],
    ["invalidated", "Invalidado"],
    ["cancelled", "Cancelado"],
    ["expired", "Vencido"],
  ] as const)("representa el estado terminal o activo %s sin inferencia local", async (state, label) => {
    window.location.hash = `#/study/plans/${planId}`;
    installStudyApi({ detail: detailForState(state as PlanState) });
    render(<App />);
    expect(await screen.findByRole("heading", { name: label, level: 2 })).toBeVisible();
    if (state === "invalidated" || state === "cancelled" || state === "expired") {
      expect(screen.getAllByText(/estado terminal|cancelado|servidor marcó/u).length).toBeGreaterThan(0);
      expect(screen.queryByRole("button", { name: "Revalidar alcance" })).not.toBeInTheDocument();
    }
  });

  it.each([
    ["cancelled", "Cancelado", () => detailForState("cancelled")],
    ["invalidated", "Invalidado", () => detailAfterRevalidation("invalidated")],
    ["expired", "Vencido", () => detailForState("expired")],
  ] as const)("rechaza una revisión nueva después de observar el estado terminal %s", async (_state, label, previousDetail) => {
    window.location.hash = `#/study/plans/${planId}`;
    const previous = previousDetail();
    const incompatible = detailAfterImpossibleTerminalRevision(previous);
    let detailReads = 0;
    installStudyApi({
      detailResponse: async () => {
        detailReads += 1;
        return jsonResponse(detailReads === 2 ? incompatible : previous);
      },
    });
    const user = userEvent.setup();
    render(<App />);

    expect(await screen.findByRole("heading", { name: label, level: 2 })).toBeVisible();
    await user.click(screen.getByRole("link", { name: "Volver a planes" }));
    await screen.findByRole("heading", { name: "Estudio de Limpieza", level: 1 });
    await user.click(screen.getByRole("link", { name: /Ver detalle del plan/u }));

    expect(await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza no disponible", level: 1 })).toBeVisible();
    expect(screen.getByText(/respuesta incompatible con el contrato/u)).toBeVisible();
    expect(screen.queryByRole("button", { name: "Revalidar alcance" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("link", { name: "Volver a Estudio de Limpieza" }));
    await screen.findByRole("heading", { name: "Estudio de Limpieza", level: 1 });
    await user.click(screen.getByRole("link", { name: /Ver detalle del plan/u }));
    expect(await screen.findByRole("heading", { name: label, level: 2 })).toBeVisible();
    expect(detailReads).toBe(3);
  });

  it.each([
    ["frozen", "Congelado"],
    ["reduced", "Selección reducida"],
  ] as const)("acepta la derivación %s a expired sin avanzar la revisión", async (state, label) => {
    window.location.hash = `#/study/plans/${planId}`;
    const previous = detailForState(state);
    const expired: PlanDetail = { ...previous, state: "expired" };
    let detailReads = 0;
    installStudyApi({
      detailResponse: async () => {
        detailReads += 1;
        return jsonResponse(detailReads === 1 ? previous : expired);
      },
    });
    const user = userEvent.setup();
    render(<App />);

    expect(await screen.findByRole("heading", { name: label, level: 2 })).toBeVisible();
    await user.click(screen.getByRole("link", { name: "Volver a planes" }));
    await screen.findByRole("heading", { name: "Estudio de Limpieza", level: 1 });
    await user.click(screen.getByRole("link", { name: /Ver detalle del plan/u }));

    expect(await screen.findByRole("heading", { name: "Vencido", level: 2 })).toBeVisible();
    expect(screen.queryByText(/respuesta incompatible con el contrato/u)).not.toBeInTheDocument();
    expect(detailReads).toBe(2);
  });

  it.each([
    ["archive", "none", "Archivar no libera almacenamiento."],
    ["trash", "not_guaranteed", "Mover a Papelera no garantiza una liberación inmediata ni definitiva."],
  ] as const)("separa tamaños y ausencia de liberación para %s", async (disposition, storageEffect, effectText) => {
    window.location.hash = `#/study/plans/${planId}`;
    installStudyApi({
      detail: {
        ...planDetail,
        disposition,
        storageEffect,
        selection: { ...planDetail.selection, disposition },
      },
    });
    render(<App />);

    const metrics = await screen.findByLabelText("Conteos y tamaños del plan");
    expect(within(metrics).getByText("Seleccionados al crear")).toBeVisible();
    expect(within(metrics).getByText("Excluidos al crear")).toBeVisible();
    expect(within(metrics).getByText("Elegibles actualmente")).toBeVisible();
    expect(within(metrics).getByText("Sin medición")).toBeVisible();
    expect(screen.getByText(effectText, { exact: false })).toBeVisible();
    expect(screen.queryByText(/espacio recuperable|espacio liberado|ahorro/iu)).not.toBeInTheDocument();
  });

  it("presenta muestras acotadas con campos nulos y también colecciones vacías", async () => {
    window.location.hash = `#/study/plans/${planId}`;
    installStudyApi();
    const user = userEvent.setup();
    const { unmount } = render(<App />);
    await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });
    await user.click(screen.getByText("Incluidas y excluidas"));
    expect(await screen.findByText("Mensaje sintético sin asunto visible")).toBeVisible();
    expect(screen.getByText("Remitente sin nombre", { exact: false })).toBeVisible();
    unmount();

    installStudyApi({ detail: { ...planDetail, includedSamples: [], excludedSamples: [] } });
    render(<App />);
    await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });
    await user.click(screen.getByText("Incluidas y excluidas"));
    expect(await screen.findAllByText("No hay muestras para esta categoría.")).toHaveLength(2);
  });

  it("mantiene cancelación disponible con fotografía ausente y bloquea revalidación", async () => {
    window.location.hash = `#/study/plans/${planId}`;
    const blockedContext: StudyContext = {
      ...studyContext,
      availability: {
        ...studyContext.availability,
        inventoryState: "paused",
        completeSnapshotAvailable: false,
        currentMapRevision: null,
        currentPolicyRevision: null,
        targetReadAvailable: false,
        planCreateAvailable: false,
        planRevalidateAvailable: false,
        blockerCodes: ["inventory_incomplete"],
      },
    };
    installStudyApi({
      context: blockedContext,
      detail: { ...planDetail, currentMapRevision: null, currentPolicyRevision: null, warnings: ["current_snapshot_unavailable"] },
    });
    render(<App />);

    expect(await screen.findByText("La fotografía sintética actual no está disponible.")).toBeVisible();
    expect(screen.getByRole("button", { name: "Revalidar alcance" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Cancelar plan" })).toBeEnabled();
  });

  it("combina fotografía ausente y selección reducida sin cerrar la cancelación local", async () => {
    window.location.hash = `#/study/plans/${planId}`;
    const reduced = detailForState("reduced");
    installStudyApi({
      context: dynamicallyBlockedStudyContext(),
      detail: {
        ...reduced,
        currentMapRevision: null,
        currentPolicyRevision: null,
        warnings: ["current_snapshot_unavailable", "selection_reduced"],
      },
    });
    render(<App />);

    expect(await screen.findByText("La fotografía sintética actual no está disponible.")).toBeVisible();
    expect(screen.getByText("La selección fue reducida de forma conservadora.")).toBeVisible();
    expect(screen.getByRole("button", { name: "Revalidar alcance" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Cancelar plan" })).toBeEnabled();
  });

  it("muestra warnings de cambio y reducción compatibles fuera de paneles plegables", async () => {
    window.location.hash = `#/study/plans/${planId}`;
    installStudyApi({
      detail: {
        ...detailForState("reduced"),
        currentMapRevision: nextMapRevision,
        currentPolicyRevision: 8,
        warnings: [
          "map_changed_since_creation",
          "policy_changed_since_creation",
          "selection_reduced",
        ],
      },
    });
    render(<App />);
    for (const text of [
      "El mapa cambió desde la creación.",
      "Las decisiones de protección cambiaron desde la creación.",
      "La selección fue reducida de forma conservadora.",
    ]) {
      expect(await screen.findByText(text)).toBeVisible();
    }
  });

  it.each(["plan_revision_conflict", "map_revision_conflict", "policy_revision_conflict"] as const)(
    "no relee ni reenvía ante %s hasta la actualización explícita",
    async (code) => {
      window.location.hash = `#/study/plans/${planId}`;
      const fetchMock = installStudyApi({ post: async () => jsonResponse(studyError(code), 409) });
      const user = userEvent.setup();
      render(<App />);
      await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });
      await waitFor(() => expect(screen.getByRole("button", { name: "Revalidar alcance" })).toBeEnabled());
      const readCount = (path: string) => fetchMock.mock.calls.filter((call) => call[0] === path && call[1]?.method === "GET").length;
      const before = {
        mapContext: readCount("/api/v2/context"),
        studyContext: readCount("/api/v3/study/context"),
        detail: readCount(`/api/v3/study/plans/${planId}`),
        history: readCount("/api/v3/study/plans?limit=10"),
      };

      await user.click(screen.getByRole("button", { name: "Revalidar alcance" }));
      expect(await screen.findByRole("alert")).toHaveTextContent(
        code === "plan_revision_conflict" ? "El plan cambió" : code === "map_revision_conflict" ? "El mapa cambió" : "Las decisiones cambiaron",
      );
      await Promise.resolve();
      expect(readCount("/api/v2/context")).toBe(before.mapContext);
      expect(readCount("/api/v3/study/context")).toBe(before.studyContext);
      expect(readCount(`/api/v3/study/plans/${planId}`)).toBe(before.detail);
      expect(readCount("/api/v3/study/plans?limit=10")).toBe(before.history);
      expect(fetchMock.mock.calls.filter((call) => call[1]?.method === "POST")).toHaveLength(1);
      expect(screen.getByRole("button", { name: "Revalidar alcance" })).toBeDisabled();

      await user.click(screen.getByRole("button", { name: "Actualizar detalle y contrato" }));
      await waitFor(() => {
        expect(readCount("/api/v2/context")).toBe(before.mapContext + 1);
        expect(readCount("/api/v3/study/context")).toBe(before.studyContext + 1);
        expect(readCount(`/api/v3/study/plans/${planId}`)).toBe(before.detail + 1);
        expect(readCount("/api/v3/study/plans?limit=10")).toBe(before.history + 1);
      });
      expect(fetchMock.mock.calls.filter((call) => call[1]?.method === "POST")).toHaveLength(1);
      expect(screen.getByRole("button", { name: "Revalidar alcance" })).toBeEnabled();
    },
  );

  it.each([
    ["plan_expired", "expired", "Vencido", "El plan venció."],
    ["invalid_transition", "cancelled", "Cancelado", "El plan ya no admite esa transición."],
  ] as const)("actualiza el detalle terminal ante %s sin repetir el comando", async (code, nextState, heading, message) => {
    window.location.hash = `#/study/plans/${planId}`;
    let detailReads = 0;
    const fetchMock = installStudyApi({
      detailResponse: async () => {
        detailReads += 1;
        return jsonResponse(detailReads === 1 ? planDetail : detailForState(nextState));
      },
      post: async () => jsonResponse(studyError(code), 409),
    });
    const user = userEvent.setup();
    render(<App />);
    await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });
    await user.click(screen.getByRole("button", { name: "Cancelar plan" }));

    expect(await screen.findByText(message, { exact: false })).toBeVisible();
    expect(await screen.findByRole("heading", { name: heading, level: 2 })).toBeVisible();
    expect(fetchMock.mock.calls.filter((call) => call[1]?.method === "POST")).toHaveLength(1);
    expect(detailReads).toBeGreaterThanOrEqual(2);
  });

  it("trata como incierto un recibo que no corresponde al CAS enviado", async () => {
    window.location.hash = `#/study/plans/${planId}`;
    const fetchMock = installStudyApi({
      post: async () => jsonResponse({ ...revalidateReceipt, commandRevision: 3 }),
    });
    const user = userEvent.setup();
    render(<App />);
    await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });
    await user.click(screen.getByRole("button", { name: "Revalidar alcance" }));
    expect(await screen.findByText(/Resultado incierto/u)).toBeVisible();
    expect(screen.getByRole("button", { name: "Repetir exactamente el mismo envío" })).toBeVisible();
    expect(fetchMock.mock.calls.filter((call) => call[1]?.method === "POST")).toHaveLength(1);
  });

  it("no confirma una revalidación cuyo evento observó otra fotografía", async () => {
    window.location.hash = `#/study/plans/${planId}`;
    const options: ApiOptions = {};
    options.post = async () => {
      const next = detailAfterRevalidation("frozen");
      options.detail = {
        ...next,
        recentEvents: [{ ...next.recentEvents[0]!, observedMapRevision: nextMapRevision }, next.recentEvents[1]!],
      };
      return jsonResponse(revalidateReceipt);
    };
    installStudyApi(options);
    const user = userEvent.setup();
    render(<App />);
    await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });
    await user.click(screen.getByRole("button", { name: "Revalidar alcance" }));
    expect(await screen.findByText(/no pudimos confirmar el estado actual/u)).toBeVisible();
    expect(screen.getByRole("button", { name: "Actualizar detalle y contrato" })).toBeVisible();
    expect(screen.queryByText(/Alcance revalidado/u)).not.toBeInTheDocument();
  });

  it("no confirma cancelación si commandRevision apunta a un evento no cancelado", async () => {
    window.location.hash = `#/study/plans/${planId}`;
    const options: ApiOptions = {};
    options.post = async () => {
      options.detail = cancelledAfterRevalidationDetail;
      return jsonResponse(cancelReceipt);
    };
    installStudyApi(options);
    const user = userEvent.setup();
    render(<App />);
    await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });
    await user.click(screen.getByRole("button", { name: "Cancelar plan" }));
    expect(await screen.findByText(/no pudimos confirmar el estado actual/u)).toBeVisible();
    expect(screen.queryByText(/Plan local cancelado/u)).not.toBeInTheDocument();
  });

  it("acepta replay histórico exacto contra un detalle vigente posterior y terminal", async () => {
    window.location.hash = `#/study/plans/${planId}`;
    const options: ApiOptions = {};
    let attempts = 0;
    options.post = async () => {
      attempts += 1;
      options.detail = cancelledAfterRevalidationDetail;
      if (attempts === 1) throw new TypeError("resultado incierto");
      return jsonResponse({ ...revalidateReceipt, replayed: true });
    };
    const fetchMock = installStudyApi(options);
    const user = userEvent.setup();
    render(<App />);
    await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });
    await user.click(screen.getByRole("button", { name: "Revalidar alcance" }));
    expect(await screen.findByRole("button", { name: "Repetir exactamente el mismo envío" })).toBeVisible();
    expect(fetchMock.mock.calls.filter((call) => call[1]?.method === "POST")).toHaveLength(1);
    await user.click(screen.getByRole("button", { name: "Repetir exactamente el mismo envío" }));
    expect(await screen.findByText(/Replay confirmado; estado actual: Cancelado/u)).toBeVisible();
    expect(await screen.findByRole("heading", { name: "Cancelado", level: 2 })).toBeVisible();
    expect(fetchMock.mock.calls.filter((call) => call[1]?.method === "POST")).toHaveLength(2);
  });

  it("mantiene sin confirmar una creación cuya selección releída no coincide con el draft", async () => {
    window.location.hash = "#/study";
    const fetchMock = installStudyApi({
      detail: {
        ...planDetail,
        selection: { ...planDetail.selection, keepLatestPerFlow: 1 },
      },
    });
    const user = userEvent.setup();
    render(<App />);
    await reachReview(user);
    await user.click(screen.getByRole("button", { name: "Crear estudio" }));
    expect(await screen.findByText(/no pudimos confirmar el estado actual/u)).toBeVisible();
    expect(screen.getByRole("button", { name: "Confirmar el estado del estudio aceptado" })).toBeVisible();
    await user.click(screen.getByRole("link", { name: /Ver detalle del plan/u }));
    await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });
    await user.click(screen.getByRole("button", { name: "Actualizar detalle y contrato" }));
    expect(await screen.findByText(/estado actual todavía no pudo confirmarse/u)).toBeVisible();
    expect(screen.getByRole("button", { name: "Cancelar plan" })).toBeDisabled();
    expect(fetchMock.mock.calls.filter((call) => call[1]?.method === "POST")).toHaveLength(1);
  });

  it("descarta un catálogo obsoleto y sólo lo reinicia por acción explícita", async () => {
    window.location.hash = "#/study";
    let firstPageReads = 0;
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path === "/api/v2/context") return jsonResponse(mapContext);
      if (path === "/api/v3/study/context") return jsonResponse(studyContext);
      if (path === "/api/v3/study/plans?limit=10") return jsonResponse(plansResponse);
      if (path === "/api/v3/study/targets?limit=50") {
        firstPageReads += 1;
        return jsonResponse({ ...targetsResponse, items: fullTargetPage(), nextCursor: "objetivos_siguiente" });
      }
      if (path === "/api/v3/study/targets?cursor=objetivos_siguiente&limit=50") {
        return jsonResponse(studyError("cursor_stale"), 409);
      }
      return jsonResponse(studyError("route_not_found"), 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<App />);

    await user.click(await screen.findByRole("button", { name: "Crear estudio" }));
    await screen.findByRole("checkbox", { name: /Boletines Example/u });
    screen.getByRole("button", { name: "Cargar más objetivos y etiquetas" }).focus();
    await user.keyboard("{Enter}");
    const restartCatalog = await screen.findByRole("button", { name: "Reiniciar catálogo desde la primera página" });
    expect(restartCatalog).toBeVisible();
    expect(restartCatalog).toHaveFocus();
    expect(screen.queryByRole("checkbox", { name: /Boletines Example/u })).not.toBeInTheDocument();
    expect(firstPageReads).toBe(1);
    await user.keyboard("{Enter}");
    await screen.findByRole("checkbox", { name: /Boletines Example/u });
    await waitFor(() => expect(screen.getByText("50 objetivos y etiquetas cargados")).toHaveFocus());
    expect(firstPageReads).toBe(2);
  });

  it("pagina historia filtrada conservando estado, límite, cursor opaco y orden", async () => {
    window.location.hash = "#/study";
    const firstPage = fullHistoryPage().map((item) => ({
      ...item,
      state: "reduced" as const,
      selectedAtCreationCount: 2,
      selectedAtCreationSizeEstimateBytes: 4096,
      currentEligibleCount: 1,
      currentEligibleSizeEstimateBytes: 2048,
    }));
    const last = firstPage.at(-1)!;
    const createdAt = new Date(Date.parse(last.createdAt) - 60_000).toISOString();
    const secondPage: PlanSummary = {
      ...last,
      planId: "cleanup-plan-v1-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
      createdAt,
      expiresAt: new Date(Date.parse(createdAt) + 86_400_000).toISOString(),
    };
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path === "/api/v2/context") return jsonResponse(mapContext);
      if (path === "/api/v3/study/context") return jsonResponse(studyContext);
      if (path === "/api/v3/study/plans?limit=10") return jsonResponse(plansResponse);
      if (path === "/api/v3/study/plans?state=reduced&limit=10") {
        return jsonResponse({ ...plansResponse, state: "reduced", items: firstPage, nextCursor: "historia_reducida" });
      }
      if (path === "/api/v3/study/plans?state=reduced&cursor=historia_reducida&limit=10") {
        return jsonResponse({ ...plansResponse, state: "reduced", items: [secondPage], nextCursor: null });
      }
      return jsonResponse(studyError("route_not_found"), 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    const { container } = render(<App />);
    await screen.findByRole("heading", { name: "Archivo", level: 3 });
    await user.selectOptions(screen.getByLabelText("Filtrar por estado"), "reduced");
    await screen.findAllByRole("heading", { name: "Archivo", level: 3 });
    const more = await screen.findByRole("button", { name: "Cargar la siguiente página de planes" });
    more.focus();
    await user.keyboard("{Enter}");

    expect(await screen.findByText("11 planes cargados")).toHaveFocus();
    expect(container.querySelectorAll(".study-plan-card")).toHaveLength(11);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v3/study/plans?state=reduced&cursor=historia_reducida&limit=10",
      expect.objectContaining({ method: "GET" }),
    );
    const links = screen.getAllByRole("link", { name: /Ver detalle del plan/u });
    expect(links.at(-1)).toHaveAttribute("href", `#/study/plans/${secondPage.planId}`);
  });

  it.each(["listingAsOf", "catalogRevision"] as const)(
    "rechaza historia paginada cuando diverge %s",
    async (field) => {
      window.location.hash = "#/study";
      const firstPage = fullHistoryPage();
      const second = {
        ...firstPage.at(-1)!,
        planId: "cleanup-plan-v1-bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        createdAt: "2026-08-29T11:50:00Z",
        expiresAt: "2026-08-30T11:50:00Z",
      };
      const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
        const path = String(input);
        if (path === "/api/v2/context") return jsonResponse(mapContext);
        if (path === "/api/v3/study/context") return jsonResponse(studyContext);
        if (path === "/api/v3/study/plans?limit=10") {
          return jsonResponse({ ...plansResponse, items: firstPage, nextCursor: "historia_siguiente" });
        }
        if (path === "/api/v3/study/plans?cursor=historia_siguiente&limit=10") {
          return jsonResponse({
            ...plansResponse,
            ...(field === "listingAsOf" ? { listingAsOf: "2026-08-29T12:31:00Z" } : { catalogRevision: 2 }),
            items: [second],
            nextCursor: null,
          });
        }
        return jsonResponse(studyError("route_not_found"), 404);
      });
      vi.stubGlobal("fetch", fetchMock);
      const user = userEvent.setup();
      const { container } = render(<App />);
      await screen.findAllByRole("heading", { name: "Archivo", level: 3 });
      await user.click(screen.getByRole("button", { name: "Cargar la siguiente página de planes" }));

      expect(await screen.findByText(/respuesta incompatible con el contrato/u)).toBeVisible();
      expect(container.querySelectorAll(".study-plan-card")).toHaveLength(0);
      expect(fetchMock.mock.calls.filter((call) => call[0] === "/api/v3/study/plans?cursor=historia_siguiente&limit=10")).toHaveLength(1);
    },
  );

  it.each(["cursor_stale", "invalid_cursor"] as const)("descarta historia ante %s y exige reinicio explícito", async (cursorCode) => {
    window.location.hash = "#/study";
    let historyReads = 0;
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path === "/api/v2/context") return jsonResponse(mapContext);
      if (path === "/api/v3/study/context") return jsonResponse(studyContext);
      if (path === "/api/v3/study/plans?limit=10") {
        historyReads += 1;
        return jsonResponse({ ...plansResponse, items: fullHistoryPage(), nextCursor: "historia_siguiente" });
      }
      if (path.includes("cursor=historia_siguiente")) {
        return jsonResponse(studyError(cursorCode), cursorCode === "invalid_cursor" ? 400 : 409);
      }
      return jsonResponse(studyError("route_not_found"), 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<App />);

    await screen.findAllByRole("heading", { name: "Archivo", level: 3 });
    screen.getByRole("button", { name: "Cargar la siguiente página de planes" }).focus();
    await user.keyboard("{Enter}");
    const restartHistory = await screen.findByRole("button", { name: "Reiniciar historia desde la primera página" });
    expect(restartHistory).toBeVisible();
    expect(restartHistory).toHaveFocus();
    expect(screen.queryAllByRole("heading", { name: "Archivo", level: 3 })).toHaveLength(0);
    expect(historyReads).toBe(1);
    await user.keyboard("{Enter}");
    await screen.findAllByRole("heading", { name: "Archivo", level: 3 });
    await waitFor(() => expect(screen.getByText("10 planes cargados")).toHaveFocus());
    expect(historyReads).toBe(2);
  });

  it("descarta miembros y eventos ante cursores inválidos y conserva sus límites al reiniciar", async () => {
    window.location.hash = `#/study/plans/${planId}`;
    const ledger = eventLedger().map((event) => ({ ...event, remainingCount: 101 }));
    const paginatedDetail = detailForMemberPagination(ledger);
    let memberFirstReads = 0;
    let eventFirstReads = 0;
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path === "/api/v2/context") return jsonResponse(mapContext);
      if (path === "/api/v3/study/context") return jsonResponse(studyContext);
      if (path === "/api/v3/study/plans?limit=10") return jsonResponse(plansResponse);
      if (path === `/api/v3/study/plans/${planId}`) return jsonResponse(paginatedDetail);
      if (path === `/api/v3/study/plans/${planId}/messages?state=all&limit=100`) {
        memberFirstReads += 1;
        return jsonResponse({ ...messagesResponse, planRevision: 51, items: fullMemberPage(), nextCursor: "miembros_siguiente" });
      }
      if (path === `/api/v3/study/plans/${planId}/messages?state=all&cursor=miembros_siguiente&limit=100`) {
        return jsonResponse(studyError("invalid_cursor"), 400);
      }
      if (path === `/api/v3/study/plans/${planId}/events?limit=50`) {
        eventFirstReads += 1;
        return jsonResponse({ ...eventsResponse, planRevision: 51, items: ledger.slice(0, 50), nextCursor: "eventos_siguiente" });
      }
      if (path === `/api/v3/study/plans/${planId}/events?cursor=eventos_siguiente&limit=50`) {
        return jsonResponse(studyError("cursor_stale"), 409);
      }
      return jsonResponse(studyError("route_not_found"), 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    const { container } = render(<App />);

    await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });
    await user.click(screen.getByText("Miembros y razones"));
    (await screen.findByRole("button", { name: /Cargar la siguiente página de todo el universo inicial/u })).focus();
    await user.keyboard("{Enter}");
    const restartMembers = await screen.findByRole("button", { name: "Reiniciar miembros desde la primera página" });
    expect(restartMembers).toBeVisible();
    expect(restartMembers).toHaveFocus();
    expect(screen.queryByText("Elegible actualmente")).not.toBeInTheDocument();
    expect(memberFirstReads).toBe(1);
    await user.keyboard("{Enter}");
    expect((await screen.findAllByText("Elegible actualmente")).length).toBeGreaterThan(0);
    await waitFor(() => expect(screen.getByText("100 miembros cargados")).toHaveFocus());
    expect(memberFirstReads).toBe(2);

    await user.click(screen.getByText("Eventos completos"));
    (await screen.findByRole("button", { name: "Cargar la siguiente página de eventos" })).focus();
    await user.keyboard("{Enter}");
    const restartEvents = await screen.findByRole("button", { name: "Reiniciar eventos desde la primera página" });
    expect(restartEvents).toBeVisible();
    expect(restartEvents).toHaveFocus();
    expect(container.querySelectorAll(".study-event-list li")).toHaveLength(0);
    expect(eventFirstReads).toBe(1);
    await user.keyboard("{Enter}");
    expect((await screen.findAllByText("Creado")).length).toBeGreaterThanOrEqual(1);
    await waitFor(() => expect(screen.getByText("50 eventos cargados")).toHaveFocus());
    expect(eventFirstReads).toBe(2);
  });

  it("devuelve el foco a la recuperación si los reinicios de catálogo e historia vuelven a fallar", async () => {
    window.location.hash = "#/study";
    let catalogReads = 0;
    let historyReads = 0;
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path === "/api/v2/context") return jsonResponse(mapContext);
      if (path === "/api/v3/study/context") return jsonResponse(studyContext);
      if (path === "/api/v3/study/plans?limit=10") {
        historyReads += 1;
        return historyReads === 1
          ? jsonResponse({ ...plansResponse, items: fullHistoryPage(), nextCursor: "historia_siguiente" })
          : jsonResponse(studyError("study_unavailable"), 503);
      }
      if (path === "/api/v3/study/plans?cursor=historia_siguiente&limit=10") {
        return jsonResponse(studyError("cursor_stale"), 409);
      }
      if (path === "/api/v3/study/targets?limit=50") {
        catalogReads += 1;
        return catalogReads === 1
          ? jsonResponse({ ...targetsResponse, items: fullTargetPage(), nextCursor: "objetivos_siguiente" })
          : jsonResponse(studyError("study_unavailable"), 503);
      }
      if (path === "/api/v3/study/targets?cursor=objetivos_siguiente&limit=50") {
        return jsonResponse(studyError("invalid_cursor"), 400);
      }
      return jsonResponse(studyError("route_not_found"), 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<App />);

    await user.click(await screen.findByRole("button", { name: "Crear estudio" }));
    (await screen.findByRole("button", { name: "Cargar más objetivos y etiquetas" })).focus();
    await user.keyboard("{Enter}");
    const restartCatalog = await screen.findByRole("button", { name: "Reiniciar catálogo desde la primera página" });
    expect(restartCatalog).toHaveFocus();
    await user.keyboard("{Enter}");
    await waitFor(() => expect(screen.getByRole("button", { name: "Reintentar lectura del catálogo" })).toHaveFocus());

    const moreHistory = screen.getByRole("button", { name: "Cargar la siguiente página de planes" });
    moreHistory.focus();
    await user.keyboard("{Enter}");
    const restartHistory = await screen.findByRole("button", { name: "Reiniciar historia desde la primera página" });
    expect(restartHistory).toHaveFocus();
    await user.keyboard("{Enter}");
    await waitFor(() => expect(screen.getByRole("button", { name: "Reintentar lectura" })).toHaveFocus());

    await Promise.resolve();
    expect(catalogReads).toBe(2);
    expect(historyReads).toBe(2);
  });

  it("devuelve el foco a la recuperación si los reinicios de miembros y eventos vuelven a fallar", async () => {
    window.location.hash = `#/study/plans/${planId}`;
    const ledger = eventLedger().map((event) => ({ ...event, remainingCount: 101 }));
    const paginatedDetail = detailForMemberPagination(ledger);
    let memberReads = 0;
    let eventReads = 0;
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path === "/api/v2/context") return jsonResponse(mapContext);
      if (path === "/api/v3/study/context") return jsonResponse(studyContext);
      if (path === "/api/v3/study/plans?limit=10") return jsonResponse(plansResponse);
      if (path === `/api/v3/study/plans/${planId}`) return jsonResponse(paginatedDetail);
      if (path === `/api/v3/study/plans/${planId}/messages?state=all&limit=100`) {
        memberReads += 1;
        return memberReads === 1
          ? jsonResponse({ ...messagesResponse, planRevision: 51, items: fullMemberPage(), nextCursor: "miembros_siguiente" })
          : jsonResponse(studyError("study_unavailable"), 503);
      }
      if (path === `/api/v3/study/plans/${planId}/messages?state=all&cursor=miembros_siguiente&limit=100`) {
        return jsonResponse(studyError("invalid_cursor"), 400);
      }
      if (path === `/api/v3/study/plans/${planId}/events?limit=50`) {
        eventReads += 1;
        return eventReads === 1
          ? jsonResponse({ ...eventsResponse, planRevision: 51, items: ledger.slice(0, 50), nextCursor: "eventos_siguiente" })
          : jsonResponse(studyError("study_unavailable"), 503);
      }
      if (path === `/api/v3/study/plans/${planId}/events?cursor=eventos_siguiente&limit=50`) {
        return jsonResponse(studyError("cursor_stale"), 409);
      }
      return jsonResponse(studyError("route_not_found"), 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<App />);

    await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });
    await user.click(screen.getByText("Miembros y razones"));
    (await screen.findByRole("button", { name: /Cargar la siguiente página de todo el universo inicial/u })).focus();
    await user.keyboard("{Enter}");
    const restartMembers = await screen.findByRole("button", { name: "Reiniciar miembros desde la primera página" });
    expect(restartMembers).toHaveFocus();
    await user.keyboard("{Enter}");
    await waitFor(() => expect(screen.getByRole("button", { name: "Reintentar miembros" })).toHaveFocus());

    await user.click(screen.getByText("Eventos completos"));
    (await screen.findByRole("button", { name: "Cargar la siguiente página de eventos" })).focus();
    await user.keyboard("{Enter}");
    const restartEvents = await screen.findByRole("button", { name: "Reiniciar eventos desde la primera página" });
    expect(restartEvents).toHaveFocus();
    await user.keyboard("{Enter}");
    await waitFor(() => expect(screen.getByRole("button", { name: "Reintentar eventos" })).toHaveFocus());

    await Promise.resolve();
    expect(memberReads).toBe(2);
    expect(eventReads).toBe(2);
  });

  it("no enfoca el catálogo oculto si el constructor se cierra durante el reinicio", async () => {
    window.location.hash = "#/study";
    const deferred = deferredResponse();
    let firstPageReads = 0;
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path === "/api/v2/context") return jsonResponse(mapContext);
      if (path === "/api/v3/study/context") return jsonResponse(studyContext);
      if (path === "/api/v3/study/plans?limit=10") return jsonResponse(plansResponse);
      if (path === "/api/v3/study/targets?limit=50") {
        firstPageReads += 1;
        if (firstPageReads === 2) return deferred.promise;
        return jsonResponse({ ...targetsResponse, items: fullTargetPage(), nextCursor: "objetivos_siguiente" });
      }
      if (path === "/api/v3/study/targets?cursor=objetivos_siguiente&limit=50") {
        return jsonResponse(studyError("cursor_stale"), 409);
      }
      return jsonResponse(studyError("route_not_found"), 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<App />);

    await user.click(await screen.findByRole("button", { name: "Crear estudio" }));
    (await screen.findByRole("button", { name: "Cargar más objetivos y etiquetas" })).focus();
    await user.keyboard("{Enter}");
    const restart = await screen.findByRole("button", { name: "Reiniciar catálogo desde la primera página" });
    expect(restart).toHaveFocus();
    await user.keyboard("{Enter}");
    const closeBuilder = screen.getByRole("button", { name: "Cerrar constructor" });
    closeBuilder.focus();
    await user.keyboard("{Enter}");
    await waitFor(() => expect(screen.getByRole("heading", { name: "Crear un estudio nuevo", level: 2 })).toHaveFocus());

    await act(async () => {
      deferred.resolve(jsonResponse({ ...targetsResponse, items: fullTargetPage(), nextCursor: "objetivos_siguiente" }));
    });
    expect(screen.getByRole("heading", { name: "Crear un estudio nuevo", level: 2 })).toHaveFocus();
    expect(firstPageReads).toBe(2);
  });

  it.each([
    ["Miembros y razones", "members"],
    ["Eventos completos", "events"],
  ] as const)("no enfoca contenido oculto si se cierra %s durante el reinicio", async (panelTitle, surface) => {
    window.location.hash = `#/study/plans/${planId}`;
    const deferred = deferredResponse();
    const ledger = eventLedger().map((event) => ({ ...event, remainingCount: 101 }));
    const paginatedDetail = detailForMemberPagination(ledger);
    let firstPageReads = 0;
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path === "/api/v2/context") return jsonResponse(mapContext);
      if (path === "/api/v3/study/context") return jsonResponse(studyContext);
      if (path === "/api/v3/study/plans?limit=10") return jsonResponse(plansResponse);
      if (path === `/api/v3/study/plans/${planId}`) return jsonResponse(paginatedDetail);
      if (path === `/api/v3/study/plans/${planId}/messages?state=all&limit=100` && surface === "members") {
        firstPageReads += 1;
        if (firstPageReads === 2) return deferred.promise;
        return jsonResponse({ ...messagesResponse, planRevision: 51, items: fullMemberPage(), nextCursor: "miembros_siguiente" });
      }
      if (path === `/api/v3/study/plans/${planId}/messages?state=all&cursor=miembros_siguiente&limit=100` && surface === "members") {
        return jsonResponse(studyError("invalid_cursor"), 400);
      }
      if (path === `/api/v3/study/plans/${planId}/events?limit=50` && surface === "events") {
        firstPageReads += 1;
        if (firstPageReads === 2) return deferred.promise;
        return jsonResponse({ ...eventsResponse, planRevision: 51, items: ledger.slice(0, 50), nextCursor: "eventos_siguiente" });
      }
      if (path === `/api/v3/study/plans/${planId}/events?cursor=eventos_siguiente&limit=50` && surface === "events") {
        return jsonResponse(studyError("cursor_stale"), 409);
      }
      return jsonResponse(studyError("route_not_found"), 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<App />);

    await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });
    const panelLabel = screen.getByText(panelTitle);
    await user.click(panelLabel);
    const more = surface === "members"
      ? await screen.findByRole("button", { name: /Cargar la siguiente página de todo el universo inicial/u })
      : await screen.findByRole("button", { name: "Cargar la siguiente página de eventos" });
    more.focus();
    await user.keyboard("{Enter}");
    const restart = surface === "members"
      ? await screen.findByRole("button", { name: "Reiniciar miembros desde la primera página" })
      : await screen.findByRole("button", { name: "Reiniciar eventos desde la primera página" });
    expect(restart).toHaveFocus();
    await user.keyboard("{Enter}");

    const summary = screen.getByText(panelTitle).closest("summary")!;
    await user.click(summary);
    await waitFor(() => expect(summary.closest("details")).not.toHaveAttribute("open"));
    await act(async () => {
      deferred.resolve(surface === "members"
        ? jsonResponse({ ...messagesResponse, planRevision: 51, items: fullMemberPage(), nextCursor: "miembros_siguiente" })
        : jsonResponse({ ...eventsResponse, planRevision: 51, items: ledger.slice(0, 50), nextCursor: "eventos_siguiente" }));
    });

    expect(summary).toHaveFocus();
    expect(firstPageReads).toBe(2);
  });

  it.each([
    ["Miembros y razones", "members"],
    ["Eventos completos", "events"],
  ] as const)("descarta el reinicio encadenado viejo si se cierra y reabre %s", async (panelTitle, surface) => {
    window.location.hash = `#/study/plans/${planId}`;
    const deferredDetail = deferredResponse();
    let detailReads = 0;
    let collectionReads = 0;
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path === "/api/v2/context") return jsonResponse(mapContext);
      if (path === "/api/v3/study/context") return jsonResponse(studyContext);
      if (path === "/api/v3/study/plans?limit=10") return jsonResponse(plansResponse);
      if (path === `/api/v3/study/plans/${planId}`) {
        detailReads += 1;
        return detailReads === 2 ? deferredDetail.promise : jsonResponse(planDetail);
      }
      if (path === `/api/v3/study/plans/${planId}/messages?state=all&limit=100` && surface === "members") {
        collectionReads += 1;
        return jsonResponse({ ...messagesResponse, planRevision: collectionReads === 1 ? 2 : 1 });
      }
      if (path === `/api/v3/study/plans/${planId}/events?limit=50` && surface === "events") {
        collectionReads += 1;
        return collectionReads === 1
          ? jsonResponse({
              ...eventsResponse,
              planRevision: 2,
              items: [...detailAfterRevalidation("frozen").recentEvents].reverse(),
            })
          : jsonResponse(eventsResponse);
      }
      return jsonResponse(studyError("route_not_found"), 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<App />);

    await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });
    const summary = screen.getByText(panelTitle).closest("summary")!;
    await user.click(summary);
    const refresh = surface === "members"
      ? await screen.findByRole("button", { name: "Actualizar detalle y reiniciar miembros" })
      : await screen.findByRole("button", { name: /eventos/u });
    expect(refresh).toHaveTextContent(surface === "members"
      ? "Actualizar detalle y reiniciar miembros"
      : "Actualizar detalle y reiniciar eventos");
    refresh.focus();
    await user.keyboard("{Enter}");

    await user.click(summary);
    await waitFor(() => expect(summary.closest("details")).not.toHaveAttribute("open"));
    await user.click(summary);
    await waitFor(() => expect(summary.closest("details")).toHaveAttribute("open"));
    const focusTarget = surface === "members" ? screen.getByLabelText("Filtrar miembros") : summary;
    if (surface === "members") await screen.findByText("2 miembros cargados");
    else await screen.findByText("1 eventos cargados");
    focusTarget.focus();

    await act(async () => {
      deferredDetail.resolve(jsonResponse(planDetail));
    });
    await Promise.resolve();

    expect(focusTarget).toHaveFocus();
    expect(collectionReads).toBe(2);
    expect(detailReads).toBe(2);
  });

  it("descarta una recuperación vieja de miembros si Joa cambia el filtro durante el detalle", async () => {
    window.location.hash = `#/study/plans/${planId}`;
    const deferredDetail = deferredResponse();
    const rows = coherentMemberRows();
    let detailReads = 0;
    const memberPaths: string[] = [];
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path === "/api/v2/context") return jsonResponse(mapContext);
      if (path === "/api/v3/study/context") return jsonResponse(studyContext);
      if (path === "/api/v3/study/plans?limit=10") return jsonResponse(plansResponse);
      if (path === `/api/v3/study/plans/${planId}`) {
        detailReads += 1;
        return detailReads === 1 ? jsonResponse(planDetail) : deferredDetail.promise;
      }
      if (path.startsWith(`/api/v3/study/plans/${planId}/messages?`)) {
        memberPaths.push(path);
        const state = new URLSearchParams(path.split("?")[1]).get("state") as MemberFilter;
        return jsonResponse({
          ...messagesResponse,
          planRevision: state === "all" ? 2 : 1,
          state,
          items: rows[state],
        });
      }
      return jsonResponse(studyError("route_not_found"), 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<App />);

    await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });
    await user.click(screen.getByText("Miembros y razones"));
    const refresh = await screen.findByRole("button", { name: "Actualizar detalle y reiniciar miembros" });
    refresh.focus();
    await user.keyboard("{Enter}");
    const filter = screen.getByLabelText("Filtrar miembros");
    await user.selectOptions(filter, "eligible");
    expect(await screen.findByText("1 miembros cargados")).toBeVisible();
    expect(filter).toHaveFocus();

    await act(async () => {
      deferredDetail.resolve(jsonResponse(planDetail));
    });
    await Promise.resolve();

    expect(filter).toHaveFocus();
    expect(memberPaths).toEqual([
      `/api/v3/study/plans/${planId}/messages?state=all&limit=100`,
      `/api/v3/study/plans/${planId}/messages?state=eligible&limit=100`,
    ]);
    expect(detailReads).toBe(2);
  });

  it("sólo deja continuar la última recuperación de eventos activada dos veces", async () => {
    window.location.hash = `#/study/plans/${planId}`;
    const firstDetail = deferredResponse();
    const secondDetail = deferredResponse();
    let detailReads = 0;
    let eventReads = 0;
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path === "/api/v2/context") return jsonResponse(mapContext);
      if (path === "/api/v3/study/context") return jsonResponse(studyContext);
      if (path === "/api/v3/study/plans?limit=10") return jsonResponse(plansResponse);
      if (path === `/api/v3/study/plans/${planId}`) {
        detailReads += 1;
        if (detailReads === 1) return jsonResponse(planDetail);
        return detailReads === 2 ? firstDetail.promise : secondDetail.promise;
      }
      if (path === `/api/v3/study/plans/${planId}/events?limit=50`) {
        eventReads += 1;
        return jsonResponse(detailReads === 1 ? {
          ...eventsResponse,
          planRevision: 2,
          items: [...detailAfterRevalidation("frozen").recentEvents].reverse(),
        } : eventsResponse);
      }
      return jsonResponse(studyError("route_not_found"), 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<App />);

    await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });
    await user.click(screen.getByText("Eventos completos"));
    const refresh = await screen.findByRole("button", { name: /eventos/u });
    expect(refresh).toHaveTextContent("Actualizar detalle y reiniciar eventos");
    refresh.focus();
    await user.keyboard("{Enter}{Enter}");
    await waitFor(() => expect(detailReads).toBe(3));

    await act(async () => {
      secondDetail.resolve(jsonResponse(planDetail));
    });
    const status = await screen.findByText("1 eventos cargados");
    expect(status).toHaveFocus();
    await act(async () => {
      firstDetail.resolve(jsonResponse(planDetail));
    });
    await Promise.resolve();

    expect(status).toHaveFocus();
    expect(eventReads).toBe(2);
    expect(detailReads).toBe(3);
  });

  it("mantiene el foco en la última recuperación de detalle entre miembros y eventos", async () => {
    window.location.hash = `#/study/plans/${planId}`;
    const memberDetail = deferredResponse();
    const eventDetail = deferredResponse();
    let detailReads = 0;
    let memberReads = 0;
    let eventReads = 0;
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path === "/api/v2/context") return jsonResponse(mapContext);
      if (path === "/api/v3/study/context") return jsonResponse(studyContext);
      if (path === "/api/v3/study/plans?limit=10") return jsonResponse(plansResponse);
      if (path === `/api/v3/study/plans/${planId}`) {
        detailReads += 1;
        if (detailReads === 1) return jsonResponse(planDetail);
        return detailReads === 2 ? memberDetail.promise : eventDetail.promise;
      }
      if (path === `/api/v3/study/plans/${planId}/messages?state=all&limit=100`) {
        memberReads += 1;
        return jsonResponse({ ...messagesResponse, planRevision: 2 });
      }
      if (path === `/api/v3/study/plans/${planId}/events?limit=50`) {
        eventReads += 1;
        return jsonResponse(detailReads === 1 ? {
          ...eventsResponse,
          planRevision: 2,
          items: [...detailAfterRevalidation("frozen").recentEvents].reverse(),
        } : eventsResponse);
      }
      return jsonResponse(studyError("route_not_found"), 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<App />);

    await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });
    await user.click(screen.getByText("Miembros y razones"));
    const memberRefresh = await screen.findByRole("button", { name: "Actualizar detalle y reiniciar miembros" });
    await user.click(screen.getByText("Eventos completos"));
    const eventRefresh = await screen.findByRole("button", { name: "Actualizar detalle y reiniciar eventos" });
    memberRefresh.focus();
    await user.keyboard("{Enter}");
    eventRefresh.focus();
    await user.keyboard("{Enter}");
    await waitFor(() => expect(detailReads).toBe(3));

    await act(async () => {
      eventDetail.resolve(jsonResponse(planDetail));
    });
    const eventStatus = await screen.findByText("1 eventos cargados");
    expect(eventStatus).toHaveFocus();
    await act(async () => {
      memberDetail.resolve(jsonResponse(planDetail));
    });
    await Promise.resolve();

    expect(eventStatus).toHaveFocus();
    expect(screen.getByRole("button", { name: "Actualizar detalle y reiniciar miembros" })).toBeVisible();
    expect(memberReads).toBe(1);
    expect(eventReads).toBe(2);
    expect(detailReads).toBe(3);
  });

  it("no recupera foco desde una colección hermana que termina después", async () => {
    window.location.hash = `#/study/plans/${planId}`;
    const delayedMembers = deferredResponse();
    let detailReads = 0;
    let memberReads = 0;
    let eventReads = 0;
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path === "/api/v2/context") return jsonResponse(mapContext);
      if (path === "/api/v3/study/context") return jsonResponse(studyContext);
      if (path === "/api/v3/study/plans?limit=10") return jsonResponse(plansResponse);
      if (path === `/api/v3/study/plans/${planId}`) {
        detailReads += 1;
        return jsonResponse(planDetail);
      }
      if (path === `/api/v3/study/plans/${planId}/messages?state=all&limit=100`) {
        memberReads += 1;
        return memberReads === 1 ? jsonResponse({ ...messagesResponse, planRevision: 2 }) : delayedMembers.promise;
      }
      if (path === `/api/v3/study/plans/${planId}/events?limit=50`) {
        eventReads += 1;
        return jsonResponse(detailReads === 1 ? {
          ...eventsResponse,
          planRevision: 2,
          items: [...detailAfterRevalidation("frozen").recentEvents].reverse(),
        } : eventsResponse);
      }
      return jsonResponse(studyError("route_not_found"), 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<App />);

    await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });
    await user.click(screen.getByText("Miembros y razones"));
    const memberRefresh = await screen.findByRole("button", { name: "Actualizar detalle y reiniciar miembros" });
    await user.click(screen.getByText("Eventos completos"));
    const eventRefresh = await screen.findByRole("button", { name: "Actualizar detalle y reiniciar eventos" });
    memberRefresh.focus();
    await user.keyboard("{Enter}");
    await waitFor(() => expect(memberReads).toBe(2));

    eventRefresh.focus();
    await user.keyboard("{Enter}");
    const eventStatus = await screen.findByText("1 eventos cargados");
    expect(eventStatus).toHaveFocus();
    await act(async () => {
      delayedMembers.resolve(jsonResponse(messagesResponse));
    });
    expect(await screen.findByText("2 miembros cargados")).toBeVisible();

    expect(eventStatus).toHaveFocus();
    expect(memberReads).toBe(2);
    expect(eventReads).toBe(2);
    expect(detailReads).toBe(3);
  });

  it("enfoca la recuperación si la última página contradice el agregado congelado", async () => {
    window.location.hash = `#/study/plans/${planId}`;
    const ledger = eventLedger().map((event) => ({ ...event, remainingCount: 101 }));
    const paginatedDetail = detailForMemberPagination(ledger);
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path === "/api/v2/context") return jsonResponse(mapContext);
      if (path === "/api/v3/study/context") return jsonResponse(studyContext);
      if (path === "/api/v3/study/plans?limit=10") return jsonResponse(plansResponse);
      if (path === `/api/v3/study/plans/${planId}`) return jsonResponse(paginatedDetail);
      if (path === `/api/v3/study/plans/${planId}/messages?state=all&limit=100`) {
        return jsonResponse({ ...messagesResponse, planRevision: 51, items: fullMemberPage(), nextCursor: "miembros_siguiente" });
      }
      if (path === `/api/v3/study/plans/${planId}/messages?state=all&cursor=miembros_siguiente&limit=100`) {
        const base = fullMemberPage().at(-1)!;
        return jsonResponse({
          ...messagesResponse,
          planRevision: 51,
          items: [{
            ...base,
            messageId: `message-v1-${"f".repeat(64)}`,
            receivedAt: new Date(Date.parse(base.receivedAt) - 60_000).toISOString(),
            sizeEstimateBytes: base.sizeEstimateBytes + 1,
          }],
          nextCursor: null,
        });
      }
      return jsonResponse(studyError("route_not_found"), 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    const { container } = render(<App />);

    await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });
    await user.click(screen.getByText("Miembros y razones"));
    (await screen.findByRole("button", { name: /Cargar la siguiente página de todo el universo inicial/u })).focus();
    await user.keyboard("{Enter}");

    const restart = await screen.findByRole("button", { name: "Reiniciar miembros desde la primera página" });
    expect(restart).toHaveFocus();
    expect(container.querySelectorAll(".study-member-list li")).toHaveLength(0);
    expect(screen.queryByText("101 miembros cargados")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Revalidar alcance" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Cancelar plan" })).toBeDisabled();
  });

  it("enfoca el estado acumulado después de cada página de catálogo e historia", async () => {
    window.location.hash = "#/study";
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path === "/api/v2/context") return jsonResponse(mapContext);
      if (path === "/api/v3/study/context") return jsonResponse(studyContext);
      if (path === "/api/v3/study/plans?limit=10") {
        return jsonResponse({ ...plansResponse, items: historyPage(0, 10), nextCursor: "historia_2" });
      }
      if (path === "/api/v3/study/plans?cursor=historia_2&limit=10") {
        return jsonResponse({ ...plansResponse, items: historyPage(10, 10), nextCursor: "historia_3" });
      }
      if (path === "/api/v3/study/plans?cursor=historia_3&limit=10") {
        return jsonResponse({ ...plansResponse, items: historyPage(20, 1), nextCursor: null });
      }
      if (path === "/api/v3/study/targets?limit=50") {
        return jsonResponse({ ...targetsResponse, items: fullTargetPage(), nextCursor: "catalogo_2" });
      }
      if (path === "/api/v3/study/targets?cursor=catalogo_2&limit=50") {
        return jsonResponse({ ...targetsResponse, items: targetPage(50, 50), nextCursor: "catalogo_3" });
      }
      if (path === "/api/v3/study/targets?cursor=catalogo_3&limit=50") {
        return jsonResponse({ ...targetsResponse, items: targetPage(100, 1), nextCursor: null });
      }
      return jsonResponse(studyError("route_not_found"), 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<App />);

    await screen.findByText("10 planes cargados");
    await user.click(await screen.findByRole("button", { name: "Crear estudio" }));
    let moreCatalog = await screen.findByRole("button", { name: "Cargar más objetivos y etiquetas" });
    moreCatalog.focus();
    await user.keyboard("{Enter}");
    expect(await screen.findByText("100 objetivos y etiquetas cargados")).toHaveFocus();
    moreCatalog = screen.getByRole("button", { name: "Cargar más objetivos y etiquetas" });
    moreCatalog.focus();
    await user.keyboard("{Enter}");
    expect(await screen.findByText("101 objetivos y etiquetas cargados")).toHaveFocus();

    let moreHistory = screen.getByRole("button", { name: "Cargar la siguiente página de planes" });
    moreHistory.focus();
    await user.keyboard("{Enter}");
    expect(await screen.findByText("20 planes cargados")).toHaveFocus();
    moreHistory = screen.getByRole("button", { name: "Cargar la siguiente página de planes" });
    moreHistory.focus();
    await user.keyboard("{Enter}");
    expect(await screen.findByText("21 planes cargados")).toHaveFocus();
  });

  it("enfoca el estado acumulado después de cada página de miembros y eventos", async () => {
    window.location.hash = `#/study/plans/${planId}`;
    const memberCount = 201;
    const ledger = eventLedger(101).map((event) => ({ ...event, remainingCount: memberCount }));
    const detail: PlanDetail = {
      ...detailForLedger(ledger),
      selectedAtCreationCount: memberCount,
      selectedAtCreationSizeEstimateBytes: memberCount * messagesResponse.items[0]!.sizeEstimateBytes,
      excludedAtCreationCount: 0,
      excludedAtCreationSizeEstimateBytes: 0,
      currentEligibleCount: memberCount,
      currentEligibleSizeEstimateBytes: memberCount * messagesResponse.items[0]!.sizeEstimateBytes,
      excludedSamples: [],
    };
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path === "/api/v2/context") return jsonResponse(mapContext);
      if (path === "/api/v3/study/context") return jsonResponse(studyContext);
      if (path === "/api/v3/study/plans?limit=10") return jsonResponse(plansResponse);
      if (path === `/api/v3/study/plans/${planId}`) return jsonResponse(detail);
      if (path === `/api/v3/study/plans/${planId}/messages?state=all&limit=100`) {
        return jsonResponse({ ...messagesResponse, planRevision: 101, items: memberPage(0, 100), nextCursor: "miembros_2" });
      }
      if (path === `/api/v3/study/plans/${planId}/messages?state=all&cursor=miembros_2&limit=100`) {
        return jsonResponse({ ...messagesResponse, planRevision: 101, items: memberPage(100, 100), nextCursor: "miembros_3" });
      }
      if (path === `/api/v3/study/plans/${planId}/messages?state=all&cursor=miembros_3&limit=100`) {
        return jsonResponse({ ...messagesResponse, planRevision: 101, items: memberPage(200, 1), nextCursor: null });
      }
      if (path === `/api/v3/study/plans/${planId}/events?limit=50`) {
        return jsonResponse({ ...eventsResponse, planRevision: 101, items: ledger.slice(0, 50), nextCursor: "eventos_2" });
      }
      if (path === `/api/v3/study/plans/${planId}/events?cursor=eventos_2&limit=50`) {
        return jsonResponse({ ...eventsResponse, planRevision: 101, items: ledger.slice(50, 100), nextCursor: "eventos_3" });
      }
      if (path === `/api/v3/study/plans/${planId}/events?cursor=eventos_3&limit=50`) {
        return jsonResponse({ ...eventsResponse, planRevision: 101, items: ledger.slice(100), nextCursor: null });
      }
      return jsonResponse(studyError("route_not_found"), 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<App />);

    await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });
    await user.click(screen.getByText("Miembros y razones"));
    let moreMembers = await screen.findByRole("button", { name: /Cargar la siguiente página de todo el universo inicial/u });
    moreMembers.focus();
    await user.keyboard("{Enter}");
    expect(await screen.findByText("200 miembros cargados")).toHaveFocus();
    moreMembers = screen.getByRole("button", { name: /Cargar la siguiente página de todo el universo inicial/u });
    moreMembers.focus();
    await user.keyboard("{Enter}");
    expect(await screen.findByText("201 miembros cargados")).toHaveFocus();

    await user.click(screen.getByText("Eventos completos"));
    let moreEvents = await screen.findByRole("button", { name: "Cargar la siguiente página de eventos" });
    moreEvents.focus();
    await user.keyboard("{Enter}");
    expect(await screen.findByText("100 eventos cargados")).toHaveFocus();
    moreEvents = screen.getByRole("button", { name: "Cargar la siguiente página de eventos" });
    moreEvents.focus();
    await user.keyboard("{Enter}");
    expect(await screen.findByText("101 eventos cargados")).toHaveFocus();
  });

  it.each([
    ["catálogo", "historia"],
    ["historia", "catálogo"],
  ] as const)("la última paginación explícita de StudyPage conserva el foco: %s y luego %s", async (first, last) => {
    window.location.hash = "#/study";
    const catalogPage = deferredResponse();
    const historyPageResponse = deferredResponse();
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path === "/api/v2/context") return jsonResponse(mapContext);
      if (path === "/api/v3/study/context") return jsonResponse(studyContext);
      if (path === "/api/v3/study/plans?limit=10") {
        return jsonResponse({ ...plansResponse, items: historyPage(0, 10), nextCursor: "historia_cruzada" });
      }
      if (path === "/api/v3/study/plans?cursor=historia_cruzada&limit=10") return historyPageResponse.promise;
      if (path === "/api/v3/study/targets?limit=50") {
        return jsonResponse({ ...targetsResponse, items: fullTargetPage(), nextCursor: "catalogo_cruzado" });
      }
      if (path === "/api/v3/study/targets?cursor=catalogo_cruzado&limit=50") return catalogPage.promise;
      return jsonResponse(studyError("route_not_found"), 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<App />);

    await screen.findByText("10 planes cargados");
    await user.click(await screen.findByRole("button", { name: "Crear estudio" }));
    const buttons = {
      catálogo: await screen.findByRole("button", { name: "Cargar más objetivos y etiquetas" }),
      historia: screen.getByRole("button", { name: "Cargar la siguiente página de planes" }),
    };
    buttons[first].focus();
    await user.keyboard("{Enter}");
    buttons[last].focus();
    await user.keyboard("{Enter}");

    const responses = {
      catálogo: jsonResponse({ ...targetsResponse, items: targetPage(50, 1), nextCursor: null }),
      historia: jsonResponse({ ...plansResponse, items: historyPage(10, 1), nextCursor: null }),
    };
    const deferred = { catálogo: catalogPage, historia: historyPageResponse };
    const statusNames = { catálogo: "51 objetivos y etiquetas cargados", historia: "11 planes cargados" };
    await act(async () => deferred[last].resolve(responses[last]));
    const winningStatus = await screen.findByText(statusNames[last]);
    expect(winningStatus).toHaveFocus();
    await act(async () => deferred[first].resolve(responses[first]));
    await screen.findByText(statusNames[first]);

    expect(winningStatus).toHaveFocus();
  });

  it.each([
    ["miembros", "eventos"],
    ["eventos", "miembros"],
  ] as const)("la última paginación explícita de StudyPlanPage conserva el foco: %s y luego %s", async (first, last) => {
    window.location.hash = `#/study/plans/${planId}`;
    const memberPageResponse = deferredResponse();
    const eventPageResponse = deferredResponse();
    const ledger = eventLedger().map((event) => ({ ...event, remainingCount: 101 }));
    const detail = detailForMemberPagination(ledger);
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path === "/api/v2/context") return jsonResponse(mapContext);
      if (path === "/api/v3/study/context") return jsonResponse(studyContext);
      if (path === "/api/v3/study/plans?limit=10") return jsonResponse(plansResponse);
      if (path === `/api/v3/study/plans/${planId}`) return jsonResponse(detail);
      if (path === `/api/v3/study/plans/${planId}/messages?state=all&limit=100`) {
        return jsonResponse({ ...messagesResponse, planRevision: 51, items: fullMemberPage(), nextCursor: "miembros_cruzados" });
      }
      if (path === `/api/v3/study/plans/${planId}/messages?state=all&cursor=miembros_cruzados&limit=100`) {
        return memberPageResponse.promise;
      }
      if (path === `/api/v3/study/plans/${planId}/events?limit=50`) {
        return jsonResponse({ ...eventsResponse, planRevision: 51, items: ledger.slice(0, 50), nextCursor: "eventos_cruzados" });
      }
      if (path === `/api/v3/study/plans/${planId}/events?cursor=eventos_cruzados&limit=50`) {
        return eventPageResponse.promise;
      }
      return jsonResponse(studyError("route_not_found"), 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<App />);

    await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });
    await user.click(screen.getByText("Miembros y razones"));
    await user.click(screen.getByText("Eventos completos"));
    const buttons = {
      miembros: await screen.findByRole("button", { name: /Cargar la siguiente página de todo el universo inicial/u }),
      eventos: await screen.findByRole("button", { name: "Cargar la siguiente página de eventos" }),
    };
    buttons[first].focus();
    await user.keyboard("{Enter}");
    buttons[last].focus();
    await user.keyboard("{Enter}");

    const responses = {
      miembros: jsonResponse({ ...messagesResponse, planRevision: 51, items: memberPage(100, 1), nextCursor: null }),
      eventos: jsonResponse({ ...eventsResponse, planRevision: 51, items: ledger.slice(50), nextCursor: null }),
    };
    const deferred = { miembros: memberPageResponse, eventos: eventPageResponse };
    const statusNames = { miembros: "101 miembros cargados", eventos: "51 eventos cargados" };
    await act(async () => deferred[last].resolve(responses[last]));
    const winningStatus = await screen.findByText(statusNames[last]);
    expect(winningStatus).toHaveFocus();
    await act(async () => deferred[first].resolve(responses[first]));
    await screen.findByText(statusNames[first]);

    expect(winningStatus).toHaveFocus();
  });

  it("descarta síncronamente una página vieja de historia al cambiar el filtro", async () => {
    window.location.hash = "#/study";
    const oldAppend = deferredResponse();
    const frozenFirstPage = deferredResponse();
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path === "/api/v2/context") return jsonResponse(mapContext);
      if (path === "/api/v3/study/context") return jsonResponse(studyContext);
      if (path === "/api/v3/study/plans?limit=10") {
        return jsonResponse({ ...plansResponse, items: historyPage(0, 10), nextCursor: "historia_vieja" });
      }
      if (path === "/api/v3/study/plans?cursor=historia_vieja&limit=10") return oldAppend.promise;
      if (path === "/api/v3/study/plans?state=frozen&limit=10") return frozenFirstPage.promise;
      return jsonResponse(studyError("route_not_found"), 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    const { container } = render(<App />);

    await screen.findByText("10 planes cargados");
    const more = screen.getByRole("button", { name: "Cargar la siguiente página de planes" });
    more.focus();
    await user.keyboard("{Enter}");
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/v3/study/plans?cursor=historia_vieja&limit=10",
      expect.objectContaining({ method: "GET" }),
    ));

    const filter = screen.getByLabelText("Filtrar por estado");
    filter.focus();
    fireEvent.change(filter, { target: { value: "frozen" } });
    expect(container.querySelectorAll(".study-plan-list [role='listitem']")).toHaveLength(0);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/v3/study/plans?state=frozen&limit=10",
      expect.objectContaining({ method: "GET" }),
    ));
    await act(async () => oldAppend.resolve(jsonResponse({
      ...plansResponse,
      items: historyPage(10, 1),
      nextCursor: null,
    })));
    expect(container.querySelectorAll(".study-plan-list [role='listitem']")).toHaveLength(0);
    expect(filter).toHaveFocus();

    await act(async () => frozenFirstPage.resolve(jsonResponse({
      ...plansResponse,
      state: "frozen",
      items: [{ ...plansResponse.items[0]!, state: "frozen" }],
      nextCursor: null,
    })));
    expect(await screen.findByText("1 planes cargados")).toBeVisible();
    expect(container.querySelectorAll(".study-plan-list [role='listitem']")).toHaveLength(1);
    expect(filter).toHaveFocus();
  });

  it("descarta síncronamente una página all vieja al cambiar miembros a eligible", async () => {
    window.location.hash = `#/study/plans/${planId}`;
    const oldAppend = deferredResponse();
    const eligibleFirstPage = deferredResponse();
    const allRows: PlanMember[] = memberPage(0, 101).map((member, index) => index === 0 ? member : {
      ...member,
      currentState: "removed",
      reasonCodes: ["missing_after_creation"],
    });
    const reducedBase = detailForState("reduced");
    const detail: PlanDetail = {
      ...reducedBase,
      selectedAtCreationCount: 101,
      selectedAtCreationSizeEstimateBytes: 206_848,
      excludedAtCreationCount: 0,
      excludedAtCreationSizeEstimateBytes: 0,
      currentEligibleCount: 1,
      currentEligibleSizeEstimateBytes: 2048,
      excludedSamples: [],
      recentEvents: [
        { ...reducedBase.recentEvents[0]!, removedCount: 100, remainingCount: 1 },
        { ...reducedBase.recentEvents[1]!, remainingCount: 101 },
      ],
    };
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path === "/api/v2/context") return jsonResponse(mapContext);
      if (path === "/api/v3/study/context") return jsonResponse(studyContext);
      if (path === "/api/v3/study/plans?limit=10") return jsonResponse(plansResponse);
      if (path === `/api/v3/study/plans/${planId}`) return jsonResponse(detail);
      if (path === `/api/v3/study/plans/${planId}/messages?state=all&limit=100`) {
        return jsonResponse({ ...messagesResponse, planRevision: 2, items: allRows.slice(0, 100), nextCursor: "miembros_viejos" });
      }
      if (path === `/api/v3/study/plans/${planId}/messages?state=all&cursor=miembros_viejos&limit=100`) {
        return oldAppend.promise;
      }
      if (path === `/api/v3/study/plans/${planId}/messages?state=eligible&limit=100`) {
        return eligibleFirstPage.promise;
      }
      return jsonResponse(studyError("route_not_found"), 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    const { container } = render(<App />);

    await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });
    await user.click(screen.getByText("Miembros y razones"));
    const more = await screen.findByRole("button", { name: /Cargar la siguiente página de todo el universo inicial/u });
    more.focus();
    await user.keyboard("{Enter}");
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      `/api/v3/study/plans/${planId}/messages?state=all&cursor=miembros_viejos&limit=100`,
      expect.objectContaining({ method: "GET" }),
    ));

    const filter = screen.getByLabelText("Filtrar miembros");
    filter.focus();
    fireEvent.change(filter, { target: { value: "eligible" } });
    expect(container.querySelectorAll(".study-member-list li")).toHaveLength(0);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      `/api/v3/study/plans/${planId}/messages?state=eligible&limit=100`,
      expect.objectContaining({ method: "GET" }),
    ));
    await act(async () => oldAppend.resolve(jsonResponse({
      ...messagesResponse,
      planRevision: 2,
      items: allRows.slice(100),
      nextCursor: null,
    })));
    expect(container.querySelectorAll(".study-member-list li")).toHaveLength(0);
    expect(filter).toHaveFocus();

    await act(async () => eligibleFirstPage.resolve(jsonResponse({
      ...messagesResponse,
      planRevision: 2,
      state: "eligible",
      items: [allRows[0]!],
      nextCursor: null,
    })));
    expect(await screen.findByText("1 miembros cargados")).toBeVisible();
    expect(container.querySelectorAll(".study-member-list li")).toHaveLength(1);
    expect(filter).toHaveFocus();
  });

  it.each([
    ["activo", detailAfterSecondRevalidation(), false, "Congelado"],
    ["terminal en replay", cancelledAfterRevalidationDetail, true, "Cancelado"],
  ] as const)(
    "no deja que una confirmación r2 diferida rebaje el detalle hermano r3: %s",
    async (_case, latestDetail, replayed, expectedState) => {
      window.location.hash = `#/study/plans/${planId}`;
      const delayedConfirmation = deferredResponse();
      const mapSetSpy = vi.spyOn(Map.prototype, "set");
      let detailReads = 0;
      const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const path = String(input);
        if (path === "/api/v2/context") return jsonResponse(mapContext);
        if (path === "/api/v3/study/context") return jsonResponse(studyContext);
        if (path === "/api/v3/study/plans?limit=10") return jsonResponse(plansResponse);
        if (path === `/api/v3/study/plans/${planId}`) {
          detailReads += 1;
          if (detailReads === 1) return jsonResponse(planDetail);
          if (detailReads === 2) return delayedConfirmation.promise;
          return jsonResponse(latestDetail);
        }
        if (path === `/api/v3/study/plans/${planId}/revalidate` && init?.method === "POST") {
          return jsonResponse({ ...revalidateReceipt, replayed });
        }
        return jsonResponse(studyError("route_not_found"), 404);
      });
      vi.stubGlobal("fetch", fetchMock);
      const user = userEvent.setup();
      try {
        render(<App />);
        await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });
        await user.click(screen.getByRole("button", { name: "Revalidar alcance" }));
        await waitFor(() => expect(detailReads).toBe(2));

        await user.click(screen.getByRole("link", { name: "Volver a planes" }));
        await screen.findByRole("heading", { name: "Estudio de Limpieza", level: 1 });
        await user.click(await screen.findByRole("link", { name: /Ver detalle del plan/u }));
        await screen.findByText("Plan r3");
        expect(screen.getByRole("heading", { name: expectedState, level: 2 })).toBeVisible();
        expect(screen.getByText(/El comando sigue pendiente/u)).toBeVisible();

        await act(async () => delayedConfirmation.resolve(jsonResponse(detailAfterRevalidation("frozen"))));
        await waitFor(() => expect(screen.queryByText(/El comando sigue pendiente/u)).not.toBeInTheDocument());
        expect(await screen.findByText(/estado actual todavía no pudo confirmarse/u)).toBeVisible();
        expect(screen.getByText("Plan r3")).toBeVisible();
        expect(screen.getByRole("heading", { name: expectedState, level: 2 })).toBeVisible();
        if (!replayed) {
          expect(screen.getByRole("button", { name: "Revalidar alcance" })).toBeDisabled();
          expect(screen.getByRole("button", { name: "Cancelar plan" })).toBeDisabled();
        } else {
          expect(screen.queryByRole("button", { name: "Revalidar alcance" })).not.toBeInTheDocument();
          expect(screen.queryByRole("button", { name: "Cancelar plan" })).not.toBeInTheDocument();
        }
        expect(fetchMock.mock.calls.filter((call) => call[1]?.method === "POST")).toHaveLength(1);
        const planWrites = mapSetSpy.mock.calls
          .filter((entry): entry is [unknown, { planRevision: number }] => {
            const [key, value] = entry;
            return key === planId
              && typeof value === "object"
              && value !== null
              && "planRevision" in value
              && typeof value.planRevision === "number";
          })
          .map(([, value]) => value.planRevision);
        expect(planWrites).toContain(3);
        expect(planWrites).not.toContain(2);
        expect(planWrites.at(-1)).toBe(3);
      } finally {
        mapSetSpy.mockRestore();
      }
    },
  );

  it.each([
    ["activo", detailAfterSecondRevalidation(), false, "Congelado"],
    ["terminal en replay", cancelledAfterRevalidationDetail, true, "Cancelado"],
  ] as const)(
    "no deja que una confirmación r2 diferida rebaje una recuperación r3 en el mismo montaje: %s",
    async (_case, latestDetail, replayed, expectedState) => {
      window.location.hash = `#/study/plans/${planId}`;
      const delayedConfirmation = deferredResponse();
      const mapSetSpy = vi.spyOn(Map.prototype, "set");
      let detailReads = 0;
      let memberReads = 0;
      const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const path = String(input);
        if (path === "/api/v2/context") return jsonResponse(mapContext);
        if (path === "/api/v3/study/context") return jsonResponse(studyContext);
        if (path === "/api/v3/study/plans?limit=10") return jsonResponse(plansResponse);
        if (path === `/api/v3/study/plans/${planId}`) {
          detailReads += 1;
          if (detailReads === 1) return jsonResponse(planDetail);
          if (detailReads === 2) return delayedConfirmation.promise;
          return jsonResponse(latestDetail);
        }
        if (path === `/api/v3/study/plans/${planId}/messages?state=all&limit=100`) {
          memberReads += 1;
          return jsonResponse({
            ...messagesResponse,
            planRevision: memberReads === 1 ? 2 : latestDetail.planRevision,
          });
        }
        if (path === `/api/v3/study/plans/${planId}/revalidate` && init?.method === "POST") {
          return jsonResponse({ ...revalidateReceipt, replayed });
        }
        return jsonResponse(studyError("route_not_found"), 404);
      });
      vi.stubGlobal("fetch", fetchMock);
      const user = userEvent.setup();
      try {
        render(<App />);
        await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });
        await user.click(screen.getByRole("button", { name: "Revalidar alcance" }));
        await waitFor(() => expect(detailReads).toBe(2));

        await user.click(screen.getByText("Miembros y razones"));
        const recoverMembers = await screen.findByRole("button", { name: "Actualizar detalle y reiniciar miembros" });
        await user.click(recoverMembers);
        await screen.findByText("Plan r3");
        await screen.findByText("2 miembros cargados");
        expect(detailReads).toBe(3);
        expect(memberReads).toBe(2);
        expect(screen.getByRole("heading", { name: expectedState, level: 2 })).toBeVisible();

        await act(async () => delayedConfirmation.resolve(jsonResponse(detailAfterRevalidation("frozen"))));

        expect(await screen.findByText(/no pudimos confirmar el estado actual/u)).toBeVisible();
        expect(screen.getByText("Plan r3")).toBeVisible();
        expect(screen.getByRole("heading", { name: expectedState, level: 2 })).toBeVisible();
        expect(screen.queryByText(/Alcance revalidado|Replay confirmado/u)).not.toBeInTheDocument();
        if (!replayed) {
          expect(screen.getByRole("button", { name: "Revalidar alcance" })).toBeDisabled();
          expect(screen.getByRole("button", { name: "Cancelar plan" })).toBeDisabled();
        } else {
          expect(screen.queryByRole("button", { name: "Revalidar alcance" })).not.toBeInTheDocument();
          expect(screen.queryByRole("button", { name: "Cancelar plan" })).not.toBeInTheDocument();
        }
        expect(fetchMock.mock.calls.filter((call) => call[1]?.method === "POST")).toHaveLength(1);
        const planWrites = mapSetSpy.mock.calls
          .filter((entry): entry is [unknown, { planRevision: number }] => {
            const [key, value] = entry;
            return key === planId
              && typeof value === "object"
              && value !== null
              && "planRevision" in value
              && typeof value.planRevision === "number";
          })
          .map(([, value]) => value.planRevision);
        expect(planWrites).toContain(3);
        expect(planWrites).not.toContain(2);
        expect(planWrites.at(-1)).toBe(3);
      } finally {
        mapSetSpy.mockRestore();
      }
    },
  );

  it("acepta active r1 a expired r2 cuando la revisión nueva conserva el evento contractual previo", async () => {
    window.location.hash = `#/study/plans/${planId}`;
    const expiredRevisionTwo: PlanDetail = {
      ...detailAfterRevalidation("frozen"),
      state: "expired",
    };
    let detailReads = 0;
    const fetchMock = installStudyApi({
      detailResponse: async () => {
        detailReads += 1;
        return jsonResponse(detailReads === 1 ? planDetail : expiredRevisionTwo);
      },
      post: async () => jsonResponse(revalidateReceipt),
    });
    const user = userEvent.setup();
    render(<App />);

    await screen.findByRole("heading", { name: "Detalle del Estudio de Limpieza", level: 1 });
    await user.click(screen.getByRole("button", { name: "Revalidar alcance" }));

    expect(await screen.findByRole("heading", { name: "Vencido", level: 2 })).toBeVisible();
    expect(screen.getByText("Plan r2")).toBeVisible();
    expect(screen.getByText(/El servidor marcó este plan como vencido/u)).toBeVisible();
    expect(screen.getByText(/Alcance revalidado; estado actual confirmado: Vencido/u)).toBeVisible();
    expect(screen.queryByText(/respuesta incompatible con el contrato/u)).not.toBeInTheDocument();
    expect(expiredRevisionTwo.recentEvents[0]!.type).toBe("revalidated");
    expect(Date.parse(expiredRevisionTwo.recentEvents[0]!.recordedAt)).toBeLessThan(Date.parse(expiredRevisionTwo.expiresAt));
    expect(expiredRevisionTwo.recentEvents[1]).toEqual(planDetail.recentEvents[0]);
    expect(detailReads).toBe(2);
    expect(fetchMock.mock.calls.filter((call) => call[1]?.method === "POST")).toHaveLength(1);
  });

  it("pagina catálogo, miembros y eventos manteniendo filtros y límites originales", async () => {
    window.location.hash = "#/study";
    let targetPage = 0;
    const paginatedEvents = eventLedger().map((event) => ({ ...event, remainingCount: 101 }));
    const paginatedDetail = detailForMemberPagination(paginatedEvents);
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path === "/api/v2/context") return jsonResponse(mapContext);
      if (path === "/api/v3/study/context") return jsonResponse(studyContext);
      if (path === "/api/v3/study/plans?limit=10") return jsonResponse(plansResponse);
      if (path === "/api/v3/study/targets?limit=50") {
        targetPage += 1;
        return jsonResponse({ ...targetsResponse, items: fullTargetPage(), nextCursor: "objetivos_siguiente" });
      }
      if (path === "/api/v3/study/targets?cursor=objetivos_siguiente&limit=50") {
        return jsonResponse({ ...targetsResponse, items: [targetsResponse.items[3]], nextCursor: null });
      }
      if (path === `/api/v3/study/plans/${planId}`) return jsonResponse(paginatedDetail);
      if (path === `/api/v3/study/plans/${planId}/messages?state=all&limit=100`) {
        return jsonResponse({ ...messagesResponse, planRevision: 51, items: fullMemberPage(), nextCursor: "miembros_siguiente" });
      }
      if (path === `/api/v3/study/plans/${planId}/messages?state=all&cursor=miembros_siguiente&limit=100`) {
        const base = fullMemberPage().at(-1)!;
        return jsonResponse({
          ...messagesResponse,
          planRevision: 51,
          items: [{
            ...base,
            messageId: `message-v1-${"f".repeat(64)}`,
            receivedAt: new Date(Date.parse(base.receivedAt) - 60_000).toISOString(),
          }],
          nextCursor: null,
        });
      }
      if (path === `/api/v3/study/plans/${planId}/events?limit=50`) {
        return jsonResponse({ ...eventsResponse, planRevision: 51, items: paginatedEvents.slice(0, 50), nextCursor: "eventos_siguiente" });
      }
      if (path === `/api/v3/study/plans/${planId}/events?cursor=eventos_siguiente&limit=50`) {
        return jsonResponse({ ...eventsResponse, planRevision: 51, items: paginatedEvents.slice(50), nextCursor: null });
      }
      return jsonResponse(studyError("route_not_found"), 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    const { unmount } = render(<App />);

    await user.click(await screen.findByRole("button", { name: "Crear estudio" }));
    await screen.findByRole("checkbox", { name: /Boletines Example/u });
    screen.getByRole("button", { name: "Cargar más objetivos y etiquetas" }).focus();
    await user.keyboard("{Enter}");
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/v3/study/targets?cursor=objetivos_siguiente&limit=50",
      expect.objectContaining({ method: "GET" }),
    ));
    expect(targetPage).toBe(1);
    expect(screen.getByText("51 objetivos y etiquetas cargados")).toHaveFocus();
    unmount();

    window.location.hash = `#/study/plans/${planId}`;
    render(<App />);
    await screen.findByText("Leé el alcance histórico y su estado efectivo sin reconstruirlo desde el mapa actual.");
    await user.click(screen.getByText("Miembros y razones"));
    (await screen.findByRole("button", { name: /Cargar la siguiente página de todo el universo inicial/u })).focus();
    await user.keyboard("{Enter}");
    expect(await screen.findByText("101 miembros cargados")).toHaveFocus();
    await user.click(screen.getByText("Eventos completos"));
    (await screen.findByRole("button", { name: "Cargar la siguiente página de eventos" })).focus();
    await user.keyboard("{Enter}");
    expect(await screen.findByText("51 eventos cargados")).toHaveFocus();
    expect(fetchMock).toHaveBeenCalledWith(
      `/api/v3/study/plans/${planId}/messages?state=all&cursor=miembros_siguiente&limit=100`,
      expect.objectContaining({ method: "GET" }),
    );
    expect(fetchMock).toHaveBeenCalledWith(
      `/api/v3/study/plans/${planId}/events?cursor=eventos_siguiente&limit=50`,
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("confirma revalidación sin cambios mediante replay y luego cancelación local", async () => {
    window.location.hash = `#/study/plans/${planId}`;
    const options: ApiOptions = {};
    options.post = async (path) => {
      if (path.endsWith("/revalidate")) {
        options.detail = detailAfterRevalidation("frozen");
        return jsonResponse({ ...revalidateReceipt, replayed: true });
      }
      options.detail = cancelledAfterRevalidationDetail;
      return jsonResponse({ ...cancelReceipt, commandRevision: 3 });
    };
    installStudyApi(options);
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Leé el alcance histórico y su estado efectivo sin reconstruirlo desde el mapa actual.");

    await user.click(screen.getByRole("button", { name: "Revalidar alcance" }));
    expect(await screen.findByText(/Replay confirmado/u)).toBeVisible();
    expect(screen.getAllByText(/29 ago 2026/u, { exact: false }).length).toBeGreaterThanOrEqual(2);
    await user.click(screen.getByRole("button", { name: "Cancelar plan" }));
    expect(await screen.findByRole("heading", { name: "Cancelado", level: 2 })).toBeVisible();
    expect(screen.getByText(/No se modificaron mensajes/u)).toBeVisible();
  });

  it.each([
    ["reduced", "Selección reducida"],
    ["invalidated", "Invalidado"],
  ] as const)("revalidación monotónica deja el plan %s", async (state, label) => {
    window.location.hash = `#/study/plans/${planId}`;
    const options: ApiOptions = { detail: state === "reduced" ? frozenTwoDetail : planDetail };
    options.post = async () => {
      options.detail = detailAfterRevalidation(state);
      return jsonResponse({ ...revalidateReceipt, commandRevision: 2, removedCount: 1 });
    };
    installStudyApi(options);
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Leé el alcance histórico y su estado efectivo sin reconstruirlo desde el mapa actual.");
    await user.click(screen.getByRole("button", { name: "Revalidar alcance" }));
    expect(await screen.findByRole("heading", { name: label, level: 2 })).toBeVisible();
    expect(screen.getByText("La selección fue reducida de forma conservadora.")).toBeVisible();
    expect(screen.queryByText(/agregado|reincorporado/u)).not.toBeInTheDocument();
  });

  it("creación completamente excluida sigue siendo éxito y navega a invalidado", async () => {
    window.location.hash = "#/study";
    installStudyApi({
      detail: {
        ...detailForState("invalidated"),
      },
    });
    const user = userEvent.setup();
    render(<App />);
    await reachReview(user);
    await user.click(screen.getByRole("button", { name: "Crear estudio" }));
    expect(await screen.findByRole("heading", { name: "Invalidado", level: 2 })).toBeVisible();
    expect(screen.queryByText(/falló la creación/u)).not.toBeInTheDocument();
  });
});
