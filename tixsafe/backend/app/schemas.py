from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import ListingStatus, OrderStatus


class Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Register(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=8, max_length=128)


class Login(BaseModel):
    email: str
    password: str


class Verify(BaseModel):
    ic_number: str = Field(description="MyKad number, e.g. 990101-14-5678")
    phone: str

    @field_validator("ic_number")
    @classmethod
    def mykad(cls, v: str) -> str:
        digits = v.replace("-", "").replace(" ", "")
        if not (digits.isdigit() and len(digits) == 12):
            raise ValueError("MyKad number must be 12 digits")
        return digits


class UserOut(Out):
    id: int
    email: str
    name: str
    verified: bool
    is_admin: bool
    strikes: int
    suspended: bool


class AuthOut(BaseModel):
    token: str
    user: UserOut


class SellerProfile(BaseModel):
    id: int
    name: str
    verified: bool
    suspended: bool
    completed_sales: int
    rating: float | None
    review_count: int
    strikes: int
    member_since: datetime


class EventIn(BaseModel):
    name: str
    artist: str
    venue: str
    starts_at: datetime


class EventOut(Out):
    id: int
    name: str
    artist: str
    venue: str
    starts_at: datetime


class EventWithCount(EventOut):
    listings: int
    lowest_price: int | None


class ListingIn(BaseModel):
    event_id: int
    section: str = Field(min_length=1, max_length=80)
    seat: str | None = Field(default=None, max_length=40)
    face_value: int = Field(gt=0, description="In sen")
    price: int = Field(gt=0, description="In sen")
    description: str = Field(default="", max_length=1000)
    ticket_reference: str = Field(min_length=4, max_length=200, description="Order ref / barcode. Never shown publicly.")


class ListingOut(Out):
    id: int
    event: EventOut
    section: str
    seat: str | None
    face_value: int
    price: int
    description: str
    status: ListingStatus
    created_at: datetime
    seller: SellerProfile


class OrderEventOut(Out):
    status: OrderStatus
    note: str
    at: datetime


class OrderOut(BaseModel):
    id: int
    listing: ListingOut
    buyer_name: str
    role: str  # "buyer" | "seller" | "admin" from the caller's perspective
    amount: int
    fee: int
    status: OrderStatus
    payment_ref: str | None
    transfer_note: str | None
    dispute_reason: str | None
    resolution_note: str | None
    pay_by: datetime
    transfer_by: datetime | None
    release_at: datetime | None
    events: list[OrderEventOut]
    can_review: bool


class TransferIn(BaseModel):
    note: str = Field(min_length=5, max_length=500, description="How the ticket was sent, e.g. 'Ticket2U transfer to buyer email'")


class DisputeIn(BaseModel):
    reason: str = Field(min_length=10, max_length=1000)


class ResolveIn(BaseModel):
    refund: bool
    note: str = Field(min_length=5, max_length=1000)


class MessageIn(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class MessageOut(BaseModel):
    id: int
    sender_name: str
    mine: bool
    body: str
    flags: list[str]
    warnings: list[str]
    at: datetime


class ReviewIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=1000)


class ReviewOut(Out):
    rating: int
    comment: str
    at: datetime
