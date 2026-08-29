import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useState } from "react";
import { CorrectionsPage } from "./CorrectionsPage";
import {
  decisionsResponse,
  flowA1Id,
  flowA2Id,
  jsonResponse,
  mapResponse,
  sourceA,
  sourceAId,
  sourceB,
  sourceBId,
  sourceDetail,
  writeResponse,
} from "../test/fixtures";

type PostBehavior = (path: string, init: RequestInit) => Promise<Response>;
type ReadBehavior = (path: string) => Promise<Response>;

function installCorrectionsApi(
  post: PostBehavior = async () => jsonResponse(writeResponse),
  read: ReadBehavior = async () => jsonResponse(sourceDetail),
) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (init?.method === "POST") return post(path, init);
    if (path.startsWith("/api/v2/map/sources/")) return read(path);
    return jsonResponse({ error: { code: "invalid_request", message: "Solicitud inválida" } }, 404);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

async function openHistory(user: ReturnType<typeof userEvent.setup>) {
  const heading = screen.getByRole("heading", { name: "Historial de decisiones" });
  const disclosure = heading.closest("details");
  if (!(disclosure instanceof HTMLDetailsElement)) throw new Error("Falta historial desplegable");
  if (!disclosure.open) await user.click(heading);
}

afterEach(() => vi.unstubAllGlobals());

