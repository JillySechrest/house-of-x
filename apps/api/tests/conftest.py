import httpx
import pytest
from fastapi.testclient import TestClient

from app.cache import Cache
from app.main import app

HICKMAN = {"id": 100, "fullName": "Jonathan Hickman"}
ATTR = "Data provided by Marvel. © 2026 MARVEL"


def uri(kind: str, id_: int) -> str:
    return f"http://gateway.marvel.com/v1/public/{kind}/{id_}"


def comic(id_, title, series_id, role, creator=HICKMAN, date="2019-07-24T00:00:00-0400", chars=()):
    return {
        "id": id_, "title": title, "issueNumber": 1, "format": "Comic", "description": None,
        "dates": [{"type": "onsaleDate", "date": date}],
        "thumbnail": {"path": "http://i.annihil.us/image_not_available", "extension": "jpg"},
        "series": {"resourceURI": uri("series", series_id), "name": "Series"},
        "creators": {"items": [{"resourceURI": uri("creators", creator["id"]), "name": creator["fullName"], "role": role}]},
        "characters": {"items": [{"resourceURI": uri("characters", c), "name": f"Char {c}"} for c in chars]},
    }


def envelope(results):
    return {"code": 200, "attributionText": ATTR, "attributionHTML": "<a>Marvel</a>",
            "data": {"offset": 0, "total": len(results), "count": len(results), "results": results}}


class FakeMarvel:
    def __init__(self, creators=None, comics_by_series=None):
        self.requests = []
        self.creators = [HICKMAN] if creators is None else creators
        self.comics_by_series = comics_by_series or {
            1: [comic(11, "House of X #1", 1, "writer", chars=(7,)), comic(12, "House of X #2", 1, "writer", date="2019-07-31T00:00:00-0400")],
            3: [comic(31, "X-Men #1", 3, "writer", date="2019-10-09T00:00:00-0400"),
                comic(32, "X-Men #2", 3, "penciller", date="2019-10-16T00:00:00-0400")],
        }

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path.removeprefix("/v1/public")
        q = request.url.params
        if path == "/creators":
            return httpx.Response(200, json=envelope(self.creators))
        if path == "/series":
            title = q["titleStartsWith"]
            ids = {"House of X": 1, "X-Men": 3}
            if title in ids:
                return httpx.Response(200, json=envelope([{"id": ids[title], "title": f"{title} (2019 - 2019)", "startYear": 2019}]))
            return httpx.Response(200, json=envelope([]))
        if path.startswith("/series/") and path.endswith("/comics"):
            sid = int(path.split("/")[2])
            return httpx.Response(200, json=envelope(self.comics_by_series.get(sid, [])))
        if path == "/comics":
            return httpx.Response(200, json=envelope([]))
        if path == "/characters":
            return httpx.Response(200, json=envelope([]))
        if path.startswith("/characters/"):
            return httpx.Response(200, json=envelope([{"id": int(path.split("/")[2]), "name": "Char 7", "description": "", "thumbnail": None}]))
        return httpx.Response(404, json={})


@pytest.fixture
def fake():
    return FakeMarvel()


@pytest.fixture
def client(fake, monkeypatch):
    monkeypatch.setenv("MARVEL_PUBLIC_KEY", "pub")
    monkeypatch.setenv("MARVEL_PRIVATE_KEY", "priv")
    app.state.cache = Cache(":memory:")
    app.state.transport = httpx.MockTransport(fake)
    yield TestClient(app)
    app.state.cache = None
    app.state.transport = None
