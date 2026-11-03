import httpx
import pytest
from fastapi.testclient import TestClient

from app.cache import Cache
from app.config import MissingKeysError, Settings
from app.main import app
from app.marvel import MarvelClient, MarvelUnavailableError, marvel_hash
from .conftest import FakeMarvel, HICKMAN, comic


def test_hash_known_input():
    # md5("1" + "abcd" + "1234")
    assert marvel_hash("1", "abcd", "1234") == "ffd275c5130566a2916217b101f26150"


def test_cache_hit_skips_network():
    fake = FakeMarvel()
    client = MarvelClient(Settings("pub", "priv"), Cache(":memory:"), httpx.MockTransport(fake))
    client.get("/creators", {"lastName": "Hickman"})
    client.get("/creators", {"lastName": "Hickman"})
    assert len(fake.requests) == 1
    params = fake.requests[0].url.params
    assert {"ts", "apikey", "hash"} <= set(params)
    assert "priv" not in str(fake.requests[0].url)


def test_marvel_down_is_502(client, monkeypatch):
    app.state.transport = httpx.MockTransport(lambda r: httpx.Response(500))
    r = client.get("/api/shelves")
    assert r.status_code == 502


def test_health_without_keys(monkeypatch):
    monkeypatch.delenv("MARVEL_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("MARVEL_PRIVATE_KEY", raising=False)
    assert TestClient(app).get("/api/health").json() == {"status": "ok"}


def test_missing_keys_503(monkeypatch):
    monkeypatch.setenv("MARVEL_PUBLIC_KEY", "")
    monkeypatch.delenv("MARVEL_PRIVATE_KEY", raising=False)
    r = TestClient(app).get("/api/comics")
    assert r.status_code == 503
    assert "MARVEL_PUBLIC_KEY" in r.json()["detail"]


def test_writer_credited_comic_in_scope_and_others_not(client):
    items = client.get("/api/comics").json()["items"]
    ids = [c["id"] for c in items]
    assert 11 in ids and 31 in ids
    assert 32 not in ids  # Hickman credited as penciller only
    assert ids == sorted(ids, key=lambda i: {31: 3, 12: 2, 11: 1}[i], reverse=True)
    assert client.get("/api/comics/32").status_code == 404
    assert client.get("/api/comics/11").json()["comic"]["thumbnail"] is None
    assert [c["id"] for c in client.get("/api/comics?shelf=prior").json()["items"]] == [12, 11]


def test_unresolved_series_skipped_and_attribution(client):
    body = client.get("/api/shelves").json()
    assert [s["title"] for s in body["prior"]["series"]] == ["House of X (2019 - 2019)"]
    assert body["attribution"]["text"].startswith("Data provided by Marvel")
    assert body["window"] == {"start": "2019-07-24", "end": "2019-10-09"}


def test_ambiguous_creator_stops(client, fake):
    fake.creators = [HICKMAN, {"id": 101, "fullName": "Jonathan Hickman Jr."}]
    r = client.get("/api/comics")
    assert r.status_code == 409
    assert "Jonathan Hickman Jr." in r.json()["detail"]


def test_character_and_search(client):
    chars = client.get("/api/characters").json()["items"]
    assert [c["id"] for c in chars] == [7]
    detail = client.get("/api/characters/7")
    assert [c["id"] for c in detail.json()["comics"]] == [11]
    assert client.get("/api/characters/999").status_code == 404
    assert client.get("/api/search?q=h").status_code == 422
    assert len(client.get("/api/search?q=house").json()["comics"]) == 2
