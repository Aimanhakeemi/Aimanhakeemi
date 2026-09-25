import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    # Identity verification is required before selling. The raw IC number is never stored.
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    ic_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    phone: Mapped[str | None] = mapped_column(String(32))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    strikes: Mapped[int] = mapped_column(Integer, default=0)
    suspended: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Token(Base):
    __tablename__ = "tokens"

    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user: Mapped[User] = relationship()


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    artist: Mapped[str] = mapped_column(String(200))
    venue: Mapped[str] = mapped_column(String(200))
    starts_at: Mapped[datetime] = mapped_column(DateTime)


class ListingStatus(str, enum.Enum):
    ACTIVE = "active"
    RESERVED = "reserved"
    SOLD = "sold"
    CANCELLED = "cancelled"


class Listing(Base):
    __tablename__ = "listings"
    # The same physical ticket can only be on sale once: this blocks the classic
    # "sell one ticket to five people" scam.
    __table_args__ = (UniqueConstraint("ticket_fingerprint", "live_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), index=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    section: Mapped[str] = mapped_column(String(80))
    seat: Mapped[str | None] = mapped_column(String(40))
    face_value: Mapped[int] = mapped_column(Integer)  # sen
    price: Mapped[int] = mapped_column(Integer)  # sen
    description: Mapped[str] = mapped_column(Text, default="")
    # sha256 of the normalised ticket order reference / barcode; the raw value is
    # only ever revealed to admins during a dispute.
    ticket_fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    # 1 while the listing is live (active/reserved/sold), NULL once cancelled, so the
    # unique constraint only applies to live listings (NULLs never collide).
    live_key: Mapped[int | None] = mapped_column(Integer, default=1)
    status: Mapped[ListingStatus] = mapped_column(Enum(ListingStatus), default=ListingStatus.ACTIVE)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    event: Mapped[Event] = relationship()
    seller: Mapped[User] = relationship()


class OrderStatus(str, enum.Enum):
    AWAITING_PAYMENT = "awaiting_payment"
    IN_ESCROW = "in_escrow"  # buyer paid, platform holds funds, seller must transfer
    TRANSFERRED = "transferred"  # seller says ticket sent, funds still held
    COMPLETED = "completed"  # funds released to seller
    DISPUTED = "disputed"
    REFUNDED = "refunded"
    EXPIRED = "expired"  # never paid


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"), index=True)
    buyer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    amount: Mapped[int] = mapped_column(Integer)  # ticket price, sen
    fee: Mapped[int] = mapped_column(Integer)  # buyer fee, sen
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), default=OrderStatus.AWAITING_PAYMENT)
    payment_ref: Mapped[str | None] = mapped_column(String(64))
    transfer_note: Mapped[str | None] = mapped_column(Text)
    dispute_reason: Mapped[str | None] = mapped_column(Text)
    resolution_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    pay_by: Mapped[datetime] = mapped_column(DateTime)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime)
    transfer_by: Mapped[datetime | None] = mapped_column(DateTime)
    transferred_at: Mapped[datetime | None] = mapped_column(DateTime)
    release_at: Mapped[datetime | None] = mapped_column(DateTime)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime)

    listing: Mapped[Listing] = relationship()
    buyer: Mapped[User] = relationship()
    events: Mapped[list["OrderEvent"]] = relationship(order_by="OrderEvent.id", cascade="all, delete-orphan")


class OrderEvent(Base):
    """Append-only audit trail of everything that happened to an order."""

    __tablename__ = "order_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus))
    note: Mapped[str] = mapped_column(Text)
    at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)  # already redacted
    flags: Mapped[str] = mapped_column(String(255), default="")  # comma-separated scam signals
    at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    sender: Mapped[User] = relationship()


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), unique=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    buyer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    rating: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str] = mapped_column(Text, default="")
    at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
