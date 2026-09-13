"""
Reading, writing and validating annotation files.

Storage is JSONL — one fingerprint per line. Chosen over a single JSON array
because labelling is append-heavy and a line-per-record file produces a clean
one-line git diff per annotation instead of reshuffling the whole document.

Validation happens in two layers:
  1. Pydantic checks the shape        (models.py)
  2. `validate_against_taxonomy`      checks every id actually exists

Layer 2 needs the taxonomy, which is why it lives here rather than on the model.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional

from pydantic import ValidationError

from loader import Taxonomy, get_taxonomy

from .models import ExtractionStatus, Fingerprint


class AnnotationError(Exception):
    """An annotation file is malformed or references unknown taxonomy ids."""


# --------------------------------------------------------------------------
# read / write
# --------------------------------------------------------------------------

def read_annotations(path: Path) -> List[Fingerprint]:
    """Load a JSONL annotation file. Reports the line number on failure."""
    path = Path(path)
    if not path.exists():
        raise AnnotationError(f"No annotation file at {path}")

    out: List[Fingerprint] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        try:
            out.append(Fingerprint(**json.loads(line)))
        except json.JSONDecodeError as e:
            raise AnnotationError(f"{path}:{lineno} is not valid JSON: {e}") from e
        except ValidationError as e:
            raise AnnotationError(f"{path}:{lineno} failed validation:\n{e}") from e

    ids = [f.report_id for f in out]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise AnnotationError(
            f"{path}: duplicate report_ids {sorted(dupes)}. Each report is "
            f"annotated once; use a separate file per annotator instead."
        )
    return out


def write_annotations(path: Path, fingerprints: Iterable[Fingerprint]) -> int:
    """Overwrite a JSONL file. Returns the number of records written."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8") as fh:
        for fp in fingerprints:
            fh.write(fp.model_dump_json(exclude_none=True) + "\n")
            n += 1
    return n


def append_annotation(path: Path, fingerprint: Fingerprint) -> None:
    """Add one record. The normal path while hand-labelling."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(fingerprint.model_dump_json(exclude_none=True) + "\n")


# --------------------------------------------------------------------------
# fitness for downstream use
# --------------------------------------------------------------------------

def is_usable(fingerprint: Fingerprint) -> bool:
    """Whether this record may be consumed by anything downstream.

    A FAILED extraction is a record of an *absence* — the provider was down, the
    quota ran out, the response would not parse. It carries the report_id and
    nothing else, and it is stored precisely so the gap stays visible.

    The danger is that it is shaped exactly like a real fingerprint: same
    fields, all null. Pattern mining that ingests it sees a report with no
    barrier failures and no hazard, which is indistinguishable from a genuinely
    uneventful report. An outage therefore looks like a quiet week.

    So the boundary is made explicit here and imported by consumers, rather than
    each of them remembering to write `!= "failed"` — the implicit version is
    the one that gets forgotten at the seam that matters.
    """
    return fingerprint.extraction_status is not ExtractionStatus.FAILED


def partition_usable(
    fingerprints: Iterable[Fingerprint],
) -> tuple[List[Fingerprint], List[Fingerprint]]:
    """Split records into (usable, failed).

    Returns both halves rather than silently dropping one. A caller that does
    not look at the second list is making the same mistake as a caller that
    never filtered — the difference is that this one had to ignore it on
    purpose.
    """
    usable: List[Fingerprint] = []
    failed: List[Fingerprint] = []

    for fingerprint in fingerprints:
        (usable if is_usable(fingerprint) else failed).append(fingerprint)

    return usable, failed


# --------------------------------------------------------------------------
# validation against the taxonomy
# --------------------------------------------------------------------------

_SINGLE_FIELDS = {
    "activity": "activities",
    "hazard": "hazards",
    "exposure": "exposures",
    "potential_consequence": "consequences",
    "severity_band": "severity_bands",
}

_LIST_FIELDS = {
    "life_saving_rules": "life_saving_rules",
    "context_flags": "context_flags",
}


def validate_against_taxonomy(
    fp: Fingerprint,
    taxonomy: Optional[Taxonomy] = None,
    narrative: Optional[str] = None,
) -> List[str]:
    """Return a list of problems. Empty list means the annotation is sound.

    Returns rather than raises, because callers usually want every problem in a
    file at once, not the first one.

    If `narrative` is supplied, evidence spans are checked to be genuine
    substrings of it. That is the mechanical form of the module's core rule:
    if we cannot point at the words, we do not claim the field.
    """
    tax = taxonomy or get_taxonomy()
    problems: List[str] = []
    where = f"{fp.report_id}"

    for field, vocab in _SINGLE_FIELDS.items():
        value = getattr(fp, field)
        if value is not None and not tax.validate_id(value, vocab):
            problems.append(f"{where}: {field}={value!r} is not in {vocab}")

    for field, vocab in _LIST_FIELDS.items():
        for value in getattr(fp, field):
            if not tax.validate_id(value, vocab):
                problems.append(f"{where}: {field} contains unknown id {value!r}")

    for i, bf in enumerate(fp.barrier_failures):
        if not tax.validate_id(bf.barrier, "barriers"):
            problems.append(
                f"{where}: barrier_failures[{i}].barrier={bf.barrier!r} unknown"
            )
        if not tax.validate_id(bf.failure_mode, "failure_modes"):
            problems.append(
                f"{where}: barrier_failures[{i}].failure_mode="
                f"{bf.failure_mode!r} unknown"
            )
        if narrative is not None and bf.evidence_span:
            if bf.evidence_span.lower() not in narrative.lower():
                problems.append(
                    f"{where}: barrier_failures[{i}].evidence_span "
                    f"{bf.evidence_span!r} does not appear in the narrative. "
                    f"Evidence must be quoted verbatim, not paraphrased."
                )

    for level in (1, 2, 3, 4):
        value = getattr(fp, f"location_l{level}")
        if value is None:
            continue
        try:
            loc = tax.location(value)
        except Exception:
            problems.append(f"{where}: location_l{level}={value!r} unknown")
            continue
        if loc.level != level:
            problems.append(
                f"{where}: {value!r} is a level-{loc.level} location but was "
                f"put in location_l{level}"
            )

    # Consistency between the status flag and the content.
    if fp.extraction_status.value == "failed" and fp.barrier_failures:
        problems.append(
            f"{where}: status is 'failed' but barrier failures are present"
        )
    if fp.extraction_status.value == "complete" and not fp.barrier_failures:
        problems.append(
            f"{where}: status is 'complete' but no barrier failure was found — "
            f"a SIF precursor is defined by a failed control"
        )

    return problems


def validate_file(
    path: Path,
    narratives: Optional[Dict[str, str]] = None,
    taxonomy: Optional[Taxonomy] = None,
) -> List[str]:
    """Validate every annotation in a file.

    Args:
        narratives: report_id -> narrative text. Supply it to enable evidence
            span checking; omit it to check ids only.
    """
    tax = taxonomy or get_taxonomy()
    problems: List[str] = []
    for fp in read_annotations(path):
        narrative = narratives.get(fp.report_id) if narratives else None
        problems.extend(validate_against_taxonomy(fp, tax, narrative))
    return problems
