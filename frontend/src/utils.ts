export function formatCount(value: number): string {
  return new Intl.NumberFormat("es-AR").format(value);
}

export function formatBytes(value: number): string {
  if (value < 1024) return `${value} B`;
  if (value < 1024 ** 2) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / 1024 ** 2).toFixed(1)} MB`;
}

export function formatDate(value: string, withTime = false): string {
  return new Intl.DateTimeFormat("es-AR", {
    dateStyle: "medium",
    ...(withTime ? { timeStyle: "short" as const } : {}),
    timeZone: "America/Argentina/Cordoba",
  }).format(new Date(value));
}

export function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

export function confidenceTone(value: string): string {
  if (value === "Alta") return "positive";
  if (value === "Media") return "neutral";
  return "warning";
}
