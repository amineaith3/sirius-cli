"""
sirius_cli/fetcher.py

Remote file downloader for the --from-url flag.
Fetches public CSV/JSON/Excel files from URLs, caches them locally under
~/.sirius_cache/ keyed by SHA-256 of the URL to prevent redundant downloads.
"""

import hashlib
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import typer

# Lazy import of requests to keep the module importable even if not installed
try:
    import requests
except ImportError:  # pragma: no cover
    requests = None  # type: ignore[assignment]


# Supported file types and their extensions
_SUPPORTED_EXTENSIONS = {".csv", ".json", ".xlsx", ".xls"}

# Map Content-Type headers to file extensions as a fallback
_CONTENT_TYPE_MAP = {
    "text/csv": ".csv",
    "application/csv": ".csv",
    "application/json": ".json",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.ms-excel": ".xls",
}


def get_cache_dir() -> Path:
    """Return the Sirius cache directory, creating it if absent."""
    cache_dir = Path.home() / ".sirius_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _url_to_cache_key(url: str) -> str:
    """Return a stable, filesystem-safe SHA-256 hex digest of the URL."""
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def _detect_extension(url: str, content_type: Optional[str] = None) -> str:
    """
    Detect the file extension from the URL path, falling back to the
    Content-Type header if the URL does not include a recognisable extension.

    Raises ValueError for unsupported types.
    """
    parsed = urlparse(url)
    path_ext = Path(parsed.path).suffix.lower()
    if path_ext in _SUPPORTED_EXTENSIONS:
        return path_ext

    if content_type:
        # Strip quality/charset params: "text/csv; charset=utf-8" → "text/csv"
        mime = content_type.split(";")[0].strip().lower()
        if mime in _CONTENT_TYPE_MAP:
            return _CONTENT_TYPE_MAP[mime]

    raise ValueError(
        f"Unsupported remote file type. "
        f"URL extension '{path_ext}' is not in {sorted(_SUPPORTED_EXTENSIONS)}. "
        f"Supported types: CSV, JSON, Excel (.xlsx/.xls)."
    )


def fetch_remote_file(url: str, cache_dir: Optional[Path] = None) -> Path:
    """
    Download a remote file to the local cache and return the local Path.

    If the file was already downloaded (cache hit), returns immediately without
    making a network request.

    Args:
        url:       The public URL to fetch.
        cache_dir: Override the cache directory (default: ~/.sirius_cache/).

    Returns:
        Path to the local cached file.

    Raises:
        ImportError: If the `requests` library is not installed.
        ValueError:  If the URL points to an unsupported file type.
        requests.RequestException: On any network-level failure.
    """
    if requests is None:  # pragma: no cover
        raise ImportError(
            "The 'requests' library is required for --from-url. "
            "Install it with: pip install requests"
        )

    resolved_cache_dir = cache_dir or get_cache_dir()
    cache_key = _url_to_cache_key(url)

    # --- Phase 1: HEAD request to detect content type and check cache ---
    try:
        head_resp = requests.head(url, timeout=10, allow_redirects=True)
        head_resp.raise_for_status()
        content_type: Optional[str] = head_resp.headers.get("Content-Type")
    except requests.RequestException:
        # HEAD may not be supported on all servers; fall back to URL-only detection
        content_type = None

    ext = _detect_extension(url, content_type)
    cached_path = resolved_cache_dir / f"{cache_key}{ext}"

    # --- Phase 2: Return cache hit immediately ---
    if cached_path.exists():
        typer.secho(
            f"  [CACHE] Using cached file: {cached_path.name}",
            fg=typer.colors.BRIGHT_BLACK,
        )
        return cached_path

    # --- Phase 3: Stream download with progress ---
    typer.echo(f"  Downloading: {url}")
    try:
        with requests.get(url, stream=True, timeout=30) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            with open(cached_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total:
                            pct = int(downloaded / total * 100)
                            typer.echo(
                                f"\r  Progress: {pct}% ({downloaded}/{total} bytes)",
                                nl=False,
                            )
            typer.echo("")  # newline after progress
    except requests.RequestException as exc:
        # Clean up partial download before raising
        if cached_path.exists():
            cached_path.unlink()
        raise exc

    typer.secho(f"  [OK] Saved to cache: {cached_path.name}", fg=typer.colors.GREEN)
    return cached_path
