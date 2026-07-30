from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from devo.main import app
from devo.ui_helpers import UiEndpointStatus

runner = CliRunner()


def test_ui_info_prints_urls_and_read_only_note(tmp_path: Path, monkeypatch) -> None:
    workspace = _workspace(tmp_path, monkeypatch)

    result = runner.invoke(app, ["ui", "info"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "http://127.0.0.1:8765" in result.output
    assert "http://127.0.0.1:5173" in result.output
    assert "devo api serve" in result.output
    assert "npm run dev" in result.output
    assert "UI v1 is read-only" in result.output
    assert _workspace_snapshot(workspace) == {}


def test_ui_urls_prints_only_local_urls(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)

    result = runner.invoke(app, ["ui", "urls"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "API: http://127.0.0.1:8765" in result.output
    assert "UI: http://127.0.0.1:5173" in result.output
    assert "0.0.0.0" not in result.output


def test_ui_status_handles_unavailable_servers_without_crashing(tmp_path: Path, monkeypatch) -> None:
    workspace = _workspace(tmp_path, monkeypatch)

    def fake_status():
        return [
            UiEndpointStatus("API health", "http://127.0.0.1:8765/api/health", "WARN", "Not reachable"),
            UiEndpointStatus("UI dev server", "http://127.0.0.1:5173", "WARN", "Not reachable"),
        ]

    monkeypatch.setattr("devo.main.check_ui_status", fake_status)

    result = runner.invoke(app, ["ui", "status"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "WARN API health" in result.output
    assert "WARN UI dev server" in result.output
    assert "does not start servers" in result.output
    assert _workspace_snapshot(workspace) == {}


def test_ui_status_reports_ok_when_mocked_reachable(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)

    def fake_status():
        return [
            UiEndpointStatus("API health", "http://127.0.0.1:8765/api/health", "OK", "Reachable"),
            UiEndpointStatus("UI dev server", "http://127.0.0.1:5173", "OK", "Reachable"),
        ]

    monkeypatch.setattr("devo.main.check_ui_status", fake_status)

    result = runner.invoke(app, ["ui", "status"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "OK   API health" in result.output
    assert "OK   UI dev server" in result.output


def test_ui_open_reports_guidance_when_ui_unavailable(tmp_path: Path, monkeypatch) -> None:
    workspace = _workspace(tmp_path, monkeypatch)

    monkeypatch.setattr(
        "devo.main.open_ui_if_reachable",
        lambda: (False, "UI is not reachable. Start the API with `devo api serve`, then start the UI from `ui` with `npm run dev`."),
    )

    result = runner.invoke(app, ["ui", "open"], terminal_width=240)

    assert result.exit_code == 1
    assert "UI is not reachable" in result.output
    assert "devo api serve" in result.output
    assert "npm run dev" in result.output
    assert _workspace_snapshot(workspace) == {}


def test_ui_open_reports_success_when_mocked_opened(tmp_path: Path, monkeypatch) -> None:
    _workspace(tmp_path, monkeypatch)
    monkeypatch.setattr("devo.main.open_ui_if_reachable", lambda: (True, "Opened http://127.0.0.1:5173"))

    result = runner.invoke(app, ["ui", "open"], terminal_width=240)

    assert result.exit_code == 0, result.output
    assert "Opened http://127.0.0.1:5173" in result.output


def _workspace(tmp_path: Path, monkeypatch) -> Path:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setenv("DEVO_WORKSPACE", str(workspace))
    return workspace


def _workspace_snapshot(workspace: Path) -> dict[str, str]:
    return {str(path.relative_to(workspace)): path.read_text(encoding="utf-8") for path in workspace.rglob("*") if path.is_file()}
