from fluent_research_mcp.fluent_compat import compatibility_report, parse_release_number, release_label


def test_parse_release_number_from_common_windows_paths() -> None:
    assert parse_release_number(r"E:\Program Files\ANSYS Inc221\v221\fluent\ntbin\win64\fluent.exe") == 221
    assert parse_release_number("AWP_ROOT242") == 242


def test_release_label() -> None:
    assert release_label(221) == "2022 R1"
    assert release_label(242) == "2024 R2"


def test_v221_recommends_batch_backend() -> None:
    report = compatibility_report(
        {
            "command": r"E:\Program Files\ANSYS Inc221\v221\fluent\ntbin\win64\fluent.exe",
            "awp_roots": {},
        },
        "0.38.1",
    )

    assert report["fluent_release_number"] == 221
    assert report["recommended_backend"] == "batch"
    assert report["official_pyfluent_expected"] is False


def test_current_pyfluent_with_v242_recommends_pyfluent() -> None:
    report = compatibility_report(
        {
            "command": r"C:\Program Files\ANSYS Inc\v242\fluent\ntbin\win64\fluent.exe",
            "awp_roots": {},
        },
        "0.38.1",
    )

    assert report["recommended_backend"] == "pyfluent"
    assert report["official_pyfluent_expected"] is True
