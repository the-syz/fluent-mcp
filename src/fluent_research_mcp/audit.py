from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .paths import ensure_within_project, resolve_project_dir


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def make_run_id(project_dir: str | Path, label: str = "run") -> str:
    safe_label = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in label)
    safe_label = safe_label.strip("-_") or "run"
    base = f"{utc_timestamp()}_{safe_label}"
    runs_dir = resolve_project_dir(project_dir) / "runs"
    candidate = base
    index = 1
    while (runs_dir / candidate).exists():
        index += 1
        candidate = f"{base}_{index}"
    return candidate


def run_dir(project_dir: str | Path, run_id: str) -> Path:
    return ensure_within_project(project_dir, Path("runs") / run_id)


def create_run_layout(project_dir: str | Path, run_id: str) -> Path:
    root = run_dir(project_dir, run_id)
    if root.exists():
        raise FileExistsError(f"运行目录已存在：{root}")
    for item in ["inputs", "udf_snapshot", "journals", "logs", "results", "visualizations"]:
        (root / item).mkdir(parents=True, exist_ok=False)
    return root


def write_json(path: str | Path, payload: dict[str, Any]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return target


def append_log(path: str | Path, message: str) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(message.rstrip() + "\n")
    return target


def write_status(project_dir: str | Path, run_id: str, stage: str, message: str) -> Path:
    payload = {
        "run_id": run_id,
        "stage": stage,
        "message": message,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    return write_json(run_dir(project_dir, run_id) / "status.json", payload)


def write_failure(
    project_dir: str | Path,
    run_id: str,
    stage: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> Path:
    root = run_dir(project_dir, run_id)
    lines = [
        f"# 运行失败：{run_id}",
        "",
        f"- 阶段：`{stage}`",
        f"- 说明：{message}",
        "",
    ]
    if details:
        lines.extend(["## 详细信息", "", "```json"])
        lines.append(json.dumps(details, indent=2, ensure_ascii=False))
        lines.append("```")
    target = root / "failure.md"
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def copy_input_snapshot(project_dir: str | Path, run_id: str, paths: list[str | Path]) -> list[Path]:
    root = run_dir(project_dir, run_id) / "inputs"
    copied: list[Path] = []
    for item in paths:
        source = ensure_within_project(project_dir, item)
        if not source.exists():
            continue
        target = root / source.name
        if source.is_dir():
            shutil.copytree(source, target, dirs_exist_ok=False)
        else:
            shutil.copy2(source, target)
        copied.append(target)
    return copied
