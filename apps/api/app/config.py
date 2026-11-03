"""Settings read from the environment. Keys are never logged or returned."""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(REPO_ROOT / ".env")

DEFAULT_MARVEL_BASE_URL = "https://gateway.marvel.com/v1/public"
# Default is 24 hours. Check the current Marvel developer terms and change this
# constant if they differ.
CACHE_TTL_SECONDS = 24 * 60 * 60
HTTP_TIMEOUT_SECONDS = 10.0


class MissingKeysError(Exception):
    pass


@dataclass(frozen=True)
class Settings:
    public_key: str
    private_key: str


def load_settings() -> Settings:
    public = os.environ.get("MARVEL_PUBLIC_KEY", "").strip()
    private = os.environ.get("MARVEL_PRIVATE_KEY", "").strip()
    if not public or not private:
        raise MissingKeysError(
            "Marvel API keys are not configured. Set MARVEL_PUBLIC_KEY and "
            "MARVEL_PRIVATE_KEY in the server environment (see .env.example)."
        )
    return Settings(public_key=public, private_key=private)


def marvel_base_url() -> str:
    return os.environ.get("MARVEL_BASE_URL", "").strip() or DEFAULT_MARVEL_BASE_URL


def cache_path() -> Path:
    override = os.environ.get("HOX_CACHE_PATH")
    if override:
        return Path(override)
    return REPO_ROOT / "apps" / "api" / ".cache" / "cache.sqlite3"
