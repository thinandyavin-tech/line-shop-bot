# line-shop-bot

[![tests](https://github.com/thinandyavin-tech/line-shop-bot/actions/workflows/tests.yml/badge.svg)](https://github.com/thinandyavin-tech/line-shop-bot/actions/workflows/tests.yml)
![python](https://img.shields.io/badge/python-3.11%2B-blue)
![license](https://img.shields.io/badge/license-MIT-green)

**An open-source LINE Official Account ordering bot for Thai shops.** Customers browse a menu, build a cart in chat (buttons *or* plain Thai like "ซาลาเปา ครีม 3"), and pay with a PromptPay QR generated for the exact total. The shop owner gets a LINE alert for every order and confirms payment with one message.

Extracted and generalised from a bot I run in production for a real food stall.

> **ภาษาไทย:** บอทรับออเดอร์ผ่าน LINE OA สำหรับร้านค้าไทย ลูกค้าดูเมนู สั่งของในแชท (กดปุ่มหรือพิมพ์ภาษาไทยธรรมดา) แล้วจ่ายผ่าน QR พร้อมเพย์ที่สร้างตามยอดจริง เจ้าของร้านได้รับแจ้งเตือนทุกออเดอร์ทาง LINE — แก้เมนูได้จากไฟล์ JSON ไฟล์เดียว

## Features

- **Menu from one JSON file** — products, prices, units, options (e.g. bun fillings), aliases, images. Rendered as a LINE Flex carousel.
- **Cart in chat** — Flex buttons, quick replies, or free text. Asks for missing options instead of guessing.
- **Optional AI order parsing** — any OpenAI-compatible LLM (Groq by default) turns messages like "ขอซาลาเปาไส้ครีมสองลูกกับคุกกี้กล่องนึง" into cart items. **The model never sets prices**: its output is validated against the menu and totals are computed in code. Without an API key a rule-based Thai/English parser is used.
- **PromptPay QR** — EMVCo-compliant dynamic QR for the exact amount (phone number or 13-digit ID), served as a LINE image.
- **Owner workflow** — new-order push to the owner; `paid <ORDER_ID>` marks it paid and notifies the customer.
- **Secure by default** — every webhook request's `X-Line-Signature` is verified (HMAC-SHA256, constant-time compare); one bad event never drops the rest.

## How it works

```
LINE app ──► /webhook (FastAPI) ──► ShopBot ──► Cart / Menu (prices in code)
                │                     │
                │                     ├─► LLM parser (optional, validated)
                │                     └─► OrderStore (SQLite)
                └─ /qr/{order}.png ◄── PromptPay payload + CRC16
```

| Module | Responsibility |
| --- | --- |
| `promptpay.py` | EMV payload, CRC-16/CCITT, QR PNG |
| `menu.py`, `cart.py` | Menu loading/validation, deterministic pricing |
| `nlu.py` | Rule-based + LLM order parsing with validation |
| `bot.py` | Conversation logic (pure, no HTTP — easy to test) |
| `app.py`, `line_api.py` | Webhook, signature check, LINE reply/push |
| `store.py` | Orders in SQLite |

## Quick start

```bash
git clone https://github.com/thinandyavin-tech/line-shop-bot.git
cd line-shop-bot
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env        # fill in your LINE channel + PromptPay ID
uvicorn line_shop_bot.app:main --factory --port 8000
```

Expose it over HTTPS (e.g. `ngrok http 8000`), set `APP_BASE_URL` to that URL, and set the webhook in the [LINE Developers Console](https://developers.line.biz/console/) to `https://<your-host>/webhook`.

Edit `menu.example.json` (or point `MENU_PATH` at your own file) to set up your shop.

### Docker

```bash
docker build -t line-shop-bot .
docker run --env-file .env -p 8000:8000 line-shop-bot
```

## Configuration

| Variable | Required | Description |
| --- | --- | --- |
| `LINE_CHANNEL_SECRET` | ✔ | Verifies webhook signatures |
| `LINE_CHANNEL_ACCESS_TOKEN` | ✔ | Sends replies and pushes |
| `PROMPTPAY_ID` | ✔ | Phone number or 13-digit ID that receives payments |
| `APP_BASE_URL` | ✔ | Public HTTPS URL of this server (for QR images) |
| `OWNER_USER_ID` | | LINE user ID that receives order alerts and can mark orders paid |
| `MENU_PATH` | | Menu JSON (default `menu.example.json`) |
| `DATABASE_PATH` | | SQLite file (default `orders.db`) |
| `LLM_API_KEY` | | Enables AI order parsing |
| `LLM_MODEL`, `LLM_BASE_URL` | | Any OpenAI-compatible endpoint (default Groq) |

## Chat commands

| Customer types | Result |
| --- | --- |
| `เมนู` / `menu` | Product carousel |
| `ขนมจีบ 4`, `ซาลาเปา ครีม 2`, free text | Adds to cart |
| `ตะกร้า` / `cart` | Cart summary |
| `ชำระเงิน` / `checkout` | Creates order + PromptPay QR |
| `ล้างตะกร้า` / `clear` | Empties cart |
| Owner: `paid <ORDER_ID>` | Marks paid, notifies customer |

## Tests

```bash
pytest          # 33 tests: PromptPay/CRC, pricing, parsing, conversation flow, webhook security
ruff check .
```

## Roadmap

- Automatic slip verification (bank slip QR / OCR)
- Persistent carts (Redis) for multi-instance deployments
- Pickup / delivery scheduling
- Admin dashboard

## License

MIT © Yavin Songkham
