from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import config, escrow, schemas as s
from .auth import admin_user, check_password, current_user, fingerprint, hash_password, issue_token
from .db import Base, engine, get_db
from .models import Event, Listing, ListingStatus, Message, Order, OrderStatus, Review, User, utcnow
from .scam_filter import WARNINGS, screen


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="TixSafe", description="Escrow-protected concert ticket resale", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])


# ---------- helpers ----------


def seller_profile(db: Session, user: User) -> s.SellerProfile:
    completed = (
        db.query(func.count(Order.id))
        .join(Listing)
        .filter(Listing.seller_id == user.id, Order.status == OrderStatus.COMPLETED)
        .scalar()
    )
    avg, count = db.query(func.avg(Review.rating), func.count(Review.id)).filter(Review.seller_id == user.id).one()
    return s.SellerProfile(
        id=user.id,
        name=user.name,
        verified=user.verified,
        suspended=user.suspended,
        completed_sales=completed,
        rating=round(float(avg), 2) if avg is not None else None,
        review_count=count,
        strikes=user.strikes,
        member_since=user.created_at,
    )


def listing_out(db: Session, listing: Listing) -> s.ListingOut:
    return s.ListingOut(
        id=listing.id,
        event=s.EventOut.model_validate(listing.event),
        section=listing.section,
        seat=listing.seat,
        face_value=listing.face_value,
        price=listing.price,
        description=listing.description,
        status=listing.status,
        created_at=listing.created_at,
        seller=seller_profile(db, listing.seller),
    )


def order_role(order: Order, user: User) -> str | None:
    if order.buyer_id == user.id:
        return "buyer"
    if order.listing.seller_id == user.id:
        return "seller"
    return "admin" if user.is_admin else None


def order_out(db: Session, order: Order, user: User) -> s.OrderOut:
    role = order_role(order, user)
    reviewed = db.query(Review.id).filter(Review.order_id == order.id).first() is not None
    return s.OrderOut(
        id=order.id,
        listing=listing_out(db, order.listing),
        buyer_name=order.buyer.name,
        role=role,
        amount=order.amount,
        fee=order.fee,
        status=order.status,
        payment_ref=order.payment_ref,
        transfer_note=order.transfer_note,
        dispute_reason=order.dispute_reason,
        resolution_note=order.resolution_note,
        pay_by=order.pay_by,
        transfer_by=order.transfer_by,
        release_at=order.release_at,
        events=[s.OrderEventOut.model_validate(e) for e in order.events],
        can_review=role == "buyer" and order.status == OrderStatus.COMPLETED and not reviewed,
    )


def load_order(db: Session, order_id: int, user: User) -> Order:
    order = db.get(Order, order_id)
    if not order or not order_role(order, user):
        raise HTTPException(404, "Order not found")
    if escrow.apply_timeouts(order):
        db.commit()
    return order


def run(db: Session, action) -> None:
    try:
        action()
    except escrow.EscrowError as e:
        db.rollback()
        raise HTTPException(409, str(e))
    db.commit()


# ---------- auth ----------