describe("editor de las siete correcciones", () => {
  it("publica exactamente los siete tipos autorizados", () => {
    installCorrectionsApi();
    render(
      <CorrectionsPage
        map={mapResponse}
        decisions={decisionsResponse}
        refreshProjection={vi.fn()}
      />,
    );

    const select = screen.getByRole("combobox", { name: "Tipo de corrección" });
    expect(within(select).getAllByRole("option").map((option) => option.textContent)).toEqual([
      "Cambiar nombre de fuente",
      "Cambiar rubro de fuente",
      "Cambiar nombre de flujo",
      "Cambiar intención de flujo",
      "Unir fuentes",
      "Separar una fuente",
      "Proteger un objetivo",
    ]);
  });

  it("inicializa rubro e intención desde el objetivo elegido", async () => {
    const user = userEvent.setup();
    installCorrectionsApi();
    render(
      <CorrectionsPage
        map={mapResponse}
        decisions={decisionsResponse}
        initialSourceId={sourceBId}
        refreshProjection={vi.fn()}
      />,
    );

    await user.selectOptions(
      screen.getByRole("combobox", { name: "Tipo de corrección" }),
      "setSourceRubro",
    );
    expect(screen.getByRole("combobox", { name: "Fuente" })).toHaveValue(sourceBId);
    expect(screen.getByRole("combobox", { name: "Rubro efectivo" }))
      .toHaveValue(sourceB.effectiveRubro);
    await user.selectOptions(screen.getByRole("combobox", { name: "Fuente" }), sourceAId);
    expect(screen.getByRole("combobox", { name: "Rubro efectivo" }))
      .toHaveValue(sourceA.effectiveRubro);

    await user.selectOptions(
      screen.getByRole("combobox", { name: "Tipo de corrección" }),
      "setFlowIntention",
    );
    expect(screen.getByRole("combobox", { name: "Intención efectiva" }))
      .toHaveValue(sourceA.flows[0]!.effectiveIntention);
    await user.selectOptions(screen.getByRole("combobox", { name: "Flujo" }), flowA2Id);
    expect(screen.getByRole("combobox", { name: "Intención efectiva" }))
      .toHaveValue(sourceA.flows[1]!.effectiveIntention);
  });

  it("desambigua nombres duplicados con IDs públicos en texto y accesibilidad", async () => {
    const user = userEvent.setup();
    const duplicateName = "Objetivo duplicado";
    const duplicateFlows = sourceA.flows.map((flow) => ({
      ...flow,
      effectiveDisplayName: duplicateName,
    }));
    installCorrectionsApi();
    render(
      <CorrectionsPage
        map={{
          ...mapResponse,
          sources: [
            { ...sourceA, effectiveDisplayName: duplicateName, flows: duplicateFlows },
            { ...sourceB, effectiveDisplayName: duplicateName },
          ],
        }}
        decisions={decisionsResponse}
        refreshProjection={vi.fn()}
      />,
    );

    const sourceOptions = within(screen.getByRole("combobox", { name: "Fuente" }))
      .getAllByRole("option").map((option) => option.textContent)
      .filter((label) => label?.startsWith(duplicateName));
    expect(sourceOptions).toHaveLength(2);
    expect(sourceOptions[0]).not.toBe(sourceOptions[1]);
    const sourceField = screen.getByRole("combobox", { name: "Fuente" }).closest(".field-with-id");
    if (!(sourceField instanceof HTMLElement)) throw new Error("Falta campo de fuente");
    expect(within(sourceField).getByLabelText(`Ver ID completo ${sourceAId}`)).toBeVisible();

    await user.selectOptions(
      screen.getByRole("combobox", { name: "Tipo de corrección" }),
      "partitionSource",
    );
    const groupControls = screen.getAllByRole("combobox", {
      name: /Grupo para Objetivo duplicado, ID/,
    });
    expect(groupControls).toHaveLength(2);
    expect(groupControls[0]).not.toHaveAccessibleName(groupControls[1]!.getAttribute("aria-label")!);
  });

  it("registra una corrección y relee mapa e historial antes de confirmar", async () => {
    const user = userEvent.setup();
    const refreshProjection = vi.fn(async () => undefined);
    const fetchMock = installCorrectionsApi();
    render(
      <CorrectionsPage
        map={mapResponse}
        decisions={decisionsResponse}
        refreshProjection={refreshProjection}
      />,
    );

    await user.type(screen.getByRole("textbox", { name: "Nuevo nombre" }), "  Horizonte   claro  ");
    await user.click(screen.getByRole("button", { name: "Registrar corrección" }));

    expect(await screen.findByText(/Corrección aplicada/i)).toBeVisible();
    expect(refreshProjection).toHaveBeenCalledTimes(1);
    expect(refreshProjection).toHaveBeenCalledWith();
    const postCall = fetchMock.mock.calls.find(([, init]) => init?.method === "POST");
    const body = JSON.parse(String(postCall?.[1]?.body)) as Record<string, unknown>;
    expect(body).toMatchObject({
      type: "setSourceDisplayName",
      sourceId: sourceAId,
      displayName: "Horizonte claro",
      expectedMapRevision: mapResponse.mapRevision,
      expectedPolicyRevision: mapResponse.policyRevision,
      supersedesDecisionIds: [],
    });
  });

  it("distingue visualmente decisiones del mismo tipo por sus objetivos públicos", async () => {
    const user = userEvent.setup();
    const first = decisionsResponse.events.find((event) => event.type === "setSourceRubro");
    if (!first || first.type !== "setSourceRubro") throw new Error("Falta fixture setSourceRubro");
    const second = {
      ...first,
      decisionId: "88888888-8888-4888-8888-888888888888",
      commandId: "99999999-9999-4999-8999-999999999999",
      revision: first.revision + 20,
      sourceId: sourceBId,
      currentTargetIds: [sourceBId],
    };
    render(
      <CorrectionsPage
        map={mapResponse}
        decisions={{ ...decisionsResponse, events: [first, second] }}
        refreshProjection={vi.fn(async () => undefined)}
      />,
    );
    await openHistory(user);

    const history = screen.getByLabelText("Historial de correcciones");
    expect(within(history).getByText("Fuente actual: Horizonte local")).toBeVisible();
    expect(within(history).getByText("Fuente actual: Nube Taller")).toBeVisible();
    expect(within(history).getByLabelText(`Ver ID completo ${sourceAId}`)).toBeVisible();
    expect(within(history).getByLabelText(`Ver ID completo ${sourceBId}`)).toBeVisible();
  });

  it("delega al contrato el límite Unicode del nombre sin recortarlo por UTF-16", () => {
    render(
      <CorrectionsPage
        map={mapResponse}
        decisions={decisionsResponse}
        refreshProjection={vi.fn(async () => undefined)}
      />,
    );

    expect(screen.getByRole("textbox", { name: "Nuevo nombre" })).not.toHaveAttribute("maxlength");
  });

  it("bloquea doble submit mientras la escritura está pendiente", async () => {
    const user = userEvent.setup();
    let resolvePost: ((response: Response) => void) | undefined;
    const pendingResponse = new Promise<Response>((resolve) => { resolvePost = resolve; });
    let postCount = 0;
    installCorrectionsApi(async () => {
      postCount += 1;
      return pendingResponse;
    });
    render(
      <CorrectionsPage
        map={mapResponse}
        decisions={decisionsResponse}
        refreshProjection={vi.fn(async () => undefined)}
      />,
    );

    const input = screen.getByRole("textbox", { name: "Nuevo nombre" });
    await user.type(input, "Horizonte");
    const submit = screen.getByRole("button", { name: "Registrar corrección" });
    await user.click(submit);
    expect(screen.getByRole("button", { name: "Registrando…" })).toBeDisabled();
    expect(input).toBeDisabled();
    expect(screen.getByRole("status")).toHaveTextContent("Registrando corrección.");
    await user.click(screen.getByRole("button", { name: "Registrando…" }));
    expect(postCount).toBe(1);
    resolvePost?.(jsonResponse(writeResponse));
    expect(await screen.findByText(/Corrección aplicada/i)).toBeVisible();
  });

  it.each([
    ["map_revision_conflict", 409],
    ["policy_revision_conflict", 409],
    ["command_id_conflict", 409],
    ["policy_conflict", 409],
    ["invalid_transition", 409],
    ["target_not_found", 422],
    ["unsupported_target", 422],
  ])("conserva el formulario y exige refresh explícito ante %s", async (code, status) => {
    const user = userEvent.setup();
    const refreshProjection = vi.fn(async () => undefined);
    installCorrectionsApi(async () => jsonResponse({
      error: { code, message: "detalle privado" },
    }, status));
    render(
      <CorrectionsPage
        map={mapResponse}
        decisions={decisionsResponse}
        refreshProjection={refreshProjection}
      />,
    );

    const input = screen.getByRole("textbox", { name: "Nuevo nombre" });
    await user.type(input, "Nombre conservado");
    await user.click(screen.getByRole("button", { name: "Registrar corrección" }));

    expect(await screen.findByText(/El formulario se conserva/i)).toBeVisible();
    expect(input).toHaveValue("Nombre conservado");
    expect(screen.getByRole("button", { name: "Registrar corrección" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Actualizar vista sin reenviar" }));
    await waitFor(() => expect(refreshProjection).toHaveBeenCalledTimes(1));
    expect(screen.getByRole("button", { name: "Registrar corrección" })).toBeEnabled();
  });

  it("exige reselección si el objetivo desaparece después de un conflicto", async () => {
    const user = userEvent.setup();
    let postCount = 0;
    installCorrectionsApi(async () => {
      postCount += 1;
      return jsonResponse({
        error: { code: "map_revision_conflict", message: "detalle privado" },
      }, 409);
    });

    function Harness() {
      const [currentMap, setCurrentMap] = useState(mapResponse);
      return (
        <CorrectionsPage
          map={currentMap}
          decisions={decisionsResponse}
          refreshProjection={async () => {
            setCurrentMap((current) => ({
              ...current,
              sources: current.sources.filter((source) => source.id !== sourceAId),
            }));
          }}
        />
      );
    }

    render(<Harness />);
    await user.type(screen.getByRole("textbox", { name: "Nuevo nombre" }), "Objetivo original");
    await user.click(screen.getByRole("button", { name: "Registrar corrección" }));
    await user.click(await screen.findByRole("button", { name: "Actualizar vista sin reenviar" }));

    expect(screen.getByRole("combobox", { name: "Fuente" })).toHaveValue("");
    await user.click(screen.getByRole("button", { name: "Registrar corrección" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Elegí una fuente.");
    expect(postCount).toBe(1);
  });

  it("mantiene el bloqueo si falla la lectura posterior a un conflicto", async () => {
    const user = userEvent.setup();
    installCorrectionsApi(async () => jsonResponse({
      error: { code: "policy_revision_conflict", message: "detalle privado" },
    }, 409));
    render(
      <CorrectionsPage
        map={mapResponse}
        decisions={decisionsResponse}
        refreshProjection={vi.fn(async () => { throw new TypeError("lectura fallida"); })}
      />,
    );
    await openHistory(user);

    await user.type(screen.getByRole("textbox", { name: "Nuevo nombre" }), "Conservar");
    await user.click(screen.getByRole("button", { name: "Registrar corrección" }));
    await user.click(await screen.findByRole("button", { name: "Actualizar vista sin reenviar" }));

    expect(await screen.findByRole("button", { name: "Actualizar vista sin reenviar" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Registrar corrección" })).toBeDisabled();
    for (const button of screen.getAllByRole("button", { name: /Deshacer/i })) {
      expect(button).toBeDisabled();
    }
  });

  it("repite exactamente el mismo cuerpo sólo tras confirmación", async () => {
    const user = userEvent.setup();
    const bodies: string[] = [];
    let attempt = 0;
    installCorrectionsApi(async (_path, init) => {
      bodies.push(String(init.body));
      attempt += 1;
      if (attempt === 1) throw new TypeError("resultado incierto");
      return jsonResponse({ ...writeResponse, replayed: true });
    });
    render(
      <CorrectionsPage
        map={mapResponse}
        decisions={decisionsResponse}
        refreshProjection={vi.fn(async () => undefined)}
      />,
    );

    await user.type(screen.getByRole("textbox", { name: "Nuevo nombre" }), "Mismo cuerpo");
    await user.click(screen.getByRole("button", { name: "Registrar corrección" }));
    expect(await screen.findByRole("heading", { name: /Retry idempotente/i })).toBeVisible();
    const retry = screen.getByRole("button", { name: "Reintentar exactamente el mismo envío" });
    expect(retry).toBeDisabled();
    await user.click(screen.getByRole("checkbox", { name: /Confirmo que no cambié/i }));
    await user.click(retry);

    expect(await screen.findByText(/replay exacto/i)).toBeVisible();
    expect(bodies).toHaveLength(2);
    expect(bodies[1]).toBe(bodies[0]);
  });

  it("no reutiliza el retry si el borrador cambió", async () => {
    const user = userEvent.setup();
    installCorrectionsApi(async () => { throw new TypeError("resultado incierto"); });
    render(
      <CorrectionsPage
        map={mapResponse}
        decisions={decisionsResponse}
        refreshProjection={vi.fn(async () => undefined)}
      />,
    );

    const input = screen.getByRole("textbox", { name: "Nuevo nombre" });
    await user.type(input, "Primero");
    await user.click(screen.getByRole("button", { name: "Registrar corrección" }));
    await screen.findByRole("heading", { name: /Retry idempotente/i });
    await user.type(input, " cambiado");

    expect(screen.getByText(/El formulario cambió/i)).toBeVisible();
    expect(screen.queryByRole("checkbox", { name: /Confirmo que no cambié/i })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Registrar corrección" })).toBeEnabled();
  });

  it("exige asignación manual total para separar una fuente", async () => {
    const user = userEvent.setup();
    const fetchMock = installCorrectionsApi();
    render(
      <CorrectionsPage
        map={mapResponse}
        decisions={decisionsResponse}
        refreshProjection={vi.fn(async () => undefined)}
      />,
    );

    await user.selectOptions(
      screen.getByRole("combobox", { name: "Tipo de corrección" }),
      "partitionSource",
    );
    await user.click(screen.getByRole("button", { name: "Registrar corrección" }));
    expect(await screen.findByText(/dos grupos no vacíos/i)).toBeVisible();
    expect(fetchMock.mock.calls.some(([, init]) => init?.method === "POST")).toBe(false);

    await user.selectOptions(screen.getByRole("combobox", { name: /Grupo para Noticias para el equipo/ }), "1");
    await user.selectOptions(screen.getByRole("combobox", { name: /Grupo para Alertas de seguridad/ }), "2");
    await user.click(screen.getByRole("button", { name: "Registrar corrección" }));
    await screen.findByText(/Corrección aplicada/i);
    const postCall = fetchMock.mock.calls.find(([, init]) => init?.method === "POST");
    const body = JSON.parse(String(postCall?.[1]?.body)) as Record<string, unknown>;
    expect(body).toMatchObject({
      type: "partitionSource",
      sourceId: sourceAId,
      groups: [
        { anchors: [{ kind: "flow", flowId: flowA1Id }] },
        { anchors: [{ kind: "flow", flowId: flowA2Id }] },
      ],
    });
  });

  it("permite hasta un grupo por flujo sin imponer un techo de cinco", async () => {
    const user = userEvent.setup();
    const flows = Array.from({ length: 6 }, (_, index) => ({
      ...sourceA.flows[0]!,
      id: `effective-flow-v1-${String(index + 1).repeat(24)}`,
      automaticFlowId: `automatic-flow-${index + 1}`,
      effectiveDisplayName: `Flujo ${index + 1}`,
    }));
    installCorrectionsApi();
    render(
      <CorrectionsPage
        map={{ ...mapResponse, sources: [{ ...sourceA, flows, flowCount: flows.length }] }}
        decisions={decisionsResponse}
        refreshProjection={vi.fn(async () => undefined)}
      />,
    );

    await user.selectOptions(screen.getByRole("combobox", { name: "Tipo de corrección" }), "partitionSource");
    const groupCount = screen.getByRole("combobox", { name: "Cantidad de grupos" });
    expect(within(groupCount).getByRole("option", { name: "6" })).toBeVisible();
    await user.selectOptions(groupCount, "6");
    expect(groupCount).toHaveValue("6");
  });

  it("deshace sólo eventos marcados undoable y usa la ruta cerrada", async () => {
    const user = userEvent.setup();
    const fetchMock = installCorrectionsApi();
    const first = decisionsResponse.events[0]!;
    render(
      <CorrectionsPage
        map={mapResponse}
        decisions={{
          ...decisionsResponse,
          events: [{ ...first, undoable: false }, decisionsResponse.events[1]!],
        }}
        refreshProjection={vi.fn(async () => undefined)}
      />,
    );
    await openHistory(user);

    expect(screen.getAllByRole("button", { name: /Deshacer/i })).toHaveLength(1);
    await user.click(screen.getByRole("button", { name: /Deshacer/i }));
    expect(await screen.findByText(/Corrección deshecha/i)).toBeVisible();
    const postCall = fetchMock.mock.calls.find(([, init]) => init?.method === "POST");
    expect(postCall?.[0]).toBe(`/api/v2/decisions/${decisionsResponse.events[1]!.decisionId}/undo`);
    const body = JSON.parse(String(postCall?.[1]?.body)) as Record<string, unknown>;
    expect(Object.keys(body).sort()).toEqual([
      "commandId",
      "expectedMapRevision",
      "expectedPolicyRevision",
      "occurredAt",
    ]);
  });

  it("limita la unión a candidatos estructurales", async () => {
    const user = userEvent.setup();
    const fetchMock = installCorrectionsApi();
    render(
      <CorrectionsPage
        map={mapResponse}
        decisions={decisionsResponse}
        refreshProjection={vi.fn(async () => undefined)}
      />,
    );

    await user.selectOptions(screen.getByRole("combobox", { name: "Tipo de corrección" }), "mergeSources");
    await user.click(screen.getByRole("checkbox", { name: /Seleccionar Horizonte local.*para unir/ }));
    await user.click(screen.getByRole("checkbox", { name: /Seleccionar Nube Taller.*para unir/ }));
    await user.click(screen.getByRole("button", { name: "Registrar corrección" }));
    await screen.findByText(/Corrección aplicada/i);
    const postCall = fetchMock.mock.calls.find(([, init]) => init?.method === "POST");
    const body = JSON.parse(String(postCall?.[1]?.body)) as Record<string, unknown>;
    expect(body).toMatchObject({ type: "mergeSources", sourceIds: [sourceAId, sourceBId] });
  });

  it("no pide metadatos de detalle hasta elegir mensaje o etiqueta", async () => {
    const user = userEvent.setup();
    const fetchMock = installCorrectionsApi();
    render(
      <CorrectionsPage
        map={mapResponse}
        decisions={decisionsResponse}
        refreshProjection={vi.fn(async () => undefined)}
      />,
    );

    await Promise.resolve();
    expect(fetchMock).not.toHaveBeenCalled();
    await user.selectOptions(screen.getByRole("combobox", { name: "Tipo de corrección" }), "protectTarget");
    await user.selectOptions(screen.getByRole("combobox", { name: "Tipo de objetivo" }), "flow");
    await Promise.resolve();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("permite reintentar la lectura mínima de objetivos de mensaje", async () => {
    const user = userEvent.setup();
    let readAttempt = 0;
    installCorrectionsApi(undefined, async () => {
      readAttempt += 1;
      return readAttempt === 1
        ? jsonResponse({ error: { code: "source_not_found", message: "detalle privado" } }, 404)
        : jsonResponse(sourceDetail);
    });
    render(
      <CorrectionsPage
        map={mapResponse}
        decisions={decisionsResponse}
        refreshProjection={vi.fn(async () => undefined)}
      />,
    );

    await user.selectOptions(screen.getByRole("combobox", { name: "Tipo de corrección" }), "protectTarget");
    await user.selectOptions(screen.getByRole("combobox", { name: "Tipo de objetivo" }), "message");
    expect(await screen.findByRole("button", { name: "Reintentar lectura de objetivos" })).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Reintentar lectura de objetivos" }));
    expect(await screen.findByRole("combobox", { name: "Objetivo publicado" })).toBeVisible();
    expect(readAttempt).toBe(2);
  });

  it("mantiene el historial vacío como un estado explícito", async () => {
    const user = userEvent.setup();
    installCorrectionsApi();
    render(
      <CorrectionsPage
        map={mapResponse}
        decisions={{ ...decisionsResponse, events: [] }}
        refreshProjection={vi.fn(async () => undefined)}
      />,
    );
    await openHistory(user);

    expect(screen.getByText("Historial vacío")).toBeVisible();
  });

  it("explica los cuatro bindings que requieren revisión", () => {
    installCorrectionsApi();
    render(
      <CorrectionsPage
        map={mapResponse}
        decisions={decisionsResponse}
        refreshProjection={vi.fn(async () => undefined)}
      />,
    );

    expect(screen.getByText(/Necesita revisión · requiere revisión/i)).toBeVisible();
    expect(screen.getByText(/Sin objetivo vigente · requiere revisión/i)).toBeVisible();
    expect(screen.getByText(/Objetivo ambiguo · requiere revisión/i)).toBeVisible();
    expect(screen.getByText(/En conflicto · requiere revisión/i)).toBeVisible();
  });

  it("conserva undo operativo aunque el mapa no tenga fuentes", async () => {
    const user = userEvent.setup();
    const fetchMock = installCorrectionsApi();
    render(
      <CorrectionsPage
        map={{ ...mapResponse, sources: [] }}
        decisions={{ ...decisionsResponse, events: [decisionsResponse.events[0]!] }}
        refreshProjection={vi.fn(async () => undefined)}
      />,
    );

    expect(screen.getByText("Mapa vacío")).toBeVisible();
    expect(screen.queryByRole("button", { name: "Registrar corrección" })).not.toBeInTheDocument();
    await openHistory(user);
    await user.click(screen.getByRole("button", { name: /Deshacer Nombre de fuente/i }));
    expect(await screen.findByText(/Corrección deshecha/i)).toBeVisible();
    expect(fetchMock.mock.calls.some(([, init]) => init?.method === "POST")).toBe(true);
  });

  it("mantiene undo pendiente, bloquea el historial y confirma replay", async () => {
    const user = userEvent.setup();
    let resolvePost: ((response: Response) => void) | undefined;
    const pendingResponse = new Promise<Response>((resolve) => { resolvePost = resolve; });
    installCorrectionsApi(async () => pendingResponse);
    render(
      <CorrectionsPage
        map={mapResponse}
        decisions={decisionsResponse}
        refreshProjection={vi.fn(async () => undefined)}
      />,
    );
    await openHistory(user);

    await user.click(screen.getAllByRole("button", { name: /Deshacer/i })[0]!);
    expect(screen.getByText("Deshaciendo…")).toBeVisible();
    expect(screen.getByRole("status")).toHaveTextContent("Deshaciendo corrección.");
    expect(screen.getByRole("button", { name: /Deshaciendo Nombre de fuente/i })).toHaveAttribute("aria-busy", "true");
    for (const button of screen.getAllByRole("button", { name: /Deshacer/i })) {
      expect(button).toBeDisabled();
    }
    resolvePost?.(jsonResponse({ ...writeResponse, replayed: true }));
    expect(await screen.findByText(/Corrección deshecha/i)).toBeVisible();
    expect(screen.getByText(/replay exacto/i)).toBeVisible();
  });

  it("conserva undo sin reenvío automático ante conflicto", async () => {
    const user = userEvent.setup();
    installCorrectionsApi(async () => jsonResponse({
      error: { code: "policy_revision_conflict", message: "detalle privado" },
    }, 409));
    render(
      <CorrectionsPage
        map={mapResponse}
        decisions={decisionsResponse}
        refreshProjection={vi.fn(async () => undefined)}
      />,
    );
    await openHistory(user);

    await user.click(screen.getAllByRole("button", { name: /Deshacer/i })[0]!);
    expect(await screen.findByText(/El formulario se conserva/i)).toBeVisible();
    expect(screen.getByRole("button", { name: "Actualizar vista sin reenviar" })).toBeEnabled();
    expect(screen.queryByRole("heading", { name: /Retry idempotente/i })).not.toBeInTheDocument();
  });

  it("invalida el retry si hubo una edición aunque el valor vuelva al original", async () => {
    const user = userEvent.setup();
    installCorrectionsApi(async () => { throw new TypeError("resultado incierto"); });
    render(
      <CorrectionsPage
        map={mapResponse}
        decisions={decisionsResponse}
        refreshProjection={vi.fn(async () => undefined)}
      />,
    );

    const input = screen.getByRole("textbox", { name: "Nuevo nombre" });
    await user.type(input, "Original");
    await user.click(screen.getByRole("button", { name: "Registrar corrección" }));
    await screen.findByRole("heading", { name: /Retry idempotente/i });
    await user.type(input, "x");
    await user.keyboard("{Backspace}");

    expect(input).toHaveValue("Original");
    expect(screen.getByText(/El formulario cambió/i)).toBeVisible();
    expect(screen.queryByRole("checkbox", { name: /Confirmo que no cambié/i })).not.toBeInTheDocument();
  });

  it("retira el retry cuando la repetición recibe un conflicto definitivo", async () => {
    const user = userEvent.setup();
    let attempt = 0;
    installCorrectionsApi(async () => {
      attempt += 1;
      if (attempt === 1) throw new TypeError("resultado incierto");
      return jsonResponse({
        error: { code: "command_id_conflict", message: "detalle privado" },
      }, 409);
    });
    render(
      <CorrectionsPage
        map={mapResponse}
        decisions={decisionsResponse}
        refreshProjection={vi.fn(async () => undefined)}
      />,
    );

    await user.type(screen.getByRole("textbox", { name: "Nuevo nombre" }), "Retry final");
    await user.click(screen.getByRole("button", { name: "Registrar corrección" }));
    await user.click(await screen.findByRole("checkbox", { name: /Confirmo que no cambié/i }));
    await user.click(screen.getByRole("button", { name: "Reintentar exactamente el mismo envío" }));

    expect(await screen.findByRole("button", { name: "Actualizar vista sin reenviar" })).toBeVisible();
    expect(screen.queryByRole("heading", { name: /Retry idempotente/i })).not.toBeInTheDocument();
  });

  it("no conserva retry si la escritura fue confirmada y falla sólo la relectura", async () => {
    const user = userEvent.setup();
    let attempt = 0;
    installCorrectionsApi(async () => {
      attempt += 1;
      if (attempt === 1) throw new TypeError("resultado incierto");
      return jsonResponse(writeResponse);
    });
    render(
      <CorrectionsPage
        map={mapResponse}
        decisions={decisionsResponse}
        refreshProjection={vi.fn(async () => { throw new TypeError("lectura fallida"); })}
      />,
    );
    await openHistory(user);

    await user.type(screen.getByRole("textbox", { name: "Nuevo nombre" }), "Aplicada");
    await user.click(screen.getByRole("button", { name: "Registrar corrección" }));
    await user.click(await screen.findByRole("checkbox", { name: /Confirmo que no cambié/i }));
    await user.click(screen.getByRole("button", { name: "Reintentar exactamente el mismo envío" }));

    expect(await screen.findByText(/La escritura fue confirmada/i)).toBeVisible();
    expect(screen.getByText(/No vuelvas a enviar la corrección/i)).toBeVisible();
    expect(screen.queryByRole("heading", { name: /Retry idempotente/i })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Registrar corrección" })).toBeDisabled();
    for (const button of screen.getAllByRole("button", { name: /Deshacer/i })) {
      expect(button).toBeDisabled();
    }
    await user.click(screen.getByRole("button", { name: "Reintentar sólo la lectura" }));
    expect(await screen.findByText(/No vuelvas a enviar la corrección/i)).toBeVisible();
    expect(screen.getByRole("button", { name: "Registrar corrección" })).toBeDisabled();
  });
});
