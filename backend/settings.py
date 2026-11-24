"""Environment-based settings for the synthetic API-backed application."""

from collections.abc import Mapping
from urllib.parse import urlsplit

from sqlalchemy.engine import URL

LOCAL_CORS_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")


def build_database_url(environ: Mapping[str, str]) -> URL:
    """Build a PostgreSQL URL without interpolating unescaped credentials."""
    sslmode = environ.get("POSTGRES_SSLMODE", "").strip()
    if sslmode and sslmode not in {
        "disable", "allow", "prefer", "require", "verify-ca", "verify-full"
    }:
        raise ValueError("POSTGRES_SSLMODE is invalid")
    port = int(environ.get("POSTGRES_PORT", "5432"))
    if not 1 <= port <= 65535:
        raise ValueError("POSTGRES_PORT must be between 1 and 65535")
    return URL.create(
        "postgresql+psycopg",
        username=environ["POSTGRES_USER"],
        password=environ["POSTGRES_PASSWORD"],
        host=environ.get("POSTGRES_HOST", "localhost"),
        port=port,
        database=environ["POSTGRES_DB"],
        query={"sslmode": sslmode} if sslmode else {},
    )


def cors_origins(environ: Mapping[str, str]) -> list[str]:
    """Allow explicit browser origins; an empty setting disables cross-origin access."""
    configured = environ.get("EMR_CORS_ORIGINS")
    if configured is None:
        return list(LOCAL_CORS_ORIGINS)
    origins = []
    for value in configured.split(","):
        origin = value.strip().rstrip("/")
        if not origin:
            continue
        parsed = urlsplit(origin)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path
            or parsed.query
            or parsed.fragment
            or "*" in origin
            or any(char.isspace() for char in origin)
        ):
            raise ValueError("EMR_CORS_ORIGINS must contain explicit HTTP(S) origins")
        # Accessing port validates malformed and out-of-range values.
        parsed.port
        if origin not in origins:
            origins.append(origin)
    return origins
