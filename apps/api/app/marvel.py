"""Server-side Marvel API client with auth hashing and caching."""
import hashlib
import json
import logging
import time
from typing import Any

import httpx

from .cache import Cache
from .config import HTTP_TIMEOUT_SECONDS, Settings, marvel_base_url

# httpx logs full request URLs (including auth params) at INFO.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


class MarvelUnavailableError(Exception):
    pass


def marvel_hash(ts: str, private_key: str, public_key: str) -> str:
    return hashlib.md5((ts + private_key + public_key).encode()).hexdigest()


class MarvelClient:
    def __init__(self, settings: Settings, cache: Cache, transport: httpx.BaseTransport | None = None):
        self.settings = settings
        self.cache = cache
        self._http = httpx.Client(base_url=marvel_base_url(), timeout=HTTP_TIMEOUT_SECONDS, transport=transport)

    def close(self) -> None:
        self._http.close()

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Return the Marvel response envelope for a path, using the cache when fresh."""
        params = params or {}
        key = f"{marvel_base_url()}{path}?{json.dumps(params, sort_keys=True)}"
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        ts = str(int(time.time()))
        auth = {
            "ts": ts,
            "apikey": self.settings.public_key,
            "hash": marvel_hash(ts, self.settings.private_key, self.settings.public_key),
        }
        try:
            response = self._http.get(path, params={**params, **auth})
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            # Do not include the exception text: it can contain the request URL.
            raise MarvelUnavailableError(
                f"Marvel's API did not respond successfully ({type(exc).__name__})."
            ) from None
        self.cache.set(key, body)
        return body

    def get_all(self, path: str, params: dict[str, Any] | None = None, max_pages: int = 20) -> tuple[list[dict], dict]:
        """Page through a list endpoint. Returns (results, last envelope)."""
        results: list[dict] = []
        body: dict = {}
        offset = 0
        for _ in range(max_pages):
            body = self.get(path, {**(params or {}), "limit": 100, "offset": offset})
            data = body.get("data", {})
            page = data.get("results", [])
            results.extend(page)
            offset += data.get("count", len(page)) or 0
            if not page or offset >= data.get("total", 0):
                break
        return results, body
