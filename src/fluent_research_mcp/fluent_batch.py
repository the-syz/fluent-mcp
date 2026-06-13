from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class BatchRunResult:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str


def resolve_fluent_command(fluent_path: str | None = None) -> str | None:
    candidate = fluent_path or os.environ.get("FLUENT_PATH") or shutil.which("fluent")
    if not candidate:
        return None
    return str(Path(candidate).expanduser()) if Path(candidate).exists() else candidate


def _journal_string(path: str | Path) -> str:
    normalized = str(Path(path).resolve()).replace("\\", "/")
    return '"' + normalized.replace('"', '\\"') + '"'


def build_solver_journal(
    *,
    case_path: str | Path,
    data_path: str | Path | None,
    result_case: str | Path,
    result_data: str | Path,
    iterations: int,
    initialization: str,
) -> str:
    lines = [
        "; 由 fluent-research-mcp 自动生成",
        "; 用于 Fluent batch/journal 后端",
        f"/file/read-case {_journal_string(case_path)}",
    ]
    if data_path:
        lines.append(f"/file/read-data {_journal_string(data_path)}")
    if initialization == "hybrid":
        lines.append("/solve/initialize/hyb-initialization")
    elif initialization not in {"none", "skip", ""}:
        lines.append(f"; 未识别的初始化方式：{initialization}，此处跳过自动初始化")
    if iterations > 0:
        lines.append(f"/solve/iterate {iterations}")
    lines.extend(
        [
            f"/file/write-case {_journal_string(result_case)}",
            f"/file/write-data {_journal_string(result_data)}",
            "/exit yes",
            "",
        ]
    )
    return "\n".join(lines)


def run_fluent_batch(
    *,
    fluent_path: str | None,
    journal_path: str | Path,
    working_dir: str | Path,
    dimension: str = "3ddp",
    processor_count: int = 1,
    timeout: int = 1800,
) -> BatchRunResult:
    fluent_command = resolve_fluent_command(fluent_path)
    if fluent_command is None:
        raise FileNotFoundError("未找到 fluent 命令，也未设置 FLUENT_PATH")
    command = [
        fluent_command,
        dimension,
        "-g",
        f"-t{processor_count}",
        "-i",
        str(Path(journal_path).resolve()),
    ]
    completed = _run_with_timeout(
        command,
        cwd=str(Path(working_dir).resolve()),
        timeout=timeout,
    )
    return BatchRunResult(
        command=command,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def _run_with_timeout(command: list[str], cwd: str, timeout: int) -> subprocess.CompletedProcess[str]:
    process = subprocess.Popen(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        _terminate_process_tree(process.pid)
        stdout, stderr = process.communicate(timeout=30)
        exc.stdout = stdout
        exc.stderr = stderr
        raise
    return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)


def _terminate_process_tree(pid: int) -> None:
    if sys.platform.startswith("win"):
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            check=False,
            capture_output=True,
            text=True,
        )
        return
    try:
        os.kill(pid, 15)
    except OSError:
        return


def classify_batch_failure(result: BatchRunResult | None, error: Exception | None = None) -> tuple[str, dict[str, Any]]:
    if error is not None:
        details: dict[str, Any] = {"error": f"{type(error).__name__}: {error}"}
        if isinstance(error, subprocess.TimeoutExpired):
            details["timeout"] = error.timeout
            details["command"] = error.cmd
            details["stdout_tail"] = (error.stdout or "")[-4000:]
            details["stderr_tail"] = (error.stderr or "")[-4000:]
        return "solver_error", details
    assert result is not None
    combined = f"{result.stdout}\n{result.stderr}".lower()
    code = "license_error" if "license" in combined else "solver_error"
    details = {
        "returncode": result.returncode,
        "command": result.command,
        "stdout_tail": result.stdout[-4000:],
        "stderr_tail": result.stderr[-4000:],
    }
    return code, details
