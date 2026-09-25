import { api, rm, when, type EventWithCount, type Listing, type Event } from "../api";
import { ErrorNote, SellerCard, useAsync } from "../components";

export function Browse() {
  const { data: events, error } = useAsync(() => api<EventWithCount[]>("/events"), []);
  return (
    <>
      <section className="hero">
        <h1>Resell concert tickets without getting scammed.</h1>
        <p>
          Your money is held in escrow and only released to the seller after the show, once you&apos;re through the gate.
          Fake ticket? Seller no-show? You get it back.
        </p>
        <div className="hero-points">
          <span>🔒 Escrow until after the event</span>
          <span>🪪 ID-verified sellers</span>
          <span>🎫 Each ticket can only be listed once</span>
          <span>💬 Chat that blocks off-platform payment</span>
        </div>
      </section>
      <h2>Upcoming events</h2>
      <ErrorNote error={error} />
      <div className="grid">
        {events?.map((e) => (
          <a key={e.id} href={`#/event/${e.id}`} className="card event-card">
            <div className="muted small">{when(e.starts_at)}</div>
            <h3>{e.name}</h3>
            <div className="muted">{e.venue}</div>
            <div className="event-foot">
              <span>{e.listings} ticket{e.listings === 1 ? "" : "s"}</span>
              {e.lowest_price !== null && <strong>from {rm(e.lowest_price)}</strong>}
            </div>
          </a>
        ))}
        {events?.length === 0 && <p className="muted">No upcoming events yet.</p>}
      </div>
    </>
  );
}

export function EventPage({ id }: { id: number }) {
  const { data: listings, error } = useAsync(() => api<Listing[]>(`/events/${id}/listings`), [id]);
  const { data: event } = useAsync(() => api<Event>(`/events/${id}`), [id]);
  return (
    <>
      <a href="#/" className="back">← All events</a>
      {event && (
        <div className="page-head">
          <h1>{event.name}</h1>
          <p className="muted">
            {event.venue} · {when(event.starts_at)}
          </p>
        </div>
      )}
      <ErrorNote error={error} />
      <div className="list">
        {listings?.map((l) => (
          <a key={l.id} href={`#/listing/${l.id}`} className="card listing-row">
            <div>
              <h3>{l.section}{l.seat && ` · ${l.seat}`}</h3>
              <SellerCard seller={l.seller} />
            </div>
            <div className="price">
              <strong>{rm(l.price)}</strong>
              <span className="muted small">face value {rm(l.face_value)}</span>
            </div>
          </a>
        ))}
        {listings?.length === 0 && <p className="muted">No tickets for sale right now. Check back later.</p>}
      </div>
    </>
  );
}
