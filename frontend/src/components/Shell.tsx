import { useState, type ReactNode } from "react";
import { Icon } from "./Icon";

type NavItem = { href: string; label: string; icon: Parameters<typeof Icon>[0]["name"] };

const navItems: NavItem[] = [
  { href: "#/", label: "Panorama", icon: "overview" },
  { href: "#/sources", label: "Fuentes", icon: "sources" },
  { href: "#/sources?view=subscriptions", label: "Suscripciones", icon: "subscription" },
  { href: "#/sources?view=spam", label: "Spam", icon: "spam" },
  { href: "#/plan", label: "Estudio de Limpieza", icon: "plan" },
  { href: "#/settings", label: "Estado", icon: "settings" },
];

type Props = {
  children: ReactNode;
  routeKey: string;
  selectedCount: number;
};

export function Shell({ children, routeKey, selectedCount }: Props) {
  const [open, setOpen] = useState(false);
  const activeHref = routeKey === "source" ? "#/sources" : routeKey;

  return (
    <div className="app-shell">
      <button
        className="mobile-menu"
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-label={open ? "Cerrar navegación" : "Abrir navegación"}
        aria-expanded={open}
      >
        <Icon name={open ? "close" : "menu"} />
      </button>
      <aside className={`sidebar ${open ? "is-open" : ""}`}>
        <a className="brand" href="#/" onClick={() => setOpen(false)}>
          <span className="brand-mark" aria-hidden="true"><span /></span>
          <span>
            <strong>Mapa de correo</strong>
            <small>Laboratorio local</small>
          </span>
        </a>

        <div className="mode-card">
          <span className="mode-dot" />
          <div><strong>Modo sintético</strong><small>Sin acceso a Gmail</small></div>
        </div>

        <nav aria-label="Secciones principales">
          {navItems.map((item) => {
            const active = activeHref === item.href;
            return (
              <a
                key={item.href}
                href={item.href}
                className={active ? "active" : undefined}
                aria-current={active ? "page" : undefined}
                onClick={() => setOpen(false)}
              >
                <Icon name={item.icon} />
                <span>{item.label}</span>
                {item.href === "#/plan" && selectedCount > 0 ? (
                  <span className="nav-count">{selectedCount}</span>
                ) : null}
              </a>
            );
          })}
        </nav>

        <div className="sidebar-footer">
          <Icon name="shield" />
          <p><strong>Todo queda en tu equipo.</strong> Base Segura no tiene credenciales ni acciones reales.</p>
        </div>
      </aside>
      {open ? <button className="scrim" type="button" aria-label="Cerrar menú" onClick={() => setOpen(false)} /> : null}
      <main className="main-content" id="main-content">{children}</main>
    </div>
  );
}
