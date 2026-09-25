"""Escrow state machine.

    AWAITING_PAYMENT --pay--> IN_ESCROW --seller transfers--> TRANSFERRED --buyer confirms / event+24h--> COMPLETED
          |                      |  \\                            |
      pay_by passes        transfer_by passes   dispute ------> DISPUTED --admin--> REFUNDED | COMPLETED
          v                      v
       EXPIRED                REFUNDED (+ seller strike)

The seller is never paid before the buyer has had a chance to use the ticket at the gate,
unless the buyer confirms early. Every transition is written to the order's audit trail.
"""
import secrets
from datetime import datetime

from sqlalchemy.orm import Session

from . import config
from .models import Listing, ListingStatus, Order, OrderEvent, OrderStatus, User, utcnow


class EscrowError(Exception):
    pass


ALLOWED = {
    OrderStatus.AWAITING_PAYMENT: {OrderStatus.IN_ESCROW, OrderStatus.EXPIRED},
    OrderStatus.IN_ESCROW: {OrderStatus.TRANSFERRED, OrderStatus.REFUNDED, OrderStatus.DISPUTED},
    OrderStatus.TRANSFERRED: {OrderStatus.COMPLETED, OrderStatus.DISPUTED},
    OrderStatus.DISPUTED: {OrderStatus.COMPLETED, OrderStatus.REFUNDED},
}
OPEN = {OrderStatus.AWAITING_PAYMENT, OrderStatus.IN_ESCROW, OrderStatus.TRANSFERRED, OrderStatus.DISPUTED}


def _move(order: Order, to: OrderStatus, note: str, now: datetime) -> None:
    if to not in ALLOWED.get(order.status, set()):
        raise EscrowError(f"Order is {order.status.value}; cannot move to {to.value}")
    order.status = to
    order.events.append(OrderEvent(status=to, note=note, at=now))
    if to not in OPEN:
        order.closed_at = now


def _strike(seller: User) -> None:
    seller.strikes += 1
    if seller.strikes >= config.MAX_STRIKES:
        seller.suspended = True


def _relist_or_cancel(listing: Listing, now: datetime) -> None:
    """After a failed sale the ticket goes back on sale only if nothing went wrong with it."""
    if listing.event.starts_at > now and not listing.seller.suspended:
        listing.status = ListingStatus.ACTIVE
    else:
        listing.status = ListingStatus.CANCELLED
        listing.live_key = None


def create_order(db: Session, listing: Listing, buyer: User, now: datetime | None = None) -> Order:
    now = now or utcnow()
    if listing.status != ListingStatus.ACTIVE:
        raise EscrowError("This ticket is no longer available")
    if listing.seller_id == buyer.id:
        raise EscrowError("You cannot buy your own listing")
    if listing.event.starts_at <= now:
        raise EscrowError("This event has already started")
    listing.status = ListingStatus.RESERVED
    order = Order(
        listing=listing,
        buyer=buyer,
        amount=listing.price,
        fee=round(listing.price * config.BUYER_FEE_PCT / 100),
        status=OrderStatus.AWAITING_PAYMENT,
        created_at=now,
        pay_by=now + config.PAYMENT_WINDOW,
    )
    order.events.append(OrderEvent(status=order.status, note="Ticket reserved. Pay within 15 minutes.", at=now))
    db.add(order)
    return order


def pay(order: Order, now: datetime | None = None) -> None:
    """Called when the payment gateway confirms the charge. Money is now held by TixSafe."""
    now = now or utcnow()
    apply_timeouts(order, now)
    event_start = order.listing.event.starts_at
    _move(order, OrderStatus.IN_ESCROW, "Payment received and held in escrow. Seller notified to transfer.", now)
    order.paid_at = now
    order.payment_ref = "PAY-" + secrets.token_hex(6).upper()
    order.transfer_by = min(now + config.TRANSFER_WINDOW, event_start)
    order.release_at = event_start + config.RELEASE_AFTER_EVENT


def mark_transferred(order: Order, note: str, now: datetime | None = None) -> None:
    now = now or utcnow()
    apply_timeouts(order, now)
    _move(order, OrderStatus.TRANSFERRED, f"Seller reports ticket transferred: {note}", now)
    order.transfer_note = note
    order.transferred_at = now


def confirm_received(order: Order, now: datetime | None = None) -> None:
    now = now or utcnow()
    apply_timeouts(order, now)
    if order.status != OrderStatus.TRANSFERRED:
        raise EscrowError("You can confirm once the seller has transferred the ticket")
    _move(order, OrderStatus.COMPLETED, "Buyer confirmed the ticket works. Funds released to seller.", now)
    order.listing.status = ListingStatus.SOLD


def dispute(order: Order, reason: str, now: datetime | None = None) -> None:
    now = now or utcnow()
    apply_timeouts(order, now)
    _move(order, OrderStatus.DISPUTED, f"Buyer opened a dispute: {reason}. Funds frozen.", now)
    order.dispute_reason = reason


def resolve(order: Order, refund: bool, note: str, now: datetime | None = None) -> None:
    now = now or utcnow()
    if order.status != OrderStatus.DISPUTED:
        raise EscrowError("Only disputed orders can be resolved")
    order.resolution_note = note
    if refund:
        _move(order, OrderStatus.REFUNDED, f"Dispute resolved for buyer, full refund: {note}", now)
        _strike(order.listing.seller)
        order.listing.status = ListingStatus.CANCELLED
        order.listing.live_key = None
    else:
        _move(order, OrderStatus.COMPLETED, f"Dispute resolved for seller, funds released: {note}", now)
        order.listing.status = ListingStatus.SOLD


def apply_timeouts(order: Order, now: datetime | None = None) -> bool:
    """Apply any deadline that has passed. Returns True if the order changed.

    Called lazily whenever an order is read or acted on, and in bulk by `sweep`.
    """
    now = now or utcnow()
    if order.status == OrderStatus.AWAITING_PAYMENT and now >= order.pay_by:
        _move(order, OrderStatus.EXPIRED, "Not paid in time. Ticket released back to the seller.", now)
        _relist_or_cancel(order.listing, now)
        return True
    if order.status == OrderStatus.IN_ESCROW and order.transfer_by and now >= order.transfer_by:
        _move(order, OrderStatus.REFUNDED, "Seller did not transfer in time. Buyer refunded in full.", now)
        _strike(order.listing.seller)
        order.listing.status = ListingStatus.CANCELLED
        order.listing.live_key = None
        return True
    if order.status == OrderStatus.TRANSFERRED and order.release_at and now >= order.release_at:
        _move(order, OrderStatus.COMPLETED, "No problem reported after the event. Funds released to seller.", now)
        order.listing.status = ListingStatus.SOLD
        return True
    return False


def sweep(db: Session, now: datetime | None = None) -> int:
    now = now or utcnow()
    changed = sum(
        apply_timeouts(o, now)
        for o in db.query(Order).filter(Order.status.in_([OrderStatus.AWAITING_PAYMENT, OrderStatus.IN_ESCROW, OrderStatus.TRANSFERRED]))
    )
    db.commit()
    return changed
