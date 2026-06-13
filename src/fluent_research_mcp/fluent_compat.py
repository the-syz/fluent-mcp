from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def parse_release_number(value: str | Path | None) -> int | None:
    if value is None:
        return None
    text = str(value)
    patterns = [
        r"AWP_ROOT(\d{3})",
        r"[\\/ ]v(\d{3})(?:[\\/]|$)",
        r"ANSYS Inc(\d{3})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def release_label(release_number: int | None) -> str | None:
    if release_number is None:
        return None
    year = 2000 + release_number // 10
    revision = release_number % 10
    return f"{year} R{revision}"


def parse_package_version(version: str | None) -> tuple[int, int, int] | None:
    if not version:
        return None
    match = re.match(r"(\d+)\.(\d+)(?:\.(\d+))?", version)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2)), int(match.group(3) or 0)


def infer_release_number(fluent_info: dict[str, Any]) -> int | None:
    candidates: list[str] = []
    for key in ("fluent_path", "command"):
        value = fluent_info.get(key)
        if value:
            candidates.append(str(value))
    for key, value in fluent_info.get("awp_roots", {}).items():
        candidates.append(str(key))
        candidates.append(str(value))
    for candidate in candidates:
        release = parse_release_number(candidate)
        if release is not None:
            return release
    return None


def compatibility_report(fluent_info: dict[str, Any], pyfluent_version: str | None) -> dict[str, Any]:
    release = infer_release_number(fluent_info)
    version_tuple = parse_package_version(pyfluent_version)
    package_band = "missing"
    if version_tuple is not None:
        package_band = "current" if version_tuple >= (0, 38, 0) else "legacy"

    official_pyfluent = False
    recommended_backend = "batch"
    reason = "未能识别 Fluent 版本，优先使用 batch/journal 后端"
    recommended_action = "设置 FLUENT_PATH，并使用 run_solver 的 backend=\"batch\""

    if release is not None and release <= 221:
        reason = "Fluent 2022 R1/v221 早于 PyFluent 官方支持起点，推荐 batch/journal"
        recommended_action = "保留当前 Fluent 版本，优先完善 batch/journal；不要指望最新版 PyFluent 稳定连接 v221"
    elif release is not None and 222 <= release < 242:
        official_pyfluent = package_band == "legacy"
        if package_band == "legacy":
            recommended_backend = "pyfluent"
            reason = "该 Fluent 版本属于旧 PyFluent 支持范围，需使用 ansys-fluent-core 0.37 或更早版本"
            recommended_action = "建议单独建 Python 3.10/3.11 环境安装旧版 ansys-fluent-core，当前主环境继续保留 batch 后端"
        else:
            reason = "该 Fluent 版本需要旧版 PyFluent，当前 ansys-fluent-core 版本偏新"
            recommended_action = "用独立 legacy 环境测试 ansys-fluent-core<=0.37；当前环境使用 batch/journal"
    elif release is not None and release >= 242:
        official_pyfluent = package_band == "current"
        if package_band == "current":
            recommended_backend = "pyfluent"
            reason = "当前 Fluent 与新版 PyFluent 支持范围匹配"
            recommended_action = "可以优先使用 backend=\"pyfluent\"，失败时回退 batch/journal"
        else:
            reason = "Fluent 版本较新，但当前 PyFluent 包缺失或过旧"
            recommended_action = "安装或升级 ansys-fluent-core 后使用 backend=\"pyfluent\""

    return {
        "fluent_release_number": release,
        "fluent_release_label": release_label(release),
        "pyfluent_version": pyfluent_version,
        "pyfluent_package_band": package_band,
        "official_pyfluent_expected": official_pyfluent,
        "recommended_backend": recommended_backend,
        "reason": reason,
        "recommended_action": recommended_action,
    }
