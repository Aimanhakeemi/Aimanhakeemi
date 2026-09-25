import { useEffect, useRef, useState } from "react";
import { api, countdown, parseDate, rm, when, type Message, type Order } from "../api";
import { ErrorNote, SellerCard, Stepper, StatusPill, useAsync, useNow } from "../components";

export function OrdersPage() {
  const { data: orders, error } = useAsync(() => api<Order[]>("/orders"), []);
  const buying = orders?.filter((o) => o.role === "buyer") ?? [];
  const selling = orders?.filter((o) => o.role === "seller") ?? [];
  return (
    <>
      <h1>My orders</h1>
      <ErrorNote error={error} />
      <OrderList title="Buying" orders={buying} empty="You haven't bought anything yet." />
      <OrderList title="Selling" orders={selling} empty="No one has bought your tickets yet." />
    </>
  );
}

function OrderList({ title, orders, empty }: { title: string; orders: Order[]; empty: string }) {
  return (
    <section>
      <h2>{title}</h2>
      <div className="list">
        {orders.map((o) => (
          <a key={o.id} href={`#/order/${o.id}`} className="card listing-row">
            <div>
              <h3>{o.listing.event.name}</h3>
              <div className="muted small">
                {o.listing.section} · Order #{o.id} · {when(o.listing.event.starts_at)}
              </div>
            </div>
            <div className="price">
              <strong>{rm(o.amount)}</strong>
              <StatusPill status={o.status} />
            </div>
          </a>
        ))}
        {orders.length === 0 && <p className="muted">{empty}</p>}
      </div>
    </section>
  );
}

