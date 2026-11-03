from pydantic import BaseModel


class Attribution(BaseModel):
    text: str | None = None
    html: str | None = None


class CreatorCredit(BaseModel):
    id: int | None = None
    name: str
    role: str | None = None


class Comic(BaseModel):
    id: int
    title: str
    issue_number: float | None = None
    series_id: int | None = None
    series_name: str | None = None
    shelf: str  # "prior" | "main"
    in_resolved_series: bool  # False => an API result from another series
    onsale_date: str | None = None
    dates: dict[str, str] = {}
    format: str | None = None
    description: str | None = None
    thumbnail: str | None = None  # None => UI renders the local placeholder
    creators: list[CreatorCredit] = []
    character_ids: list[int] = []


class Character(BaseModel):
    id: int
    name: str
    seed: bool = False
    description: str | None = None
    thumbnail: str | None = None


class SeriesRef(BaseModel):
    id: int
    title: str
    start_year: int | None = None
    comic_count: int = 0


class Shelf(BaseModel):
    label: str
    series: list[SeriesRef]


class Scope(BaseModel):
    creator_id: int
    creator_name: str
    window_start: str | None = None
    window_end: str | None = None
    prior: Shelf
    main: Shelf
    comics: list[Comic]
    characters: list[Character]
    attribution: Attribution
