import type { Dispatch, SetStateAction } from "react";
import type {
  CancelReceipt,
  CreatePlanRequest,
  CreateReceipt,
  PlanDetail,
  PreparedCommand,
  RevalidateReceipt,
} from "./types";

export type CreateCommandDraft = Omit<CreatePlanRequest, "commandId"> & {
  targetLabels: { kind: "source" | "flow" | "sender"; targetId: string; label: string }[];
  excludedLabelLabels: { targetId: string; label: string }[];
};

export type StudyCommandEntry =
  | { kind: "create"; command: PreparedCommand<CreateReceipt>; draft: CreateCommandDraft }
  | {
      kind: "revalidate";
      planId: string;
      expectedPlanRevision: number;
      expectedMapRevision: string;
      expectedPolicyRevision: number;
      command: PreparedCommand<RevalidateReceipt>;
    }
  | { kind: "cancel"; planId: string; expectedPlanRevision: number; command: PreparedCommand<CancelReceipt> };

export type StudyCommandMemory =
  | { status: "pending"; entry: StudyCommandEntry }
  | {
      status: "uncertain";
      entry: StudyCommandEntry;
      recoveryRequired: boolean;
      replayInvalidated: boolean;
    }
  | {
      status: "recovery_required";
      entry: Exclude<StudyCommandEntry, { kind: "create" }>;
      code: "map_revision_conflict" | "policy_revision_conflict" | "plan_revision_conflict";
    }
  | {
      status: "unconfirmed";
      planId: string;
      commandRevision: number;
      removedCount: number | null;
      entry: StudyCommandEntry;
    };

export type SetStudyCommandMemory = Dispatch<SetStateAction<StudyCommandMemory | null>>;

export function matchesCreateDraft(plan: PlanDetail, draft: CreateCommandDraft): boolean {
  const planTargets = plan.selection.targets;
  const targetsMatch = planTargets.length === draft.targets.length &&
    planTargets.every((target, index) => target.kind === draft.targets[index]?.kind && target.targetId === draft.targets[index]?.targetId);
  const planLabels = plan.selection.excludedLabelIds;
  const labelsMatch = planLabels.length === draft.excludedLabelIds.length &&
    planLabels.every((labelId, index) => labelId === draft.excludedLabelIds[index]);
  const requested = plan.selection.temporalFilterRequested;
  const temporal = draft.temporalFilter;
  const temporalMatches = requested.kind === temporal.kind && (
    requested.kind === "all" ||
    (requested.kind === "beforeDate" && temporal.kind === "beforeDate" && requested.date === temporal.date) ||
    (requested.kind === "dateRange" && temporal.kind === "dateRange" &&
      requested.onOrAfterDate === temporal.onOrAfterDate && requested.beforeDate === temporal.beforeDate) ||
    (requested.kind === "olderThanDays" && temporal.kind === "olderThanDays" && requested.days === temporal.days)
  );
  return plan.createdFromMapRevision === draft.expectedMapRevision &&
    plan.createdFromPolicyRevision === draft.expectedPolicyRevision &&
    plan.selection.disposition === draft.disposition &&
    targetsMatch && temporalMatches &&
    plan.selection.readState === draft.readState &&
    labelsMatch &&
    plan.selection.keepLatestPerFlow === draft.keepLatestPerFlow;
}
