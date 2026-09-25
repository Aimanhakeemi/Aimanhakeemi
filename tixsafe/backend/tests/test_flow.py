from datetime import timedelta

from app import escrow
from app.models import Order, OrderStatus, User, utcnow

from .conftest import register


def buy_and_pay(client, buyer, listing):
    order = client.post(f"/api/listings/{listing['id']}/buy", headers=buyer).json()
    return client.post(f"/api/orders/{order['id']}/pay", headers=buyer).json()


def test_happy_path_holds_money_until_buyer_confirms(client, seller, buyer, listing):
    order = client.post(f"/api/listings/{listing['id']}/buy", headers=buyer).json()
    assert order["status"] == "awaiting_payment"
    assert order["fee"] == 2600  # 5% of RM520

    # Listing disappears from the marketplace while reserved.
    assert client.get(f"/api/events/{listing['event']['id']}/listings").json() == []

    # Seller cannot transfer before the buyer pays.
    assert client.post(f"/api/orders/{order['id']}/transfer", headers=seller, json={"note": "sent via app"}).status_code == 409

    order = client.post(f"/api/orders/{order['id']}/pay", headers=buyer).json()
    assert order["status"] == "in_escrow" and order["payment_ref"].startswith("PAY-")

    # Only the seller may mark transfer, only the buyer may confirm.
    assert client.post(f"/api/orders/{order['id']}/transfer", headers=buyer, json={"note": "sent via app"}).status_code == 403
    order = client.post(f"/api/orders/{order['id']}/transfer", headers=seller, json={"note": "Ticket2U transfer"}).json()
    assert order["status"] == "transferred"
    assert client.post(f"/api/orders/{order['id']}/confirm", headers=seller).status_code == 403

    order = client.post(f"/api/orders/{order['id']}/confirm", headers=buyer).json()
    assert order["status"] == "completed" and order["can_review"]
    assert [e["status"] for e in order["events"]] == ["awaiting_payment", "in_escrow", "transferred", "completed"]

    r = client.post(f"/api/orders/{order['id']}/review", headers=buyer, json={"rating": 5, "comment": "Legit!"})
    assert r.status_code == 200
    profile = client.get(f"/api/sellers/{listing['seller']['id']}").json()
    assert profile["completed_sales"] == 1 and profile["rating"] == 5.0


def test_unverified_user_cannot_sell(client, buyer, event):
    r = client.post("/api/listings", headers=buyer, json={
        "event_id": event.id, "section": "A", "face_value": 100, "price": 100, "ticket_reference": "ABCD1",
    })
    assert r.status_code == 403


def test_price_cap(client, seller, event):
    r = client.post("/api/listings", headers=seller, json={
        "event_id": event.id, "section": "A", "face_value": 10000, "price": 11001, "ticket_reference": "ABCD1",
    })
    assert r.status_code == 422 and "RM 110.00" in r.json()["detail"]


def test_same_ticket_cannot_be_listed_twice(client, seller, event, listing):
    other = register(client, "Other")
    client.post("/api/me/verify", headers=other, json={"ic_number": "880202105555", "phone": "0123334444"})
    # Different spacing / case still matches the same ticket.
    r = client.post("/api/listings", headers=other, json={
        "event_id": event.id, "section": "PEN A", "face_value": 50000, "price": 50000, "ticket_reference": "ord-123-456 ",
    })
    assert r.status_code == 409
    # Once withdrawn, the ticket can be listed again.
    client.delete(f"/api/listings/{listing['id']}", headers=seller)
    r = client.post("/api/listings", headers=seller, json={
        "event_id": event.id, "section": "PEN A", "face_value": 50000, "price": 50000, "ticket_reference": "ORD-123-456",
    })
    assert r.status_code == 200


def test_one_ic_one_account(client, seller):
    other = register(client, "Other")
    r = client.post("/api/me/verify", headers=other, json={"ic_number": "990101145678", "phone": "0123334444"})
    assert r.status_code == 409


def test_cannot_buy_own_listing(client, seller, listing):
    assert client.post(f"/api/listings/{listing['id']}/buy", headers=seller).status_code == 409


