export type User = {
  id: number;
  email: string;
  name: string;
  verified: boolean;
  is_admin: boolean;
  strikes: number;
  suspended: boolean;
};

export type Seller = {
  id: number;
  name: string;
  verified: boolean;
  suspended: boolean;
  completed_sales: number;
  rating: number | null;
  review_count: number;
  strikes: number;
  member_since: string;
};

export type Event = { id: number; name: string; artist: string; venue: string; starts_at: string };
export type EventWithCount = Event & { listings: number; lowest_price: number | null };

export type Listing = {
  id: number;
  event: Event;
  section: string;
  seat: string | null;
  face_value: number;
  price: number;
  description: string;
  status: "active" | "reserved" | "sold" | "cancelled";
  created_at: string;
  seller: Seller;
};

export type OrderStatus =
  | "awaiting_payment"
  | "in_escrow"
  | "transferred"
  | "completed"
  | "disputed"
  | "refunded"
  | "expired";

export type Order = {
  id: number;
  listing: Listing;
  buyer_name: string;
  role: "buyer" | "seller" | "admin";
  amount: number;
  fee: number;
  status: OrderStatus;
  payment_ref: string | null;
  transfer_note: string | null;
  dispute_reason: string | null;
  resolution_note: string | null;
  pay_by: string;
  transfer_by: string | null;
  release_at: string | null;
  events: { status: OrderStatus; note: string; at: string }[];
  can_review: boolean;
};

export type Message = {
  id: number;
  sender_name: string;
  mine: boolean;
  body: string;
  flags: string[];
  warnings: string[];
  at: string;
};

const TOKEN_KEY = "tixsafe_token";

export const auth = {
  get token(): string | null {
    try {
      return localStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },
  set token(value: string | null) {
    try {
      if (value) localStorage.setItem(TOKEN_KEY, value);
      else localStorage.removeItem(TOKEN_KEY);
    } catch {
      /* storage unavailable: session-only login */
    }
  },
};

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export async function api<T>(path: string, init: { method?: string; body?: unknown } = {}): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (auth.token) headers.Authorization = `Bearer ${auth.token}`;
  const res = await fetch(`/api${path}`, {
    method: init.method ?? (init.body === undefined ? "GET" : "POST"),
    headers,
    body: init.body === undefined ? undefined : JSON.stringify(init.body),
  });
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const detail = data?.detail;
    const message = Array.isArray(detail)
      ? detail.map((d: { msg: string }) => d.msg.replace(/^Value error, /, "")).join("; ")
      : detail ?? res.statusText;
    throw new ApiError(res.status, message);
  }
  return data as T;
}

// Server stores naive UTC timestamps.
export const parseDate = (s: string) => new Date(s.endsWith("Z") ? s : s + "Z");

export const rm = (sen: number) =>
  "RM " + (sen / 100).toLocaleString("en-MY", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export const when = (s: string) =>
  parseDate(s).toLocaleString("en-MY", { weekday: "short", day: "numeric", month: "short", hour: "numeric", minute: "2-digit" });

export function countdown(s: string, now: number): string {
  const ms = parseDate(s).getTime() - now;
  if (ms <= 0) return "now";
  const m = Math.floor(ms / 60000);
  if (m < 60) return `${m}m ${Math.floor((ms % 60000) / 1000)}s`;
  const h = Math.floor(m / 60);
  if (h < 48) return `${h}h ${m % 60}m`;
  return `${Math.floor(h / 24)} days`;
}
