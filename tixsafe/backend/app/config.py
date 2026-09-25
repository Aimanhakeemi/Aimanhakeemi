"""Platform rules. Kept in one place so the safety policy is easy to audit."""
import os
from datetime import timedelta

DATABASE_URL = os.getenv("TIXSAFE_DB", "sqlite:///./tixsafe.db")

# A buyer has this long to pay after reserving a listing before it is released.
PAYMENT_WINDOW = timedelta(minutes=15)
# After payment lands in escrow, the seller must transfer the ticket within this window
# (or before the event starts, whichever comes first) or the buyer is refunded automatically.
TRANSFER_WINDOW = timedelta(hours=24)
# Escrow is only released to the seller this long after the event starts, unless the buyer
# confirms earlier. This is the key protection: a fake ticket is discovered at the gate,
# while the money is still held.
RELEASE_AFTER_EVENT = timedelta(hours=24)
# Anti-scalping cap on asking price relative to face value.
MAX_MARKUP = 0.10
# Platform fee charged to the buyer, in percent of the ticket price.
BUYER_FEE_PCT = 5
# Sellers with this many strikes (failed transfers / lost disputes) are suspended.
MAX_STRIKES = 2
