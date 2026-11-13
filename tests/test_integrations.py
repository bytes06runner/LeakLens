"""The pre-commit hook and the GitHub Action are thin wrappers around `leaklens scan`; check they stay consistent."""

from pathlib import Path

import yaml
from click.testing import CliRunner

from leaklens.cli import EXIT_FINDINGS, EXIT_OK, main

ROOT = Path(__file__).resolve().parents[1]


def test_pre_commit_hook_definition():
    (hook,) = yaml.safe_load((ROOT / ".pre-commit-hooks.yaml").read_text())
    assert hook["id"] == "leaklens" and hook["language"] == "python"
    assert hook["entry"] == "leaklens scan" and set(hook["types_or"]) == {"python", "jupyter"}


def test_hook_entry_accepts_several_files_and_fails_only_on_the_leaky_one(tmp_path):
    clean, leaky = tmp_path / "clean.py", tmp_path / "leaky.py"
    clean.write_text("x = 1\n")
    leaky.write_text("import pandas as pd\nfrom sklearn.model_selection import train_test_split\n"
                     "df = pd.read_csv('v.csv')\nX = df.drop(columns=['patient_id', 'y'])\n"
                     "a, b, c, d = train_test_split(X, df['y'])\n")
    assert CliRunner().invoke(main, ["scan", str(clean)]).exit_code == EXIT_OK
    res = CliRunner().invoke(main, ["scan", str(clean), str(leaky)])
    assert res.exit_code == EXIT_FINDINGS and "leaky.py" in res.output


def test_action_definition_matches_the_cli():
    action = yaml.safe_load((ROOT / "action.yml").read_text())
    assert action["runs"]["using"] == "composite"
    assert set(action["inputs"]) == {"paths", "fail-on", "min-confidence", "upload-sarif"}
    script = next(s["run"] for s in action["runs"]["steps"] if s.get("id") == "scan")
    for flag in ("--format sarif", "--output", "--fail-on", "--min-confidence"):
        assert flag in script
    assert any("upload-sarif" in str(s.get("uses", "")) for s in action["runs"]["steps"])
