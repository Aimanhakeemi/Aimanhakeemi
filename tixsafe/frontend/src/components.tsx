import { useEffect, useState } from "react";
import type { Order, OrderStatus, Seller } from "./api";
import { parseDate } from "./api";

export function useAsync<T>(load: () => Promise<T>, deps: unknown[]) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  useEffect(() => {
    let live = true;
    load()
      .then((d) => live && (setData(d), setError(null)))
      .catch((e) => live && setError(e.message));
    return () => {
      live = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);
  return { data, setData, error, reload: () => setTick((t) => t + 1) };
}

export function useNow(intervalMs = 1000) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), intervalMs);
    return () => clearInterval(t);
  }, [intervalMs]);
  return now;
}

export function SellerCard({ seller }: { seller: Seller }) {
  const since = parseDate(seller.member_since).toLocaleDateString("en-MY", { month: "short", year: "numeric" });
  return (
    <div className="seller">
      <div className="avatar" aria-hidden>
        {seller.name[0]}
      </div>
      <div>
        <div className="seller-name">
          {seller.name}
          {seller.verified && <span className="badge ok">✓ ID verified</span>}
          {seller.suspended && <span className="badge bad">Suspended</span>}
        </div>
        <div className="muted small">
          {seller.completed_sales} completed sale{seller.completed_sales === 1 ? "" : "s"}
          {seller.rating !== null && ` · ★ ${seller.rating.toFixed(1)} (${seller.review_count})`}
          {seller.strikes > 0 && ` · ${seller.strikes} strike${seller.strikes > 1 ? "s" : ""}`}
          {` · since ${since}`}
        </div>
      </div>
    </div>
  );
}

const STATUS_LABEL: Record<OrderStatus, [string, string]> = {
  awaiting_payment: ["Awaiting payment", "warn"],
  in_escrow: ["Paid · held in escrow", "info"],
  transferred: ["Ticket sent · funds held", "info"],
  completed: ["Completed", "ok"],
  disputed: ["Disputed · funds frozen", "bad"],
  refunded: ["Refunded", "muted"],
  expired: ["Expired", "muted"],
};

export function StatusPill({ status }: { status: OrderStatus }) {
  const [label, tone] = STATUS_LABEL[status];
  return <span className={`pill ${tone}`}>{label}</span>;
}

const STEPS: { key: OrderStatus; label: string }[] = [
  { key: "awaiting_payment", label: "Reserved" },
  { key: "in_escrow", label: "Paid to escrow" },
  { key: "transferred", label: "Ticket sent" },
  { key: "completed", label: "Released to seller" },
];

export function Stepper({ order }: { order: Order }) {
  const reached = new Set(order.events.map((e) => e.status));
  const failed = ["refunded", "expired", "disputed"].includes(order.status);
  return (
    <ol className="stepper">
      {STEPS.map((s) => (
        <li key={s.key} className={reached.has(s.key) ? "done" : ""}>
          <span className="dot" />
          {s.label}
        </li>
      ))}
      {failed && (
        <li className="done failed">
          <span className="dot" />
          {STATUS_LABEL[order.status][0]}
        </li>
      )}
    </ol>
  );
}

export function ErrorNote({ error }: { error: string | null }) {
  return error ? <p className="error">{error}</p> : null;
}
