import base64
import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

from line_shop_bot.app import create_app
from line_shop_bot.config import Settings

from .conftest import ROOT

SECRET = "test-secret"


class FakeLine:
    def __init__(self):
        self.replies, self.pushes = [], []

    async def reply(self, token, messages):
        self.replies.append((token, messages))

    async def push(self, to, messages):
        self.pushes.append((to, messages))


@pytest.fixture
def setup(tmp_path):
    settings = Settings(line_channel_secret=SECRET, line_access_token="x", promptpay_id="0812345678",
                        app_base_url="https://shop.test", owner_user_id="U-owner",
                        menu_path=str(ROOT / "menu.example.json"), database_path=str(tmp_path / "o.db"))
    line = FakeLine()
    return TestClient(create_app(settings, line=line)), line


def signed(payload: dict) -> tuple[bytes, dict]:
    body = json.dumps(payload).encode()
    sig = base64.b64encode(hmac.new(SECRET.encode(), body, hashlib.sha256).digest()).decode()
    return body, {"x-line-signature": sig, "content-type": "application/json"}


def text_event(text, user="U-1"):
    return {"events": [{"type": "message", "replyToken": "r1", "source": {"userId": user},
                        "message": {"type": "text", "text": text}}]}


def test_health(setup):
    client, _ = setup
    assert client.get("/health").json() == {"status": "ok"}


def test_rejects_unsigned_or_forged_requests(setup):
    client, line = setup
    body, _ = signed(text_event("เมนู"))
    assert client.post("/webhook", content=body).status_code == 401
    assert client.post("/webhook", content=body, headers={"x-line-signature": "forged"}).status_code == 401
    assert line.replies == []


def test_full_order_over_webhook_and_qr_endpoint(setup):
    client, line = setup
    for msg in ["ขนมจีบ 3", "ชำระเงิน"]:
        body, headers = signed(text_event(msg))
        assert client.post("/webhook", content=body, headers=headers).status_code == 200

    qr_url = line.replies[-1][1][1]["originalContentUrl"]
    assert line.pushes[0][0] == "U-owner"
    png = client.get(qr_url.replace("https://shop.test", ""))
    assert png.status_code == 200 and png.content.startswith(b"\x89PNG")
    assert client.get("/qr/NOPE1234.png").status_code == 404
