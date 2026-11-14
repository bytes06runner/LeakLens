"""benchmark/real/score_labels.py: kappa, sheet reading, displayed-cell mapping and the strict entity rule."""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("score_labels", ROOT / "benchmark" / "real" / "score_labels.py")
sl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sl)

HEAD = "labeller,notebook_id,leak_type,cell,line_start,line_end,confidence,note,minutes,entity_column\n"


def test_kappa_known_values():
    assert sl.cohen_kappa([True, False, True, False], [True, False, True, False]) == 1.0
    assert sl.cohen_kappa([True, True, False, False], [True, False, True, False]) == 0.0
    assert sl.cohen_kappa([True, True], [True, True]) is None  # no variation: undefined


def test_agreement_and_disagreement_list(tmp_path):
    d = tmp_path / "returned"
    d.mkdir()
    (d / "labelling_sheet_A.csv").write_text(HEAD + "A,R001,group,4,2,2,sure,,5,\nA,R002,none,,,,sure,,3,\n")
    (d / "labelling_sheet_B.csv").write_text(HEAD + "B,R001,group,4,2,2,sure,,5,\nB,R002,temporal,3,1,1,likely,,3,\n")
    sl.agree(d, tmp_path / "out")
    dis = (tmp_path / "out" / "disagreements.csv").read_text().splitlines()
    assert dis[1].startswith("R002,temporal,no,yes")
    assert json.loads((tmp_path / "out" / "agreement.json").read_text())["group"]["counts"] == [1, 0, 0, 1]


def test_score_maps_displayed_cells_and_applies_the_entity_rule(tmp_path):
    out = tmp_path / "run"
    out.mkdir()

    def finding(cell, line, typ, col):
        return {
            "type": typ,
            "confidence": "medium",
            "message": f"Rows are split without regard to `{col}`;",
            "location": {"cell": cell, "line_start": line, "line_end": line},
        }

    recs = [
        {"notebook_id": "R001", "status": "ok", "findings": [finding(3, 2, "group", "visit")]},
        {"notebook_id": "R002", "status": "ok", "findings": [finding(5, 1, "group", "patient_id")]},
    ]
    (out / "findings.jsonl").write_text("".join(json.dumps(r) + "\n" for r in recs))
    labels = tmp_path / "labels.csv"
    labels.write_text(HEAD + "settled,R001,group,4,2,2,sure,,,patient_id\nsettled,R002,group,6,1,1,sure,,,patient_id\n")
    sl.score(labels, out, boot=50)
    rep = json.loads((out / "summary.json").read_text())
    strict = {r["type"]: r for r in rep["strict (headline)|medium"]}
    lenient = {r["type"]: r for r in rep["lenient|medium"]}
    assert (lenient["group"]["tp"], lenient["group"]["fn"]) == (2, 0)  # displayed cell 4 = finding cell 3
    assert (strict["group"]["tp"], strict["group"]["fn"]) == (1, 1)  # `visit` is the wrong entity
