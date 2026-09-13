from intelligence.precedent.vector_search import vector_search


def _matches(new_report, old_report, field):
    """True only when both reports state the same value for `field`.

    A null means the extractor could not find the value in the narrative, not
    that the value is absent from the world. Two nulls are therefore two
    unknowns, and two unknowns are not a match — without this guard a pair of
    reports that share nothing but our own ignorance scored 55/100 against a
    threshold of 50, and were shown to a safety officer as precedents.
    """
    new_value = new_report.get(field)
    old_value = old_report.get(field)

    if new_value is None or old_value is None:
        return False

    return new_value == old_value


def calculate_structured_score(new_report, old_report):
    score = 0

    # Activity match — 30 points
    if _matches(new_report, old_report, "activity"):
        score += 30

    # Hazard match — 25 points
    if _matches(new_report, old_report, "hazard"):
        score += 25

    # Life-Saving Rule match — 15 points
    new_rules = set(new_report.get("life_saving_rules", []))
    old_rules = set(old_report.get("life_saving_rules", []))

    if new_rules and old_rules:
        common_rules = new_rules & old_rules
        score += int(15 * len(common_rules) / len(new_rules))

    # Barrier + Failure Mode match — 30 points
    new_failures = {
        (x["barrier"], x["failure_mode"])
        for x in new_report.get("barrier_failures", [])
    }

    old_failures = {
        (x["barrier"], x["failure_mode"])
        for x in old_report.get("barrier_failures", [])
    }

    if new_failures and old_failures:
        common_failures = new_failures & old_failures
        score += int(30 * len(common_failures) / len(new_failures))

    return score


def find_precedents(new_report, historical_reports=None, threshold=50):

    # Get candidates from PostgreSQL vector search
    vector_results = vector_search(new_report, top_k=10)

    # Create lookup for historical reports
    historical_lookup = {
        report["report_id"]: report
        for report in (historical_reports or [])
    }

    matches = []

    for result in vector_results:

        report_id = result["report_id"]

        # We need the full historical fingerprint
        old_report = historical_lookup.get(report_id)

        if old_report is None:
            continue

        structured_score = calculate_structured_score(
            new_report,
            old_report
        )

        vector_score = int(result["similarity"] * 100)

        # 70% structured + 30% vector
        final_score = int(
            (structured_score * 0.7) +
            (vector_score * 0.3)
        )

        if final_score >= threshold:
            matches.append({
                "report_id": report_id,
                "match_score": final_score,
                "structured_score": structured_score,
                "vector_similarity": round(
                    result["similarity"],
                    3
                )
            })

    matches.sort(
        key=lambda x: x["match_score"],
        reverse=True
    )

    return matches