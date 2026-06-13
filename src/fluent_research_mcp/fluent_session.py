from __future__ import annotations

import importlib.metadata
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .fluent_compat import compatibility_report


def package_version(package: str) -> str | None:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return None


def awp_roots() -> dict[str, str]:
    return {key: value for key, value in os.environ.items() if key.startswith("AWP_ROOT")}


def detect_environment() -> dict[str, Any]:
    fluent_cmd = shutil.which("fluent")
    fluent_path = os.environ.get("FLUENT_PATH")
    compiler_cmd = shutil.which("cl") or shutil.which("gcc") or shutil.which("clang")
    packages = {
        "mcp": package_version("mcp"),
        "ansys-fluent-core": package_version("ansys-fluent-core"),
        "ansys-fluent-visualization": package_version("ansys-fluent-visualization"),
    }
    fluent_info = {
        "command": fluent_cmd,
        "fluent_path": fluent_path,
        "fluent_path_exists": bool(fluent_path and Path(fluent_path).exists()),
        "awp_roots": awp_roots(),
        "available": bool(fluent_cmd or fluent_path or awp_roots()),
    }
    return {
        "python": {
            "executable": sys.executable,
            "version": sys.version.split()[0],
        },
        "packages": packages,
        "fluent": fluent_info,
        "compatibility": compatibility_report(fluent_info, packages["ansys-fluent-core"]),
        "compiler": {
            "command": compiler_cmd,
            "available": bool(compiler_cmd),
        },
    }


def import_pyfluent():
    try:
        import ansys.fluent.core as pyfluent  # type: ignore
    except ImportError as exc:
        raise RuntimeError("未安装 ansys-fluent-core") from exc
    return pyfluent


@dataclass
class FluentLaunchOptions:
    mode: str = "solver"
    precision: str = "double"
    dimension: str | None = None
    processor_count: int = 2
    start_transcript: bool = True
    fluent_path: str | None = None
    start_timeout: int | None = 120


class FluentSession:
    def __init__(self, options: FluentLaunchOptions | None = None):
        self.options = options or FluentLaunchOptions()
        self.pyfluent = None
        self.solver = None

    def __enter__(self):
        self.launch()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.exit()
        return False

    def launch(self):
        self.pyfluent = import_pyfluent()
        mode = getattr(self.pyfluent.FluentMode, self.options.mode.upper(), None)
        precision = getattr(self.pyfluent.Precision, self.options.precision.upper(), None)
        dimension = _pyfluent_dimension(self.pyfluent, self.options.dimension)
        launch_kwargs = {
            "mode": mode or self.options.mode,
            "precision": precision or self.options.precision,
            "processor_count": self.options.processor_count,
            "start_transcript": self.options.start_transcript,
        }
        if dimension is not None:
            launch_kwargs["dimension"] = dimension
        fluent_path = self.options.fluent_path or os.environ.get("FLUENT_PATH") or shutil.which("fluent")
        if fluent_path:
            launch_kwargs["fluent_path"] = fluent_path
        if self.options.start_timeout is not None:
            launch_kwargs["start_timeout"] = self.options.start_timeout
        self.solver = self.pyfluent.launch_fluent(**launch_kwargs)
        return self.solver

    def exit(self) -> None:
        if self.solver is None:
            return
        try:
            self.solver.exit()
        finally:
            self.solver = None


def _pyfluent_dimension(pyfluent: Any, dimension: str | None) -> Any | None:
    if not dimension:
        return None
    normalized = dimension.lower()
    if normalized.startswith("2"):
        return getattr(pyfluent.Dimension, "TWO", 2)
    if normalized.startswith("3"):
        return getattr(pyfluent.Dimension, "THREE", 3)
    return dimension


def run_fluent_version_probe(timeout: int = 20) -> dict[str, Any]:
    command = shutil.which("fluent")
    if not command:
        return {"ok": False, "message": "未找到 fluent 命令"}
    try:
        completed = subprocess.run(
            [command, "-v"],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except Exception as exc:  # pragma: no cover - 依赖本机 Fluent 安装状态。
        return {"ok": False, "message": str(exc)}
    return {
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }
