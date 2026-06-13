from __future__ import annotations

from fluent_research_mcp import fluent_session
from fluent_research_mcp.fluent_session import FluentLaunchOptions, FluentSession


class _FakeSolver:
    def exit(self) -> None:
        return None


class _FakePyFluent:
    class FluentMode:
        SOLVER = "solver-mode"

    class Precision:
        DOUBLE = "double-precision"

    class Dimension:
        TWO = "two-dimensional"
        THREE = "three-dimensional"

    def __init__(self) -> None:
        self.launch_kwargs = None

    def launch_fluent(self, **kwargs):
        self.launch_kwargs = kwargs
        return _FakeSolver()


def test_fluent_session_passes_explicit_fluent_path(monkeypatch) -> None:
    fake = _FakePyFluent()
    monkeypatch.setattr(fluent_session, "import_pyfluent", lambda: fake)

    FluentSession(FluentLaunchOptions(fluent_path=r"E:\ANSYS\v221\fluent.exe")).launch()

    assert fake.launch_kwargs["fluent_path"] == r"E:\ANSYS\v221\fluent.exe"
    assert fake.launch_kwargs["mode"] == "solver-mode"
    assert fake.launch_kwargs["precision"] == "double-precision"


def test_fluent_session_uses_fluent_path_environment(monkeypatch) -> None:
    fake = _FakePyFluent()
    monkeypatch.setattr(fluent_session, "import_pyfluent", lambda: fake)
    monkeypatch.setenv("FLUENT_PATH", r"E:\ANSYS\v221\fluent\ntbin\win64\fluent.exe")
    monkeypatch.setattr(fluent_session.shutil, "which", lambda command: None)

    FluentSession().launch()

    assert fake.launch_kwargs["fluent_path"] == r"E:\ANSYS\v221\fluent\ntbin\win64\fluent.exe"


def test_fluent_session_maps_2d_dimension(monkeypatch) -> None:
    fake = _FakePyFluent()
    monkeypatch.setattr(fluent_session, "import_pyfluent", lambda: fake)

    FluentSession(FluentLaunchOptions(dimension="2ddp")).launch()

    assert fake.launch_kwargs["dimension"] == "two-dimensional"
