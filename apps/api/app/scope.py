"""Resolve the Hickman scope from the Marvel API. No hardcoded ids or issue numbers."""
import re
from typing import Any

from .config import marvel_base_url
from .marvel import MarvelClient
from .models import Attribution, Character, Comic, CreatorCredit, Scope, SeriesRef, Shelf

SCOPE_CACHE_KEY = "scope:v1"

PRIOR_SERIES = [("House of X", 2019), ("Powers of X", 2019)]
MAIN_SERIES = [("X-Men", 2019), ("Giant-Size X-Men", 2020), ("Inferno", 2021)]
SEED_CHARACTERS = [
    "Professor X", "Magneto", "Cyclops", "Jean Grey", "Storm", "Wolverine",
    "Emma Frost", "Nightcrawler", "Mystique", "Moira MacTaggert", "Apocalypse", "Kate Pryde",
]
SEED_FALLBACKS = {"Kate Pryde": "Kitty Pryde"}
UNSET_ONSALE_PREFIX = "2029-12-31"


class CreatorNotResolvedError(Exception):
    pass


class AmbiguousCreatorError(Exception):
    pass


def resource_id(uri: str | None) -> int | None:
    if not uri:
        return None
    match = re.search(r"/(\d+)$", uri)
    return int(match.group(1)) if match else None


def thumbnail_url(thumbnail: dict | None) -> str | None:
    if not thumbnail or not thumbnail.get("path") or "image_not_available" in thumbnail["path"]:
        return None
    path = thumbnail["path"]
    if path.startswith("http://"):
        path = "https://" + path[len("http://"):]
    return f"{path}/portrait_xlarge.{thumbnail.get('extension', 'jpg')}"


def onsale_date(raw: dict) -> str | None:
    for entry in raw.get("dates") or []:
        if entry.get("type") == "onsaleDate" and entry.get("date"):
            date = entry["date"][:10]
            return None if date.startswith(UNSET_ONSALE_PREFIX) else date
    return None


def credits_writer(raw: dict, creator_id: int) -> bool:
    """True only when the API credits this creator with the writer role."""
    for item in (raw.get("creators") or {}).get("items") or []:
        if resource_id(item.get("resourceURI")) == creator_id and (item.get("role") or "").strip().lower() == "writer":
            return True
    return False


def _title_matches(title: str, wanted: str) -> bool:
    return re.sub(r"\s*\([^)]*\)\s*$", "", title or "").strip().lower() == wanted.lower()


def resolve_series(client: MarvelClient, title: str, year: int) -> dict | None:
    body = client.get("/series", {"titleStartsWith": title, "startYear": year, "limit": 100})
    for result in body.get("data", {}).get("results", []):
        if result.get("startYear") == year and _title_matches(result.get("title", ""), title):
            return result
    return None


def parse_comic(raw: dict, shelf: str, in_resolved_series: bool) -> Comic:
    series = raw.get("series") or {}
    return Comic(
        id=raw["id"],
        title=raw.get("title") or "",
        issue_number=raw.get("issueNumber"),
        series_id=resource_id(series.get("resourceURI")),
        series_name=series.get("name"),
        shelf=shelf,
        in_resolved_series=in_resolved_series,
        onsale_date=onsale_date(raw),
        dates={d["type"]: d["date"] for d in raw.get("dates") or [] if d.get("type") and d.get("date")},
        format=raw.get("format") or None,
        description=raw.get("description") or None,
        thumbnail=thumbnail_url(raw.get("thumbnail")),
        creators=[
            CreatorCredit(id=resource_id(i.get("resourceURI")), name=i.get("name", ""), role=i.get("role"))
            for i in (raw.get("creators") or {}).get("items") or []
        ],
        character_ids=[
            cid for cid in (resource_id(i.get("resourceURI")) for i in (raw.get("characters") or {}).get("items") or [])
            if cid is not None
        ],
    )


def resolve_creator(client: MarvelClient) -> tuple[dict, dict]:
    body = client.get("/creators", {"lastName": "Hickman", "firstName": "Jonathan"})
    results = body.get("data", {}).get("results", [])
    if len(results) > 1:
        names = ", ".join(sorted(f"{r.get('fullName', '?')} (id {r.get('id')})" for r in results))
        raise AmbiguousCreatorError(f"More than one creator matched Jonathan Hickman: {names}. Not guessing.")
    if not results:
        raise CreatorNotResolvedError("Marvel's API returned no creator matching Jonathan Hickman.")
    return results[0], body


