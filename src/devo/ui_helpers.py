from __future__ import annotations

import webbrowser
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_API_URL = "http://127.0.0.1:8765"
DEFAULT_UI_URL = "http://127.0.0.1:5173"
API_HEALTH_URL = f"{DEFAULT_API_URL}/api/health"
UI_STATUS_TIMEOUT_SECONDS = 1.5


@dataclass(frozen=True)
class UiEndpointStatus:
    name: str
    url: str
    status: str
    detail: str


def ui_urls() -> dict[str, str]:
    return {
        "api": DEFAULT_API_URL,
        "api_health": API_HEALTH_URL,
        "ui": DEFAULT_UI_URL,
    }


def check_ui_status(timeout_seconds: float = UI_STATUS_TIMEOUT_SECONDS) -> list[UiEndpointStatus]:
    return [
        _check_url("API health", API_HEALTH_URL, timeout_seconds=timeout_seconds, expect_text='"read_only"'),
        _check_url("UI dev server", DEFAULT_UI_URL, timeout_seconds=timeout_seconds, expect_text="Devo Dashboard"),
    ]


def open_ui_if_reachable(timeout_seconds: float = UI_STATUS_TIMEOUT_SECONDS) -> tuple[bool, str]:
    status = _check_url("UI dev server", DEFAULT_UI_URL, timeout_seconds=timeout_seconds, expect_text="Devo Dashboard")
    if status.status != "OK":
        return (
            False,
            "UI is not reachable. Start the API with `devo api serve`, then start the UI from `ui` with `npm run dev`.",
        )
    opened = webbrowser.open(DEFAULT_UI_URL, new=2)
    if not opened:
        return False, f"Could not open browser automatically. Open {DEFAULT_UI_URL} manually."
    return True, f"Opened {DEFAULT_UI_URL}"


def _check_url(name: str, url: str, *, timeout_seconds: float, expect_text: str | None = None) -> UiEndpointStatus:
    request = Request(url, headers={"Accept": "application/json,text/html"})
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - local-only fixed URLs
            status_code = getattr(response, "status", 200)
            body = response.read(8192).decode("utf-8", errors="replace")
    except HTTPError as exc:
        return UiEndpointStatus(name=name, url=url, status="FAIL", detail=f"HTTP {exc.code}")
    except (OSError, URLError) as exc:
        return UiEndpointStatus(name=name, url=url, status="WARN", detail=f"Not reachable: {exc}")
    if status_code >= 400:
        return UiEndpointStatus(name=name, url=url, status="FAIL", detail=f"HTTP {status_code}")
    if expect_text and expect_text not in body:
        return UiEndpointStatus(name=name, url=url, status="WARN", detail=f"Reachable, but expected marker was not found.")
    return UiEndpointStatus(name=name, url=url, status="OK", detail=f"Reachable: HTTP {status_code}")