export function OrderPage({ id }: { id: number }) {
  const { data: order, setData, error } = useAsync(() => api<Order>(`/orders/${id}`), [id]);
  const now = useNow();
  const [actionError, setActionError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Re-fetch when a deadline passes so the server can apply it.
  const deadline = order && nextDeadline(order);
  useEffect(() => {
    if (!deadline) return;
    const ms = parseDate(deadline).getTime() - Date.now() + 1000;
    if (ms > 2 ** 31 - 1) return;
    const t = setTimeout(() => api<Order>(`/orders/${id}`).then(setData), Math.max(ms, 0));
    return () => clearTimeout(t);
  }, [deadline, id, setData]);

  if (error) return <ErrorNote error={error} />;
  if (!order) return null;

  async function act(path: string, body: unknown = {}) {
    setBusy(true);
    setActionError(null);
    try {
      setData(await api<Order>(`/orders/${id}/${path}`, { body }));
    } catch (e) {
      setActionError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const l = order.listing;
  return (
    <>
      <a href="#/orders" className="back">← My orders</a>
      <div className="page-head">
        <h1>
          {l.event.name} <StatusPill status={order.status} />
        </h1>
        <p className="muted">
          Order #{order.id} · {l.section} · {l.event.venue} · {when(l.event.starts_at)}
        </p>
      </div>
      <Stepper order={order} />
      <div className="two-col">
        <div>
          <div className="card">
            <NextStep order={order} now={now} busy={busy} act={act} />
            <ErrorNote error={actionError} />
          </div>
          {order.can_review && <ReviewBox orderId={order.id} onDone={() => setData({ ...order, can_review: false })} />}
          <Chat orderId={order.id} />
        </div>
        <aside>
          <div className="card">
            <div className="row"><span>Ticket</span><span>{rm(order.amount)}</span></div>
            {order.role !== "seller" && (
              <div className="row"><span>Buyer protection</span><span>{rm(order.fee)}</span></div>
            )}
            {order.payment_ref && <div className="row muted small"><span>Payment ref</span><span>{order.payment_ref}</span></div>}
            <h3>{order.role === "seller" ? "Buyer" : "Seller"}</h3>
            {order.role === "seller" ? <p>{order.buyer_name}</p> : <SellerCard seller={l.seller} />}
          </div>
          <div className="card">
            <h3>Activity</h3>
            <ol className="timeline">
              {order.events.map((e, i) => (
                <li key={i}>
                  <div className="small muted">{when(e.at)}</div>
                  {e.note}
                </li>
              ))}
            </ol>
          </div>
        </aside>
      </div>
    </>
  );
}

function nextDeadline(o: Order): string | null {
  if (o.status === "awaiting_payment") return o.pay_by;
  if (o.status === "in_escrow") return o.transfer_by;
  if (o.status === "transferred") return o.release_at;
  return null;
}

type ActProps = { order: Order; now: number; busy: boolean; act: (path: string, body?: unknown) => void };

function NextStep({ order: o, now, busy, act }: ActProps) {
  const [note, setNote] = useState("");
  const [reason, setReason] = useState("");
  const [disputing, setDisputing] = useState(false);
  const buyer = o.role === "buyer";
  if (o.role === "admin") {
    return (
      <>
        <h2>Viewing as support</h2>
        <p>Buyer: {o.buyer_name}. Resolve disputes from the Disputes page.</p>
        {o.dispute_reason && <p className="callout">“{o.dispute_reason}”</p>}
      </>
    );
  }

  const disputeForm = buyer && (o.status === "in_escrow" || o.status === "transferred") && (
    <div className="dispute">
      {disputing ? (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            act("dispute", { reason });
          }}
        >
          <label>
            What went wrong?
            <textarea value={reason} onChange={(e) => setReason(e.target.value)} placeholder="e.g. The barcode was rejected at the gate" required minLength={10} />
          </label>
          <div className="actions">
            <button className="btn danger" disabled={busy}>Open dispute & freeze funds</button>
            <button type="button" className="link" onClick={() => setDisputing(false)}>Cancel</button>
          </div>
        </form>
      ) : (
        <button className="link danger-text" onClick={() => setDisputing(true)}>
          Something wrong? Report a problem
        </button>
      )}
    </div>
  );

  switch (o.status) {
    case "awaiting_payment":
      return buyer ? (
        <>
          <h2>Pay to secure your ticket</h2>
          <p>
            Reserved for you for <strong>{countdown(o.pay_by, now)}</strong>. Your {rm(o.amount + o.fee)} goes to TixSafe
            escrow, not to the seller.
          </p>
          <button className="btn" disabled={busy} onClick={() => act("pay")}>
            Pay {rm(o.amount + o.fee)} (demo FPX / card)
          </button>
        </>
      ) : (
        <>
          <h2>Waiting for the buyer to pay</h2>
          <p>Reservation expires in {countdown(o.pay_by, now)}. Don&apos;t send the ticket yet.</p>
        </>
      );
    case "in_escrow":
      return buyer ? (
        <>
          <h2>Payment secured in escrow</h2>
          <p>
            The seller has <strong>{countdown(o.transfer_by!, now)}</strong> to transfer the ticket. If they don&apos;t, you
            get a full refund automatically.
          </p>
          {disputeForm}
        </>
      ) : (
        <>
          <h2>Buyer has paid. Transfer the ticket now.</h2>
          <p>
            {rm(o.amount)} is held for you. Transfer within <strong>{countdown(o.transfer_by!, now)}</strong> using the
            official ticketing app&apos;s transfer feature, then tell us how you sent it.
          </p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              act("transfer", { note });
            }}
          >
            <label>
              How did you send it?
              <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="e.g. Ticket2U transfer to buyer's registered email" required minLength={5} />
            </label>
            <button className="btn" disabled={busy}>I&apos;ve transferred the ticket</button>
          </form>
        </>
      );
    case "transferred":
      return buyer ? (
        <>
          <h2>The seller says the ticket is sent</h2>
          <p className="callout">“{o.transfer_note}”</p>
          <p>
            Check the ticket shows in your official app. The money is held until{" "}
            <strong>{when(o.release_at!)}</strong> (24h after the show) so you can use it at the gate first.
          </p>
          <button className="btn" disabled={busy} onClick={() => act("confirm")}>
            Ticket works, release payment
          </button>
          {disputeForm}
        </>
      ) : (
        <>
          <h2>Ticket sent. Payment on its way.</h2>
          <p>
            {rm(o.amount)} will be released on <strong>{when(o.release_at!)}</strong>, or sooner if the buyer confirms.
          </p>
        </>
      );
    case "completed":
      return (
        <>
          <h2>Done 🎉</h2>
          <p>{buyer ? "Enjoy the show!" : `${rm(o.amount)} has been released to you.`}</p>
          {o.resolution_note && <p className="muted">Resolution: {o.resolution_note}</p>}
        </>
      );
    case "disputed":
      return (
        <>
          <h2>Under review</h2>
          <p>Funds are frozen while TixSafe support reviews this order. Add any evidence in the chat below.</p>
          <p className="callout">“{o.dispute_reason}”</p>
        </>
      );
    case "refunded":
      return (
        <>
          <h2>Refunded</h2>
          <p>{buyer ? `${rm(o.amount + o.fee)} has been returned to you.` : "The buyer was refunded."}</p>
          {o.resolution_note && <p className="muted">Resolution: {o.resolution_note}</p>}
        </>
      );
    case "expired":
      return (
        <>
          <h2>Reservation expired</h2>
          <p>No payment was made, so nothing was charged.</p>
        </>
      );
  }
}

