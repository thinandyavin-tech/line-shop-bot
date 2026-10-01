"""Conversation logic, independent of HTTP so it can be tested directly."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from urllib.parse import parse_qs

from . import messages as m
from .cart import Cart
from .menu import Menu
from .nlu import ParsedItem, parse_rule_based
from .store import OrderStore

MENU_WORDS = {"เมนู", "menu", "สั่ง", "สั่งซื้อ", "order"}
CART_WORDS = {"ตะกร้า", "cart", "ดูตะกร้า"}
CLEAR_WORDS = {"ล้างตะกร้า", "ยกเลิก", "clear", "cancel"}
CHECKOUT_WORDS = {"ชำระเงิน", "จ่ายเงิน", "checkout", "pay"}

Parser = Callable[[str, Menu], Awaitable[list[ParsedItem]]]


async def _rules(text: str, menu: Menu) -> list[ParsedItem]:
    return parse_rule_based(text, menu)


@dataclass
class Outcome:
    reply: list[dict] = field(default_factory=list)
    push: list[tuple[str, list[dict]]] = field(default_factory=list)


class ShopBot:
    def __init__(self, menu: Menu, store: OrderStore, qr_url: Callable[[str], str],
                 owner_user_id: str = "", parser: Parser = _rules):
        self.menu, self.store, self.qr_url = menu, store, qr_url
        self.owner_user_id, self.parser = owner_user_id, parser
        self.carts: dict[str, Cart] = {}

    def cart(self, user_id: str) -> Cart:
        return self.carts.setdefault(user_id, Cart())

    async def on_follow(self, user_id: str) -> Outcome:
        return Outcome([m.text(f"ยินดีต้อนรับสู่ {self.menu.shop_name} 🙏\nพิมพ์สิ่งที่อยากสั่งได้เลย หรือกดดูเมนู",
                               [("เมนู", "เมนู")]), m.menu_carousel(self.menu)])

    async def on_text(self, user_id: str, text: str) -> Outcome:
        t = text.strip()
        low = t.lower()
        if user_id == self.owner_user_id and low.startswith("paid "):
            return self._owner_mark_paid(t.split(maxsplit=1)[1].strip().upper())
        if low in MENU_WORDS:
            return Outcome([m.menu_carousel(self.menu)])
        if low in CART_WORDS:
            return Outcome([m.cart_summary(self.cart(user_id), self.menu)])
        if low in CLEAR_WORDS:
            self.cart(user_id).clear()
            return Outcome([m.text("ล้างตะกร้าแล้ว", [("เมนู", "เมนู")])])
        if low in CHECKOUT_WORDS:
            return self._checkout(user_id)

        items = await self.parser(t, self.menu)
        if not items:
            return Outcome([m.text("ขอโทษค่ะ ไม่เจอสินค้านี้ในเมนู ลองดูเมนูได้เลย", [("เมนู", "เมนู")])])
        return self._add_items(user_id, items)

    async def on_postback(self, user_id: str, data: str) -> Outcome:
        q = {k: v[0] for k, v in parse_qs(data).items()}
        if "add" in q:
            item = ParsedItem(q["add"], int(q.get("qty", "1")), q.get("opt"))
            return self._add_items(user_id, [item])
        return Outcome()

    def _add_items(self, user_id: str, items: list[ParsedItem]) -> Outcome:
        cart, notes = self.cart(user_id), []
        for it in items:
            product = self.menu.get(it.product_id)
            if product.options and it.option is None:
                return Outcome([m.text(f"{product.name} มีให้เลือก: {', '.join(product.options)}",
                                       [(o, f"{product.name} {o} {it.qty}") for o in product.options])])
            try:
                cart.add(self.menu, it.product_id, it.qty, it.option)
                notes.append(f"+ {product.name}{f' ({it.option})' if it.option else ''} x{it.qty}")
            except ValueError as e:
                notes.append(f"⚠️ {e}")
        return Outcome([m.text("\n".join(notes)), m.cart_summary(cart, self.menu)])

    def _checkout(self, user_id: str) -> Outcome:
        cart = self.cart(user_id)
        if cart.is_empty():
            return Outcome([m.cart_summary(cart, self.menu)])
        total = cart.total(self.menu)
        items = [{"product_id": l.product_id, "option": l.option, "qty": l.qty} for l in cart.lines]
        summary = cart.summary_lines(self.menu)
        order = self.store.create(user_id, items, total)
        cart.clear()
        out = Outcome(m.payment(order.id, total, self.qr_url(order.id)))
        if self.owner_user_id:
            out.push.append((self.owner_user_id, [m.text(
                f"🔔 ออเดอร์ใหม่ #{order.id}\n" + "\n".join(summary) +
                f"\nรวม {total:,.0f}฿\nเมื่อได้รับเงินแล้วพิมพ์: paid {order.id}")]))
        return out

    def _owner_mark_paid(self, order_id: str) -> Outcome:
        order = self.store.get(order_id)
        if order is None or not self.store.set_status(order_id, "paid"):
            return Outcome([m.text(f"ไม่พบออเดอร์ #{order_id}")])
        return Outcome([m.text(f"บันทึกแล้ว: #{order_id} ชำระเงินแล้ว")],
                       [(order.user_id, [m.text(f"ได้รับชำระเงินออเดอร์ #{order_id} แล้ว ขอบคุณค่ะ 🙏")])])
