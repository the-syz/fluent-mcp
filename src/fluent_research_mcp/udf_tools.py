from __future__ import annotations

import difflib
import shutil
from pathlib import Path
from typing import Any

from .audit import run_dir, utc_timestamp, write_failure, write_status
from .fluent_session import FluentSession, detect_environment
from .paths import PathSecurityError, ensure_within_project, relative_to_project, require_relative_path
from .schemas import error_result, ok_result


def _validate_udf_path(path: str) -> Path:
    rel = require_relative_path(path)
    parts = rel.parts
    if len(parts) < 3 or parts[0] != "udf" or parts[1] not in {"src", "include"}:
        raise PathSecurityError("UDF 文件必须位于 udf/src 或 udf/include 目录下")
    return rel


def write_udf_files(project_dir: str, files: list[dict[str, str]], reason: str = "") -> dict[str, Any]:
    if not files:
        return error_result("write_udf_files", "没有提供任何文件", code="input_error")
    timestamp = utc_timestamp()
    history = ensure_within_project(project_dir, Path("udf") / "history" / timestamp)
    before_dir = history / "before"
    after_dir = history / "after"
    before_dir.mkdir(parents=True, exist_ok=False)
    after_dir.mkdir(parents=True, exist_ok=False)
    changed: list[str] = []
    diff_chunks: list[str] = []

    try:
        for item in files:
            rel = _validate_udf_path(item["path"])
            target = ensure_within_project(project_dir, rel)
            old = target.read_text(encoding="utf-8") if target.exists() else ""
            new = item["content"]
            before_snapshot = before_dir / rel.name
            after_snapshot = after_dir / rel.name
            before_snapshot.write_text(old, encoding="utf-8")
            after_snapshot.write_text(new, encoding="utf-8")
            diff_chunks.extend(
                difflib.unified_diff(
                    old.splitlines(keepends=True),
                    new.splitlines(keepends=True),
                    fromfile=f"a/{rel.as_posix()}",
                    tofile=f"b/{rel.as_posix()}",
                )
            )
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(new, encoding="utf-8")
            changed.append(rel.as_posix())
    except (KeyError, PathSecurityError) as exc:
        return error_result("write_udf_files", str(exc), code="input_error")

    (history / "reason.txt").write_text(reason, encoding="utf-8")
    diff_path = history / "diff.patch"
    diff_path.write_text("".join(diff_chunks), encoding="utf-8")
    return ok_result(
        "write_udf_files",
        "UDF 文件已写入，并已生成 diff",
        artifacts=[relative_to_project(project_dir, diff_path)],
        data={"changed_files": changed, "history_dir": relative_to_project(project_dir, history)},
    )


def compile_load_udf(
    project_dir: str,
    run_id: str,
    library_name: str,
    source_files: list[str],
    reviewed_diff: bool = False,
) -> dict[str, Any]:
    if not reviewed_diff:
        return error_result("compile_load_udf", "编译 UDF 前必须将 reviewed_diff 设为 true", code="input_error")
    try:
        sources = [ensure_within_project(project_dir, _validate_udf_path(path)) for path in source_files]
    except PathSecurityError as exc:
        return error_result("compile_load_udf", str(exc), code="input_error")
    missing = [str(path) for path in sources if not path.exists()]
    if missing:
        return error_result("compile_load_udf", "源文件不存在", code="input_error", details={"missing": missing})

    root = run_dir(project_dir, run_id)
    if not root.exists():
        return error_result("compile_load_udf", "运行目录不存在", code="input_error", details={"run_id": run_id})
    snapshot = root / "udf_snapshot"
    snapshot.mkdir(parents=True, exist_ok=True)
    for source in sources:
        shutil.copy2(source, snapshot / source.name)

    env = detect_environment()
    compile_log = root / "logs" / "udf_compile.log"
    load_log = root / "logs" / "udf_load.log"
    if not env["packages"]["ansys-fluent-core"] or not env["fluent"]["available"]:
        message = "Fluent/PyFluent 环境不可用，无法编译 UDF"
        compile_log.write_text(message + "\n", encoding="utf-8")
        write_status(project_dir, run_id, "udf_compile_error", message)
        failure = write_failure(project_dir, run_id, "udf_compile_error", message, {"environment": env})
        return error_result(
            "compile_load_udf",
            message,
            code="environment_error",
            artifacts=[
                relative_to_project(project_dir, compile_log),
                relative_to_project(project_dir, failure),
            ],
            data={"run_id": run_id},
        )

    try:
        with FluentSession() as session:
            solver = session.solver
            compile_log.write_text(f"正在编译 {library_name}: {source_files}\n", encoding="utf-8")
            solver.settings.setup.user_defined.compiled_udf.compile(
                library_name=library_name,
                source_files=[str(path) for path in sources],
            )
            load_log.write_text(f"正在加载 {library_name}\n", encoding="utf-8")
            solver.settings.setup.user_defined.compiled_udf.load(library_name=library_name)
    except Exception as exc:
        message = "UDF 编译或加载失败"
        compile_log.write_text(str(exc) + "\n", encoding="utf-8")
        failure = write_failure(project_dir, run_id, "udf_compile_error", message, {"error": str(exc)})
        return error_result(
            "compile_load_udf",
            message,
            code="udf_compile_error",
            details={"error": str(exc)},
            artifacts=[relative_to_project(project_dir, compile_log), relative_to_project(project_dir, failure)],
            data={"run_id": run_id},
        )

    return ok_result(
        "compile_load_udf",
        "UDF 已编译并加载",
        artifacts=[relative_to_project(project_dir, compile_log), relative_to_project(project_dir, load_log)],
        data={"run_id": run_id, "library_name": library_name},
    )