function ReviewBox({ orderId, onDone }: { orderId: number; onDone: () => void }) {
  const [rating, setRating] = useState(5);
  const [comment, setComment] = useState("");
  const [error, setError] = useState<string | null>(null);
  return (
    <form
      className="card"
      onSubmit={async (e) => {
        e.preventDefault();
        try {
          await api(`/orders/${orderId}/review`, { body: { rating, comment } });
          onDone();
        } catch (err) {
          setError((err as Error).message);
        }
      }}
    >
      <h3>Rate your seller</h3>
      <div className="stars" role="radiogroup" aria-label="Rating">
        {[1, 2, 3, 4, 5].map((n) => (
          <button type="button" key={n} aria-checked={n === rating} role="radio" className={n <= rating ? "on" : ""} onClick={() => setRating(n)}>
            ★
          </button>
        ))}
      </div>
      <input value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Optional comment" />
      <button className="btn">Submit review</button>
      <ErrorNote error={error} />
    </form>
  );
}

function Chat({ orderId }: { orderId: number }) {
  const { data: messages, setData, error } = useAsync(() => api<Message[]>(`/orders/${orderId}/messages`), [orderId]);
  const [text, setText] = useState("");
  const [sendError, setSendError] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const t = setInterval(() => api<Message[]>(`/orders/${orderId}/messages`).then(setData).catch(() => {}), 5000);
    return () => clearInterval(t);
  }, [orderId, setData]);

  useEffect(() => endRef.current?.scrollIntoView({ block: "nearest" }), [messages?.length]);

  async function send(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    try {
      const m = await api<Message>(`/orders/${orderId}/messages`, { body: { body: text } });
      setData([...(messages ?? []), m]);
      setText("");
      setSendError(null);
    } catch (err) {
      setSendError((err as Error).message);
    }
  }

  return (
    <div className="card chat">
      <h3>Chat</h3>
      <p className="muted small">
        Keep all communication here; it&apos;s your evidence if something goes wrong. Phone numbers, links and bank details
        are hidden automatically.
      </p>
      <ErrorNote error={error} />
      <div className="messages">
        {messages?.map((m) => (
          <div key={m.id} className={`msg ${m.mine ? "mine" : ""}`}>
            <div className="bubble">
              {!m.mine && <div className="small muted">{m.sender_name}</div>}
              {m.body}
            </div>
            {m.warnings.map((w) => (
              <div key={w} className="warning">⚠️ {w}</div>
            ))}
          </div>
        ))}
        {messages?.length === 0 && <p className="muted small">No messages yet.</p>}
        <div ref={endRef} />
      </div>
      <form onSubmit={send} className="chat-form">
        <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Type a message…" maxLength={2000} />
        <button className="btn">Send</button>
      </form>
      <ErrorNote error={sendError} />
    </div>
  );
}
