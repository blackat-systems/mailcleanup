import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { currentRoute } from "./routing";
import type { SourceDetailResponse } from "./types";
import {
  connection,
  context,
  decisionsResponse,
  indexResponse,
  jsonResponse,
  mapResponse,
  sourceAId,
  sourceB,
  sourceBId,
  sourceDetail,
  sync,
  writeResponse,
} from "./test/fixtures";

type ApiOverrides = {
  context?: unknown;
  connection?: unknown;
  sync?: unknown;
  index?: unknown;
  map?: unknown;
  decisions?: unknown;
  source?: unknown;
  sourceRead?: (path: string) => Promise<Response>;
  error?: { path: string; status: number; code: string };
  transportPath?: string;
};

function installApi(overrides: ApiOverrides = {}) {
  const payloads: Record<string, unknown> = {
    "/api/v2/context": overrides.context ?? context,
    "/api/v2/connection": overrides.connection ?? connection,
    "/api/v2/sync": overrides.sync ?? sync,
    "/api/v2/index": overrides.index ?? indexResponse,
    "/api/v2/map": overrides.map ?? mapResponse,
    "/api/v2/decisions": overrides.decisions ?? decisionsResponse,
  };
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const path = String(input);
    if (path === overrides.transportPath) throw new TypeError("transporte local interrumpido");
    if (path === overrides.error?.path) {
      return jsonResponse({ error: { code: overrides.error.code, message: "mensaje servidor" } }, overrides.error.status);
    }
    if (path.startsWith("/api/v2/map/sources/")) {
      if (overrides.sourceRead) return overrides.sourceRead(path);
      return jsonResponse(overrides.source ?? sourceDetail);
    }
    const payload = payloads[path];
    return payload === undefined
      ? jsonResponse({ error: { code: "invalid_request", message: "Solicitud inválida" } }, 404)
      : jsonResponse(payload);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("enrutado local", () => {
  it("acepta sólo las rutas publicadas y decodifica IDs", () => {
    window.location.hash = `#/source/${encodeURIComponent("source/uno")}`;
    expect(currentRoute()).toEqual({ page: "source", key: "source", id: "source/uno" });
    window.location.hash = "#/sources?view=desconocida";
    expect(currentRoute()).toEqual({ page: "sources", key: "#/sources", view: "all" });
    window.location.hash = "#/study";
    expect(currentRoute()).toEqual({ page: "study", key: "#/study" });
    const planId = "cleanup-plan-v1-12345678-1234-4234-8234-123456789abc";
    window.location.hash = `#/study/plans/${planId}`;
    expect(currentRoute()).toEqual({ page: "study_plan", key: "#/study", planId });
    window.location.hash = "#/estudio";
    expect(currentRoute()).toEqual({ page: "not_found", key: "not_found" });
  });
});

describe("recorrido sintético de Mapa Total", () => {
  beforeEach(() => {
    window.location.hash = "#/";
    installApi();
  });

  it("coordina el contexto primero y después lee la fotografía", async () => {
    const fetchMock = installApi();
    render(<App />);

    expect(await screen.findByRole("heading", { name: "Mapa Total con datos de demostración" })).toBeVisible();
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/v2/context");
    expect(fetchMock).toHaveBeenCalledTimes(6);
    expect(screen.getByText("Demostración local sin acceso externo")).toBeVisible();
    expect(screen.getByText("Horizonte local")).toBeVisible();
  });

  it("descubre Estudio sin exponer Limpieza Controlada ni controles de ejecución", async () => {
    render(<App />);
    await screen.findByRole("heading", { name: "Mapa Total con datos de demostración" });

    expect(screen.getByRole("link", { name: "Estudio de Limpieza" })).toBeVisible();
    expect(screen.queryByText("Limpieza Controlada")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /conectar|sincronizar|ejecutar/i })).not.toBeInTheDocument();
    expect(screen.getByText(/Sin credenciales · sin conexión a Gmail/i)).toBeVisible();
  });

  it("bloquea toda la superficie si las capacidades no son sintéticas", async () => {
    installApi({
      context: {
        ...context,
        capabilities: { ...context.capabilities, realData: true },
      },
    });
    render(<App />);

    expect(await screen.findByRole("heading", { name: "Mapa Total bloqueado" })).toBeVisible();
    expect(screen.queryByRole("link", { name: "Correcciones" })).not.toBeInTheDocument();
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it("muestra un error recuperable ante una respuesta fuera de contrato", async () => {
    installApi({ map: { ...mapResponse, campoPrivado: "no permitido" } });
    render(<App />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "La API local devolvió una respuesta que no cumple el contrato.",
    );
    expect(screen.getByRole("button", { name: "Reintentar lectura" })).toBeEnabled();
  });

  it.each([
    ["map_unavailable", "El mapa sintético no está disponible."],
    ["account_unavailable", "La cuenta sintética de demostración no está disponible."],
  ])("presenta %s con retry explícito", async (code, message) => {
    installApi({ error: { path: "/api/v2/map", status: 503, code } });
    render(<App />);

    expect(await screen.findByRole("alert")).toHaveTextContent(message);
    expect(screen.getByRole("button", { name: "Reintentar lectura" })).toBeEnabled();
  });

  it("convierte un fallo de transporte en un error local sin filtrar detalles", async () => {
    installApi({ transportPath: "/api/v2/context" });
    render(<App />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "No pudimos comunicarnos con la API local.",
    );
    expect(screen.queryByText("transporte local interrumpido")).not.toBeInTheDocument();
  });

  it("rechaza una fotografía incoherente entre sync, índice y mapa", async () => {
    installApi({
      map: { ...mapResponse, sync: { ...mapResponse.sync, state: "running", partial: true } },
      index: { ...indexResponse, partial: true },
    });
    render(<App />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "La API local devolvió una respuesta que no cumple el contrato.",
    );
  });

  it("presenta el estado vacío sin inventar fuentes", async () => {
    installApi({
      map: {
        ...mapResponse,
        summary: {
          ...mapResponse.summary,
          messageCount: 0,
          sourceCount: 0,
          flowCount: 0,
          protectedMessageCount: 0,
          reviewRequiredMessageCount: 0,
          hardExcludedMessageCount: 0,
          totalBytes: 0,
          firstSeen: null,
          lastSeen: null,
        },
        sources: [],
      },
      index: { ...indexResponse, messageCount: 0 },
    });
    render(<App />);

    expect(await screen.findByText("El mapa está disponible, pero vacío")).toBeVisible();
    expect(screen.queryByText("Horizonte local")).not.toBeInTheDocument();
  });

  it("señala explícitamente una fotografía parcial", async () => {
    installApi({
      map: { ...mapResponse, sync: { ...mapResponse.sync, state: "running", partial: true } },
      sync: { ...sync, state: "running", partial: true },
      index: { ...indexResponse, partial: true },
    });
    render(<App />);

    expect(await screen.findAllByText("Mapa parcial")).not.toHaveLength(0);
  });

  it("filtra las vistas auxiliares sin convertirlas en entidades nuevas", async () => {
    window.location.hash = "#/sources?view=spam";
    render(<App />);

    expect(await screen.findByRole("heading", { name: "Spam" })).toBeVisible();
    expect(screen.getByText("Remitente aislado")).toBeVisible();
    expect(screen.queryByText("Nube Taller")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Fuentes" })).toHaveAttribute("aria-current", "page");
  });

  it("permite buscar por dominio y conserva filtros presentacionales", async () => {
    const user = userEvent.setup();
    window.location.hash = "#/sources";
    render(<App />);
    await screen.findByRole("heading", { name: "Fuentes y flujos" });

    await user.type(screen.getByRole("searchbox", { name: /Buscar fuente/i }), "nube-taller.example");
    expect(screen.getByText("Nube Taller")).toBeVisible();
    expect(screen.queryByText("Horizonte local")).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("1 fuente");
  });

  it("filtra por cada valor efectivo de protección sin inferir equivalencias", async () => {
    const user = userEvent.setup();
    window.location.hash = "#/sources";
    render(<App />);
    await screen.findByRole("heading", { name: "Fuentes y flujos" });
    await user.click(screen.getByText("Más filtros"));

    await user.selectOptions(
      screen.getByRole("combobox", { name: "Protección efectiva" }),
      "Elegida por el usuario",
    );
    expect(screen.getByText("Horizonte local")).toBeVisible();
    expect(screen.queryByText("Nube Taller")).not.toBeInTheDocument();
  });

  it("separa automático, efectivo, protección y evidencia en el detalle", async () => {
    const user = userEvent.setup();
    window.location.hash = `#/source/${encodeURIComponent(sourceAId)}`;
    render(<App />);

    expect(await screen.findByRole("heading", { name: "Horizonte local" })).toBeVisible();
    const securityFlow = screen.getByRole("heading", { name: "Alertas de seguridad" }).closest("article");
    expect(securityFlow).not.toBeNull();
    const securityBadges = securityFlow!.querySelector<HTMLElement>(".flow-card-heading .badge-row");
    expect(securityBadges).not.toBeNull();
    expect(within(securityBadges!).getByText("Revisión obligatoria")).toBeVisible();
    expect(within(securityBadges!).getByText("Protegido")).toBeVisible();
    expect(within(securityBadges!).getByText("Confianza contradictoria")).toBeVisible();
    const valuesHeading = screen.getByRole("heading", { name: "Valores automáticos y efectivos" });
    const valuesDisclosure = valuesHeading.closest("details");
    expect(valuesDisclosure).not.toHaveAttribute("open");
    await user.click(valuesHeading);
    const protectionHeading = screen.getByRole("heading", { name: "Protección de la fuente" });
    await user.click(protectionHeading);
    expect(screen.getAllByText("Resultado efectivo de reglas y decisiones locales").length)
      .toBeGreaterThan(0);
    await user.click(screen.getByRole("heading", { name: "Cómo se clasificó esta fuente" }));
    expect(screen.getByRole("heading", { name: "Evidencia automática" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Decisiones de Joa", level: 3 })).toBeVisible();
    expect(screen.getByText(/Sin contenido ni recursos remotos/)).toBeVisible();
    const protectedMessage = screen.getByText("Revisión de acceso de demostración").closest("summary");
    expect(protectedMessage).not.toBeNull();
    expect(within(protectedMessage!).getByText("Revisión obligatoria")).toBeVisible();
    expect(within(protectedMessage!).getByText("Protegido")).toBeVisible();
    expect(within(protectedMessage!).getByText("Confianza contradictoria")).toBeVisible();
  });

  it("mantiene la parcialidad visible dentro del detalle", async () => {
    window.location.hash = `#/source/${encodeURIComponent(sourceAId)}`;
    installApi({
      map: { ...mapResponse, sync: { ...mapResponse.sync, state: "running", partial: true } },
      sync: { ...sync, state: "running", partial: true },
      index: { ...indexResponse, partial: true },
    });
    render(<App />);

    expect(await screen.findByText("Mapa parcial.")).toBeVisible();
    expect(screen.getByText(/La pertenencia de esta fuente y sus conteos pueden cambiar/i)).toBeVisible();
  });

  it("no conserva datos de otra fuente mientras cambia el detalle", async () => {
    let resolveSecond: ((response: Response) => void) | undefined;
    const second = new Promise<Response>((resolve) => { resolveSecond = resolve; });
    const sourceBDetail: SourceDetailResponse = {
      ...sourceB,
      contractVersion: 1,
      dataMode: "synthetic",
      recentMessages: [],
    };
    window.location.hash = `#/source/${encodeURIComponent(sourceAId)}`;
    installApi({
      sourceRead: async (path) => path.endsWith(sourceAId) ? jsonResponse(sourceDetail) : second,
    });
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Horizonte local" })).toBeVisible();

    window.location.hash = `#/source/${encodeURIComponent(sourceBId)}`;
    window.dispatchEvent(new HashChangeEvent("hashchange"));

    expect(await screen.findByText("Leyendo fuente, flujos y evidencia…")).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Horizonte local" })).not.toBeInTheDocument();
    resolveSecond?.(jsonResponse(sourceBDetail));
    expect(await screen.findByRole("heading", { name: "Nube Taller" })).toBeVisible();
  });

  it("ofrece regreso seguro cuando la fuente ya no existe", async () => {
    window.location.hash = `#/source/${encodeURIComponent(sourceAId)}`;
    installApi({
      map: { ...mapResponse, sync: { ...mapResponse.sync, state: "running", partial: true } },
      sync: { ...sync, state: "running", partial: true },
      index: { ...indexResponse, partial: true },
      error: {
        path: `/api/v2/map/sources/${sourceAId}`,
        status: 404,
        code: "source_not_found",
      },
    });
    render(<App />);

    expect(await screen.findByText("Fuente inexistente")).toBeVisible();
    expect(screen.getByText("Mapa parcial.")).toBeVisible();
    expect(screen.getByRole("link", { name: "Volver a fuentes" })).toHaveAttribute("href", "#/sources");
    expect(screen.queryByRole("button", { name: "Reintentar lectura" })).not.toBeInTheDocument();
  });

  it("acepta un replay original con revisiones avanzadas y renueva el estado completo", async () => {
    const user = userEvent.setup();
    const advancedSync = {
      ...sync,
      processedCount: 6,
      updatedAt: "2026-08-27T20:02:00Z",
    };
    const advancedMap = {
      ...mapResponse,
      mapRevision: `map-v1-${"c".repeat(64)}`,
      policyRevision: 9,
      sync: {
        state: advancedSync.state,
        mode: advancedSync.mode,
        processedCount: advancedSync.processedCount,
        startedAt: advancedSync.startedAt,
        updatedAt: advancedSync.updatedAt,
        errorCode: advancedSync.errorCode,
        partial: advancedSync.partial,
      },
      summary: { ...mapResponse.summary, messageCount: 6 },
    };
    const advancedIndex = { ...indexResponse, messageCount: 6 };
    const advancedDecisions = { ...decisionsResponse, policyRevision: 9 };
    let advanced = false;
    let postAttempts = 0;
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (init?.method === "POST") {
        postAttempts += 1;
        if (postAttempts === 1) {
          advanced = true;
          throw new TypeError("resultado incierto");
        }
        return jsonResponse({ ...writeResponse, replayed: true });
      }
      const payloads: Record<string, unknown> = {
        "/api/v2/context": context,
        "/api/v2/connection": connection,
        "/api/v2/sync": advanced ? advancedSync : sync,
        "/api/v2/index": advanced ? advancedIndex : indexResponse,
        "/api/v2/map": advanced ? advancedMap : mapResponse,
        "/api/v2/decisions": advanced ? advancedDecisions : decisionsResponse,
      };
      const payload = payloads[path];
      return payload === undefined
        ? jsonResponse({ error: { code: "invalid_request", message: "Solicitud inválida" } }, 404)
        : jsonResponse(payload);
    });
    vi.stubGlobal("fetch", fetchMock);
    window.location.hash = "#/corrections";
    render(<App />);

    expect(await screen.findByRole("heading", { name: "Correcciones reversibles" })).toBeVisible();
    await user.type(screen.getByRole("textbox", { name: "Nuevo nombre" }), "Nombre confirmado");
    await user.click(screen.getByRole("button", { name: "Registrar corrección" }));
    await user.click(await screen.findByRole("checkbox", { name: /Confirmo que no cambié/i }));
    await user.click(screen.getByRole("button", { name: "Reintentar exactamente el mismo envío" }));

    expect(await screen.findByText(/replay exacto/i)).toBeVisible();
    expect(postAttempts).toBe(2);
    const lastPost = fetchMock.mock.calls.map(([, init]) => init?.method).lastIndexOf("POST");
    expect(fetchMock.mock.calls.slice(lastPost + 1).map(([input]) => String(input))).toEqual([
      "/api/v2/context",
      "/api/v2/connection",
      "/api/v2/sync",
      "/api/v2/index",
      "/api/v2/map",
      "/api/v2/decisions",
    ]);

    await user.click(screen.getByRole("link", { name: "Estado" }));
    await user.click(await screen.findByRole("heading", { name: "Contexto, índice y sincronización" }));
    const indexCard = (await screen.findByRole("heading", { name: "Fixture sintético" })).closest("section");
    const syncCard = screen.getByRole("heading", { name: "Completado" }).closest("section");
    expect(indexCard).not.toBeNull();
    expect(syncCard).not.toBeNull();
    expect(within(indexCard!).getByText("6")).toBeVisible();
    expect(within(syncCard!).getByText("6")).toBeVisible();
  });

  it("cierra el menú con Escape y devuelve el foco", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByRole("heading", { name: "Mapa Total con datos de demostración" });
    const menu = screen.getByRole("button", { name: "Abrir navegación" });

    await user.click(menu);
    expect(screen.getByRole("button", { name: "Cerrar navegación" })).toHaveAttribute("aria-expanded", "true");
    expect(document.getElementById("main-content")).toHaveAttribute("inert");
    await user.keyboard("{Escape}");
    expect(screen.getByRole("button", { name: "Abrir navegación" })).toHaveFocus();
    expect(document.getElementById("main-content")).not.toHaveAttribute("inert");
  });

  it("mueve el foco al contenido también al navegar desde escritorio", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByRole("heading", { name: "Mapa Total con datos de demostración" });

    await user.click(screen.getByRole("link", { name: "Fuentes" }));

    expect(await screen.findByRole("heading", { name: "Fuentes y flujos" })).toBeVisible();
    await waitFor(() => expect(document.getElementById("main-content")).toHaveFocus());
  });

  it("mueve el foco al contenido al elegir una ruta del menú móvil", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByRole("heading", { name: "Mapa Total con datos de demostración" });
    await user.click(screen.getByRole("button", { name: "Abrir navegación" }));
    await user.click(screen.getByRole("link", { name: "Fuentes" }));

    expect(await screen.findByRole("heading", { name: "Fuentes y flujos" })).toBeVisible();
    expect(document.getElementById("main-content")).toHaveFocus();
  });
});
