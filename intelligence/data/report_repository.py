"""File-backed historical corpus for the intelligence module.

Two sources, same output shape:

  * JSONL — real SIF fingerprints produced by the NLP module (Module 3).
    This is the default. `nlp/data/predictions.jsonl` if extraction has been
    run, otherwise the 30-report gold set at `nlp/data/gold/gold.jsonl`.
  * JSON  — `historical_reports.json`, three synthetic rows. Kept as a
    fallback so the module still loads with no NLP corpus present, and so
    the existing tests that assume it keep working.

Pick explicitly with `load_historical_reports(source=...)`, or set
SANKETAK_HISTORICAL_REPORTS to a path. Suffix decides the reader.

The JSONL side is where translation happens. A `Fingerprint` carries more
than the intelligence engine reads — evidence spans, confidence, provenance,
locations — and its `barrier_failures` are objects, not dicts. Rather than
bend either schema, this module flattens at the boundary into the dict shape
the engine already reads from Postgres (see
`app.services.intelligence_data.load_historical_reports_from_db`).
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_NLP_SRC = _REPO_ROOT / "nlp" / "src"

JSON_FALLBACK = Path(__file__).parent / "historical_reports.json"
PREDICTIONS = _REPO_ROOT / "nlp" / "data" / "predictions.jsonl"
GOLD = _REPO_ROOT / "nlp" / "data" / "gold" / "gold.jsonl"

ENV_VAR = "SANKETAK_HISTORICAL_REPORTS"


def default_source() -> Path:
    """Best available corpus: env override, then predictions, gold, JSON."""
    override = os.environ.get(ENV_VAR)
    if override:
        return Path(override)
    for candidate in (PREDICTIONS, GOLD):
        if candidate.exists():
            return candidate
    return JSON_FALLBACK


def load_historical_reports(source: Optional[os.PathLike] = None) -> List[dict]:
    """Load the historical corpus as a list of engine-shaped dicts.

    Records whose extraction failed are dropped here and the count is logged;
    they are not reports about which nothing went wrong, they are reports we
    could not read.
    """
    reports, _ = load_historical_reports_with_stats(source)
    return reports


def load_historical_reports_with_stats(
    source: Optional[os.PathLike] = None,
) -> Tuple[List[dict], dict]:
    """As `load_historical_reports`, plus what was read and what was skipped."""
    path = Path(source) if source is not None else default_source()

    if path.suffix == ".jsonl":
        reports, stats = _load_jsonl(path)
    else:
        reports, stats = _load_json(path)

    stats["source"] = str(path)
    stats["loaded"] = len(reports)
    if stats.get("unusable"):
        logger.warning(
            "%s: skipped %d record(s) with extraction_status=failed: %s",
            path, stats["unusable"], ", ".join(stats["unusable_report_ids"]),
        )
    return reports, stats


# --------------------------------------------------------------------------
# readers
# --------------------------------------------------------------------------

def _load_json(path: Path) -> Tuple[List[dict], dict]:
    with open(path, "r", encoding="utf-8") as fh:
        reports = json.load(fh)
    return reports, {"format": "json", "unusable": 0, "unusable_report_ids": []}


def _load_jsonl(path: Path) -> Tuple[List[dict], dict]:
    read_annotations, partition_usable = _annotation_api()

    fingerprints = read_annotations(path)
    usable, unusable = partition_usable(fingerprints)

    return (
        [_to_engine_report(fp) for fp in usable],
        {
            "format": "jsonl",
            "unusable": len(unusable),
            "unusable_report_ids": [fp.report_id for fp in unusable],
        },
    )


def _annotation_api():
    """Import Module 3's annotation store, which lives outside this package."""
    if str(_NLP_SRC) not in sys.path:
        sys.path.insert(0, str(_NLP_SRC))
    from annotation import partition_usable, read_annotations  # noqa: E402
    return read_annotations, partition_usable


# --------------------------------------------------------------------------
# boundary translation: Fingerprint -> engine dict
# --------------------------------------------------------------------------

def _to_engine_report(fp) -> dict:
    """Flatten one `Fingerprint` into the dict the engine reads.

    `barrier_failures` becomes [{"barrier": ..., "failure_mode": ...}] —
    the two keys the engine indexes by name, with the annotation-only extras
    (primary, evidence_span, confidence) left behind. Keeping them would not
    break the engine, which reads by key, but they would travel into API
    responses as unexplained payload.
    """
    return {
        "report_id": fp.report_id,
        "activity": fp.activity,
        "hazard": fp.hazard,
        "exposure": fp.exposure,
        "potential_consequence": fp.potential_consequence,
        "life_saving_rules": list(fp.life_saving_rules),
        "barrier_failures": [
            {"barrier": bf.barrier, "failure_mode": bf.failure_mode}
            for bf in fp.barrier_failures
        ],
    }
