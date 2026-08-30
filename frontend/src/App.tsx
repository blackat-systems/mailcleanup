import { useEffect, useState } from "react";
import { Shell } from "./components/Shell";
import { BlockedState, ErrorState, LoadingState } from "./components/Primitives";
import { useMapWorkspace } from "./hooks";
import { CorrectionsPage } from "./pages/CorrectionsPage";
import { OverviewPage } from "./pages/OverviewPage";
import { SourceDetailPage } from "./pages/SourceDetailPage";
import { SourcesPage } from "./pages/SourcesPage";
import { StatusPage } from "./pages/StatusPage";
import { currentRoute, type Route } from "./routing";
import { StudyApplication } from "./study/StudyApplication";
import type { StudyCommandMemory } from "./study/commandMemory";
import type { PlanDetail } from "./study/types";

export default function App() {
  const [route, setRoute] = useState<Route>(currentRoute);
  const [studyCommandMemory, setStudyCommandMemory] = useState<StudyCommandMemory | null>(null);
  const [studyPlanSnapshots] = useState(() => new Map<string, PlanDetail>());

  useEffect(() => {
    const updateRoute = () => {
      setRoute(currentRoute());
      window.scrollTo({ top: 0, behavior: "instant" });
      queueMicrotask(() => document.getElementById("main-content")?.focus());
    };
    window.addEventListener("hashchange", updateRoute);
    return () => window.removeEventListener("hashchange", updateRoute);
  }, []);

  if (route.page === "study" || route.page === "study_plan") {
    return (
      <StudyApplication
        route={route}
        commandMemory={studyCommandMemory}
        setCommandMemory={setStudyCommandMemory}
        planSnapshots={studyPlanSnapshots}
      />
    );
  }
  if (route.page === "not_found") {
    return (
      <Shell routeKey={route.key} writeEnabled>
        <div className="page not-found-page">
          <h1>Esta sección no existe</h1>
          <p>Volvé a una ruta publicada de MailCleanup.</p>
          <a className="button button-primary" href="#/">Volver a Panorama</a>
        </div>
      </Shell>
    );
  }
  return <MapApplication route={route} />;
}

function MapApplication({ route }: { route: Exclude<Route, { page: "study" | "study_plan" | "not_found" }> }) {
  const workspace = useMapWorkspace();

  if (workspace.state.kind === "loading") {
    return (
      <Shell routeKey={route.key}>
        <div className="page"><h1 className="sr-only">Mapa Total</h1><LoadingState label="Coordinando contexto y fotografía sintética…" /></div>
      </Shell>
    );
  }
  if (workspace.state.kind === "blocked") {
    return <Shell routeKey={route.key}><BlockedState reason={workspace.state.reason} /></Shell>;
  }
  if (workspace.state.kind === "error") {
    return (
      <Shell routeKey={route.key}>
        <div className="page">
          <h1 className="sr-only">Mapa Total no disponible</h1>
          <ErrorState message={workspace.state.error.message} retry={workspace.reload} />
        </div>
      </Shell>
    );
  }

  const data = workspace.state.data;
  let content;
  if (route.page === "sources") {
    content = <SourcesPage map={data.map} view={route.view} />;
  } else if (route.page === "source") {
    content = (
      <SourceDetailPage
        id={route.id}
        mapRevision={data.map.mapRevision}
        partial={data.map.sync.partial}
      />
    );
  } else if (route.page === "corrections") {
    content = (
      <CorrectionsPage
        map={data.map}
        decisions={data.decisions}
        initialSourceId={route.sourceId}
        refreshProjection={workspace.refreshProjection}
      />
    );
  } else if (route.page === "status") {
    content = <StatusPage data={data} />;
  } else {
    content = <OverviewPage map={data.map} />;
  }

  return (
    <Shell
      routeKey={route.key}
      partial={data.map.sync.partial}
      reviewCount={data.map.policyReview.total}
      writeEnabled
    >
      {content}
    </Shell>
  );
}
