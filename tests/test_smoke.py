from click.testing import CliRunner

import leaklens
from leaklens.cli import EXIT_FINDINGS, EXIT_OK, EXIT_UNANALYSABLE, EXIT_USAGE, main

LEAKY = """import pandas as pd
from sklearn.model_selection import train_test_split
df = pd.read_csv("visits.csv")
X = df.drop(columns=["patient_id", "outcome"])
X_train, X_test, y_train, y_test = train_test_split(X, df["outcome"], random_state=0)
"""


def test_six_leakage_types():
    assert len(leaklens.LEAKAGE_TYPES) == 6
    assert {"group", "temporal"} <= set(leaklens.LEAKAGE_TYPES)


def test_info_runs():
    result = CliRunner().invoke(main, ["info"])
    assert result.exit_code == 0
    assert "DEV split only" in result.output


def test_scan_clean_file_exits_zero(tmp_path):
    f = tmp_path / "x.py"
    f.write_text("print(1)\n")
    result = CliRunner().invoke(main, ["scan", str(f)])
    assert result.exit_code == EXIT_OK
    assert "0 finding(s) in 1 analysed file(s)" in result.output


def test_scan_reports_group_leak_and_exits_one(tmp_path):
    f = tmp_path / "leaky.py"
    f.write_text(LEAKY)
    result = CliRunner().invoke(main, ["scan", str(f)])
    assert result.exit_code == EXIT_FINDINGS
    assert "group (LL-GRP-001)" in result.output and "line 5" in result.output
    assert CliRunner().invoke(main, ["scan", "--fail-on", "never", str(f)]).exit_code == EXIT_OK


def test_scan_json_matches_schema_and_sarif_is_well_formed(tmp_path):
    import json
    from pathlib import Path

    import jsonschema

    f = tmp_path / "leaky.py"
    f.write_text(LEAKY)
    schema = json.loads((Path(leaklens.__file__).parent / "report" / "finding.schema.json").read_text())
    report = json.loads(CliRunner().invoke(main, ["scan", "--format", "json", "--fail-on", "never", str(f)]).output)
    assert report["schema"] == "leaklens/report/v1" and report["scan"]["mode"] == "static"
    assert [x["status"] for x in report["files"]] == ["ok"]
    for finding in report["findings"]:
        jsonschema.validate(finding, schema)
    sarif = json.loads(CliRunner().invoke(main, ["scan", "--format", "sarif", "--fail-on", "never", str(f)]).output)
    run = sarif["runs"][0]
    assert sarif["version"] == "2.1.0" and run["tool"]["driver"]["name"] == "LeakLens"
    assert run["results"][0]["ruleId"] == "LL-GRP-001" and run["results"][0]["level"] == "error"
    assert run["results"][0]["locations"][0]["physicalLocation"]["region"]["startLine"] == 5


def test_scan_never_reports_an_unparseable_file_as_clean(tmp_path):
    f = tmp_path / "py2.py"
    f.write_text("print 'x'\n")
    result = CliRunner().invoke(main, ["scan", str(f)])
    assert result.exit_code == EXIT_UNANALYSABLE
    assert "not analysed" in result.output


def test_scan_usage_and_untrusted_execution_are_refused(tmp_path):
    f = tmp_path / "x.py"
    f.write_text("print(1)\n")
    assert CliRunner().invoke(main, ["scan"]).exit_code == EXIT_USAGE
    result = CliRunner().invoke(main, ["scan", "--dynamic", str(f)])  # executing code needs --trust-code
    assert result.exit_code == EXIT_UNANALYSABLE and "--trust-code" in result.output


def test_static_scan_does_not_import_or_run_the_code(tmp_path):
    marker = tmp_path / "ran"
    f = tmp_path / "side_effect.py"
    f.write_text(f"open({str(marker)!r}, 'w').write('x')\n")
    assert CliRunner().invoke(main, ["scan", str(f)]).exit_code == EXIT_OK
    assert not marker.exists()


def test_subpackages_import():
    import leaklens.dynamic  # noqa: F401
    import leaklens.impact  # noqa: F401
    import leaklens.ingest  # noqa: F401
    import leaklens.report  # noqa: F401
    import leaklens.static  # noqa: F401