@app.post("/api/auth/register", response_model=s.AuthOut)
def register(body: s.Register, db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(409, "Email already registered")
    user = User(email=email, name=body.name, password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    return s.AuthOut(token=issue_token(db, user), user=s.UserOut.model_validate(user))


@app.post("/api/auth/login", response_model=s.AuthOut)
def login(body: s.Login, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email.lower()).first()
    if not user or not check_password(body.password, user.password_hash):
        raise HTTPException(401, "Wrong email or password")
    return s.AuthOut(token=issue_token(db, user), user=s.UserOut.model_validate(user))


@app.get("/api/me", response_model=s.UserOut)
def me(user: User = Depends(current_user)):
    return user


@app.post("/api/me/verify", response_model=s.UserOut)
def verify(body: s.Verify, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Identity check before selling.

    This demo only checks the MyKad format and that one IC maps to one account (so a
    banned scammer cannot just open a new account). In production, plug an eKYC provider
    in here (MyKad OCR + liveness selfie) and an SMS OTP for the phone number.
    """
    user.ic_hash = fingerprint("IC", body.ic_number)
    user.phone = body.phone
    user.verified = True
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "This IC is already linked to another account")
    return user


# ---------- events & listings ----------


@app.get("/api/events", response_model=list[s.EventWithCount])
def list_events(db: Session = Depends(get_db)):
    rows = (
        db.query(Event, func.count(Listing.id), func.min(Listing.price))
        .outerjoin(Listing, (Listing.event_id == Event.id) & (Listing.status == ListingStatus.ACTIVE))
        .filter(Event.starts_at > utcnow())
        .group_by(Event.id)
        .order_by(Event.starts_at)
        .all()
    )
    return [
        s.EventWithCount(**s.EventOut.model_validate(e).model_dump(), listings=n, lowest_price=low)
        for e, n, low in rows
    ]


@app.post("/api/events", response_model=s.EventOut)
def create_event(body: s.EventIn, _: User = Depends(admin_user), db: Session = Depends(get_db)):
    event = Event(**body.model_dump())
    db.add(event)
    db.commit()
    return event


@app.get("/api/events/{event_id}", response_model=s.EventOut)
def get_event(event_id: int, db: Session = Depends(get_db)):
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(404, "Event not found")
    return event


@app.get("/api/events/{event_id}/listings", response_model=list[s.ListingOut])
def event_listings(event_id: int, db: Session = Depends(get_db)):
    listings = (
        db.query(Listing)
        .join(User, Listing.seller_id == User.id)
        .filter(Listing.event_id == event_id, Listing.status == ListingStatus.ACTIVE, User.suspended.is_(False))
        .order_by(Listing.price)
        .all()
    )
    return [listing_out(db, l) for l in listings]


@app.get("/api/listings/{listing_id}", response_model=s.ListingOut)
def get_listing(listing_id: int, db: Session = Depends(get_db)):
    listing = db.get(Listing, listing_id)
    if not listing:
        raise HTTPException(404, "Listing not found")
    return listing_out(db, listing)


@app.get("/api/me/listings", response_model=list[s.ListingOut])
def my_listings(user: User = Depends(current_user), db: Session = Depends(get_db)):
    listings = db.query(Listing).filter(Listing.seller_id == user.id).order_by(Listing.created_at.desc()).all()
    return [listing_out(db, l) for l in listings]


@app.post("/api/listings", response_model=s.ListingOut)
def create_listing(body: s.ListingIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if user.suspended:
        raise HTTPException(403, "Your selling account is suspended")
    if not user.verified:
        raise HTTPException(403, "Verify your identity before selling")
    event = db.get(Event, body.event_id)
    if not event or event.starts_at <= utcnow():
        raise HTTPException(404, "Event not found or already started")
    cap = int(body.face_value * (1 + config.MAX_MARKUP))
    if body.price > cap:
        raise HTTPException(422, f"Price cannot exceed face value + {int(config.MAX_MARKUP * 100)}% (RM {cap / 100:.2f})")
    listing = Listing(
        event=event,
        seller=user,
        section=body.section,
        seat=body.seat,
        face_value=body.face_value,
        price=body.price,
        description=screen(body.description).body,
        ticket_fingerprint=fingerprint(str(event.id), body.ticket_reference),
    )
    db.add(listing)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "This ticket is already listed on TixSafe. Each ticket can only be sold once.")
    return listing_out(db, listing)


@app.delete("/api/listings/{listing_id}", response_model=s.ListingOut)
def cancel_listing(listing_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    listing = db.get(Listing, listing_id)
    if not listing or listing.seller_id != user.id:
        raise HTTPException(404, "Listing not found")
    if listing.status != ListingStatus.ACTIVE:
        raise HTTPException(409, "Only active listings can be withdrawn")
    listing.status = ListingStatus.CANCELLED
    listing.live_key = None
    db.commit()
    return listing_out(db, listing)


@app.get("/api/sellers/{user_id}", response_model=s.SellerProfile)
def get_seller(user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "Seller not found")
    return seller_profile(db, user)


@app.get("/api/sellers/{user_id}/reviews", response_model=list[s.ReviewOut])
def seller_reviews(user_id: int, db: Session = Depends(get_db)):
    return db.query(Review).filter(Review.seller_id == user_id).order_by(Review.at.desc()).limit(50).all()


# ---------- orders / escrow ----------


@app.post("/api/listings/{listing_id}/buy", response_model=s.OrderOut)
def buy(listing_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    listing = db.get(Listing, listing_id)
    if not listing or listing.seller.suspended:
        raise HTTPException(404, "Listing not found")
    order = None

    def action():
        nonlocal order
        order = escrow.create_order(db, listing, user)

    run(db, action)
    return order_out(db, order, user)


@app.get("/api/orders", response_model=list[s.OrderOut])
def my_orders(user: User = Depends(current_user), db: Session = Depends(get_db)):
    orders = (
        db.query(Order)
        .join(Listing)
        .filter((Order.buyer_id == user.id) | (Listing.seller_id == user.id))
        .order_by(Order.created_at.desc())
        .all()
    )
    if sum(escrow.apply_timeouts(o) for o in orders):
        db.commit()
    return [order_out(db, o, user) for o in orders]


@app.get("/api/orders/{order_id}", response_model=s.OrderOut)
def get_order(order_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return order_out(db, load_order(db, order_id, user), user)


def _require(order: Order, user: User, role: str) -> None:
    if order_role(order, user) != role:
        raise HTTPException(403, f"Only the {role} can do this")


@app.post("/api/orders/{order_id}/pay", response_model=s.OrderOut)
def pay(order_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Demo payment. In production this is the FPX/DuitNow/card gateway webhook, and the
    money sits in a trust/escrow account until release."""
    order = load_order(db, order_id, user)
    _require(order, user, "buyer")
    run(db, lambda: escrow.pay(order))
    return order_out(db, order, user)


@app.post("/api/orders/{order_id}/transfer", response_model=s.OrderOut)
def transfer(order_id: int, body: s.TransferIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    order = load_order(db, order_id, user)
    _require(order, user, "seller")
    run(db, lambda: escrow.mark_transferred(order, screen(body.note).body))
    return order_out(db, order, user)


@app.post("/api/orders/{order_id}/confirm", response_model=s.OrderOut)
def confirm(order_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    order = load_order(db, order_id, user)
    _require(order, user, "buyer")
    run(db, lambda: escrow.confirm_received(order))
    return order_out(db, order, user)


@app.post("/api/orders/{order_id}/dispute", response_model=s.OrderOut)
def open_dispute(order_id: int, body: s.DisputeIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    order = load_order(db, order_id, user)
    _require(order, user, "buyer")
    run(db, lambda: escrow.dispute(order, body.reason))
    return order_out(db, order, user)


@app.post("/api/orders/{order_id}/review", response_model=s.ReviewOut)
def review(order_id: int, body: s.ReviewIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    order = load_order(db, order_id, user)
    _require(order, user, "buyer")
    if order.status != OrderStatus.COMPLETED:
        raise HTTPException(409, "You can review once the order is completed")
    if db.query(Review).filter(Review.order_id == order.id).first():
        raise HTTPException(409, "Already reviewed")
    r = Review(order_id=order.id, seller_id=order.listing.seller_id, buyer_id=user.id, rating=body.rating, comment=body.comment)
    db.add(r)
    db.commit()
    return r


# ---------- chat ----------


def message_out(m: Message, user: User) -> s.MessageOut:
    flags = [f for f in m.flags.split(",") if f]
    return s.MessageOut(
        id=m.id, sender_name=m.sender.name, mine=m.sender_id == user.id, body=m.body,
        flags=flags, warnings=[WARNINGS[f] for f in flags], at=m.at,
    )


@app.get("/api/orders/{order_id}/messages", response_model=list[s.MessageOut])
def get_messages(order_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    order = load_order(db, order_id, user)
    msgs = db.query(Message).filter(Message.order_id == order.id).order_by(Message.id).all()
    return [message_out(m, user) for m in msgs]


@app.post("/api/orders/{order_id}/messages", response_model=s.MessageOut)
def send_message(order_id: int, body: s.MessageIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    order = load_order(db, order_id, user)
    if order_role(order, user) == "admin":
        raise HTTPException(403, "Admins cannot post in order chat")
    screened = screen(body.body)
    m = Message(order_id=order.id, sender=user, body=screened.body, flags=",".join(screened.flags))
    db.add(m)
    db.commit()
    return message_out(m, user)


# ---------- admin ----------


@app.get("/api/admin/disputes", response_model=list[s.OrderOut])
def disputes(user: User = Depends(admin_user), db: Session = Depends(get_db)):
    orders = db.query(Order).filter(Order.status == OrderStatus.DISPUTED).order_by(Order.created_at).all()
    return [order_out(db, o, user) for o in orders]


@app.post("/api/admin/orders/{order_id}/resolve", response_model=s.OrderOut)
def resolve(order_id: int, body: s.ResolveIn, user: User = Depends(admin_user), db: Session = Depends(get_db)):
    order = load_order(db, order_id, user)
    run(db, lambda: escrow.resolve(order, body.refund, body.note))
    return order_out(db, order, user)


@app.post("/api/admin/sweep")
def sweep(_: User = Depends(admin_user), db: Session = Depends(get_db)):
    """Apply expired deadlines to every open order. Run from cron every minute in production."""
    return {"changed": escrow.sweep(db)}
