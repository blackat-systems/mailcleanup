import { describe, expect, it } from "vitest";

import appSource from "../App.tsx?raw";
import shellSource from "../components/Shell.tsx?raw";
import apiSource from "./api.ts?raw";
import commandsSource from "./commands.ts?raw";
import commandMemorySource from "./commandMemory.ts?raw";
import decodersSource from "./decoders.ts?raw";
import hooksSource from "./hooks.ts?raw";
import presentersSource from "./presenters.ts?raw";
import studyApplicationSource from "./StudyApplication.tsx?raw";
import typesSource from "./types.ts?raw";
import studyPageSource from "./pages/StudyPage.tsx?raw";
import studyPlanPageSource from "./pages/StudyPlanPage.tsx?raw";
import routingSource from "../routing.ts?raw";
import stylesSource from "../styles.css?raw";

const runtimeSource = [
  appSource,
  shellSource,
  apiSource,
  commandsSource,
  commandMemorySource,
  decodersSource,
  hooksSource,
  presentersSource,
  typesSource,
  studyApplicationSource,
  studyPageSource,
  studyPlanPageSource,
  routingSource,
  stylesSource,
].join("\n");

describe("barrera sintética del frontend de Estudio", () => {
  it("no incorpora red externa, persistencia del navegador ni HTML peligroso", () => {
    expect(runtimeSource).not.toMatch(/https?:\/\//u);
    expect(runtimeSource).not.toMatch(/\b(?:localStorage|sessionStorage|indexedDB|WebSocket|EventSource|BroadcastChannel|SharedWorker|Worker|sendBeacon|serviceWorker|CacheStorage|caches)\b/u);
    expect(runtimeSource).not.toContain("dangerouslySetInnerHTML");
    expect(runtimeSource).not.toMatch(/\b(?:window\.open|document\.cookie)\b/u);
  });

  it("mantiene una frontera HTTP relativa sin v1 ni lecturas v2 adicionales", () => {
    expect(apiSource).not.toContain("/api/v1");
    expect(apiSource).not.toMatch(/\/api\/v2\/(?!context\b)/u);
    expect(apiSource).not.toContain("Authorization");
    expect(apiSource).toContain('credentials: "omit"');
    expect(apiSource).toContain('mode: "same-origin"');
    expect(apiSource).toContain('redirect: "error"');
  });

  it("no expone aprobación, ejecución ni una puerta D9", () => {
    expect(runtimeSource).not.toMatch(/\b(?:Aprobar|Ejecutar|Archivar ahora|Mover a Papelera ahora|Desuscribir)\b/u);
    expect(runtimeSource).not.toMatch(/\bD9\b/u);
    expect(runtimeSource).not.toContain("Limpieza Controlada");
    expect(runtimeSource).toContain("Vista previa sin efectos; no modifica Gmail");
  });

  it("no registra metadatos ni errores crudos", () => {
    expect(runtimeSource).not.toMatch(/\bconsole\.(?:log|debug|info|warn|error)\b/u);
  });
});
