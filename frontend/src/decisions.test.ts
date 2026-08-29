import { describe, expect, it } from "vitest";
import {
  buildDecisionRequest,
  buildUndoRequest,
  DECISION_LIMITS,
  isStructuralCandidate,
  normalizeDisplayName,
  sameDraft,
  type DecisionDraft,
} from "./decisions";
import type { DecisionRequest, ProtectionTarget } from "./types";
import {
  flowA1Id,
  flowA2Id,
  mapResponse,
  sourceA,
  sourceAId,
  sourceBId,
  sourceCId,
} from "./test/fixtures";

function successful(draft: DecisionDraft): DecisionRequest {
  const result = buildDecisionRequest(draft, mapResponse);
  expect(result.ok).toBe(true);
  if (!result.ok) throw new Error(result.message);
  return result.body;
}

function expectCommonMetadata(body: DecisionRequest) {
  expect(body.commandId).toMatch(/^[0-9a-f-]{36}$/iu);
  expect(body.decisionId).toMatch(/^[0-9a-f-]{36}$/iu);
  expect(Number.isNaN(Date.parse(body.occurredAt))).toBe(false);
  expect(body.expectedMapRevision).toBe(mapResponse.mapRevision);
  expect(body.expectedPolicyRevision).toBe(mapResponse.policyRevision);
  expect(body.supersedesDecisionIds).toEqual([]);
}

describe("siete comandos D5 cerrados", () => {
  it("normaliza y limita nombres visibles a 1–120 caracteres", () => {
    expect(normalizeDisplayName("  Horizonte   local  ")).toBe("Horizonte local");
    expect(normalizeDisplayName(" ")).toBeNull();
    expect(normalizeDisplayName("x".repeat(120))).toHaveLength(120);
    expect(normalizeDisplayName("x".repeat(121))).toBeNull();
    expect(normalizeDisplayName("😀".repeat(120))).toBe("😀".repeat(120));
    expect(normalizeDisplayName("😀".repeat(121))).toBeNull();
  });

  it("construye setSourceDisplayName sin campos adicionales", () => {
    const body = successful({
      type: "setSourceDisplayName",
      sourceId: sourceAId,
      displayName: "  Horizonte   claro ",
    });
    expectCommonMetadata(body);
    expect(body).toMatchObject({
      type: "setSourceDisplayName",
      sourceId: sourceAId,
      displayName: "Horizonte claro",
    });
    expect(Object.keys(body).sort()).toEqual([
      "commandId",
      "decisionId",
      "displayName",
      "expectedMapRevision",
      "expectedPolicyRevision",
      "occurredAt",
      "sourceId",
      "supersedesDecisionIds",
      "type",
    ]);
  });

  it("construye setSourceRubro", () => {
    expect(successful({
      type: "setSourceRubro",
      sourceId: sourceAId,
      rubro: "Salud y gobierno",
    })).toMatchObject({
      type: "setSourceRubro",
      sourceId: sourceAId,
      rubro: "Salud y gobierno",
    });
  });

  it("construye setFlowDisplayName", () => {
    expect(successful({
      type: "setFlowDisplayName",
      flowId: flowA1Id,
      displayName: "Alertas internas",
    })).toMatchObject({
      type: "setFlowDisplayName",
      flowId: flowA1Id,
      displayName: "Alertas internas",
    });
  });

  it("construye setFlowIntention", () => {
    expect(successful({
      type: "setFlowIntention",
      flowId: flowA1Id,
      intention: "Seguridad",
    })).toMatchObject({ type: "setFlowIntention", flowId: flowA1Id, intention: "Seguridad" });
  });

  it("canoniza mergeSources y exige dos fuentes", () => {
    const valid = successful({
      type: "mergeSources",
      sourceIds: [sourceCId, sourceAId, sourceAId, sourceBId],
    });
    expect(valid).toMatchObject({
      type: "mergeSources",
      sourceIds: [sourceAId, sourceBId, sourceCId],
    });
    expect(buildDecisionRequest({ type: "mergeSources", sourceIds: [sourceAId] }, mapResponse))
      .toEqual({ ok: false, message: "Elegí al menos dos fuentes estructurales." });
  });

  it("respeta el máximo contractual de fuentes por unión", () => {
    const sourceIds = Array.from(
      { length: DECISION_LIMITS.mergeSources + 1 },
      (_, index) => `effective-source-v1-${index.toString(16).padStart(24, "0")}`,
    );
    expect(buildDecisionRequest({ type: "mergeSources", sourceIds }, mapResponse)).toEqual({
      ok: false,
      message: "Una unión admite como máximo 100 fuentes.",
    });
  });

  it("serializa partitionSource con anchors públicos de flujo", () => {
    const body = successful({
      type: "partitionSource",
      sourceId: sourceAId,
      groups: [[flowA2Id], [flowA1Id]],
      expectedFlowIds: [flowA1Id, flowA2Id],
    });
    expect(body).toMatchObject({
      type: "partitionSource",
      sourceId: sourceAId,
      groups: [
        { anchors: [{ kind: "flow", flowId: flowA2Id }] },
        { anchors: [{ kind: "flow", flowId: flowA1Id }] },
      ],
    });
  });

  it("rechaza grupos vacíos, duplicados o cobertura incompleta", () => {
    const invalidDrafts: DecisionDraft[] = [
      {
        type: "partitionSource",
        sourceId: sourceAId,
        groups: [[flowA1Id], []],
        expectedFlowIds: [flowA1Id, flowA2Id],
      },
      {
        type: "partitionSource",
        sourceId: sourceAId,
        groups: [[flowA1Id], [flowA1Id]],
        expectedFlowIds: [flowA1Id, flowA2Id],
      },
      {
        type: "partitionSource",
        sourceId: sourceAId,
        groups: [[flowA1Id], [flowA2Id]],
        expectedFlowIds: [flowA1Id, flowA2Id, "otro"],
      },
    ];
    for (const draft of invalidDrafts) {
      expect(buildDecisionRequest(draft, mapResponse).ok).toBe(false);
    }
  });

  it("respeta los máximos contractuales de grupos y anclas de partición", () => {
    const tooManyGroups = Array.from(
      { length: DECISION_LIMITS.partitionGroups + 1 },
      (_, index) => [`flow-${index}`],
    );
    expect(buildDecisionRequest({
      type: "partitionSource",
      sourceId: sourceAId,
      groups: tooManyGroups,
      expectedFlowIds: tooManyGroups.flat(),
    }, mapResponse)).toMatchObject({ ok: false });

    const tooManyAnchors = Array.from(
      { length: DECISION_LIMITS.partitionAnchors + 1 },
      (_, index) => `flow-${index}`,
    );
    expect(buildDecisionRequest({
      type: "partitionSource",
      sourceId: sourceAId,
      groups: [tooManyAnchors.slice(0, 500), tooManyAnchors.slice(500)],
      expectedFlowIds: tooManyAnchors,
    }, mapResponse)).toEqual({
      ok: false,
      message: "La fuente debe publicar hasta 1.000 flujos únicos para separarla.",
    });
  });

  it.each<ProtectionTarget>([
    { kind: "source", sourceId: sourceAId },
    { kind: "flow", flowId: flowA1Id },
    { kind: "message", messageId: "message-v1-uno" },
    { kind: "sender", senderAddress: "demo@ejemplo.example" },
    { kind: "label", labelId: "STARRED" },
  ])("conserva exactamente un objetivo protectTarget de tipo $kind", (target) => {
    expect(successful({ type: "protectTarget", target })).toMatchObject({
      type: "protectTarget",
      target,
    });
  });
});

