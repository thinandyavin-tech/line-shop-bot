"""Shop menu loaded from JSON. Prices live here, in code-controlled data — never in the LLM."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path


@dataclass(frozen=True)
class Product:
    id: str
    name: str
    price: Decimal
    unit: str = "ชิ้น"
    options: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()
    image_url: str | None = None

    def matches(self, text: str) -> bool:
        t = text.strip().lower()
        return t in {self.id.lower(), self.name.lower(), *(a.lower() for a in self.aliases)}


@dataclass
class Menu:
    shop_name: str
    products: list[Product] = field(default_factory=list)

    def get(self, product_id: str) -> Product | None:
        return next((p for p in self.products if p.id == product_id), None)

    def find(self, text: str) -> Product | None:
        return next((p for p in self.products if p.matches(text)), None)

    @classmethod
    def load(cls, path: str | Path) -> Menu:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        products = [
            Product(
                id=p["id"],
                name=p["name"],
                price=Decimal(str(p["price"])),
                unit=p.get("unit", "ชิ้น"),
                options=tuple(p.get("options", [])),
                aliases=tuple(p.get("aliases", [])),
                image_url=p.get("image_url"),
            )
            for p in data["products"]
        ]
        ids = [p.id for p in products]
        if len(ids) != len(set(ids)):
            raise ValueError("product ids must be unique")
        if any(p.price <= 0 for p in products):
            raise ValueError("prices must be positive")
        return cls(shop_name=data["shop_name"], products=products)
