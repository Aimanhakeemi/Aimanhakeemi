import { useState } from "react";
import { api, rm, when, type Listing, type Order } from "../api";
import { go, useSession } from "../App";
import { ErrorNote, SellerCard, useAsync } from "../components";

const BUYER_FEE_PCT = 5;

export function ListingPage({ id }: { id: number }) {
  const { user } = useSession();
  const { data: l, error } = useAsync(() => api<Listing>(`/listings/${id}`), [id]);
  const [busy, setBusy] = useState(false);
  const [buyError, setBuyError] = useState<string | null>(null);

  if (error) return <ErrorNote error={error} />;
  if (!l) return null;

  const fee = Math.round((l.price * BUYER_FEE_PCT) / 100);
  const mine = user?.id === l.seller.id;

  async function buy() {
    if (!user) return go("/login");
    setBusy(true);
    setBuyError(null);
    try {
      const order = await api<Order>(`/listings/${id}/buy`, { body: {} });
      go(`/order/${order.id}`);
    } catch (e) {
      setBuyError((e as Error).message);
      setBusy(false);
    }
  }

  return (
    <>
      <a href={`#/event/${l.event.id}`} className="back">← {l.event.name}</a>
      <div className="two-col">
        <div className="card">
          <div className="muted small">{l.event.venue} · {when(l.event.starts_at)}</div>
          <h1>{l.section}{l.seat && ` · ${l.seat}`}</h1>
          {l.description && <p>{l.description}</p>}
          <h3>Seller</h3>
          <SellerCard seller={l.seller} />
        </div>
        <aside className="card checkout">
          <div className="row"><span>Ticket</span><span>{rm(l.price)}</span></div>
          <div className="row muted"><span>Face value</span><span>{rm(l.face_value)}</span></div>
          <div className="row"><span>Buyer protection ({BUYER_FEE_PCT}%)</span><span>{rm(fee)}</span></div>
          <div className="row total"><span>Total</span><span>{rm(l.price + fee)}</span></div>
          {l.status === "active" ? (
            mine ? (
              <p className="muted">This is your listing.</p>
            ) : (
              <button className="btn wide" disabled={busy} onClick={buy}>
                {user ? "Reserve & pay securely" : "Log in to buy"}
              </button>
            )
          ) : (
            <p className="muted">This ticket is no longer available.</p>
          )}
          <ErrorNote error={buyError} />
          <ul className="protect">
            <li>Your payment is held by TixSafe, not the seller.</li>
            <li>Seller must transfer within 24h or you&apos;re refunded automatically.</li>
            <li>Money is released 24h after the show, or when you confirm.</li>
            <li>Ticket doesn&apos;t work? Open a dispute and funds are frozen.</li>
          </ul>
        </aside>
      </div>
    </>
  );
}
