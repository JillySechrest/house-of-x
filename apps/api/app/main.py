import os
from typing import Iterator

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .cache import Cache
from .config import MissingKeysError, cache_path, load_settings
from .marvel import MarvelClient, MarvelUnavailableError
from .models import Character, Scope
from .scope import AmbiguousCreatorError, CreatorNotResolvedError, get_scope, thumbnail_url

app = FastAPI(title="House of X API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in os.environ.get("HOX_CORS_ORIGINS", "http://localhost:5173").split(",") if o],
    allow_methods=["GET"],
)


def _message(request: Request, status: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"detail": message})


@app.exception_handler(MissingKeysError)
def missing_keys(request: Request, exc: MissingKeysError):
    return _message(request, 503, str(exc))


@app.exception_handler(MarvelUnavailableError)
def marvel_down(request: Request, exc: MarvelUnavailableError):
    return _message(request, 502, f"Could not reach Marvel's API. {exc}")


@app.exception_handler(AmbiguousCreatorError)
def ambiguous(request: Request, exc: AmbiguousCreatorError):
    return _message(request, 409, str(exc))


@app.exception_handler(CreatorNotResolvedError)
def no_creator(request: Request, exc: CreatorNotResolvedError):
    return _message(request, 404, str(exc))


def get_client(request: Request) -> Iterator[MarvelClient]:
    settings = load_settings()  # raises MissingKeysError -> 503
    if getattr(request.app.state, "cache", None) is None:
        request.app.state.cache = Cache(cache_path())
    client = MarvelClient(settings, request.app.state.cache, getattr(request.app.state, "transport", None))
    try:
        yield client
    finally:
        client.close()


def scope_dep(client: MarvelClient = Depends(get_client)) -> Scope:
    return get_scope(client)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/shelves")
def shelves(scope: Scope = Depends(scope_dep)):
    return {
        "creator": {"id": scope.creator_id, "name": scope.creator_name},
        "window": {"start": scope.window_start, "end": scope.window_end},
        "prior": scope.prior,
        "main": scope.main,
        "attribution": scope.attribution,
    }


@app.get("/api/comics")
def comics(shelf: str | None = Query(None, pattern="^(main|prior)$"), scope: Scope = Depends(scope_dep)):
    items = [c for c in scope.comics if shelf is None or c.shelf == shelf]
    return {"items": items, "attribution": scope.attribution}


@app.get("/api/comics/{comic_id}")
def comic(comic_id: int, scope: Scope = Depends(scope_dep)):
    for c in scope.comics:
        if c.id == comic_id:
            return {"comic": c, "attribution": scope.attribution}
    raise HTTPException(404, "This comic is not on the Hickman shelves.")


@app.get("/api/characters")
def characters(scope: Scope = Depends(scope_dep)):
    return {"items": scope.characters, "attribution": scope.attribution}


@app.get("/api/characters/{character_id}")
def character(character_id: int, client: MarvelClient = Depends(get_client), scope: Scope = Depends(scope_dep)):
    found = next((c for c in scope.characters if c.id == character_id), None)
    if found is None:
        raise HTTPException(404, "This character does not appear on the Hickman shelves.")
    if not found.seed and found.description is None and found.thumbnail is None:
        results = client.get(f"/characters/{character_id}").get("data", {}).get("results", [])
        if results:
            found = Character(
                id=found.id, name=results[0].get("name") or found.name,
                description=results[0].get("description") or None,
                thumbnail=thumbnail_url(results[0].get("thumbnail")),
            )
    in_scope = [c for c in scope.comics if character_id in c.character_ids]
    return {"character": found, "comics": in_scope, "attribution": scope.attribution}


@app.get("/api/search")
def search(q: str = Query(..., min_length=2), scope: Scope = Depends(scope_dep)):
    needle = q.strip().lower()
    if len(needle) < 2:
        raise HTTPException(422, "Search needs at least 2 characters.")
    return {
        "comics": [c for c in scope.comics if needle in c.title.lower() or needle in (c.series_name or "").lower()],
        "characters": [c for c in scope.characters if needle in c.name.lower()],
        "attribution": scope.attribution,
    }
