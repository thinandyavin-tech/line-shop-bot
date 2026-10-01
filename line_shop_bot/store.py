"""Order storage in SQLite (swap for Postgres by changing this module only)."""
from __future__ import annotations

import json
import secrets
import sqlite3
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal


@dataclass
class Order:
    id: str
    user_id: str
    items: list[dict]
    total: Decimal
    status: str
    created_at: str


class OrderStore:
    def __init__(self, path: str = "orders.db"):
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.Lock()
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS orders (id TEXT PRIMARY KEY, user_id TEXT NOT NULL, "
            "items TEXT NOT NULL, total TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL)"
        )
        self._db.commit()

    def create(self, user_id: str, items: list[dict], total: Decimal) -> Order:
        order = Order(
            id=secrets.token_hex(4).upper(),
            user_id=user_id,
            items=items,
            total=total,
            status="awaiting_payment",
            created_at=datetime.now(UTC).isoformat(timespec="seconds"),
        )
        with self._lock:
            self._db.execute("INSERT INTO orders VALUES (?,?,?,?,?,?)",
                             (order.id, user_id, json.dumps(items, ensure_ascii=False),
                              str(total), order.status, order.created_at))
            self._db.commit()
        return order

    def get(self, order_id: str) -> Order | None:
        row = self._db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if not row:
            return None
        return Order(row[0], row[1], json.loads(row[2]), Decimal(row[3]), row[4], row[5])

    def set_status(self, order_id: str, status: str) -> bool:
        with self._lock:
            cur = self._db.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
            self._db.commit()
        return cur.rowcount == 1
