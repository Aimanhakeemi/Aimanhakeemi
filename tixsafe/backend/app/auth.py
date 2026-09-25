import hashlib
import hmac
import os
import secrets

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .db import get_db
from .models import Token, User

_ITERATIONS = 200_000


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    return f"{salt.hex()}${digest.hex()}"


def check_password(password: str, stored: str) -> bool:
    salt, digest = stored.split("$")
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), _ITERATIONS)
    return hmac.compare_digest(candidate.hex(), digest)


def fingerprint(*parts: str) -> str:
    normalised = "|".join("".join(p.split()).upper() for p in parts)
    return hashlib.sha256(normalised.encode()).hexdigest()


def issue_token(db: Session, user: User) -> str:
    token = secrets.token_urlsafe(32)
    db.add(Token(token=token, user_id=user.id))
    db.commit()
    return token


def current_user(authorization: str = Header(default=""), db: Session = Depends(get_db)) -> User:
    scheme, _, token = authorization.partition(" ")
    row = db.get(Token, token) if scheme.lower() == "bearer" and token else None
    if not row:
        raise HTTPException(401, "Please log in")
    return row.user


def admin_user(user: User = Depends(current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(403, "Admins only")
    return user
