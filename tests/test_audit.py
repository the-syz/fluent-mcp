from pathlib import Path

import pytest

from fluent_research_mcp.audit import create_run_layout, make_run_id
from fluent_research_mcp.paths import create_standard_layout


def test_run_id_is_unique_when_existing_dir_present(tmp_path: Path) -> None:
    create_standard_layout(tmp_path)
    first = make_run_id(tmp_path, "baseline")
    create_run_layout(tmp_path, first)
    second = make_run_id(tmp_path, "baseline")
    assert first != second


def test_existing_run_directory_is_not_overwritten(tmp_path: Path) -> None:
    create_standard_layout(tmp_path)
    run_id = "20260509T153000Z_baseline"
    create_run_layout(tmp_path, run_id)
    with pytest.raises(FileExistsError):
        create_run_layout(tmp_path, run_id)

