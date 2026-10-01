"""Turn customer messages into cart items.

A rule-based parser handles simple messages ("ซาลาเปา หมู 3", "cookie 2"). If an LLM is
configured it handles free text ("ขอซาลาเปาไส้ครีมสองลูกกับคุกกี้กล่องนึง"). Either way the
result is validated against the menu: the LLM can only point at products and quantities,
it never sets prices.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

import httpx

from .menu import Menu

THAI_NUMBERS = {"หนึ่ง": 1, "นึง": 1, "สอง": 2, "สาม": 3, "สี่": 4, "ห้า": 5,
                "หก": 6, "เจ็ด": 7, "แปด": 8, "เก้า": 9, "สิบ": 10}


@dataclass(frozen=True)
class ParsedItem:
    product_id: str
    qty: int
    option: str | None = None


def parse_rule_based(text: str, menu: Menu) -> list[ParsedItem]:
    """Match '<product> [option] [qty]' — one item per line or comma."""
    items = []
    for chunk in re.split(r"[,\n]+", text):
        chunk = chunk.strip()
        if not chunk:
            continue
        qty_match = re.search(r"(\d+)", chunk)
        qty = int(qty_match.group(1)) if qty_match else next(
            (n for w, n in THAI_NUMBERS.items() if w in chunk), 1)
        words = re.sub(r"\d+", " ", chunk).split()
        product = next((p for w in words if (p := menu.find(w))), None) or next(
            (p for p in menu.products if p.name in chunk or any(a in chunk for a in p.aliases)), None)
        if product is None:
            continue
        option = next((o for o in product.options if o in chunk), None)
        items.append(ParsedItem(product.id, qty, option))
    return items


def _llm_prompt(menu: Menu) -> str:
    catalog = [{"id": p.id, "name": p.name, "options": list(p.options)} for p in menu.products]
    return (
        "Extract the items a customer wants to order. Reply with JSON only: "
        '{"items":[{"product_id":str,"qty":int,"option":str|null}]}. '
        "Use only product ids and options from this catalog; skip anything not in it. "
        f"Catalog: {json.dumps(catalog, ensure_ascii=False)}"
    )


def validate(raw_items: list, menu: Menu) -> list[ParsedItem]:
    out = []
    for it in raw_items if isinstance(raw_items, list) else []:
        if not isinstance(it, dict):
            continue
        product = menu.get(str(it.get("product_id", "")))
        try:
            qty = int(it.get("qty", 1))
        except (TypeError, ValueError):
            continue
        if product is None or not 1 <= qty <= 99:
            continue
        option = it.get("option")
        if product.options and option not in product.options:
            option = None  # let the bot ask instead of guessing
        out.append(ParsedItem(product.id, qty, option if product.options else None))
    return out


async def parse_with_llm(text: str, menu: Menu, api_key: str, model: str,
                         base_url: str = "https://api.groq.com/openai/v1",
                         client: httpx.AsyncClient | None = None) -> list[ParsedItem]:
    """OpenAI-compatible chat call (Groq by default). Falls back to rules on any error."""
    try:
        async with (client or httpx.AsyncClient(timeout=15)) as c:
            r = await c.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "temperature": 0,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": _llm_prompt(menu)},
                        {"role": "user", "content": text},
                    ],
                },
            )
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"]
            items = validate(json.loads(content).get("items", []), menu)
            return items or parse_rule_based(text, menu)
    except Exception:
        return parse_rule_based(text, menu)
