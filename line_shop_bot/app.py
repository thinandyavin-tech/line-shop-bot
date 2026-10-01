"""FastAPI webhook server."""
from __future__ import annotations

import json
import logging

from fastapi import FastAPI, HTTPException, Request, Response

from . import promptpay
from .bot import ShopBot
from .config import Settings
from .line_api import LineClient, verify_signature
from .menu import Menu
from .nlu import parse_rule_based, parse_with_llm
from .store import OrderStore

log = logging.getLogger("line_shop_bot")


def create_app(settings: Settings, line: LineClient | None = None) -> FastAPI:
    menu = Menu.load(settings.menu_path)
    store = OrderStore(settings.database_path)
    line = line or LineClient(settings.line_access_token)

    async def parser(text: str, m: Menu):
        if settings.llm_api_key:
            return await parse_with_llm(
                text, m, settings.llm_api_key, settings.llm_model, settings.llm_base_url
            )
        return parse_rule_based(text, m)

    bot = ShopBot(menu, store, qr_url=lambda oid: f"{settings.app_base_url}/qr/{oid}.png",
                  owner_user_id=settings.owner_user_id, parser=parser)
    app = FastAPI(title=f"{menu.shop_name} LINE bot")
    app.state.bot = bot

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/qr/{order_id}.png")
    def qr(order_id: str) -> Response:
        order = store.get(order_id.upper())
        if order is None or order.status != "awaiting_payment":
            raise HTTPException(404)
        png = promptpay.qr_png(promptpay.payload(settings.promptpay_id, order.total))
        return Response(png, media_type="image/png", headers={"Cache-Control": "no-store"})

    @app.post("/webhook")
    async def webhook(request: Request) -> dict:
        body = await request.body()
        if not verify_signature(settings.line_channel_secret, body, request.headers.get("x-line-signature")):
            raise HTTPException(401, "bad signature")
        for event in json.loads(body).get("events", []):
            try:
                user_id = event.get("source", {}).get("userId", "")
                kind = event.get("type")
                if kind == "follow":
                    outcome = await bot.on_follow(user_id)
                elif kind == "message" and event["message"].get("type") == "text":
                    outcome = await bot.on_text(user_id, event["message"]["text"])
                elif kind == "postback":
                    outcome = await bot.on_postback(user_id, event["postback"]["data"])
                else:
                    continue
                if outcome.reply and event.get("replyToken"):
                    await line.reply(event["replyToken"], outcome.reply)
                for to, msgs in outcome.push:
                    await line.push(to, msgs)
            except Exception:  # one bad event must not drop the rest
                log.exception("failed to handle event")
        return {"ok": True}

    return app


def main() -> FastAPI:  # uvicorn line_shop_bot.app:main --factory
    logging.basicConfig(level=logging.INFO)
    return create_app(Settings.from_env())
