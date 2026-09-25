import { useState } from "react";
import { api, rm, type Order } from "../api";
import { useSession } from "../App";
import { ErrorNote, useAsync } from "../components";

export function AdminPage() {
  const { user } = useSession();
  const { data: orders, error, reload } = useAsync(() => api<Order[]>("/admin/disputes"), []);
  if (!user?.is_admin) return <p>Admins only.</p>;
  return (
    <>
      <h1>Open disputes</h1>
      <ErrorNote error={error} />
      <div className="list">
        {orders?.map((o) => <DisputeCard key={o.id} order={o} onResolved={reload} />)}
        {orders?.length === 0 && <p className="muted">No open disputes. 🎉</p>}
      </div>
    </>
  );
}

function DisputeCard({ order: o, onResolved }: { order: Order; onResolved: () => void }) {
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const resolve = async (refund: boolean) => {
    try {
      await api(`/admin/orders/${o.id}/resolve`, { body: { refund, note } });
      onResolved();
    } catch (e) {
      setError((e as Error).message);
    }
  };
  return (
    <div className="card">
      <h3>
        Order #{o.id} · {o.listing.event.name} · {rm(o.amount)}
      </h3>
      <p className="muted small">
        Buyer {o.buyer_name} vs seller {o.listing.seller.name} ({o.listing.seller.completed_sales} sales, {o.listing.seller.strikes} strikes)
      </p>
      <p><strong>Buyer says:</strong> {o.dispute_reason}</p>
      {o.transfer_note && <p><strong>Seller's transfer note:</strong> {o.transfer_note}</p>}
      <a href={`#/order/${o.id}`}>View full timeline & chat →</a>
      <label>
        Resolution note
        <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="e.g. Organiser confirmed barcode invalid" />
      </label>
      <div className="actions">
        <button className="btn danger" disabled={note.length < 5} onClick={() => resolve(true)}>Refund buyer (+ seller strike)</button>
        <button className="btn secondary" disabled={note.length < 5} onClick={() => resolve(false)}>Release to seller</button>
      </div>
      <ErrorNote error={error} />
    </div>
  );
}