def resolve_seed_characters(client: MarvelClient) -> list[Character]:
    found: list[Character] = []
    seen: set[int] = set()
    for name in SEED_CHARACTERS:
        candidates = [name] + ([SEED_FALLBACKS[name]] if name in SEED_FALLBACKS else [])
        for candidate in candidates:
            results = client.get("/characters", {"name": candidate}).get("data", {}).get("results", [])
            if results:
                raw = results[0]
                if raw["id"] not in seen:
                    seen.add(raw["id"])
                    found.append(Character(
                        id=raw["id"], name=raw.get("name") or candidate, seed=True,
                        description=raw.get("description") or None, thumbnail=thumbnail_url(raw.get("thumbnail")),
                    ))
                break
    return found


def build_scope(client: MarvelClient) -> Scope:
    creator, creator_body = resolve_creator(client)
    creator_id = creator["id"]
    attribution = Attribution(
        text=creator_body.get("attributionText"), html=creator_body.get("attributionHTML")
    )

    def fetch_series_comics(series_id: int) -> list[dict]:
        raws, _ = client.get_all(f"/series/{series_id}/comics", {"creators": creator_id, "orderBy": "onsaleDate"})
        return [r for r in raws if credits_writer(r, creator_id)]

    shelves: dict[str, list[SeriesRef]] = {"prior": [], "main": []}
    by_id: dict[int, Comic] = {}
    raw_by_id: dict[int, dict] = {}
    for shelf, wanted in (("prior", PRIOR_SERIES), ("main", MAIN_SERIES)):
        for title, year in wanted:
            series = resolve_series(client, title, year)
            if series is None:
                continue
            raws = fetch_series_comics(series["id"])
            shelves[shelf].append(SeriesRef(
                id=series["id"], title=series.get("title", title), start_year=series.get("startYear"),
                comic_count=len(raws),
            ))
            for raw in raws:
                raw_by_id.setdefault(raw["id"], raw)
                by_id.setdefault(raw["id"], parse_comic(raw, shelf, True))

    # Window: from the House of X series' first on-sale date to the last
    # Hickman-written issue in the resolved set.
    hox = next((s for s in shelves["prior"] if s.title.lower().startswith("house of x")), None)
    hox_dates = [c.onsale_date for c in by_id.values() if c.series_id == (hox.id if hox else None) and c.onsale_date]
    all_dates = [c.onsale_date for c in by_id.values() if c.onsale_date]
    window_start = min(hox_dates or all_dates, default=None)
    window_end = max(all_dates, default=None)

    # Other series: only comics in the window where Hickman is credited as writer.
    if window_start and window_end:
        raws, _ = client.get_all("/comics", {
            "creators": creator_id, "dateRange": f"{window_start},{window_end}", "orderBy": "onsaleDate",
        })
        for raw in raws:
            if raw["id"] in by_id or not credits_writer(raw, creator_id):
                continue
            comic = parse_comic(raw, "main", False)
            if comic.onsale_date and window_start <= comic.onsale_date <= window_end:
                by_id[comic.id] = comic
                raw_by_id[comic.id] = raw

    comics = sorted(by_id.values(), key=lambda c: (c.onsale_date or "", c.id), reverse=True)

    # Roster: seeds resolved first, then characters credited on in-scope comics.
    characters = resolve_seed_characters(client)
    known = {c.id for c in characters}
    derived: dict[int, str] = {}
    for raw in raw_by_id.values():
        for item in (raw.get("characters") or {}).get("items") or []:
            cid = resource_id(item.get("resourceURI"))
            if cid is not None and cid not in known:
                derived[cid] = item.get("name", "")
    characters += [Character(id=cid, name=name) for cid, name in sorted(derived.items(), key=lambda kv: kv[1].lower())]

    return Scope(
        creator_id=creator_id,
        creator_name=creator.get("fullName") or "Jonathan Hickman",
        window_start=window_start,
        window_end=window_end,
        prior=Shelf(label="House of X / Powers of X", series=shelves["prior"]),
        main=Shelf(label="X-Men, post-House of X", series=shelves["main"]),
        comics=comics,
        characters=characters,
        attribution=attribution,
    )


def get_scope(client: MarvelClient) -> Scope:
    key = f"{marvel_base_url()}:{SCOPE_CACHE_KEY}"
    cached = client.cache.get(key)
    if cached is not None:
        return Scope.model_validate(cached)
    scope = build_scope(client)
    client.cache.set(key, scope.model_dump())
    return scope
