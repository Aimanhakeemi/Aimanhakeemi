# TixSafe: resell concert tickets without getting scammed

Buying resale concert tickets on Facebook, X, Telegram or Carousell often ends the same way: the buyer pays by bank transfer or DuitNow, and the seller disappears, sends a screenshot, or sells the same ticket to five people.

TixSafe puts **escrow** between buyer and seller. The buyer pays the platform. The seller is only paid **after the show**, once the buyer has used the ticket at the gate, or earlier if the buyer confirms it works.

## How each scam is blocked

| Scam | Protection | Where in code |
| --- | --- | --- |
| Buyer pays, seller vanishes | Money goes to escrow. Seller must transfer within 24h (or before the show), otherwise the buyer is **refunded automatically** and the seller gets a strike | `backend/app/escrow.py` |
| Fake or screenshot ticket | Escrow is only released **24h after the event starts**. Buyer can dispute until then, which freezes the funds | `escrow.py` · `RELEASE_AFTER_EVENT` |
| One ticket sold to many buyers | The ticket's order ref/barcode is normalised and SHA-256 fingerprinted. A **unique constraint** stops the same ticket being live twice, even under different accounts | `models.Listing.__table_args__` |
| "Just DuitNow/TNG me", "WhatsApp me" | In-app chat **redacts phone numbers, emails, links and bank account numbers**, and shows scam warnings to both sides | `backend/app/scam_filter.py` |
| Throwaway scammer accounts | Sellers must verify ID first. **One MyKad = one account** (stored hashed). 2 strikes = suspended, and their listings are hidden | `main.verify`, `escrow._strike` |
| Scalping | Price capped at face value + 10% | `config.MAX_MARKUP` |

Every state change is written to an append-only audit trail (`OrderEvent`). Support uses it, together with the chat, to resolve disputes.

```
AWAITING_PAYMENT ──pay──▶ IN_ESCROW ──seller transfers──▶ TRANSFERRED ──buyer confirms / event+24h──▶ COMPLETED
      │ 15 min              │ 24h, no transfer   └──dispute──┐     │
      ▼                     ▼                                ▼     ▼
   EXPIRED          REFUNDED (+ strike)              DISPUTED ──admin──▶ REFUNDED | COMPLETED
```

## Run it

**Backend** (Python 3.11+):

```bash
cd tixsafe/backend
pip install -r requirements.txt
python -m app.seed               # demo events + accounts
uvicorn app.main:app --reload    # http://localhost:8000/docs
pytest                           # 28 tests
```

**Frontend** (Node 20+):

```bash
cd tixsafe/frontend
npm install
npm run dev                      # http://localhost:5173 (proxies /api to :8000)
```

Demo logins (password `password123`): `buyer@demo.my`, `seller@demo.my` (verified), `admin@tixsafe.my` (resolves disputes).

## What's stubbed (needed before real money)

This is a working MVP. The rules and state machine are real, but three integrations are mocked:

1. **Payments.** `POST /orders/{id}/pay` just marks the order paid. Production needs a licensed gateway (e.g. FPX/DuitNow via Billplz, iPay88, Stripe MY) that supports holding funds or paying out later. The funds must sit in a trust/escrow account, and `pay()` should be triggered by the gateway's signed webhook, not the client.
2. **Identity (eKYC).** `/me/verify` only checks the MyKad format and that it's unique. Plug in an eKYC provider (MyKad OCR + liveness selfie) and SMS OTP.
3. **Ticket verification.** Today the fingerprint only stops duplicate listings. Where organisers or ticketing platforms (Ticket2U, Ticketmaster, etc.) expose transfer APIs, TixSafe could confirm the transfer directly instead of trusting the seller's note.

Also for production: run `POST /api/admin/sweep` from cron every minute (deadlines are otherwise applied lazily whenever an order is read), move from SQLite to Postgres, add rate limiting, and send email/push notifications at each step.

## Stack

FastAPI · SQLAlchemy 2 · SQLite · pytest | React 19 · TypeScript · Vite (no UI library)