def test_unpaid_reservation_expires_and_relists(client, db, buyer, listing):
    order = client.post(f"/api/listings/{listing['id']}/buy", headers=buyer).json()
    o = db.get(Order, order["id"])
    escrow.apply_timeouts(o, o.pay_by + timedelta(seconds=1))
    db.commit()
    assert o.status == OrderStatus.EXPIRED
    assert len(client.get(f"/api/events/{listing['event']['id']}/listings").json()) == 1


def test_seller_no_show_refunds_buyer_and_strikes_seller(client, db, seller, buyer, listing):
    order = buy_and_pay(client, buyer, listing)
    o = db.get(Order, order["id"])
    escrow.apply_timeouts(o, o.transfer_by)
    db.commit()
    assert o.status == OrderStatus.REFUNDED
    assert o.listing.seller.strikes == 1


def test_funds_auto_release_only_after_event(client, db, seller, buyer, listing):
    order = buy_and_pay(client, buyer, listing)
    client.post(f"/api/orders/{order['id']}/transfer", headers=seller, json={"note": "sent via app"})
    o = db.get(Order, order["id"])
    event_start = o.listing.event.starts_at
    assert not escrow.apply_timeouts(o, event_start)  # still held on show night
    assert escrow.apply_timeouts(o, event_start + timedelta(hours=24))
    assert o.status == OrderStatus.COMPLETED


def test_fake_ticket_dispute_refunds_buyer(client, db, seller, buyer, admin, listing):
    order = buy_and_pay(client, buyer, listing)
    client.post(f"/api/orders/{order['id']}/transfer", headers=seller, json={"note": "sent screenshot"})
    r = client.post(f"/api/orders/{order['id']}/dispute", headers=buyer, json={"reason": "Barcode rejected at the gate, ticket was a screenshot"})
    assert r.json()["status"] == "disputed"
    # Buyer can no longer confirm, and auto-release no longer applies.
    assert client.post(f"/api/orders/{order['id']}/confirm", headers=buyer).status_code == 409
    o = db.get(Order, order["id"])
    assert not escrow.apply_timeouts(o, utcnow() + timedelta(days=365))

    assert len(client.get("/api/admin/disputes", headers=admin).json()) == 1
    assert client.get("/api/admin/disputes", headers=buyer).status_code == 403
    r = client.post(f"/api/admin/orders/{order['id']}/resolve", headers=admin, json={"refund": True, "note": "Organiser confirmed barcode invalid"})
    assert r.json()["status"] == "refunded"
    assert client.get(f"/api/sellers/{listing['seller']['id']}").json()["strikes"] == 1


def test_two_strikes_suspends_seller(client, db, seller, buyer, event):
    for ref in ("T1-0001", "T2-0002"):
        listing = client.post("/api/listings", headers=seller, json={
            "event_id": event.id, "section": "A", "face_value": 100, "price": 100, "ticket_reference": ref,
        }).json()
        o = db.get(Order, buy_and_pay(client, buyer, listing)["id"])
        escrow.apply_timeouts(o, o.transfer_by)
        db.commit()
    assert db.query(User).filter(User.email == "seller@x.my").one().suspended
    r = client.post("/api/listings", headers=seller, json={
        "event_id": event.id, "section": "A", "face_value": 100, "price": 100, "ticket_reference": "T3-0003",
    })
    assert r.status_code == 403


def test_outsiders_cannot_see_order(client, buyer, listing):
    order = client.post(f"/api/listings/{listing['id']}/buy", headers=buyer).json()
    stranger = register(client, "Stranger")
    assert client.get(f"/api/orders/{order['id']}", headers=stranger).status_code == 404
    assert client.get(f"/api/orders/{order['id']}/messages", headers=stranger).status_code == 404


def test_chat_redacts_off_platform_payment(client, seller, buyer, listing):
    order = client.post(f"/api/listings/{listing['id']}/buy", headers=buyer).json()
    r = client.post(f"/api/orders/{order['id']}/messages", headers=seller,
                    json={"body": "Cancel this and just DuitNow me at 0123456789, whatsapp faster. Maybank 1234 5678 9012"})
    m = r.json()
    assert "0123456789" not in m["body"] and "1234 5678 9012" not in m["body"]
    assert {"off_platform_payment", "contact_details", "off_platform_contact"} <= set(m["flags"])
    assert m["warnings"]
    msgs = client.get(f"/api/orders/{order['id']}/messages", headers=buyer).json()
    assert msgs[0]["mine"] is False and msgs[0]["flags"] == m["flags"]
