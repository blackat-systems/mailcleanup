import type { ReactNode } from "react";
import { Icon } from "./Icon";

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

export function Badge({ children, tone = "neutral" }: { children: ReactNode; tone?: string }) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

export function LoadingState({ label = "Organizando el mapa…" }: { label?: string }) {
  return <div className="state-panel" role="status"><span className="loader" /><p>{label}</p></div>;
}

export function ErrorState({ message, retry }: { message: string; retry: () => void }) {
  return (
    <div className="state-panel state-error" role="alert">
      <Icon name="info" />
      <div><strong>No pudimos leer la API local</strong><p>{message}</p></div>
      <button className="button button-secondary" type="button" onClick={retry}>Reintentar</button>
    </div>
  );
}

export function EmptyState({ title, detail }: { title: string; detail: string }) {
  return <div className="state-panel"><Icon name="search" /><div><strong>{title}</strong><p>{detail}</p></div></div>;
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
  tone: string;
}) {
  return (
    <article className={`stat-card stat-${tone}`}>
      <span>{label}</span><strong>{value}</strong><small>{note}</small>
    </article>
  );
}
