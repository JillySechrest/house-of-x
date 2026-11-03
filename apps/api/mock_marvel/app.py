"""Local stand-in for Marvel's retired public API, serving sample fixtures.

Serves the subset of /v1/public the catalog calls and checks ts/apikey/hash
the way Marvel did. Fixture data is sample data, not Marvel's.
"""
import hashlib
import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

FIXTURE_PATH = Path(os.environ.get("HOX_FIXTURES", Path(__file__).resolve().parents[1] / "fixtures" / "marvel_sample.json"))
DEMO_PUBLIC_KEY = os.environ.get("MOCK_MARVEL_PUBLIC_KEY", "demo-public-key")
DEMO_PRIVATE_KEY = os.environ.get("MOCK_MARVEL_PRIVATE_KEY", "demo-private-key")

app = FastAPI(title="Mock Marvel gateway (sample data)")
_data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _resource_id(uri: str) -> int:
    return int(uri.rsplit("/", 1)[-1])


def _onsale(comic: dict) -> str:
    return next((d["date"][:10] for d in comic["dates"] if d["type"] == "onsaleDate"), "")


def _creator_ids(comic: dict) -> set[int]:
    return {_resource_id(i["resourceURI"]) for i in comic["creators"]["items"]}


def _envelope(results: list[dict], params) -> dict:
    limit = min(int(params.get("limit", 20)), 100)
    offset = int(params.get("offset", 0))
    page = results[offset:offset + limit]
    return {
        "code": 200, "status": "Ok",
        "attributionText": _data["attributionText"], "attributionHTML": _data["attributionHTML"],
        "data": {"offset": offset, "limit": limit, "total": len(results), "count": len(page), "results": page},
    }


@app.middleware("http")
async def check_auth(request: Request, call_next):
    p = request.query_params
    if not all(k in p for k in ("ts", "apikey", "hash")):
        return JSONResponse({"code": 409, "message": "Missing ts, apikey or hash"}, status_code=409)
    if p["apikey"] != DEMO_PUBLIC_KEY:
        return JSONResponse({"code": 401, "message": "Invalid Referer or API key"}, status_code=401)
    expected = hashlib.md5((p["ts"] + DEMO_PRIVATE_KEY + DEMO_PUBLIC_KEY).encode()).hexdigest()
    if p["hash"] != expected:
        return JSONResponse({"code": 401, "message": "Invalid hash"}, status_code=401)
    return await call_next(request)


def _filter_comics(comics: list[dict], params) -> list[dict]:
    if "creators" in params:
        wanted = {int(x) for x in params["creators"].split(",")}
        comics = [c for c in comics if wanted & _creator_ids(c)]
    if "dateRange" in params:
        start, end = params["dateRange"].split(",")
        comics = [c for c in comics if start <= _onsale(c) <= end]
    if params.get("orderBy") == "-onsaleDate":
        return sorted(comics, key=_onsale, reverse=True)
    return sorted(comics, key=_onsale)


@app.get("/v1/public/creators")
def creators(request: Request):
    p = request.query_params
    found = [c for c in _data["creators"]
             if p.get("lastName", c["lastName"]).lower() == c["lastName"].lower()
             and p.get("firstName", c["firstName"]).lower() == c["firstName"].lower()]
    return _envelope(found, p)


@app.get("/v1/public/series")
def series(request: Request):
    p = request.query_params
    found = [s for s in _data["series"]
             if s["title"].lower().startswith(p.get("titleStartsWith", "").lower())
             and ("startYear" not in p or s["startYear"] == int(p["startYear"]))]
    return _envelope(found, p)


@app.get("/v1/public/series/{series_id}/comics")
def series_comics(series_id: int, request: Request):
    p = request.query_params
    comics = [c for c in _data["comics"] if _resource_id(c["series"]["resourceURI"]) == series_id]
    return _envelope(_filter_comics(comics, p), p)


@app.get("/v1/public/comics")
def comics(request: Request):
    p = request.query_params
    return _envelope(_filter_comics(_data["comics"], p), p)


@app.get("/v1/public/characters")
def characters(request: Request):
    p = request.query_params
    found = [c for c in _data["characters"] if "name" not in p or c["name"].lower() == p["name"].lower()]
    return _envelope(found, p)


@app.get("/v1/public/characters/{character_id}")
def character(character_id: int, request: Request):
    found = [c for c in _data["characters"] if c["id"] == character_id]
    if not found:
        raise HTTPException(404, "We couldn't find that character")
    return _envelope(found, request.query_params)
