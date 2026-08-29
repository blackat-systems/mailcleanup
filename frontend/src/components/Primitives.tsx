import type { ReactNode } from "react";
import { Icon } from "./Icon";
import { shortId } from "../utils";

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow: string;
  title: string;
  description: string;
  actions?: ReactNode;
}) {
  return (
    <header className="page-header">
      <div>
        <span className="eyebrow">{eyebrow}</span>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {actions ? <div className="page-actions">{actions}</div> : null}
    </header>
  );
}

export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "positive" | "warning" | "protected" | "critical";
}) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

export function LoadingState({ label = "Leyendo el mapa sintético…" }: { label?: string }) {
  return (
    <div className="state-panel" role="status" aria-live="polite">
      <span className="loader" aria-hidden="true" />
      <p>{label}</p>
    </div>
  );
}

export function ErrorState({
  title = "No pudimos leer la API local",
  message,
  retry,
  backHref,
}: {
  title?: string;
  message: string;
  retry?: () => void;
  backHref?: string;
}) {
  return (
    <section className="state-panel state-error" role="alert" aria-labelledby="error-title">
      <Icon name="info" />
      <div>
        <strong id="error-title">{title}</strong>
        <p>{message}</p>
        <div className="state-actions">
          {retry ? (
            <button className="button button-secondary" type="button" onClick={retry}>
              Reintentar lectura
            </button>
          ) : null}
          {backHref ? <a className="button button-secondary" href={backHref}>Volver a fuentes</a> : null}
        </div>
      </div>
    </section>
  );
}

export function BlockedState({ reason }: { reason: string }) {
  return (
    <section className="page blocked-page" role="alert" aria-labelledby="blocked-title">
      <div className="state-panel state-error">
        <Icon name="shield" />
        <div>
          <span className="eyebrow">Superficie detenida</span>
          <h1 id="blocked-title">Mapa Total bloqueado</h1>
          <p>{reason}</p>
          <p>No se muestran controles de escritura hasta recuperar el contrato sintético esperado.</p>
        </div>
      </div>
    </section>
  );
}

export function EmptyState({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="state-panel state-empty">
      <Icon name="search" />
      <div><strong>{title}</strong><p>{detail}</p></div>
    </div>
  );
}

export function StatusMessage({ children }: { children: ReactNode }) {
  return <div className="inline-status" role="status" aria-live="polite">{children}</div>;
}

export function AlertMessage({ children }: { children: ReactNode }) {
  return <div className="inline-alert" role="alert">{children}</div>;
}

export function PublicId({ value }: { value: string }) {
  return (
    <details className="public-id">
      <summary aria-label={`Ver ID completo ${value}`}><code>{shortId(value)}</code></summary>
      <code>{value}</code>
    </details>
  );
}

export function StatCard({
  label,
  value,
  note,
  tone,
}: {
  label: string;
  value: string;
  note: string;
  tone: "ink" | "blue" | "green" | "gold";
}) {
  return (
    <article className={`stat-card stat-${tone}`}>
      <span>{label}</span><strong>{value}</strong><small>{note}</small>
    </article>
  );
}

export function DisclosurePanel({
  eyebrow,
  title,
  summary,
  children,
  className = "",
}: {
  eyebrow: string;
  title: string;
  summary: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <details className={`panel disclosure-panel ${className}`.trim()}>
      <summary>
        <span className="disclosure-title">
          <span className="eyebrow">{eyebrow}</span>
          <span className="disclosure-heading" role="heading" aria-level={2}>{title}</span>
        </span>
        <span className="disclosure-summary">{summary}</span>
      </summary>
      <div className="disclosure-content">{children}</div>
    </details>
  );
}
