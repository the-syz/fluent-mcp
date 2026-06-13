from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .audit import copy_input_snapshot, create_run_layout, make_run_id, write_failure, write_json, write_status
from .fluent_batch import build_solver_journal, classify_batch_failure, run_fluent_batch
from .fluent_session import FluentLaunchOptions, FluentSession, detect_environment, run_fluent_version_probe
from .paths import PathSecurityError, create_standard_layout, ensure_within_project, relative_to_project, validate_project_layout
from .schemas import error_result, ok_result
from .summaries import write_report, write_summary


def check_environment(project_dir: str, fluent_version: str = "auto", probe_fluent: bool = False) -> dict[str, Any]:
    project_layout = validate_project_layout(project_dir)
    env = detect_environment()
    warnings = []
    if not env["packages"]["ansys-fluent-core"]:
        warnings.append("未安装 ansys-fluent-core")
    if not env["fluent"]["available"]:
        warnings.append("未在 PATH 或 AWP_ROOT* 环境变量中发现 Fluent")
    if not env["compiler"]["available"]:
        warnings.append("未在 PATH 中发现 C 编译器，compiled UDF 流程可能失败")
    compatibility = env.get("compatibility", {})
    if compatibility.get("recommended_backend") == "batch":
        warnings.append(compatibility.get("reason", "当前环境建议使用 batch/journal 后端"))
    data: dict[str, Any] = {
        "requested_fluent_version": fluent_version,
        "environment": env,
        "project_layout": project_layout,
    }
    if probe_fluent:
        data["fluent_probe"] = run_fluent_version_probe()
    return ok_result("check_environment", "环境检查完成", warnings=warnings, data=data)


