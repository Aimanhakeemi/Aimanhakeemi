import { useState } from "react";
import { api, rm, when, type EventWithCount, type Listing, type User } from "../api";
import { useSession } from "../App";
import { ErrorNote, useAsync } from "../components";

const MAX_MARKUP = 0.1;

export function SellPage() {
  const { user } = useSession();
  if (!user) return null;
  if (user.suspended)
    return (
      <div className="card">
        <h1>Selling suspended</h1>
        <p>Your account received {user.strikes} strikes for failed transfers or lost disputes. Contact support.</p>
      </div>
    );
  return (
    <>
      <h1>Sell a ticket</h1>
      {user.verified ? <ListingForm /> : <VerifyForm />}
      <MyListings />
    </>
  );
}

function VerifyForm() {
  const { setUser } = useSession();
  const [ic, setIc] = useState("");
  const [phone, setPhone] = useState("");
  const [error, setError] = useState<string | null>(null);
  return (
    <form
      className="card narrow"
      onSubmit={async (e) => {
        e.preventDefault();
        try {
          setUser(await api<User>("/me/verify", { body: { ic_number: ic, phone } }));
        } catch (err) {
          setError((err as Error).message);
        }
      }}
    >
      <h2>Step 1: Verify your identity</h2>
      <p className="muted">
        Every seller is tied to one MyKad. Scammers can&apos;t hide behind throwaway accounts, and buyers see the “ID
        verified” badge. Your IC number is hashed and never shown to anyone.
      </p>
      <label>
        MyKad number
        <input value={ic} onChange={(e) => setIc(e.target.value)} placeholder="990101-14-5678" required />
      </label>
      <label>
        Phone number
        <input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+60 12-345 6789" required />
      </label>
      <button className="btn">Verify</button>
      <p className="small muted">Demo: format check only. Production uses eKYC (MyKad scan + selfie) and SMS OTP.</p>
      <ErrorNote error={error} />
    </form>
  );
}

function ListingForm() {
  const { data: events } = useAsync(() => api<EventWithCount[]>("/events"), []);
  const [form, setForm] = useState({ event_id: "", section: "", seat: "", face: "", price: "", description: "", ref: "" });
  const [error, setError] = useState<string | null>(null);
  const [created, setCreated] = useState<Listing | null>(null);
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
    setForm({ ...form, [k]: e.target.value });

  const face = Math.round(Number(form.face) * 100);
  const cap = Math.floor(face * (1 + MAX_MARKUP));

  if (created)
    return (
      <div className="card narrow">
        <h2>Listed! 🎫</h2>
        <p>
          {created.section} for {created.event.name} at {rm(created.price)}. We&apos;ll notify you when someone pays. Don&apos;t
          transfer the ticket until the order says “Paid · held in escrow”.
        </p>
        <a className="btn" href={`#/listing/${created.id}`}>View listing</a>{" "}
        <button className="link" onClick={() => { setCreated(null); setForm({ ...form, section: "", seat: "", ref: "" }); }}>
          List another
        </button>
      </div>
    );

  return (
    <form
      className="card narrow"
      onSubmit={async (e) => {
        e.preventDefault();
        setError(null);
        try {
          setCreated(
            await api<Listing>("/listings", {
              body: {
                event_id: Number(form.event_id),
                section: form.section,
                seat: form.seat || null,
                face_value: face,
                price: Math.round(Number(form.price) * 100),
                description: form.description,
                ticket_reference: form.ref,
              },
            }),
          );
        } catch (err) {
          setError((err as Error).message);
        }
      }}
    >
      <h2>Ticket details</h2>
      <label>
        Event
        <select value={form.event_id} onChange={set("event_id")} required>
          <option value="">Choose an event…</option>
          {events?.map((e) => (
            <option key={e.id} value={e.id}>
              {e.name} · {when(e.starts_at)}
            </option>
          ))}
        </select>
      </label>
      <div className="cols">
        <label>
          Section / category
          <input value={form.section} onChange={set("section")} placeholder="CAT 1 – Zone A" required />
        </label>
        <label>
          Seat (optional)
          <input value={form.seat} onChange={set("seat")} placeholder="Row F, 12" />
        </label>
      </div>
      <div className="cols">
        <label>
          Face value (RM)
          <input type="number" min="1" step="0.01" value={form.face} onChange={set("face")} required />
        </label>
        <label>
          Your price (RM)
          <input type="number" min="1" step="0.01" max={face ? cap / 100 : undefined} value={form.price} onChange={set("price")} required />
          {face > 0 && <span className="hint">Max {rm(cap)} (face value + {MAX_MARKUP * 100}%)</span>}
        </label>
      </div>
      <label>
        Ticket order reference / barcode number
        <input value={form.ref} onChange={set("ref")} placeholder="e.g. T2U-88231-004" required minLength={4} />
        <span className="hint">
          Private. We store a fingerprint so the same ticket can&apos;t be sold twice, and use it if there&apos;s a dispute.
        </span>
      </label>
      <label>
        Notes for buyers
        <textarea value={form.description} onChange={set("description")} placeholder="How will you transfer? Why are you selling?" />
      </label>
      <button className="btn">List ticket</button>
      <ErrorNote error={error} />
    </form>
  );
}

function MyListings() {
  const { data: listings, reload } = useAsync(() => api<Listing[]>("/me/listings"), []);
  if (!listings?.length) return null;
  return (
    <section>
      <h2>Your listings</h2>
      <div className="list">
        {listings.map((l) => (
          <div key={l.id} className="card listing-row">
            <div>
              <h3>{l.event.name}</h3>
              <div className="muted small">{l.section} · {rm(l.price)}</div>
            </div>
            <div className="price">
              <span className={`pill ${l.status === "active" ? "ok" : "muted"}`}>{l.status}</span>
              {l.status === "active" && (
                <button className="link" onClick={() => api(`/listings/${l.id}`, { method: "DELETE" }).then(reload)}>
                  Withdraw
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
