import { describe, expect, it } from "vitest";
import { confidenceTone, formatBytes, initials } from "./utils";

describe("formatos de presentación", () => {
  it("presenta volumen sin perder la unidad", () => {
    expect(formatBytes(512)).toBe("512 B");
    expect(formatBytes(2048)).toBe("2.0 KB");
  });

  it("crea iniciales estables y tonos conservadores", () => {
    expect(initials("Diario Horizonte")).toBe("DH");
    expect(confidenceTone("Alta")).toBe("positive");
    expect(confidenceTone("Contradictoria")).toBe("critical");
  });
});
