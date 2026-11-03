"""SQLite response cache. Not a source of truth; entries expire after the TTL."""
import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from .config import CACHE_TTL_SECONDS


class Cache:
    def __init__(self, path: Path | str, ttl: float = CACHE_TTL_SECONDS):
        self.path = str(path)
        self.ttl = ttl
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._memory_conn = sqlite3.connect(":memory:", check_same_thread=False) if self.path == ":memory:" else None
        with self._conn() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS cache "
                "(key TEXT PRIMARY KEY, value TEXT NOT NULL, stored_at REAL NOT NULL)"
            )

    def _conn(self) -> sqlite3.Connection:
        return self._memory_conn or sqlite3.connect(self.path)

    def get(self, key: str) -> Any | None:
        with self._conn() as conn:
            row = conn.execute("SELECT value, stored_at FROM cache WHERE key = ?", (key,)).fetchone()
        if row is None or time.time() - row[1] > self.ttl:
            return None
        return json.loads(row[0])

    def set(self, key: str, value: Any) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO cache (key, value, stored_at) VALUES (?, ?, ?)",
                (key, json.dumps(value), time.time()),
            )
