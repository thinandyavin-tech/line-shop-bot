"""Shopping cart with deterministic pricing."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from .menu import Menu

MAX_QTY_PER_LINE = 99


@dataclass
class CartLine:
    product_id: str
    option: str | None
    qty: int


@dataclass
class Cart:
    lines: list[CartLine] = field(default_factory=list)

    def add(self, menu: Menu, product_id: str, qty: int, option: str | None = None) -> CartLine:
        product = menu.get(product_id)
        if product is None:
            raise ValueError(f"unknown product {product_id!r}")
        if not 1 <= qty <= MAX_QTY_PER_LINE:
            raise ValueError("quantity must be between 1 and 99")
        if product.options:
            if option not in product.options:
                raise ValueError(f"{product.name}: choose one of {', '.join(product.options)}")
        else:
            option = None
        for line in self.lines:
            if line.product_id == product_id and line.option == option:
                line.qty = min(MAX_QTY_PER_LINE, line.qty + qty)
                return line
        line = CartLine(product_id, option, qty)
        self.lines.append(line)
        return line

    def remove(self, product_id: str, option: str | None = None) -> bool:
        before = len(self.lines)
        self.lines = [l for l in self.lines if not (l.product_id == product_id and l.option == option)]
        return len(self.lines) < before

    def clear(self) -> None:
        self.lines.clear()

    def is_empty(self) -> bool:
        return not self.lines

    def total(self, menu: Menu) -> Decimal:
        return sum((menu.get(l.product_id).price * l.qty for l in self.lines), Decimal("0"))

    def summary_lines(self, menu: Menu) -> list[str]:
        out = []
        for l in self.lines:
            p = menu.get(l.product_id)
            label = f"{p.name} ({l.option})" if l.option else p.name
            out.append(f"{label} x{l.qty} = {p.price * l.qty:,.0f}฿")
        return out
