from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .fluent_tools import check_environment as check_environment_impl
from .fluent_tools import create_project as create_project_impl
from .fluent_tools import open_case as open_case_impl
from .fluent_tools import run_solver as run_solver_impl
from .schemas import error_result, ok_result
from .summaries import write_report, write_summary
from .udf_tools import compile_load_udf as compile_load_udf_impl
from .udf_tools import write_udf_files as write_udf_files_impl
from .visualization_tools import export_results as export_results_impl

mcp = FastMCP("fluent-research-mcp")


@mcp.tool()
def check_environment(project_dir: str, fluent_version: str = "auto", probe_fluent: bool = False) -> dict[str, Any]:
    return check_environment_impl(project_dir, fluent_version, probe_fluent)


@mcp.tool()
def create_project(project_dir: str, project_name: str = "fluent_project", overwrite: bool = False) -> dict[str, Any]:
    return create_project_impl(project_dir, project_name, overwrite)


@mcp.tool()
def open_case(
    project_dir: str,
    case_file: str,
    data_file: str | None = None,
    mode: str = "solver",
    precision: str = "double",
    fluent_dimension: str = "3ddp",
    processor_count: int = 2,
    fluent_path: str | None = None,
) -> dict[str, Any]:
    return open_case_impl(project_dir, case_file, data_file, mode, precision, fluent_dimension, processor_count, fluent_path)


@mcp.tool()
def run_solver(
    project_dir: str,
    case_file: str,
    data_file: str | None = None,
    run_id: str = "auto",
    initialization: str = "hybrid",
    iterations: int = 100,
    convergence: dict[str, Any] | None = None,
    fluent_path: str | None = None,
    backend: str = "pyfluent",
    fluent_dimension: str = "3ddp",
    processor_count: int = 1,
    batch_timeout: int = 1800,
) -> dict[str, Any]:
    return run_solver_impl(
        project_dir,
        case_file,
        data_file,
        run_id,
        initialization,
        iterations,
        convergence,
        fluent_path,
        backend,
        fluent_dimension,
        processor_count,
        batch_timeout,
    )


@mcp.tool()
def write_udf_files(project_dir: str, files: list[dict[str, str]], reason: str = "") -> dict[str, Any]:
    return write_udf_files_impl(project_dir, files, reason)


@mcp.tool()
def compile_load_udf(
    project_dir: str,
    run_id: str,
    library_name: str,
    source_files: list[str],
    reviewed_diff: bool = False,
) -> dict[str, Any]:
    return compile_load_udf_impl(project_dir, run_id, library_name, source_files, reviewed_diff)


@mcp.tool()
def export_results(
    project_dir: str,
    run_id: str,
    exports: list[str],
    fields: list[str] | None = None,
    surfaces: list[str] | None = None,
) -> dict[str, Any]:
    return export_results_impl(project_dir, run_id, exports, fields, surfaces)


@mcp.tool()
def summarize_run(project_dir: str, run_id: str) -> dict[str, Any]:
    try:
        summary = write_summary(project_dir, run_id)
        report = write_report(project_dir, run_id)
    except Exception as exc:
        return error_result("summarize_run", "生成运行摘要失败", code="input_error", details={"error": str(exc)})
    return ok_result("summarize_run", "运行摘要已生成", artifacts=[str(summary), str(report)], data={"run_id": run_id})


@mcp.prompt()
def review_udf_change(diff: str) -> str:
    return (
        "请审查这份 Fluent UDF diff。重点检查物理公式、单位、边界假设、"
        "thread 访问、内存安全和可能的编译错误。\n\n"
        f"{diff}"
    )


@mcp.prompt()
def analyze_failed_run(failure_summary: str) -> str:
    return (
        "请分析这次 Fluent 运行失败。将失败归类为环境、license、输入、"
        "Fluent 执行、UDF 编译/加载、求解或后处理问题，"
        "并列出下一步具体诊断操作。\n\n"
        f"{failure_summary}"
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
