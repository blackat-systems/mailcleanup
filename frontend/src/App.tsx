import { useEffect, useState } from "react";
import { Shell } from "./components/Shell";
import { OverviewPage } from "./pages/OverviewPage";
import { PlanPage } from "./pages/PlanPage";
import { SettingsPage } from "./pages/SettingsPage";
import { SourceDetailPage } from "./pages/SourceDetailPage";
import { SourcesPage } from "./pages/SourcesPage";

type Route =
  | { page: "overview"; key: "#/" }
  | { page: "sources"; key: string; view: string }
  | { page: "source"; key: "source"; id: string }
  | { page: "plan"; key: "#/plan" }
  | { page: "settings"; key: "#/settings" };

function currentRoute(): Route {
  const raw = window.location.hash.slice(1) || "/";
  const [path = "/", query = ""] = raw.split("?");
  if (path === "/sources") {
    const view = new URLSearchParams(query).get("view") ?? "all";
    const key = view === "all" ? "#/sources" : `#/sources?view=${view}`;
    return { page: "sources", key, view };
  }
  if (path.startsWith("/source/")) {
    return { page: "source", key: "source", id: decodeURIComponent(path.slice(8)) };
  }
  if (path === "/plan") return { page: "plan", key: "#/plan" };
  if (path === "/settings") return { page: "settings", key: "#/settings" };
  return { page: "overview", key: "#/" };
}

export default function App() {
  const [route, setRoute] = useState<Route>(currentRoute);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  useEffect(() => {
    const updateRoute = () => {
      setRoute(currentRoute());
      window.scrollTo({ top: 0, behavior: "instant" });
    };
    window.addEventListener("hashchange", updateRoute);
    return () => window.removeEventListener("hashchange", updateRoute);
  }, []);

  const toggle = (id: string) => {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  let content;
  if (route.page === "sources") {
    content = <SourcesPage view={route.view} selected={selected} onToggle={toggle} />;
  } else if (route.page === "source") {
    content = <SourceDetailPage id={route.id} selected={selected.has(route.id)} onToggle={toggle} />;
  } else if (route.page === "plan") {
    content = <PlanPage selected={selected} onToggle={toggle} />;
  } else if (route.page === "settings") {
    content = <SettingsPage />;
  } else {
    content = <OverviewPage selected={selected} onToggle={toggle} />;
  }

  return <Shell routeKey={route.key} selectedCount={selected.size}>{content}</Shell>;
}
