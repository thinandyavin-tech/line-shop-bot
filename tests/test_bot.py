from decimal import Decimal

import pytest

from line_shop_bot.bot import ShopBot
from line_shop_bot.store import OrderStore

OWNER = "U-owner"
CUSTOMER = "U-customer"


@pytest.fixture
def bot(menu):
    return ShopBot(menu, OrderStore(":memory:"), qr_url=lambda oid: f"https://shop.test/qr/{oid}.png",
                   owner_user_id=OWNER)


@pytest.fixture
def anyio_backend():
    return "asyncio"


def texts(outcome):
    return [m.get("text", "") for m in outcome.reply]


@pytest.mark.anyio
async def test_order_flow_creates_order_and_alerts_owner(bot):
    await bot.on_text(CUSTOMER, "ขนมจีบ 4")
    await bot.on_postback(CUSTOMER, "add=bun&opt=ครีม&qty=2")
    out = await bot.on_text(CUSTOMER, "ชำระเงิน")

    assert "ยอดชำระ 70.00฿" in texts(out)[0]
    image = out.reply[1]
    assert image["type"] == "image" and image["originalContentUrl"].startswith("https://shop.test/qr/")

    order_id = image["originalContentUrl"].rsplit("/", 1)[1].removesuffix(".png")
    order = bot.store.get(order_id)
    assert order.total == Decimal("70") and order.status == "awaiting_payment"

    [(to, msgs)] = out.push
    assert to == OWNER and f"paid {order_id}" in msgs[0]["text"]
    assert bot.cart(CUSTOMER).is_empty()


@pytest.mark.anyio
async def test_owner_marks_paid_and_customer_is_notified(bot):
    await bot.on_text(CUSTOMER, "คุกกี้ 1")
    out = await bot.on_text(CUSTOMER, "checkout")
    order_id = out.reply[1]["originalContentUrl"].rsplit("/", 1)[1][:-4]

    paid = await bot.on_text(OWNER, f"paid {order_id.lower()}")
    assert bot.store.get(order_id).status == "paid"
    assert paid.push[0][0] == CUSTOMER


@pytest.mark.anyio
async def test_customers_cannot_use_owner_commands(bot):
    out = await bot.on_text(CUSTOMER, "paid ABCD1234")
    assert "ไม่เจอสินค้า" in texts(out)[0]


@pytest.mark.anyio
async def test_bot_asks_for_option_when_missing(bot):
    out = await bot.on_text(CUSTOMER, "ซาลาเปา 2")
    assert "มีให้เลือก" in texts(out)[0]
    assert bot.cart(CUSTOMER).is_empty()
    quick = [i["action"]["text"] for i in out.reply[0]["quickReply"]["items"]]
    assert "ซาลาเปา ครีม 2" in quick


@pytest.mark.anyio
async def test_empty_checkout_and_unknown_text(bot):
    assert "ว่าง" in texts(await bot.on_text(CUSTOMER, "ชำระเงิน"))[0]
    assert "ไม่เจอสินค้า" in texts(await bot.on_text(CUSTOMER, "อยากได้รถยนต์"))[0]
    assert bot.store.get("ANYTHING") is None
