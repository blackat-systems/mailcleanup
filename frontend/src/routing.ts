import type { SourceView } from "./pages/SourcesPage";

export type Route =
  | { page: "overview"; key: "#/" }
  | { page: "sources"; key: string; view: SourceView }
  | { page: "source"; key: "source"; id: string }
  | { page: "corrections"; key: "#/corrections"; sourceId?: string }
  | { page: "status"; key: "#/status" }
  | { page: "not_found"; key: "not_found" };

const sourceViews = new Set<SourceView>(["all", "subscriptions", "spam", "protected"]);

function safelyDecode(value: string): string | null {
  try {
    return decodeURIComponent(value);
  } catch {
    return null;
  }
}

export function currentRoute(): Route {
  const raw = window.location.hash.slice(1) || "/";
  const separator = raw.indexOf("?");
  const path = separator >= 0 ? raw.slice(0, separator) : raw;
  const query = separator >= 0 ? raw.slice(separator + 1) : "";
  if (path === "/sources") {
    const requested = new URLSearchParams(query).get("view") ?? "all";
    const view = sourceViews.has(requested as SourceView) ? (requested as SourceView) : "all";
    const key = view === "all" ? "#/sources" : `#/sources?view=${view}`;
    return { page: "sources", key, view };
  }
  if (path.startsWith("/source/")) {
    const id = safelyDecode(path.slice(8));
    return id ? { page: "source", key: "source", id } : { page: "not_found", key: "not_found" };
  }
  if (path === "/corrections") {
    const encodedSource = new URLSearchParams(query).get("sourceId");
    const sourceId = encodedSource ? safelyDecode(encodedSource) : null;
    return sourceId
      ? { page: "corrections", key: "#/corrections", sourceId }
      : { page: "corrections", key: "#/corrections" };
  }
  if (path === "/status") return { page: "status", key: "#/status" };
  if (path === "/") return { page: "overview", key: "#/" };
  return { page: "not_found", key: "not_found" };
}
