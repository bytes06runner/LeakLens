from click.testing import CliRunner

import leaklens
from leaklens.cli import EXIT_NOT_IMPLEMENTED, main


def test_six_leakage_types():
    assert len(leaklens.LEAKAGE_TYPES) == 6
    assert {"group", "temporal"} <= set(leaklens.LEAKAGE_TYPES)


def test_info_runs():
    result = CliRunner().invoke(main, ["info"])
    assert result.exit_code == 0
    assert "Phase 0" in result.output


def test_scan_refuses_until_implemented(tmp_path):
    f = tmp_path / "x.py"
    f.write_text("print(1)\n")
    result = CliRunner().invoke(main, ["scan", str(f)])
    # Must not pretend the file is clean.
    assert result.exit_code == EXIT_NOT_IMPLEMENTED
    assert "not implemented" in result.output


def test_subpackages_import():
    import leaklens.dynamic  # noqa: F401
    import leaklens.impact  # noqa: F401
    import leaklens.ingest  # noqa: F401
    import leaklens.report  # noqa: F401
    import leaklens.static  # noqa: F401
