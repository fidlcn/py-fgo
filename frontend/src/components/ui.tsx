// Small reusable presentational components.

import type { CSSProperties, ReactNode } from "react";

export function StatusBadge({ status }: { status: string }) {
  const cls = statusClass(status);
  return <span className={`badge ${cls}`}>{status}</span>;
}

export function statusClass(status: string): string {
  const s = status.toLowerCase();
  if (["running", "online", "completed", "ok", "device"].includes(s)) return "ok";
  if (["paused", "stopping", "pending", "idle", "offline", "unauthorized"].includes(s))
    return "muted";
  if (["failed", "error", "stopped"].includes(s)) return "err";
  return "muted";
}

export function Card({
  title,
  actions,
  children,
  style,
}: {
  title?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  style?: CSSProperties;
}) {
  return (
    <div className="card" style={style}>
      {(title || actions) && (
        <div className="spread" style={{ marginBottom: 12 }}>
          <div style={{ fontWeight: 600 }}>{title}</div>
          <div className="row">{actions}</div>
        </div>
      )}
      {children}
    </div>
  );
}

export function Field({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <div className="field">
      <label>{label}</label>
      {children}
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="muted" style={{ padding: "12px 4px" }}>{children}</div>;
}

export function Stat({ value, label }: { value: ReactNode; label: string }) {
  return (
    <div className="stat">
      <div className="v">{value}</div>
      <div className="k">{label}</div>
    </div>
  );
}
