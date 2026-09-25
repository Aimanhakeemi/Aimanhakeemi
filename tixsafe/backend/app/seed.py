"""Demo data: `python -m app.seed`. Creates an admin, a seller, a buyer and some events."""
from datetime import timedelta

from .auth import fingerprint, hash_password
from .db import Base, SessionLocal, engine
from .models import Event, Listing, User, utcnow

PASSWORD = "password123"


def seed() -> None:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    db = SessionLocal()
    # 12:00 UTC = 8pm in Malaysia
    now = utcnow().replace(hour=12, minute=0, second=0, microsecond=0)

    admin = User(email="admin@tixsafe.my", name="TixSafe Support", password_hash=hash_password(PASSWORD), is_admin=True, verified=True)
    seller = User(email="seller@demo.my", name="Aisyah R.", password_hash=hash_password(PASSWORD), verified=True,
                  ic_hash=fingerprint("IC", "990101145678"), phone="+60123456789")
    buyer = User(email="buyer@demo.my", name="Daniel T.", password_hash=hash_password(PASSWORD))
    db.add_all([admin, seller, buyer])

    events = [
        Event(name="Blackpink World Tour", artist="BLACKPINK", venue="Bukit Jalil National Stadium", starts_at=now + timedelta(days=21)),
        Event(name="Coldplay: Music of the Spheres", artist="Coldplay", venue="Bukit Jalil National Stadium", starts_at=now + timedelta(days=45)),
        Event(name="Siti Nurhaliza Live", artist="Siti Nurhaliza", venue="Axiata Arena", starts_at=now + timedelta(days=10)),
        Event(name="Ed Sheeran +-=÷× Tour", artist="Ed Sheeran", venue="Bukit Jalil National Stadium", starts_at=now + timedelta(days=60)),
    ]
    db.add_all(events)
    db.flush()

    for i, (event, section, face, price) in enumerate([
        (events[0], "CAT 1 – Zone A", 88800, 92000),
        (events[0], "CAT 3", 48800, 48800),
        (events[1], "PEN B (Standing)", 65800, 70000),
        (events[2], "Lower Tier 104", 35000, 32000),
    ]):
        db.add(Listing(event=event, seller=seller, section=section, seat=None, face_value=face, price=price,
                       description="Can't make it anymore. Official transfer through the ticketing app.",
                       ticket_fingerprint=fingerprint(str(event.id), f"DEMO-{i}")))
    db.commit()
    print(f"Seeded. Log in as admin@tixsafe.my / seller@demo.my / buyer@demo.my with password '{PASSWORD}'")


if __name__ == "__main__":
    seed()
