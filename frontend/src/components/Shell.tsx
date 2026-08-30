import { useEffect, useRef, useState, type ReactNode } from "react";
import { Icon } from "./Icon";

type NavItem = {
  href: string;
  label: string;
  icon: Parameters<typeof Icon>[0]["name"];
  write?: boolean;
};

const navItems: readonly NavItem[] = [
  { href: "#/", label: "Panorama", icon: "overview" },
  { href: "#/sources", label: "Fuentes", icon: "sources" },
  { href: "#/corrections", label: "Correcciones", icon: "corrections", write: true },
  { href: "#/study", label: "Estudio de Limpieza", icon: "search" },
  { href: "#/status", label: "Estado", icon: "settings" },
];

type Props = {
  children: ReactNode;
  routeKey: string;
  partial?: boolean;
  reviewCount?: number;
  writeEnabled?: boolean;
};

export function Shell({
  children,
  routeKey,
  partial = false,
  reviewCount = 0,
  writeEnabled = false,
}: Props) {
  const [open, setOpen] = useState(false);
  const menuButton = useRef<HTMLButtonElement>(null);
  const activeHref = routeKey === "source" || routeKey.startsWith("#/sources")
    ? "#/sources"
    : routeKey;

  const closeAfterNavigation = () => {
    const wasOpen = open;
    setOpen(false);
    if (wasOpen) queueMicrotask(() => document.getElementById("main-content")?.focus());
  };

  useEffect(() => {
    if (!open) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        menuButton.current?.focus();
      }
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [open]);

  return (
    <div className="app-shell">
      <a
        className="skip-link"
        href="#main-content"
        onClick={(event) => {
          event.preventDefault();
          setOpen(false);
          queueMicrotask(() => document.getElementById("main-content")?.focus());
        }}
      >
        Saltar al contenido
      </a>
      <button
        ref={menuButton}
        className="mobile-menu"
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-label={open ? "Cerrar navegación" : "Abrir navegación"}
        aria-expanded={open}
        aria-controls="primary-sidebar"
      >
        <Icon name={open ? "close" : "menu"} />
      </button>
      <aside id="primary-sidebar" className={`sidebar ${open ? "is-open" : ""}`}>
        <a className="brand" href="#/" onClick={closeAfterNavigation}>
          <span className="brand-mark" aria-hidden="true"><span /></span>
          <span>
            <strong>Mapa Total</strong>
            <small>Laboratorio local</small>
          </span>
        </a>

        <div className="mode-card">
          <span className="mode-dot" aria-hidden="true" />
          <div>
            <strong>Datos de demostración</strong>
            <small>{partial ? "Mapa parcial" : "Estado sintético"}</small>
          </div>
        </div>

        <nav aria-label="Secciones principales">
          {navItems.filter((item) => !item.write || writeEnabled).map((item) => {
            const active = activeHref === item.href;
            return (
              <a
                key={item.href}
                href={item.href}
                className={active ? "active" : undefined}
                aria-current={active ? "page" : undefined}
                onClick={closeAfterNavigation}
              >
                <Icon name={item.icon} />
                <span>{item.label}</span>
                {item.write && reviewCount > 0 ? (
                  <span className="nav-count" aria-label={`${reviewCount} decisiones para revisar`}>
                    {reviewCount}
                  </span>
                ) : null}
              </a>
            );
          })}
        </nav>

        <div className="sidebar-footer">
          <Icon name="shield" />
          <p>
            <strong>Sin acceso a Gmail.</strong>
            La interfaz no conecta cuentas, no controla sincronizaciones y no ejecuta acciones.
          </p>
        </div>
      </aside>
      {open ? (
        <button
          className="scrim"
          type="button"
          aria-label="Cerrar menú"
          onClick={() => {
            setOpen(false);
            menuButton.current?.focus();
          }}
        />
      ) : null}
      <main
        className="main-content"
        id="main-content"
        tabIndex={-1}
        inert={open ? true : undefined}
        aria-hidden={open ? true : undefined}
      >
        {children}
      </main>
    </div>
  );
}
