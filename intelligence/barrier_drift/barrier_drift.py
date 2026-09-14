from collections import Counter


def detect_barrier_drift(
    historical_reports,
    activity=None,
    hazard=None,
    threshold=2
):

    failures = []

    for report in historical_reports:

        # Filter by activity
        if activity and report.get("activity") != activity:
            continue

        # Filter by hazard
        if hazard and report.get("hazard") != hazard:
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