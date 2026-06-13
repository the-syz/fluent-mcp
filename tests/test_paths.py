from pathlib import Path

import pytest

from fluent_research_mcp.paths import PathSecurityError, create_standard_layout, ensure_within_project, validate_project_layout


def test_standard_layout(tmp_path: Path) -> None:
    create_standard_layout(tmp_path)
    result = validate_project_layout(tmp_path)
    assert result["ok"] is True
    assert result["missing"] == []


def test_rejects_path_escape(tmp_path: Path) -> None:
    with pytest.raises(PathSecurityError):
        ensure_within_project(tmp_path, tmp_path.parent / "outside.cas.h5")


def test_accepts_relative_inside_project(tmp_path: Path) -> None:
    resolved = ensure_within_project(tmp_path, "cases/baseline.cas.h5")
    assert resolved == (tmp_path / "cases" / "baseline.cas.h5").resolve()

