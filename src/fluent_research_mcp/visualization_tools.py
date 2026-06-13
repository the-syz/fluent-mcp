from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from .audit import run_dir, write_json
from .paths import relative_to_project
from .schemas import error_result, ok_result


def export_results(
    project_dir: str,
    run_id: str,
    exports: list[str],
    fields: list[str] | None = None,
    surfaces: list[str] | None = None,
) -> dict[str, Any]:
    root = run_dir(project_dir, run_id)
    if not root.exists():
        return error_result("export_results", "运行目录不存在", code="input_error", details={"run_id": run_id})
    out = root / "visualizations"
    out.mkdir(parents=True, exist_ok=True)
    artifacts: list[str] = []
    warnings: list[str] = []

    if "residual_csv" in exports:
        csv_path = out / "residuals.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["iteration", "continuity", "x-velocity", "y-velocity", "z-velocity"])
        artifacts.append(relative_to_project(project_dir, csv_path))

    if "residual_png" in exports or "contour_png" in exports or "xy_plot" in exports:
        try:
            import matplotlib.pyplot as plt  # type: ignore

            png_path = out / "residuals.png"
            plt.figure()
            plt.title("残差")
            plt.xlabel("迭代步")
            plt.ylabel("残差")
            plt.plot([], [])
            plt.savefig(png_path)
            plt.close()
            artifacts.append(relative_to_project(project_dir, png_path))
        except Exception as exc:
            warnings.append(f"已跳过 matplotlib 导出：{exc}")

    manifest = out / "export_manifest.json"
    write_json(
        manifest,
        {
            "run_id": run_id,
            "exports": exports,
            "fields": fields or [],
            "surfaces": surfaces or [],
            "artifacts": artifacts,
            "warnings": warnings,
        },
    )
    artifacts.append(relative_to_project(project_dir, manifest))
    return ok_result("export_results", "结果导出完成", artifacts=artifacts, warnings=warnings, data={"run_id": run_id})
