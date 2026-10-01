import json

import httpx
import pytest

from line_shop_bot.nlu import ParsedItem, parse_rule_based, parse_with_llm, validate


def test_rule_parser_product_option_qty(menu):
    assert parse_rule_based("ซาลาเปา ครีม 3", menu) == [ParsedItem("bun", 3, "ครีม")]


def test_rule_parser_thai_number_words_and_aliases(menu):
    assert parse_rule_based("คุกกี้ สอง", menu) == [ParsedItem("cookie", 2)]
    assert parse_rule_based("shumai 5", menu) == [ParsedItem("shumai", 5)]


def test_rule_parser_multiple_items_and_unknowns(menu):
    items = parse_rule_based("ขนมจีบ 10, พิซซ่า 2\nซาลาเปา หมูแดง", menu)
    assert items == [ParsedItem("shumai", 10), ParsedItem("bun", 1, "หมูแดง")]


def test_validate_drops_anything_not_on_the_menu(menu):
    raw = [
        {"product_id": "bun", "qty": 2, "option": "ครีม"},
        {"product_id": "pizza", "qty": 1},                       # not on menu
        {"product_id": "shumai", "qty": 0},                      # bad qty
        {"product_id": "bun", "qty": 1, "option": "ช็อกโกแลต"},  # bad option -> ask later
        {"product_id": "cookie", "qty": "lots"},                 # garbage
        "not a dict",
    ]
    assert validate(raw, menu) == [ParsedItem("bun", 2, "ครีม"), ParsedItem("bun", 1, None)]


def _fake_llm(content: str, status: int = 200):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer test-key"
        return httpx.Response(status, json={"choices": [{"message": {"content": content}}]})
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.anyio
async def test_llm_result_is_validated(menu):
    content = json.dumps({"items": [{"product_id": "cookie", "qty": 1, "option": None},
                                    {"product_id": "free_iphone", "qty": 1}]})
    items = await parse_with_llm("ขอคุกกี้กล่องนึงกับไอโฟน", menu, "test-key", "m", client=_fake_llm(content))
    assert items == [ParsedItem("cookie", 1)]


@pytest.mark.anyio
async def test_llm_failure_falls_back_to_rules(menu):
    items = await parse_with_llm("ขนมจีบ 3", menu, "test-key", "m", client=_fake_llm("oops", status=500))
    assert items == [ParsedItem("shumai", 3)]


@pytest.fixture
def anyio_backend():
    return "asyncio"