def create_project(project_dir: str, project_name: str = "fluent_project", overwrite: bool = False) -> dict[str, Any]:
    project = Path(project_dir).expanduser().resolve()
    if project.exists() and any(project.iterdir()) and not overwrite:
        return error_result(
            "create_project",
            "项目目录已存在且不是空目录",
            code="input_error",
            details={"project_dir": str(project), "overwrite": overwrite},
        )
    create_standard_layout(project)
    configs = {
        "environment.json": {
            "project_name": project_name,
            "fluent_version": "auto",
            "notes": "由 fluent-research-mcp 生成。",
        },
        "solver_defaults.json": {
            "precision": "double",
            "processor_count": 2,
            "initialization": "hybrid",
            "iterations": 100,
        },
        "visualization_defaults.json": {
            "fields": ["pressure", "velocity-magnitude"],
            "surfaces": [],
            "exports": ["residual_csv", "residual_png"],
        },
    }
    artifacts = []
    for filename, payload in configs.items():
        target = project / "configs" / filename
        if overwrite or not target.exists():
            write_json(target, payload)
        artifacts.append(str(target))
    readme = project / "README.md"
    if overwrite or not readme.exists():
        readme.write_text(f"# {project_name}\n\n此目录用于 Fluent/PyFluent MCP 科研仿真运行。\n", encoding="utf-8")
    artifacts.append(str(readme))
    return ok_result("create_project", "项目目录结构已创建", artifacts=artifacts, data=validate_project_layout(project))


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
    try:
        case_path = ensure_within_project(project_dir, case_file)
        data_path = ensure_within_project(project_dir, data_file) if data_file else None
    except PathSecurityError as exc:
        return error_result("open_case", str(exc), code="input_error")
    if not case_path.exists():
        return error_result("open_case", "case 文件不存在", code="input_error", details={"case_file": str(case_path)})
    if data_path and not data_path.exists():
        return error_result("open_case", "data 文件不存在", code="input_error", details={"data_file": str(data_path)})
    try:
        options = FluentLaunchOptions(
            mode=mode,
            precision=precision,
            dimension=fluent_dimension,
            processor_count=processor_count,
            fluent_path=fluent_path,
        )
        with FluentSession(options) as session:
            solver = session.solver
            solver.file.read_case(file_name=str(case_path))
            if data_path:
                solver.file.read_data(file_name=str(data_path))
            healthy = solver.is_server_healthy() if hasattr(solver, "is_server_healthy") else True
    except Exception as exc:
        return error_result("open_case", "Fluent 打开 case 失败", code="fluent_error", details={"error": str(exc)})
    return ok_result("open_case", "case 已成功打开", data={"healthy": healthy})


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
    try:
        case_path = ensure_within_project(project_dir, case_file)
        data_path = ensure_within_project(project_dir, data_file) if data_file else None
    except PathSecurityError as exc:
        return error_result("run_solver", str(exc), code="input_error")
    if not case_path.exists():
        return error_result("run_solver", "case 文件不存在", code="input_error", details={"case_file": str(case_path)})
    if data_path and not data_path.exists():
        return error_result("run_solver", "data 文件不存在", code="input_error", details={"data_file": str(data_path)})
    if backend not in {"pyfluent", "batch"}:
        return error_result(
            "run_solver",
            "backend 只能是 pyfluent 或 batch",
            code="input_error",
            details={"backend": backend},
        )

    actual_run_id = make_run_id(project_dir, "solver") if run_id == "auto" else run_id
    root = create_run_layout(project_dir, actual_run_id)
    artifacts = [relative_to_project(project_dir, root)]
    write_status(project_dir, actual_run_id, "created", "运行目录已创建")
    copy_input_snapshot(project_dir, actual_run_id, [case_path] + ([data_path] if data_path else []))

    env = detect_environment()
    pyfluent_required = backend == "pyfluent"
    environment_ready = env["fluent"]["available"] and (not pyfluent_required or env["packages"]["ansys-fluent-core"])
    if not environment_ready:
        message = "Fluent/PyFluent 环境不可用" if pyfluent_required else "Fluent batch 环境不可用"
        details = {"environment": env}
        write_status(project_dir, actual_run_id, "environment_error", message)
        failure = write_failure(project_dir, actual_run_id, "environment_error", message, details)
        summary = write_summary(
            project_dir,
            actual_run_id,
            {
                "ok": False,
                "stage": "environment_error",
                "case_file": str(case_path),
                "data_file": str(data_path) if data_path else None,
                "backend": backend,
                "iterations": iterations,
                "convergence": convergence or {},
                "errors": [details],
            },
        )
        report = write_report(project_dir, actual_run_id)
        artifacts.extend(
            [
                relative_to_project(project_dir, failure),
                relative_to_project(project_dir, summary),
                relative_to_project(project_dir, report),
            ]
        )
        return error_result(
            "run_solver",
            message,
            code="environment_error",
            details=details,
            artifacts=artifacts,
            data={"run_id": actual_run_id},
        )

    if backend == "batch":
        result_case = root / "results" / "solved.cas.h5"
        result_data = root / "results" / "solved.dat.h5"
        journal = root / "journals" / "run_solver.jou"
        transcript = root / "logs" / "fluent_batch_stdout.log"
        stderr_log = root / "logs" / "fluent_batch_stderr.log"
        command_log = root / "logs" / "fluent_batch_command.json"
        journal.write_text(
            build_solver_journal(
                case_path=case_path,
                data_path=data_path,
                result_case=result_case,
                result_data=result_data,
                iterations=iterations,
                initialization=initialization,
            ),
            encoding="utf-8",
        )
        artifacts.append(relative_to_project(project_dir, journal))
        try:
            write_status(project_dir, actual_run_id, "launch_fluent_batch", "正在用 batch/journal 启动 Fluent")
            batch_result = run_fluent_batch(
                fluent_path=fluent_path,
                journal_path=journal,
                working_dir=root,
                dimension=fluent_dimension,
                processor_count=processor_count,
                timeout=batch_timeout,
            )
            transcript.write_text(batch_result.stdout, encoding="utf-8", errors="replace")
            stderr_log.write_text(batch_result.stderr, encoding="utf-8", errors="replace")
            write_json(
                command_log,
                {
                    "command": batch_result.command,
                    "returncode": batch_result.returncode,
                    "backend": "batch",
                    "fluent_dimension": fluent_dimension,
                    "processor_count": processor_count,
                    "timeout": batch_timeout,
                },
            )
            artifacts.extend(
                [
                    relative_to_project(project_dir, transcript),
                    relative_to_project(project_dir, stderr_log),
                    relative_to_project(project_dir, command_log),
                ]
            )
            if batch_result.returncode != 0:
                code, details = classify_batch_failure(batch_result)
                message = "Fluent batch 求解运行失败"
                write_status(project_dir, actual_run_id, code, message)
                failure = write_failure(project_dir, actual_run_id, code, message, details)
                summary = write_summary(
                    project_dir,
                    actual_run_id,
                    {
                        "ok": False,
                        "stage": code,
                        "backend": backend,
                        "case_file": str(case_path),
                        "data_file": str(data_path) if data_path else None,
                        "iterations": iterations,
                        "errors": [details],
                    },
                )
                report = write_report(project_dir, actual_run_id)
                artifacts.extend(
                    [
                        relative_to_project(project_dir, failure),
                        relative_to_project(project_dir, summary),
                        relative_to_project(project_dir, report),
                    ]
                )
                return error_result(
                    "run_solver",
                    message,
                    code=code,  # type: ignore[arg-type]
                    details=details,
                    artifacts=artifacts,
                    data={"run_id": actual_run_id, "backend": backend},
                )
        except Exception as exc:
            code, details = classify_batch_failure(None, exc)
            message = "Fluent batch 求解运行失败"
            write_status(project_dir, actual_run_id, code, message)
            failure = write_failure(project_dir, actual_run_id, code, message, details)
            summary = write_summary(project_dir, actual_run_id, {"ok": False, "stage": code, "backend": backend, "errors": [details]})
            report = write_report(project_dir, actual_run_id)
            artifacts.extend([relative_to_project(project_dir, failure), relative_to_project(project_dir, summary), relative_to_project(project_dir, report)])
            return error_result(
                "run_solver",
                message,
                code=code,  # type: ignore[arg-type]
                details=details,
                artifacts=artifacts,
                data={"run_id": actual_run_id, "backend": backend},
            )

        write_status(project_dir, actual_run_id, "completed", "batch/journal 求解运行完成")
        summary = write_summary(
            project_dir,
            actual_run_id,
            {
                "ok": True,
                "stage": "completed",
                "backend": backend,
                "case_file": str(case_path),
                "data_file": str(data_path) if data_path else None,
                "iterations": iterations,
            },
        )
        report = write_report(project_dir, actual_run_id)
        artifacts.extend([relative_to_project(project_dir, result_case), relative_to_project(project_dir, result_data), relative_to_project(project_dir, summary), relative_to_project(project_dir, report)])
        return ok_result("run_solver", "batch/journal 求解运行完成", artifacts=artifacts, data={"run_id": actual_run_id, "backend": backend})

    try:
        write_status(project_dir, actual_run_id, "launch_fluent", "正在启动 Fluent")
        with FluentSession(
            FluentLaunchOptions(
                fluent_path=fluent_path,
                dimension=fluent_dimension,
                processor_count=processor_count,
            )
        ) as session:
            solver = session.solver
            write_status(project_dir, actual_run_id, "read_case", "正在读取 case/data")
            solver.file.read_case(file_name=str(case_path))
            if data_path:
                solver.file.read_data(file_name=str(data_path))
            write_status(project_dir, actual_run_id, "initialize", f"初始化方式={initialization}")
            if initialization == "hybrid":
                solver.tui.solve.initialize.hyb_initialization()
            write_status(project_dir, actual_run_id, "iterate", f"迭代步数={iterations}")
            solver.tui.solve.iterate(iterations)
            result_case = root / "results" / "solved.cas.h5"
            result_data = root / "results" / "solved.dat.h5"
            solver.file.write_case(file_name=str(result_case))
            solver.file.write_data(file_name=str(result_data))
    except Exception as exc:
        message = "Fluent 求解运行失败"
        details = {"error": str(exc)}
        write_status(project_dir, actual_run_id, "solver_error", message)
        failure = write_failure(project_dir, actual_run_id, "solver_error", message, details)
        summary = write_summary(project_dir, actual_run_id, {"ok": False, "stage": "solver_error", "errors": [details]})
        report = write_report(project_dir, actual_run_id)
        artifacts.extend([relative_to_project(project_dir, failure), relative_to_project(project_dir, summary), relative_to_project(project_dir, report)])
        return error_result("run_solver", message, code="solver_error", details=details, artifacts=artifacts, data={"run_id": actual_run_id})

    write_status(project_dir, actual_run_id, "completed", "求解运行完成")
    summary = write_summary(
        project_dir,
        actual_run_id,
        {
            "ok": True,
            "stage": "completed",
            "backend": backend,
            "case_file": str(case_path),
            "data_file": str(data_path) if data_path else None,
            "iterations": iterations,
        },
    )
    report = write_report(project_dir, actual_run_id)
    artifacts.extend(
        [
            relative_to_project(project_dir, root / "results" / "solved.cas.h5"),
            relative_to_project(project_dir, root / "results" / "solved.dat.h5"),
            relative_to_project(project_dir, summary),
            relative_to_project(project_dir, report),
        ]
    )
    return ok_result("run_solver", "求解运行完成", artifacts=artifacts, data={"run_id": actual_run_id, "backend": backend})
