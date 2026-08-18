import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { dashboard, preview, source } from "./test/fixtures";

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("recorrido principal", () => {
  beforeEach(() => {
    window.location.hash = "#/";
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const path = String(input);
        if (path === "/api/v1/dashboard") return jsonResponse(dashboard);
        if (path.startsWith("/api/v1/sources?")) return jsonResponse([source]);
        if (path === "/api/v1/history") return jsonResponse([]);
        if (path === "/api/v1/plans/preview") return jsonResponse(preview, 201);
        return jsonResponse({ detail: "No encontrado" }, 404);
      }),
    );
  });

  it("expone el modo sintético y el panorama", async () => {
    render(<App />);
    expect(await screen.findByRole("heading", { name: /convertida en un mapa/i })).toBeVisible();
    expect(screen.getByText("Modo sintético")).toBeVisible();
    expect(screen.getByText("0 credenciales · 0 conexiones externas · 0 acciones sobre correos")).toBeVisible();
    expect(screen.getByText("Diario Horizonte")).toBeVisible();
  });

  it("selecciona una fuente y genera sólo una simulación", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Diario Horizonte");
    await user.click(screen.getByRole("checkbox", { name: /sumar al plan/i }));
    await user.click(screen.getByRole("link", { name: /^estudio de limpieza/i }));

    expect(await screen.findByRole("heading", { name: /decidir con una vista previa/i })).toBeVisible();
    expect(screen.getByText("Ejecución bloqueada")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Crear vista previa" }));

    expect(await screen.findByText("mensajes incluidos")).toBeVisible();
    expect(screen.getByText("Base Segura no contiene un botón de ejecutar.")).toBeVisible();
  });
});
