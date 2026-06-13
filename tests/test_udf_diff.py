from pathlib import Path

from fluent_research_mcp.fluent_tools import create_project
from fluent_research_mcp.udf_tools import write_udf_files


def test_write_udf_files_creates_diff_for_new_file(tmp_path: Path) -> None:
    result = create_project(str(tmp_path), "study")
    assert result["ok"] is True
    write_result = write_udf_files(
        str(tmp_path),
        [{"path": "udf/src/source_terms.c", "content": "#include \"udf.h\"\n"}],
        "initial UDF",
    )
    assert write_result["ok"] is True
    diff_path = tmp_path / write_result["artifacts"][0]
    assert diff_path.exists()
    assert "+#include \"udf.h\"" in diff_path.read_text(encoding="utf-8")
    assert (tmp_path / "udf" / "src" / "source_terms.c").exists()


def test_write_udf_files_rejects_non_udf_path(tmp_path: Path) -> None:
    create_project(str(tmp_path), "study")
    result = write_udf_files(str(tmp_path), [{"path": "README.md", "content": "bad"}])
    assert result["ok"] is False
    assert result["errors"][0]["code"] == "input_error"

