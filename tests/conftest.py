from pathlib import Path

import pytest

from line_shop_bot.menu import Menu

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def menu() -> Menu:
    return Menu.load(ROOT / "menu.example.json")
