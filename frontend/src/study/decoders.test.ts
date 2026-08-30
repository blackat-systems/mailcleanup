import { describe, expect, it } from "vitest";
import {
  decodeStudyError,
  isCancelReceipt,
  isCreateReceipt,
  isEventsResponse,
  isMessagesResponse,
  isPlanDetail,
  isPlansResponse,
  isRevalidateReceipt,
  isStudyContext,
  isTargetsResponse,
  isTemporalFilter,
} from "./decoders";
import {
  INVENTORY_STATES,
  PLAN_STATES,
  STUDY_ERROR_CODES,
  WARNING_CODES,
  type StudyErrorCode,
} from "./types";
import {
  eventsResponse,
  detailAfterRevalidation,
  detailForState,
  messagesResponse,
  planDetail,
  planId,
  plansResponse,
  studyContext,
  studyError,
  targetsResponse,
  createReceipt,
  revalidateReceipt,
  cancelReceipt,
} from "./test/fixtures";

const errorStatus: Record<StudyErrorCode, number> = {
  invalid_request: 400,
  invalid_cursor: 400,
  invalid_local_origin: 403,
  route_not_found: 404,
  target_not_found: 404,
  plan_not_found: 404,
  method_not_allowed: 405,
  map_revision_conflict: 409,
  policy_revision_conflict: 409,
  plan_revision_conflict: 409,
  command_id_conflict: 409,
  cursor_stale: 409,
  invalid_transition: 409,
  plan_expired: 409,
  payload_too_large: 413,
  plan_too_large: 413,
  json_required: 415,
  unsupported_target: 422,
  invalid_filter: 422,
  study_unavailable: 503,
  inventory_incomplete: 503,
  account_unavailable: 503,
  internal_error: 500,
};

