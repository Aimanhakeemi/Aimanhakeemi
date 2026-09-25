from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import create_engine

from app import main
from app.auth import hash_password
from app.db import Base, get_db
from app.models import Event, User, utcnow


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def client(db):
    main.app.dependency_overrides[get_db] = lambda: db
    yield TestClient(main.app)
    main.app.dependency_overrides.clear()


@pytest.fixture
def event(db):
    e = Event(name="Coldplay KL", artist="Coldplay", venue="Bukit Jalil", starts_at=utcnow() + timedelta(days=10))
    db.add(e)
    db.commit()
    return e


def register(client, name, email=None):
    r = client.post("/api/auth/register", json={"email": email or f"{name.lower()}@x.my", "name": name, "password": "password123"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture
def seller(client):
    h = register(client, "Seller")
    r = client.post("/api/me/verify", headers=h, json={"ic_number": "990101-14-5678", "phone": "+60123456789"})
    assert r.status_code == 200, r.text
    return h


@pytest.fixture
def buyer(client):
    return register(client, "Buyer")


@pytest.fixture
def admin(client, db):
    h = register(client, "Admin")
    db.query(User).filter(User.email == "admin@x.my").update({"is_admin": True})
    db.commit()
    return h


@pytest.fixture
def listing(client, seller, event):
    r = client.post("/api/listings", headers=seller, json={
        "event_id": event.id, "section": "PEN A", "face_value": 50000, "price": 52000, "ticket_reference": "ORD-123-456",
    })
    assert r.status_code == 200, r.text
    return r.json()
