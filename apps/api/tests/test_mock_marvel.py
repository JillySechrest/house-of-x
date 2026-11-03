import hashlib

import httpx
import pytest
from fastapi.testclient import TestClient

from app.cache import Cache
from app.config import Settings
from app.main import app
from app.marvel import MarvelClient
from app.scope import build_scope
from mock_marvel.app import DEMO_PRIVATE_KEY, DEMO_PUBLIC_KEY, app as mock_app

mock = TestClient(mock_app)


def auth(ts="1", public=DEMO_PUBLIC_KEY, private=DEMO_PRIVATE_KEY):
    return {"ts": ts, "apikey": public, "hash": hashlib.md5((ts + private + public).encode()).hexdigest()}


class MockGateway(httpx.BaseTransport):
    """Routes the catalog's httpx calls into the mock app in-process."""

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        r = mock.get(request.url.path, params=dict(request.url.params))
        return httpx.Response(r.status_code, json=r.json())


def test_auth_required_and_checked():
    assert mock.get("/v1/public/creators").status_code == 409
    assert mock.get("/v1/public/creators", params={**auth(), "hash": "bad"}).status_code == 401
    assert mock.get("/v1/public/creators", params=auth(public="nope")).status_code == 401
    body = mock.get("/v1/public/creators", params={**auth(), "lastName": "Hickman", "firstName": "Jonathan"}).json()
    assert body["data"]["total"] == 1
    assert "not provided by Marvel" in body["attributionText"]


def test_filters_and_paging():
    series = mock.get("/v1/public/series", params={**auth(), "titleStartsWith": "Inferno", "startYear": 2021}).json()
    assert series["data"]["results"] == []
    series = mock.get("/v1/public/series", params={**auth(), "titleStartsWith": "House of X", "startYear": 2019}).json()
    assert [s["id"] for s in series["data"]["results"]] == [101]
    comics = mock.get("/v1/public/comics", params={**auth(), "creators": 1001, "dateRange": "2019-07-01,2020-02-01", "limit": 2}).json()["data"]
    assert comics["count"] == 2 and comics["total"] > 2


def test_scope_flow_against_mock():
    client = MarvelClient(Settings(DEMO_PUBLIC_KEY, DEMO_PRIVATE_KEY), Cache(":memory:"), MockGateway())
    scope = build_scope(client)
    ids = {c.id for c in scope.comics}
    assert {5001, 5002, 5003, 5004, 5006, 5007} <= ids
    assert 5005 not in ids  # Hickman credited as penciller only
    assert 5008 not in ids  # outside the window
    assert 5009 not in ids  # other series, no Hickman credit
    assert [s.title for s in scope.main.series] == ["X-Men (2019 - 2021)", "Giant-Size X-Men (2020 - 2020)"]  # Inferno unresolved
    assert next(c for c in scope.comics if c.id == 5007).in_resolved_series is False
    assert next(c for c in scope.comics if c.id == 5002).thumbnail is None
    assert scope.window_start == "2019-07-24" and scope.window_end == "2020-01-22"
    assert "not provided by Marvel" in scope.attribution.text
    assert "Kitty Pryde" in [c.name for c in scope.characters]
