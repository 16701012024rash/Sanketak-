from intelligence.intelligence_engine import analyze_report


def intelligence_analysis(sif_fingerprint, recent_reports):
    """
    Main interface for the backend.

    Input:
        sif_fingerprint = structured SIF fingerprint
        recent_reports = recent SIF fingerprints

    Output:
        Intelligence Engine results
    """

    result = analyze_report(
        sif_fingerprint,
        recent_reports
    )

    return result