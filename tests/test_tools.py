from pathlib import Path
import subprocess

from fluent_research_mcp import fluent_batch
from fluent_research_mcp import fluent_tools
from fluent_research_mcp.fluent_tools import check_environment, create_project, run_solver
from fluent_research_mcp.schemas import ToolResult


def test_tool_result_schema_is_complete() -> None:
    payload = {
        "ok": True,
        "stage": "test",
        "message": "done",
        "artifacts": [],
        "warnings": [],
        "errors": [],
        "data": {},
    }
    assert ToolResult(**payload).ok is True


def test_create_project_writes_expected_files(tmp_path: Path) -> None:
    result = create_project(str(tmp_path), "pipe_flow")
    assert result["ok"] is True
    assert (tmp_path / "configs" / "environment.json").exists()
    assert (tmp_path / "udf" / "src").is_dir()
    assert (tmp_path / "runs").is_dir()


def test_create_project_refuses_non_empty_without_overwrite(tmp_path: Path) -> None:
    (tmp_path / "existing.txt").write_text("x", encoding="utf-8")
    result = create_project(str(tmp_path), "pipe_flow")
    assert result["ok"] is False
    assert result["errors"][0]["code"] == "input_error"


def test_check_environment_reports_missing_layout(tmp_path: Path) -> None:
    result = check_environment(str(tmp_path))
    assert result["ok"] is True
    assert result["data"]["project_layout"]["ok"] is False


def test_run_solver_missing_case_is_structured_error(tmp_path: Path) -> None:
    create_project(str(tmp_path), "study")
    result = run_solver(str(tmp_path), "cases/missing.cas.h5")
    assert result["ok"] is False
    assert result["stage"] == "run_solver"
    assert result["errors"][0]["code"] == "input_error"


def test_run_solver_batch_backend_writes_journal_and_logs(tmp_path: Path, monkeypatch) -> None:
    create_project(str(tmp_path), "study")
    case = tmp_path / "cases" / "baseline.cas"
    case.write_text("dummy", encoding="utf-8")
    monkeypatch.setattr(
        fluent_tools,
        "detect_environment",
        lambda: {
            "packages": {"ansys-fluent-core": None},
            "fluent": {"available": True},
            "compiler": {"available": False},
        },
    )

    def fake_run(command, **kwargs):
        assert command[1] == "3ddp"
        assert "-i" in command
        return subprocess.CompletedProcess(command, 0, stdout="fluent ok", stderr="")

    monkeypatch.setattr(fluent_batch, "_run_with_timeout", fake_run)
    result = run_solver(
        str(tmp_path),
        "cases/baseline.cas",
        iterations=1,
        backend="batch",
        fluent_path="fluent",
    )

    assert result["ok"] is True
    run_root = tmp_path / "runs" / result["data"]["run_id"]
    assert (run_root / "journals" / "run_solver.jou").exists()
    assert (run_root / "logs" / "fluent_batch_stdout.log").read_text(encoding="utf-8") == "fluent ok"
    journal = (run_root / "journals" / "run_solver.jou").read_text(encoding="utf-8")
    assert "/file/read-case" in journal
    assert "/solve/iterate 1" in journal


def test_run_solver_batch_backend_reports_failed_process(tmp_path: Path, monkeypatch) -> None:
    create_project(str(tmp_path), "study")
    case = tmp_path / "cases" / "baseline.cas"
    case.write_text("dummy", encoding="utf-8")
    monkeypatch.setattr(
        fluent_tools,
        "detect_environment",
        lambda: {
            "packages": {"ansys-fluent-core": None},
            "fluent": {"available": True},
            "compiler": {"available": False},
        },
    )

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(command, 2, stdout="license failed", stderr="bad license")

    monkeypatch.setattr(fluent_batch, "_run_with_timeout", fake_run)
    result = run_solver(
        str(tmp_path),
        "cases/baseline.cas",
        iterations=1,
        backend="batch",
        fluent_path="fluent",
    )

    assert result["ok"] is False
    assert result["errors"][0]["code"] == "license_error"
    run_root = tmp_path / "runs" / result["data"]["run_id"]
    assert (run_root / "failure.md").exists()
