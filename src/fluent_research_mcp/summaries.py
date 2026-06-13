from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .audit import run_dir, write_json


def build_summary(project_dir: str | Path, run_id: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    root = run_dir(project_dir, run_id)
    artifacts = []
    if root.exists():
        artifacts = [
            path.relative_to(root).as_posix()
            for path in sorted(root.rglob("*"))
            if path.is_file() and path.name not in {"summary.json", "report.md"}
        ]
    payload: dict[str, Any] = {
        "run_id": run_id,
        "run_dir": str(root),
        "artifacts": artifacts,
        "warnings": [],
        "errors": [],
    }
    if extra:
        payload.update(extra)
    return payload


def write_summary(project_dir: str | Path, run_id: str, extra: dict[str, Any] | None = None) -> Path:
    return write_json(run_dir(project_dir, run_id) / "summary.json", build_summary(project_dir, run_id, extra))


def write_report(project_dir: str | Path, run_id: str, summary: dict[str, Any] | None = None) -> Path:
    root = run_dir(project_dir, run_id)
    if summary is None:
        summary_path = root / "summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else build_summary(project_dir, run_id)
    lines = [
        f"# Fluent 运行报告：{run_id}",
        "",
        f"运行目录：`{root}`",
        "",
        "## 状态",
        "",
        f"- 是否成功：`{summary.get('ok', 'unknown')}`",
        f"- 阶段：`{summary.get('stage', 'unknown')}`",
        "",
        "## 产物",
        "",
    ]
    artifacts = summary.get("artifacts", [])
    if artifacts:
        lines.extend(f"- `{item}`" for item in artifacts)
    else:
        lines.append("- 未记录产物。")
    lines.append("")
    target = root / "report.md"
    target.write_text("\n".join(lines), encoding="utf-8")
    return target
