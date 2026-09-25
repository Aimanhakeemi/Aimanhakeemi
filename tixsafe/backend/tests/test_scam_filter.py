import pytest

from app.scam_filter import screen


@pytest.mark.parametrize("text,flag", [
    ("Boleh bank in terus ke akaun saya?", "off_platform_payment"),
    ("TNG pun boleh", "off_platform_payment"),
    ("Pay me directly, cheaper", "off_platform_payment"),
    ("whatsapp me la", "off_platform_contact"),
    ("pm me for more", "off_platform_contact"),
    ("check https://ticket-transfer.xyz/claim", "link"),
    ("wa.me/60123456789", "link"),
    ("my email is scam@mail.com", "contact_details"),
    ("call +6012-345 6789", "contact_details"),
    ("urgent, many people want this", "pressure"),
])
def test_flags(text, flag):
    assert flag in screen(text).flags


@pytest.mark.parametrize("text", [
    "Hi, is this seat near the stage?",
    "Transferred! Check your Ticket2U app please",
    "Section 104, row 12",
    "Thanks, see you at the show on 12/10",
])
def test_normal_messages_pass_untouched(text):
    result = screen(text)
    assert result.flags == [] and result.body == text


def test_redacts_values():
    body = screen("Maybank 5140 1234 5678, call 012-3456789").body
    assert "5140" not in body and "3456789" not in body
    assert "[phone removed]" in body and "[account no. removed]" in body
