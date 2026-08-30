import { isCancelReceipt, isCreateReceipt, isRevalidateReceipt } from "./decoders";
import type {
  CancelPlanRequest,
  CancelReceipt,
  CreatePlanRequest,
  CreateReceipt,
  PreparedCommand,
  RevalidatePlanRequest,
  RevalidateReceipt,
} from "./types";

function commandId(): string {
  return crypto.randomUUID();
}

function prepared<T>(path: string, body: object, decode: PreparedCommand<T>["decode"]): PreparedCommand<T> {
  return { path, serializedBody: JSON.stringify(body), decode };
}

export function prepareCreate(body: Omit<CreatePlanRequest, "commandId">): PreparedCommand<CreateReceipt> {
  const request: CreatePlanRequest = { commandId: commandId(), ...body };
  return prepared("/api/v3/study/plans", request, isCreateReceipt);
}

export function prepareRevalidate(
  planId: string,
  body: Omit<RevalidatePlanRequest, "commandId">,
): PreparedCommand<RevalidateReceipt> {
  const request: RevalidatePlanRequest = { commandId: commandId(), ...body };
  return prepared(
    `/api/v3/study/plans/${encodeURIComponent(planId)}/revalidate`,
    request,
    isRevalidateReceipt,
  );
}

export function prepareCancel(
  planId: string,
  body: Omit<CancelPlanRequest, "commandId">,
): PreparedCommand<CancelReceipt> {
  const request: CancelPlanRequest = { commandId: commandId(), ...body };
  return prepared(
    `/api/v3/study/plans/${encodeURIComponent(planId)}/cancel`,
    request,
    isCancelReceipt,
  );
}
