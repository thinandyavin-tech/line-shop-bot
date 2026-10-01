from decimal import Decimal

import pytest

from line_shop_bot import promptpay as pp


def test_crc_matches_ccitt_false_check_value():
    # Standard check value for CRC-16/CCITT-FALSE over "123456789"
    assert pp.crc16_ccitt("123456789") == "29B1"


def test_phone_is_converted_to_international_format():
    assert pp.normalize_target("081-234-5678") == ("01", "0066812345678")
    assert pp.normalize_target("66812345678") == ("01", "0066812345678")


def test_national_id_uses_tag_02():
    assert pp.normalize_target("1-2345-67890-12-3") == ("02", "1234567890123")


@pytest.mark.parametrize("bad", ["12345", "", "08123"])
def test_rejects_invalid_targets(bad):
    with pytest.raises(ValueError):
        pp.payload(bad)


def test_dynamic_qr_with_amount():
    data = pp.payload("0812345678", Decimal("185"))
    fields = pp.parse(data)
    assert pp.is_valid(data)
    assert fields["01"] == "12"          # one-time QR
    assert fields["54"] == "185.00"
    assert fields["53"] == "764"         # THB
    assert fields["58"] == "TH"
    assert pp.parse(fields["29"]) == {"00": pp.PROMPTPAY_AID, "01": "0066812345678"}


def test_static_qr_without_amount():
    fields = pp.parse(pp.payload("0812345678"))
    assert fields["01"] == "11"
    assert "54" not in fields


def test_tampering_breaks_checksum():
    data = pp.payload("0812345678", 100)
    assert not pp.is_valid(data.replace("100.00", "900.00"))


def test_qr_png_renders():
    png = pp.qr_png(pp.payload("0812345678", 50))
    assert png.startswith(b"\x89PNG")