describe("revisiones, candidatos y retry", () => {
  it("crea IDs nuevos en comandos nuevos", () => {
    const first = successful({ type: "setSourceRubro", sourceId: sourceAId, rubro: "Personal" });
    const second = successful({ type: "setSourceRubro", sourceId: sourceAId, rubro: "Personal" });
    expect(first.commandId).not.toBe(second.commandId);
    expect(first.decisionId).not.toBe(second.decisionId);
  });

  it("construye undo sólo con metadata de comando", () => {
    const body = buildUndoRequest(mapResponse);
    expect(Object.keys(body).sort()).toEqual([
      "commandId",
      "expectedMapRevision",
      "expectedPolicyRevision",
      "occurredAt",
    ]);
    expect(body.expectedMapRevision).toBe(mapResponse.mapRevision);
    expect(body.expectedPolicyRevision).toBe(mapResponse.policyRevision);
  });

  it("limita unión y separación a fuentes estructurales elegibles", () => {
    expect(isStructuralCandidate(sourceA)).toBe(true);
    expect(isStructuralCandidate({ ...sourceA, automaticSourceIds: ["a", "b"] })).toBe(false);
    expect(isStructuralCandidate({ ...sourceA, structuralDecisionIds: ["decision"] })).toBe(false);
  });

  it("detecta si el borrador de un retry sigue idéntico", () => {
    const draft: DecisionDraft = { type: "setSourceRubro", sourceId: sourceAId, rubro: "Personal" };
    const changed: DecisionDraft = {
      type: "setSourceRubro",
      sourceId: sourceAId,
      rubro: "Desconocido",
    };
    expect(sameDraft(draft, { ...draft })).toBe(true);
    expect(sameDraft(draft, changed)).toBe(false);
  });
});
