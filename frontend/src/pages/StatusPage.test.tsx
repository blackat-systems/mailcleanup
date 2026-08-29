import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { StatusPage } from "./StatusPage";
import type { SyncState, WorkspaceData } from "../types";
import {
  connection,
  context,
  decisionsResponse,
  indexResponse,
  mapResponse,
  sync,
} from "../test/fixtures";
import { syncLabels } from "../utils";

function workspace(state: SyncState, partial = state !== "completed"): WorkspaceData {
  const currentSync = {
    ...sync,
    state,
    partial,
    mode: state === "not_started" ? null : sync.mode,
    startedAt: state === "not_started" ? null : sync.startedAt,
    updatedAt: state === "not_started" ? null : sync.updatedAt,
    errorCode: state === "failed" ? "fixture_failure" : null,
  };
  return {
    context,
    connection,
    sync: currentSync,
    index: { ...indexResponse, partial },
    map: { ...mapResponse, sync: currentSync },
    decisions: decisionsResponse,
  };
}

describe("estado de sólo lectura", () => {
  it.each<SyncState>([
    "not_started",
    "running",
    "paused",
    "completed",
    "requires_full_resync",
    "failed",
  ])("presenta el estado de sincronización %s sin controles", (state) => {
    render(<StatusPage data={workspace(state)} />);

    expect(screen.getByText(syncLabels[state], { selector: ".disclosure-summary" })).toBeVisible();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    if (state === "completed") {
      expect(screen.getByText("Completo", { selector: ".status-summary strong" })).toBeVisible();
    } else {
      expect(screen.getAllByText("Mapa parcial")).not.toHaveLength(0);
    }
  });

  it("expone capacidades habilitadas y bloqueadas sin cambiar su semántica", async () => {
    const user = userEvent.setup();
    render(<StatusPage data={workspace("completed")} />);
    await user.click(screen.getByRole("heading", { name: "Puertas publicadas por C5" }));

    expect(screen.getByText("Lectura del mapa").previousElementSibling).toHaveTextContent("Disponible");
    expect(screen.getByText("Conexión a Gmail").previousElementSibling).toHaveTextContent("Bloqueada");
    expect(screen.getByText("Ejecución").previousElementSibling).toHaveTextContent("Bloqueada");
  });

  it("declara el estado parcial y nunca sugiere controlarlo", async () => {
    const user = userEvent.setup();
    render(<StatusPage data={workspace("running", true)} />);

    expect(screen.getAllByText("Mapa parcial")).not.toHaveLength(0);
    await user.click(screen.getByRole("heading", { name: "Contexto, índice y sincronización" }));
    expect(screen.getByText(/No hay botones para iniciar, pausar, reanudar o reconstruir/i)).toBeVisible();
  });
});
