from __future__ import annotations

from pathlib import Path


STANDARD_DIRS = [
    "configs",
    "cases",
    "udf/src",
    "udf/include",
    "udf/builds",
    "udf/history",
    "journals",
    "runs",
    "visualizations",
]


class PathSecurityError(ValueError):
    pass


def resolve_project_dir(project_dir: str | Path) -> Path:
    return Path(project_dir).expanduser().resolve()


def ensure_within_project(project_dir: str | Path, candidate: str | Path) -> Path:
    project = resolve_project_dir(project_dir)
    path = Path(candidate)
    if not path.is_absolute():
        path = project / path
    resolved = path.expanduser().resolve()
    if resolved == project or project in resolved.parents:
        return resolved
    raise PathSecurityError(f"路径超出了 project_dir 范围：{candidate}")


def relative_to_project(project_dir: str | Path, candidate: str | Path) -> str:
    project = resolve_project_dir(project_dir)
    resolved = ensure_within_project(project, candidate)
    return resolved.relative_to(project).as_posix()


def require_relative_path(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        raise PathSecurityError(f"此处不接受绝对路径：{path}")
    if any(part == ".." for part in candidate.parts):
        raise PathSecurityError(f"此处不接受上级目录跳转：{path}")
    return candidate


def create_standard_layout(project_dir: str | Path) -> list[Path]:
    project = resolve_project_dir(project_dir)
    created: list[Path] = []
    project.mkdir(parents=True, exist_ok=True)
    for item in STANDARD_DIRS:
        path = project / item
        path.mkdir(parents=True, exist_ok=True)
        created.append(path)
    return created


def validate_project_layout(project_dir: str | Path) -> dict[str, object]:
    project = resolve_project_dir(project_dir)
    missing = [item for item in STANDARD_DIRS if not (project / item).is_dir()]
    return {
        "project_dir": str(project),
        "exists": project.exists(),
        "missing": missing,
        "ok": project.exists() and not missing,
    }
