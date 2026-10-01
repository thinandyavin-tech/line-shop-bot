"""Minimal LINE Messaging API client: signature check, reply, push."""
from __future__ import annotations

import base64
import hashlib
import hmac

import httpx

API = "https://api.line.me/v2/bot"


def verify_signature(channel_secret: str, body: bytes, signature: str | None) -> bool:
    if not signature or not channel_secret:
        return False
    digest = hmac.new(channel_secret.encode(), body, hashlib.sha256).digest()
    return hmac.compare_digest(base64.b64encode(digest).decode(), signature)


class LineClient:
    def __init__(self, access_token: str, http: httpx.AsyncClient | None = None):
        self._headers = {"Authorization": f"Bearer {access_token}"}
        self._http = http or httpx.AsyncClient(timeout=10)

    async def reply(self, reply_token: str, messages: list[dict]) -> None:
        r = await self._http.post(f"{API}/message/reply", headers=self._headers,
                                  json={"replyToken": reply_token, "messages": messages[:5]})
        r.raise_for_status()

    async def push(self, to: str, messages: list[dict]) -> None:
        r = await self._http.post(f"{API}/message/push", headers=self._headers,
                                  json={"to": to, "messages": messages[:5]})
        r.raise_for_status()
