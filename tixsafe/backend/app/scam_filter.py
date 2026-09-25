"""Chat guard.

Almost every social-media ticket scam ends the same way: the "seller" moves the buyer
off-platform ("just DuitNow me", "WhatsApp me") where there is no escrow. The chat guard
redacts contact and payment details and tells both sides why, so the only way to pay
is through escrow.
"""
import re
from dataclasses import dataclass, field

PHONE = re.compile(r"(?:\+?6?0)[\s-]?1\d[\s-]?\d{3,4}[\s-]?\d{4}\b|\b01\d{8,9}\b")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
URL = re.compile(r"\b(?:https?://|www\.)\S+|\b(?:wa\.me|t\.me|bit\.ly|tinyurl\.com)/\S*", re.I)
# Long digit runs look like bank account numbers (Malaysian accounts are 10-16 digits).
ACCOUNT = re.compile(r"\b\d(?:[\s-]?\d){9,15}\b")

OFF_PLATFORM_PAYMENT = re.compile(
    r"\b(bank\s*(?:in|transfer)|transfer\s+(?:to\s+)?(?:my|me)|duit\s*now|tng|touch\s*[`'n ]*\s*go|"
    r"e-?wallet|boost|grab\s*pay|shopee\s*pay|maybank2u|m2u|cimb\s*clicks|fpx\s+direct|"
    r"pay\s+(?:outside|direct(?:ly)?|me\s+direct(?:ly)?)|cash\s*(?:only|on)|deposit\s+first|"
    r"crypto|usdt|gift\s*card)\b",
    re.I,
)
OFF_PLATFORM_CONTACT = re.compile(
    r"\b(whats\s*app|wasap|watsap|wsap|telegram|tele|dm\s+me|pm\s+me|ig\s+dm|insta(?:gram)?|"
    r"wechat|line\s+id|call\s+me|text\s+me)\b",
    re.I,
)
PRESSURE = re.compile(
    r"\b(urgent(?:ly)?|last\s+chance|many\s+(?:people|buyers)\s+(?:want|asking)|"
    r"first\s+come|pay\s+now\s+or|within\s+\d+\s*min)\b",
    re.I,
)

WARNINGS = {
    "off_platform_payment": "Payment outside TixSafe is not protected by escrow. Never pay a seller directly.",
    "contact_details": "Contact details are hidden. Keep the conversation here so it can be used in a dispute.",
    "off_platform_contact": "Moving to WhatsApp/Telegram/DM is the #1 sign of a scam. Stay on TixSafe.",
    "link": "Links are hidden. Scammers use fake 'payment' or 'ticket transfer' pages to steal details.",
    "pressure": "Pressure to rush is a common scam tactic. Your payment is held until after the show anyway.",
}


@dataclass
class Screened:
    body: str
    flags: list[str] = field(default_factory=list)

    @property
    def warnings(self) -> list[str]:
        return [WARNINGS[f] for f in self.flags]


def screen(text: str) -> Screened:
    flags: list[str] = []
    body = text

    for pattern, label, flag in (
        (URL, "[link removed]", "link"),
        (EMAIL, "[email removed]", "contact_details"),
        (PHONE, "[phone removed]", "contact_details"),
        (ACCOUNT, "[account no. removed]", "off_platform_payment"),
    ):
        body, n = pattern.subn(label, body)
        if n and flag not in flags:
            flags.append(flag)

    for pattern, flag in (
        (OFF_PLATFORM_PAYMENT, "off_platform_payment"),
        (OFF_PLATFORM_CONTACT, "off_platform_contact"),
        (PRESSURE, "pressure"),
    ):
        if pattern.search(text) and flag not in flags:
            flags.append(flag)

    return Screened(body=body, flags=flags)