describe("decodificadores cerrados de Estudio", () => {
  it("acepta el contexto exacto y rechaza capacidades, límites y campos extra", () => {
    expect(isStudyContext(studyContext)).toBe(true);
    expect(isStudyContext({ ...studyContext, extra: true })).toBe(false);
    expect(isStudyContext({
      ...studyContext,
      capabilities: { ...studyContext.capabilities, execute: true },
    })).toBe(false);
    expect(isStudyContext({
      ...studyContext,
      limits: { ...studyContext.limits, maxTargets: 99 },
    })).toBe(false);
    expect(isStudyContext({
      ...studyContext,
      availability: { ...studyContext.availability, currentPolicyRevision: 0 },
    })).toBe(true);
  });

  it.each(INVENTORY_STATES)("acepta el estado de inventario %s con disponibilidad coherente", (inventoryState) => {
    const completed = inventoryState === "completed";
    const context = completed ? studyContext : {
      ...studyContext,
      availability: {
        ...studyContext.availability,
        inventoryState,
        completeSnapshotAvailable: false,
        currentMapRevision: null,
        currentPolicyRevision: null,
        targetReadAvailable: false,
        planCreateAvailable: false,
        planRevalidateAvailable: false,
        blockerCodes: ["inventory_incomplete"],
      },
    };
    expect(isStudyContext(context)).toBe(true);
  });

  it("acepta cuenta ausente y composición bloqueada sin degradar el contrato", () => {
    expect(isStudyContext({
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
    })).toBe(true);
    expect(isStudyContext({
      ...studyContext,
      availability: {
        ...studyContext.availability,
        completeSnapshotAvailable: false,
        currentMapRevision: null,
        currentPolicyRevision: null,
        targetReadAvailable: false,
        planCreateAvailable: false,
        planRevalidateAvailable: false,
        blockerCodes: ["study_unavailable"],
      },
    })).toBe(true);
  });

  it("valida catálogo, orden, IDs, unicidad y enteros sin aceptar booleanos", () => {
    expect(isTargetsResponse(targetsResponse)).toBe(true);
    expect(isTargetsResponse({ ...targetsResponse, items: [...targetsResponse.items].reverse() })).toBe(false);
    expect(isTargetsResponse({ ...targetsResponse, items: [...targetsResponse.items, targetsResponse.items[0]] })).toBe(false);
    expect(isTargetsResponse({ ...targetsResponse, items: [{ ...targetsResponse.items[0], messageCount: true }] })).toBe(false);
    expect(isTargetsResponse({ ...targetsResponse, nextCursor: " ".repeat(2) })).toBe(false);
    expect(isTargetsResponse({ ...targetsResponse, policyRevision: 0 })).toBe(true);
    expect(isTargetsResponse({
      ...targetsResponse,
      items: targetsResponse.items.map((item) => item.kind === "sender" ? { ...item, displayAddress: ["persona", "invalid.invalid"].join("@") } : item),
    })).toBe(false);
  });

  it("reproduce el casefold completo y el desempate por puntos de código del backend", () => {
    const first = { ...targetsResponse.items[0]!, displayName: "ſource" };
    const second = {
      ...targetsResponse.items[0]!,
      targetId: `effective-source-v1-${"b".repeat(24)}`,
      displayName: "target",
    };
    expect(isTargetsResponse({ ...targetsResponse, items: [first, second] })).toBe(true);
    expect(isTargetsResponse({ ...targetsResponse, items: [second, first] })).toBe(false);
  });

  it.each([
    { kind: "all" },
    { kind: "beforeDate", date: "2026-08-29" },
    { kind: "dateRange", onOrAfterDate: "2026-08-01", beforeDate: "2026-08-29" },
    { kind: "olderThanDays", days: 30 },
  ])("acepta la variante temporal cerrada $kind", (value) => {
    expect(isTemporalFilter(value)).toBe(true);
  });

  it("rechaza fechas no canónicas, rangos invertidos y variantes temporales abiertas", () => {
    expect(isTemporalFilter({ kind: "beforeDate", date: "2026-02-30" })).toBe(false);
    expect(isTemporalFilter({ kind: "dateRange", onOrAfterDate: "2026-08-29", beforeDate: "2026-08-29" })).toBe(false);
    expect(isTemporalFilter({ kind: "olderThanDays", days: true })).toBe(false);
    expect(isTemporalFilter({ kind: "all", date: "2026-08-29" })).toBe(false);
    expect(isTemporalFilter({ kind: "beforeDate", date: "0001-01-01" })).toBe(true);
    expect(isTemporalFilter({ kind: "beforeDate", date: "0000-01-01" })).toBe(false);
  });

  it("conserva orden temporal de microsegundos sin reducirlo a milisegundos", () => {
    const later = {
      ...plansResponse.items[0]!,
      planId: "cleanup-plan-v1-12345678-1234-4234-8234-123456789abd",
      createdAt: "2026-08-29T12:00:00.000002Z",
      expiresAt: "2026-08-30T12:00:00.000002Z",
    };
    const earlier = {
      ...plansResponse.items[0]!,
      planId,
      createdAt: "2026-08-29T12:00:00.000001Z",
      expiresAt: "2026-08-30T12:00:00.000001Z",
    };
    expect(isPlansResponse({ ...plansResponse, items: [later, earlier] })).toBe(true);
    expect(isMessagesResponse({
      ...messagesResponse,
      items: [
        { ...messagesResponse.items[0]!, messageId: `message-v1-${"b".repeat(64)}`, receivedAt: later.createdAt },
        { ...messagesResponse.items[0]!, messageId: `message-v1-${"a".repeat(64)}`, receivedAt: earlier.createdAt },
      ],
    })).toBe(true);
  });

  it.each(PLAN_STATES)("acepta el estado de plan %s en historia", (state) => {
    const disposition = state === "frozen" ? "archive" : "trash";
    const storageEffect = disposition === "archive" ? "none" : "not_guaranteed";
    const selectedAtCreationCount = state === "reduced" ? 2 : 1;
    const selectedAtCreationSizeEstimateBytes = state === "reduced" ? 4096 : 2048;
    const currentEligibleCount = state === "invalidated" ? 0 : 1;
    const currentEligibleSizeEstimateBytes = state === "invalidated" ? 0 : 2048;
    expect(isPlansResponse({
      ...plansResponse,
      listingAsOf: state === "expired" ? "2026-08-30T12:00:00Z" : plansResponse.listingAsOf,
      state,
      items: [{
        ...plansResponse.items[0], state, disposition, storageEffect,
        selectedAtCreationCount, selectedAtCreationSizeEstimateBytes,
        currentEligibleCount, currentEligibleSizeEstimateBytes,
      }],
    })).toBe(true);
  });

  it("valida detalle, muestras, warnings ordenados y respuesta sin campos extra", () => {
    expect(isPlanDetail(planDetail)).toBe(true);
    expect(isPlanDetail({ ...planDetail, accountKey: "privado" })).toBe(false);
    expect(isPlanDetail({ ...planDetail, warnings: WARNING_CODES })).toBe(false);
    expect(isPlanDetail({
      ...planDetail,
      currentMapRevision: null,
      currentPolicyRevision: null,
      warnings: ["current_snapshot_unavailable"],
    })).toBe(true);
    expect(isPlanDetail({
      ...planDetail,
      currentMapRevision: `map-v1-${"b".repeat(64)}`,
      currentPolicyRevision: 8,
      warnings: ["map_changed_since_creation", "policy_changed_since_creation"],
    })).toBe(true);
    expect(isPlanDetail({ ...planDetail, warnings: ["selection_reduced", "current_snapshot_unavailable"] })).toBe(false);
    expect(isPlanDetail({ ...planDetail, warnings: ["selection_reduced", "selection_reduced"] })).toBe(false);
    expect(isPlanDetail({
      ...planDetail,
      includedSamples: [{ ...planDetail.includedSamples[0], exclusionReasons: ["starred"] }],
    })).toBe(false);
    expect(isPlanDetail({
      ...planDetail,
      includedSamples: [{ ...planDetail.includedSamples[0], senderAddress: ["persona", "invalid.invalid"].join("@") }],
    })).toBe(false);
    expect(isPlanDetail({
      ...planDetail,
      createdFromPolicyRevision: 0,
      currentPolicyRevision: 0,
      recentEvents: planDetail.recentEvents.map((event) => ({ ...event, observedPolicyRevision: 0 })),
    })).toBe(true);
  });

  it("acepta hasta cinco muestras por colección y rechaza la sexta", () => {
    const base = planDetail.includedSamples[0]!;
    const samples = Array.from({ length: 6 }, (_value, index) => ({
      ...base,
      messageId: `message-v1-${index.toString(16).padStart(64, "0")}`,
      receivedAt: new Date(Date.parse(base.receivedAt) - index * 60_000).toISOString(),
    }));
    const withSamples = (count: number) => ({
      ...planDetail,
      selectedAtCreationCount: count,
      selectedAtCreationSizeEstimateBytes: count * 2048,
      currentEligibleCount: count,
      currentEligibleSizeEstimateBytes: count * 2048,
      includedSamples: samples.slice(0, count),
      recentEvents: [{ ...planDetail.recentEvents[0]!, remainingCount: count }],
    });
    expect(isPlanDetail(withSamples(5))).toBe(true);
    expect(isPlanDetail(withSamples(6))).toBe(false);
  });

  it("rechaza motivos duplicados o desordenados en miembros", () => {
    const removed = {
      ...messagesResponse,
      state: "removed",
      items: [{
        ...messagesResponse.items[0],
        currentState: "removed",
        reasonCodes: ["starred", "protection_changed"],
      }],
    };
    expect(isMessagesResponse(removed)).toBe(true);
    expect(isMessagesResponse({
      ...removed,
      items: [{ ...removed.items[0], reasonCodes: ["protection_changed", "starred"] }],
    })).toBe(false);
    expect(isMessagesResponse({
      ...removed,
      items: [{ ...removed.items[0], reasonCodes: ["starred", "starred"] }],
    })).toBe(false);
    expect(isMessagesResponse({
      ...removed,
      items: [{ ...removed.items[0], reasonCodes: ["missing_after_creation"] }],
    })).toBe(true);
    expect(isMessagesResponse({
      ...removed,
      items: [{ ...removed.items[0], reasonCodes: ["missing_after_creation", "scope_changed"] }],
    })).toBe(false);
  });

  it("valida eventos ascendentes completos y rechaza expired como evento", () => {
    expect(isEventsResponse(eventsResponse)).toBe(true);
    expect(isEventsResponse({
      ...eventsResponse,
      items: [{ ...eventsResponse.items[0], state: "expired" }],
    })).toBe(false);
  });

  it("rechaza huecos, revivir terminales y aritmética incoherente del ledger", () => {
    const revalidated = detailAfterRevalidation("frozen");
    const ascending = [...revalidated.recentEvents].reverse();
    expect(isEventsResponse({ ...eventsResponse, planRevision: 2, items: ascending })).toBe(true);
    expect(isEventsResponse({
      ...eventsResponse,
      planRevision: 3,
      items: [ascending[0]!, { ...ascending[1]!, revision: 3 }],
    })).toBe(false);
    expect(isEventsResponse({
      ...eventsResponse,
      planRevision: 3,
      items: [
        ascending[0]!,
        {
          revision: 2, type: "cancelled", recordedAt: "2026-08-29T13:00:00Z", state: "cancelled",
          observedMapRevision: null, observedPolicyRevision: null, removedCount: 0, remainingCount: 1,
        },
        { ...ascending[1]!, revision: 3, recordedAt: "2026-08-29T14:00:00Z" },
      ],
    })).toBe(false);
    const reduced = detailForState("reduced");
    expect(isPlanDetail({
      ...reduced,
      selectedAtCreationCount: 3,
      selectedAtCreationSizeEstimateBytes: 6144,
      recentEvents: [reduced.recentEvents[0]!, { ...reduced.recentEvents[1]!, remainingCount: 3 }],
    })).toBe(false);
  });

  it("liga el encabezado, la última revalidación y la ventana reciente al ledger", () => {
    const revalidated = detailAfterRevalidation("frozen");
    expect(isPlanDetail(revalidated)).toBe(true);
    expect(isPlanDetail({ ...planDetail, lastRevalidatedAt: "2026-08-29T13:00:00Z" })).toBe(false);
    expect(isPlanDetail({
      ...planDetail,
      recentEvents: [{ ...planDetail.recentEvents[0]!, observedPolicyRevision: 8 }],
    })).toBe(false);
    expect(isPlanDetail({ ...revalidated, recentEvents: [revalidated.recentEvents[0]!] })).toBe(false);
  });

  it("mantiene recibos cerrados y revisiones propias de cada comando", () => {
    expect(isCreateReceipt(createReceipt)).toBe(true);
    expect(isRevalidateReceipt(revalidateReceipt)).toBe(true);
    expect(isCancelReceipt(cancelReceipt)).toBe(true);
    expect(isCreateReceipt({ ...createReceipt, extra: true })).toBe(false);
    expect(isCreateReceipt({ ...createReceipt, commandRevision: 2 })).toBe(false);
    expect(isRevalidateReceipt({ ...revalidateReceipt, commandRevision: true })).toBe(false);
    expect(isRevalidateReceipt({ ...revalidateReceipt, removedCount: -1 })).toBe(false);
    expect(isCancelReceipt({ ...cancelReceipt, removedCount: 0 })).toBe(false);
  });

  it.each(STUDY_ERROR_CODES)("acepta el error público exacto %s", (code) => {
    expect(decodeStudyError(studyError(code), errorStatus[code])).toBe(code);
    expect(decodeStudyError(studyError(code), 418)).toBeNull();
  });

  it("rechaza mensajes remotos alterados y campos extra en errores", () => {
    expect(decodeStudyError({
      ...studyError("invalid_request"),
      error: { code: "invalid_request", message: "detalle remoto" },
    }, 400)).toBeNull();
    expect(decodeStudyError({ ...studyError("invalid_request"), trace: "privada" }, 400)).toBeNull();
  });
});
