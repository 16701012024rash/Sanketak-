from intelligence.intelligence_engine import analyze_report


def _as_dict(fingerprint):
    """Accept either a plain dict or the NLP module's Fingerprint model.

    Module 3 emits pydantic `Fingerprint` objects; everything below this line
    reads fields with `.get()`, which a pydantic model does not have. Rather
    than import Fingerprint here — which would tie the intelligence engine to
    the NLP package's import path for one method call — we duck-type on
    `model_dump`. Anything dict-like passes through untouched.
    """
    if hasattr(fingerprint, "model_dump"):
        return fingerprint.model_dump()

    return fingerprint


def intelligence_analysis(sif_fingerprint, recent_reports):
    """
    Main interface for the backend.

    Input:
        sif_fingerprint = structured SIF fingerprint, as a dict or a
                          Fingerprint model from the NLP module
        recent_reports = recent SIF fingerprints, same

    Output:
        Intelligence Engine results
    """

    sif_fingerprint = _as_dict(sif_fingerprint)
    recent_reports = [_as_dict(report) for report in recent_reports or []]

    result = analyze_report(
        sif_fingerprint,
        recent_reports=recent_reports
    )

    return result