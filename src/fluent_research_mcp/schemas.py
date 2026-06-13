from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


ErrorCode = Literal[
    "environment_error",
    "license_error",
    "input_error",
    "fluent_error",
    "udf_compile_error",
    "udf_load_error",
    "solver_error",
    "postprocess_error",
]


class ToolError(BaseModel):
    code: ErrorCode
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    ok: bool
    stage: str
    message: str
    artifacts: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[ToolError] = Field(default_factory=list)
    data: dict[str, Any] = Field(default_factory=dict)


def ok_result(
    stage: str,
    message: str,
    *,
    artifacts: list[str] | None = None,
    warnings: list[str] | None = None,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return ToolResult(
        ok=True,
        stage=stage,
        message=message,
        artifacts=artifacts or [],
        warnings=warnings or [],
        data=data or {},
    ).model_dump()


def error_result(
    stage: str,
    message: str,
    *,
    code: ErrorCode,
    details: dict[str, Any] | None = None,
    artifacts: list[str] | None = None,
    warnings: list[str] | None = None,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return ToolResult(
        ok=False,
        stage=stage,
        message=message,
        artifacts=artifacts or [],
        warnings=warnings or [],
        errors=[ToolError(code=code, message=message, details=details or {})],
        data=data or {},
    ).model_dump()

