"""LINE message payloads (plain dicts, so they are easy to test)."""
from __future__ import annotations

from decimal import Decimal

from .cart import Cart
from .menu import Menu, Product


def text(t: str, quick: list[tuple[str, str]] | None = None) -> dict:
    msg = {"type": "text", "text": t}
    if quick:
        msg["quickReply"] = {"items": [
            {"type": "action", "action": {"type": "message", "label": label[:20], "text": value}}
            for label, value in quick[:13]
        ]}
    return msg


def _product_bubble(p: Product) -> dict:
    if p.options:
        buttons = [{"type": "button", "style": "primary", "height": "sm",
                    "action": {"type": "postback", "label": o[:20], "data": f"add={p.id}&opt={o}&qty=1",
                               "displayText": f"{p.name} {o}"}} for o in p.options[:4]]
    else:
        buttons = [{"type": "button", "style": "primary", "height": "sm",
                    "action": {"type": "postback", "label": "ใส่ตะกร้า", "data": f"add={p.id}&qty=1",
                               "displayText": p.name}}]
    bubble = {
        "type": "bubble", "size": "kilo",
        "body": {"type": "box", "layout": "vertical", "spacing": "sm", "contents": [
            {"type": "text", "text": p.name, "weight": "bold", "size": "lg", "wrap": True},
            {"type": "text", "text": f"{p.price:,.0f}฿ / {p.unit}", "color": "#06C755"},
        ]},
        "footer": {"type": "box", "layout": "vertical", "spacing": "sm", "contents": buttons},
    }
    if p.image_url:
        bubble["hero"] = {"type": "image", "url": p.image_url, "size": "full",
                          "aspectRatio": "20:13", "aspectMode": "cover"}
    return bubble


def menu_carousel(menu: Menu) -> dict:
    return {"type": "flex", "altText": f"เมนู {menu.shop_name}",
            "contents": {"type": "carousel", "contents": [_product_bubble(p) for p in menu.products[:12]]}}


def cart_summary(cart: Cart, menu: Menu) -> dict:
    if cart.is_empty():
        return text("ตะกร้ายังว่างอยู่ พิมพ์ \"เมนู\" เพื่อดูสินค้า", [("เมนู", "เมนู")])
    body = "\n".join(cart.summary_lines(menu))
    return text(f"🛒 ตะกร้าของคุณ\n{body}\n\nรวม {cart.total(menu):,.0f}฿",
                [("ชำระเงิน", "ชำระเงิน"), ("เพิ่มสินค้า", "เมนู"), ("ล้างตะกร้า", "ล้างตะกร้า")])


def payment(order_id: str, total: Decimal, qr_url: str) -> list[dict]:
    return [
        text(f"✅ ออเดอร์ #{order_id}\nยอดชำระ {total:,.2f}฿\nสแกน QR PromptPay ด้านล่าง แล้วส่งสลิปในแชทนี้ได้เลย"),
        {"type": "image", "originalContentUrl": qr_url, "previewImageUrl": qr_url},
    ]
