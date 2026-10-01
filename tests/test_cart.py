from decimal import Decimal

import pytest

from line_shop_bot.cart import Cart


def test_total_uses_menu_prices(menu):
    cart = Cart()
    cart.add(menu, "shumai", 4)
    cart.add(menu, "bun", 2, "ครีม")
    assert cart.total(menu) == Decimal("70")


def test_same_item_merges_into_one_line(menu):
    cart = Cart()
    cart.add(menu, "bun", 1, "ครีม")
    cart.add(menu, "bun", 2, "ครีม")
    cart.add(menu, "bun", 1, "หมูแดง")
    assert [(l.option, l.qty) for l in cart.lines] == [("ครีม", 3), ("หมูแดง", 1)]


def test_option_required_when_product_has_options(menu):
    with pytest.raises(ValueError):
        Cart().add(menu, "bun", 1)
    with pytest.raises(ValueError):
        Cart().add(menu, "bun", 1, "ช็อกโกแลต")


def test_option_ignored_for_simple_products(menu):
    cart = Cart()
    cart.add(menu, "cookie", 1, "ไม่มีจริง")
    assert cart.lines[0].option is None


@pytest.mark.parametrize("qty", [0, -1, 100])
def test_quantity_bounds(menu, qty):
    with pytest.raises(ValueError):
        Cart().add(menu, "shumai", qty)


def test_unknown_product(menu):
    with pytest.raises(ValueError):
        Cart().add(menu, "pizza", 1)


def test_remove_and_clear(menu):
    cart = Cart()
    cart.add(menu, "shumai", 1)
    cart.add(menu, "cookie", 1)
    assert cart.remove("shumai")
    assert not cart.remove("shumai")
    cart.clear()
    assert cart.is_empty()
