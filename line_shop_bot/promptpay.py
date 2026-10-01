"""PromptPay QR payloads (Thai EMVCo standard) and QR image rendering."""
from __future__ import annotations

import io
import re
from decimal import Decimal

PROMPTPAY_AID = "A000000677010111"


def tlv(tag: str, value: str) -> str:
    """Encode one EMV field: 2-digit tag, 2-digit length, value."""
    if len(value) > 99:
        raise ValueError(f"field {tag} too long")
    return f"{tag}{len(value):02d}{value}"


def crc16_ccitt(data: str) -> str:
    """CRC-16/CCITT-FALSE as required by EMVCo (poly 0x1021, init 0xFFFF)."""
    crc = 0xFFFF
    for byte in data.encode("ascii"):
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else (crc << 1)
            crc &= 0xFFFF
    return f"{crc:04X}"


def normalize_target(target: str) -> tuple[str, str]:
    """Return (sub-tag, value) for a phone number (01) or 13-digit national/tax ID (02)."""
    digits = re.sub(r"\D", "", target)
    if len(digits) == 13:
        return "02", digits
    if len(digits) == 10 and digits.startswith("0"):
        return "01", "0066" + digits[1:]
    if len(digits) == 11 and digits.startswith("66"):
        return "01", "00" + digits
    raise ValueError("PromptPay ID must be a Thai mobile number or a 13-digit ID")


def payload(target: str, amount: Decimal | float | None = None) -> str:
    """Build a PromptPay payload; with an amount it becomes a one-time (dynamic) QR."""
    sub_tag, value = normalize_target(target)
    fields = [
        tlv("00", "01"),
        tlv("01", "12" if amount else "11"),
        tlv("29", tlv("00", PROMPTPAY_AID) + tlv(sub_tag, value)),
        tlv("53", "764"),  # THB
        tlv("58", "TH"),
    ]
    if amount:
        amount = Decimal(str(amount)).quantize(Decimal("0.01"))
        if amount <= 0:
            raise ValueError("amount must be positive")
        fields.append(tlv("54", f"{amount}"))
    body = "".join(fields) + "6304"
    return body + crc16_ccitt(body)


def parse(data: str) -> dict[str, str]:
    """Split a payload back into top-level fields (used by tests and for debugging)."""
    out, i = {}, 0
    while i < len(data):
        tag, length = data[i:i + 2], int(data[i + 2:i + 4])
        out[tag] = data[i + 4:i + 4 + length]
        i += 4 + length
    return out


def is_valid(data: str) -> bool:
    return len(data) > 8 and data[-8:-4] == "6304" and crc16_ccitt(data[:-4]) == data[-4:]


def qr_png(data: str) -> bytes:
    import qrcode  # imported lazily so the core logic has no image dependency

    buf = io.BytesIO()
    qrcode.make(data, box_size=10, border=2).save(buf, format="PNG")
    return buf.getvalue()
