"""The finding record and its JSON form (docs/SPEC.md section 3; schema: finding.schema.json)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

SEVERITY_ORDER = {"info": 0, "low": 1, "medium": 2, "high": 3}
CONFIDENCE_ORDER = {"low": 0, "medium": 1, "high": 2}

# Severity priors by type (SPEC section 4, following the measured ranking in Roth, arXiv:2604.04199).
SEVERITY_PRIOR = {
    "preprocessing": "low",
    "overlap": "high",
    "multi_test": "medium",
    "group": "high",
    "temporal": "high",
    "target_derived": "low",
}


@dataclass
class Finding:
    rule_id: str
    type: str
    subtype: str | None
    confidence: str
    file: str
    flat_line_start: int
    flat_line_end: int
    message: str
    evidence: list[dict] = field(default_factory=list)
    fix_description: str = ""
    canonical_fix: str | None = None
    severity: str | None = None
    cell: int | None = None
    line_start: int = 0
    line_end: int = 0
    id: str = ""
    related: list[str] = field(default_factory=list)
    dynamic: dict = field(default_factory=lambda: {"status": "not_run"})
    impact: dict = field(default_factory=lambda: {"status": "not_run"})
    suppressed: dict | None = None
    context: dict = field(default_factory=dict)  # not serialised: column names etc. for the dynamic pass

    def __post_init__(self) -> None:
        if self.severity is None:
            self.severity = SEVERITY_PRIOR[self.type]
            if self.type == "preprocessing" and self.subtype == "supervised":
                self.severity = "high"

    def set_id(self, normalised_source: str) -> None:
        h = hashlib.sha256(f"{self.rule_id}\0{self.file}\0{normalised_source}".encode()).hexdigest()
        self.id = h[:16]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "type": self.type,
            "subtype": self.subtype,
            "severity": self.severity,
            "confidence": self.confidence,
            "location": {
                "file": self.file,
                "line_start": self.line_start,
                "line_end": self.line_end,
                "cell": self.cell,
                "flat_line_start": self.flat_line_start,
                "flat_line_end": self.flat_line_end,
            },
            "message": self.message,
            "evidence": self.evidence,
            "related": self.related,
            "suggested_fix": {"description": self.fix_description, "canonical_fix": self.canonical_fix},
            "dynamic": self.dynamic,
            "impact": self.impact,
            "suppressed": self.suppressed,
        }


def passes(f: Finding, fail_on: str = "high", min_confidence: str = "medium") -> bool:
    """True when the finding counts towards a non-zero exit code (SPEC section 7)."""
    if f.suppressed is not None or fail_on == "never":
        return False
    return (
        SEVERITY_ORDER[f.severity] >= SEVERITY_ORDER[fail_on]
        and CONFIDENCE_ORDER[f.confidence] >= CONFIDENCE_ORDER[min_confidence]
    )
