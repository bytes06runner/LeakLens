"""The finding schema, SPEC.md and the code must agree."""

import json
import re
from pathlib import Path

import jsonschema
import pytest

from leaklens import LEAKAGE_TYPES, cli

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "src" / "leaklens" / "report" / "finding.schema.json").read_text())
SPEC = (ROOT / "docs" / "SPEC.md").read_text()

# Hand-written example of the finding LeakLens should produce for tests/fixtures/taxonomy/group_pos.py.
EXAMPLE = {
    "id": "0123456789abcdef",
    "rule_id": "LL-GRP-001",
    "type": "group",
    "subtype": None,
    "severity": "high",
    "confidence": "medium",
    "location": {"file": "group_pos.py", "line_start": 10, "line_end": 10, "cell": None,
                 "flat_line_start": 10, "flat_line_end": 10},
    "message": "Random split on rows that share `patient_id` values; the same patient can be in train and test.",
    "evidence": [
        {"kind": "split_call", "detail": "train_test_split without groups"},
        {"kind": "entity_column", "detail": "patient_id (name evidence)"},
    ],
    "related": [],
    "suggested_fix": {"description": "Use GroupShuffleSplit with groups=patient_id.",
                      "canonical_fix": "replace_splitter:GroupShuffleSplit"},
    "dynamic": {"status": "not_run"},
    "impact": {"status": "not_run"},
    "suppressed": None,
}


def test_schema_is_valid():
    jsonschema.Draft202012Validator.check_schema(SCHEMA)


def test_example_finding_validates():
    jsonschema.validate(EXAMPLE, SCHEMA)


def test_example_points_at_leak_marker():
    lines = (ROOT / "tests" / "fixtures" / "taxonomy" / "group_pos.py").read_text().splitlines()
    assert "# LEAK: group" in lines[EXAMPLE["location"]["line_start"] - 1]


@pytest.mark.parametrize("bad", [{"type": "leaky"}, {"severity": "critical"}, {"rule_id": "LL-XYZ-001"}])
def test_schema_rejects_bad_values(bad):
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({**EXAMPLE, **bad}, SCHEMA)


def test_schema_types_match_package():
    assert tuple(SCHEMA["properties"]["type"]["enum"]) == LEAKAGE_TYPES


def test_rule_prefixes_match_spec():
    in_schema = set(re.search(r"\((.*?)\)", SCHEMA["properties"]["rule_id"]["pattern"]).group(1).split("|"))
    in_spec = set(re.findall(r"\| `LL-([A-Z]{3})` \|", SPEC))
    assert in_schema == in_spec


def test_exit_codes_match_spec():
    table = dict(re.findall(r"\| `(\d)` \| ([^|]+)\|", SPEC))
    assert set(table) == {"0", "1", "2", "3"}
    assert (cli.EXIT_OK, cli.EXIT_FINDINGS, cli.EXIT_USAGE, cli.EXIT_UNANALYSABLE) == (0, 1, 2, 3)
