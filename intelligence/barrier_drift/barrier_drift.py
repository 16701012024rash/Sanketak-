from collections import Counter


# Distinguishes "the caller did not ask to filter on this" from "the caller
# asked to filter, and the value is unknown". Both used to arrive as None and
# were treated identically, which is the whole bug.
_UNSET = object()


def detect_barrier_drift(
    historical_reports,
    activity=_UNSET,
    hazard=_UNSET,
    threshold=2
):
    """Repeated barrier failures within a comparable cohort.

    Scoping is the point. Drift means "this control keeps failing on work like
    *this*", so the cohort has to be like-for-like — the same activity, the
    same hazard. `if activity and ...` collapsed three different cases into
    one: a caller who wanted no filter, a caller who passed an empty string,
    and a caller whose report had a null activity because the narrative never
    said. All three scanned the whole history, so a welding report and a
    driving report merged into a single "REPEATED" trend.

    Now:
      - omitted        no filtering on that dimension; the caller chose that
      - a value        filter to it, as before
      - None           unknown for this report, so it cannot scope anything

    If every dimension the caller supplied is unknown, there is no cohort to
    speak of and we return no drift. A trend built from unrelated work is worse
    than no trend, because it is confident and wrong.
    """

    # Which dimensions can actually scope the cohort?
    filters = {}
    supplied = 0

    for field, value in (("activity", activity), ("hazard", hazard)):
        if value is _UNSET:
            continue
        supplied += 1
        if value is not None:
            filters[field] = value

    if supplied and not filters:
        return []

    failures = []

    for report in historical_reports:

        # Filter on whichever dimensions are known
        if any(report.get(field) != value for field, value in filters.items()):
            continue

        for failure in report.get("barrier_failures", []):

            key = (
                failure["barrier"],
                failure["failure_mode"]
            )

            failures.append(key)

    counts = Counter(failures)

    drift = []

    for (barrier, failure_mode), count in counts.items():

        if count >= threshold:

            drift.append({
                "barrier": barrier,
                "failure_mode": failure_mode,
                "occurrences": count,
                "risk_status": "REPEATED"
            })

    drift.sort(
        key=lambda x: x["occurrences"],
        reverse=True
    )

    return drift