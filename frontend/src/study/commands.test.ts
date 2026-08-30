import { afterEach, describe, expect, it, vi } from "vitest";
import { prepareCancel, prepareCreate, prepareRevalidate } from "./commands";
import { mapRevision, planId, sourceId } from "./test/fixtures";
import type { TemporalFilter } from "./types";

const uuids = [
  "12345678-1234-4234-8234-123456789abc",
  "22345678-1234-4234-8234-123456789abc",
  "32345678-1234-4234-8234-123456789abc",
];

describe("preparación CAS y replay", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("usa un UUID v4 distinto para cada comando nuevo", () => {
    const randomUUID = vi.fn()
      .mockReturnValueOnce(uuids[0])
      .mockReturnValueOnce(uuids[1])
      .mockReturnValueOnce(uuids[2]);
    vi.stubGlobal("crypto", { randomUUID });
    const create = prepareCreate({
      expectedMapRevision: mapRevision,
      expectedPolicyRevision: 7,
      disposition: "archive",
      targets: [{ kind: "source", targetId: sourceId }],
      temporalFilter: { kind: "all" },
      readState: "any",
      excludedLabelIds: [],
      keepLatestPerFlow: 0,
    });
    const revalidate = prepareRevalidate(planId, {
      expectedPlanRevision: 1,
      expectedMapRevision: mapRevision,
      expectedPolicyRevision: 7,
    });
    const cancel = prepareCancel(planId, { expectedPlanRevision: 1 });

    expect(JSON.parse(create.serializedBody)).toMatchObject({ commandId: uuids[0] });
    expect(JSON.parse(revalidate.serializedBody)).toMatchObject({ commandId: uuids[1] });
    expect(JSON.parse(cancel.serializedBody)).toMatchObject({ commandId: uuids[2] });
    expect(new Set([create.serializedBody, revalidate.serializedBody, cancel.serializedBody]).size).toBe(3);
  });

  it.each([
    { kind: "all" },
    { kind: "beforeDate", date: "2026-08-29" },
    { kind: "dateRange", onOrAfterDate: "2026-08-01", beforeDate: "2026-08-29" },
    { kind: "olderThanDays", days: 30 },
  ] as TemporalFilter[])("conserva la variante temporal $kind en el cuerpo exacto", (temporalFilter) => {
    vi.stubGlobal("crypto", { randomUUID: vi.fn(() => uuids[0]) });
    const command = prepareCreate({
      expectedMapRevision: mapRevision,
      expectedPolicyRevision: 7,
      disposition: "trash",
      targets: [{ kind: "source", targetId: sourceId }],
      temporalFilter,
      readState: "unread",
      excludedLabelIds: [],
      keepLatestPerFlow: 5,
    });
    expect(JSON.parse(command.serializedBody)).toEqual({
      commandId: uuids[0],
      expectedMapRevision: mapRevision,
      expectedPolicyRevision: 7,
      disposition: "trash",
      targets: [{ kind: "source", targetId: sourceId }],
      temporalFilter,
      readState: "unread",
      excludedLabelIds: [],
      keepLatestPerFlow: 5,
    });
  });

  it("mantiene ruta y cuerpo serializado para un replay exacto", () => {
    vi.stubGlobal("crypto", { randomUUID: vi.fn(() => uuids[0]) });
    const command = prepareCancel(planId, { expectedPlanRevision: 9 });
    const preserved = { ...command };
    expect(preserved.path).toBe(`/api/v3/study/plans/${planId}/cancel`);
    expect(preserved.serializedBody).toBe(command.serializedBody);
    expect(JSON.parse(preserved.serializedBody)).toEqual({
      commandId: uuids[0],
      expectedPlanRevision: 9,
    });
  });
});
