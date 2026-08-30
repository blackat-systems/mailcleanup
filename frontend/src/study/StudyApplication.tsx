import { AlertMessage, LoadingState } from "../components/Primitives";
import { Shell } from "../components/Shell";
import type { Route } from "../routing";
import { StudyPage } from "./pages/StudyPage";
import { StudyPlanPage } from "./pages/StudyPlanPage";
import { useStudyContexts } from "./hooks";
import type { SetStudyCommandMemory, StudyCommandMemory } from "./commandMemory";
import type { PlanDetail } from "./types";

type StudyRoute = Extract<Route, { page: "study" | "study_plan" }>;

export function StudyApplication({
  route,
  commandMemory,
  setCommandMemory,
  planSnapshots,
}: {
  route: StudyRoute;
  commandMemory: StudyCommandMemory | null;
  setCommandMemory: SetStudyCommandMemory;
  planSnapshots: Map<string, PlanDetail>;
}) {
  const contexts = useStudyContexts();

  return (
    <Shell routeKey="#/study" writeEnabled>
      <div className="study-safety-strip" role="status" aria-live="polite">
        <strong>Datos de demostración.</strong>
        <span>Vista previa sin efectos; no modifica Gmail.</span>
        <span>La capacidad de ejecución permanece desactivada.</span>
      </div>
      {contexts.state.loading && contexts.state.context === null ? (
        <div className="study-context-progress">
          <LoadingState label="Comprobando los contratos sintéticos v2 y v3…" />
        </div>
      ) : null}
      {contexts.state.error ? (
        <div className="study-context-alert">
          <AlertMessage>
            <strong>Comandos bloqueados.</strong> {contexts.state.error} La historia congelada sigue disponible.
          </AlertMessage>
        </div>
      ) : null}
      {route.page === "study" ? (
        <StudyPage
          contexts={contexts.state}
          refreshContexts={contexts.refresh}
          commandMemory={commandMemory}
          setCommandMemory={setCommandMemory}
          planSnapshots={planSnapshots}
        />
      ) : (
        <StudyPlanPage
          key={route.planId}
          planId={route.planId}
          contexts={contexts.state}
          refreshContexts={contexts.refresh}
          commandMemory={commandMemory}
          setCommandMemory={setCommandMemory}
          planSnapshots={planSnapshots}
        />
      )}
    </Shell>
  );
}
