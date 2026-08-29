import type {
  DecisionRequest,
  Intencion,
  MapResponse,
  ProtectionTarget,
  Rubro,
  SourceProjection,
  UndoRequest,
} from "./types";

export type DecisionDraft =
  | { type: "setSourceDisplayName"; sourceId: string; displayName: string }
  | { type: "setSourceRubro"; sourceId: string; rubro: Rubro }
  | { type: "setFlowDisplayName"; flowId: string; displayName: string }
  | { type: "setFlowIntention"; flowId: string; intention: Intencion }
  | { type: "mergeSources"; sourceIds: readonly string[] }
  | {
      type: "partitionSource";
      sourceId: string;
      groups: readonly (readonly string[])[];
      expectedFlowIds: readonly string[];
    }
  | { type: "protectTarget"; target: ProtectionTarget };

export type BuildResult =
  | { ok: true; body: DecisionRequest }
  | { ok: false; message: string };

export const DECISION_LIMITS = {
  mergeSources: 100,
  partitionGroups: 100,
  partitionAnchors: 1_000,
} as const;

function metadata(map: MapResponse) {
  return {
    commandId: crypto.randomUUID(),
    decisionId: crypto.randomUUID(),
    occurredAt: new Date().toISOString(),
    expectedMapRevision: map.mapRevision,
    expectedPolicyRevision: map.policyRevision,
    supersedesDecisionIds: [] as const,
  };
}

export function normalizeDisplayName(value: string): string | null {
  const normalized = value.trim().split(/\s+/u).filter(Boolean).join(" ");
  const length = Array.from(normalized).length;
  return length >= 1 && length <= 120 ? normalized : null;
}

function canonical(values: readonly string[]): string[] {
  return [...new Set(values)].sort();
}

export function buildDecisionRequest(draft: DecisionDraft, map: MapResponse): BuildResult {
  const common = metadata(map);
  switch (draft.type) {
    case "setSourceDisplayName": {
      const displayName = normalizeDisplayName(draft.displayName);
      if (!displayName) {
        return { ok: false, message: "El nombre debe tener entre 1 y 120 caracteres." };
      }
      return {
        ok: true,
        body: { ...common, type: draft.type, sourceId: draft.sourceId, displayName },
      };
    }
    case "setSourceRubro":
      return {
        ok: true,
        body: { ...common, type: draft.type, sourceId: draft.sourceId, rubro: draft.rubro },
      };
    case "setFlowDisplayName": {
      const displayName = normalizeDisplayName(draft.displayName);
      if (!displayName) {
        return { ok: false, message: "El nombre debe tener entre 1 y 120 caracteres." };
      }
      return {
        ok: true,
        body: { ...common, type: draft.type, flowId: draft.flowId, displayName },
      };
    }
    case "setFlowIntention":
      return {
        ok: true,
        body: { ...common, type: draft.type, flowId: draft.flowId, intention: draft.intention },
      };
    case "mergeSources": {
      const sourceIds = canonical(draft.sourceIds);
      if (sourceIds.length < 2) {
        return { ok: false, message: "Elegí al menos dos fuentes estructurales." };
      }
      if (sourceIds.length > DECISION_LIMITS.mergeSources) {
        return { ok: false, message: "Una unión admite como máximo 100 fuentes." };
      }
      return { ok: true, body: { ...common, type: draft.type, sourceIds } };
    }
    case "partitionSource": {
      const groups = draft.groups.map(canonical);
      if (groups.length < 2 || groups.some((group) => group.length === 0)) {
        return { ok: false, message: "La separación necesita al menos dos grupos no vacíos." };
      }
      if (groups.length > DECISION_LIMITS.partitionGroups) {
        return { ok: false, message: "Una separación admite como máximo 100 grupos." };
      }
      const assigned = canonical(groups.flat());
      const expected = canonical(draft.expectedFlowIds);
      if (
        expected.length !== draft.expectedFlowIds.length ||
        expected.length > DECISION_LIMITS.partitionAnchors
      ) {
        return {
          ok: false,
          message: "La fuente debe publicar hasta 1.000 flujos únicos para separarla.",
        };
      }
      if (
        assigned.length !== groups.reduce((total, group) => total + group.length, 0) ||
        assigned.length !== expected.length ||
        assigned.some((flowId, index) => flowId !== expected[index])
      ) {
        return {
          ok: false,
          message: "Cada flujo debe aparecer una sola vez y todos deben quedar cubiertos.",
        };
      }
      return {
        ok: true,
        body: {
          ...common,
          type: draft.type,
          sourceId: draft.sourceId,
          groups: groups.map((flowIds) => ({
            anchors: flowIds.map((flowId) => ({ kind: "flow" as const, flowId })),
          })),
        },
      };
    }
    case "protectTarget":
      return { ok: true, body: { ...common, type: draft.type, target: draft.target } };
  }
}

export function buildUndoRequest(map: MapResponse): UndoRequest {
  return {
    commandId: crypto.randomUUID(),
    occurredAt: new Date().toISOString(),
    expectedMapRevision: map.mapRevision,
    expectedPolicyRevision: map.policyRevision,
  };
}

export function isStructuralCandidate(source: SourceProjection): boolean {
  return source.automaticSourceIds.length === 1 && source.structuralDecisionIds.length === 0;
}

export function sameDraft(left: DecisionDraft, right: DecisionDraft): boolean {
  return JSON.stringify(left) === JSON.stringify(right);
}
