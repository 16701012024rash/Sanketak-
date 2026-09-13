from collections import Counter


def detect_emerging_risks(historical_reports, recent_reports, threshold=2):
    recent_failures = []

    for report in recent_reports:
        for failure in report.get("barrier_failures", []):
            key = (
                failure["barrier"],
                failure["failure_mode"]
            )
            recent_failures.append(key)

    counts = Counter(recent_failures)

    emerging_risks = []

    for (barrier, failure_mode), count in counts.items():
        if count >= threshold:
            emerging_risks.append({
                "barrier": barrier,
                "failure_mode": failure_mode,
                "recent_occurrences": count,
                "risk_status": "EMERGING"
            })

    emerging_risks.sort(
        key=lambda x: x["recent_occurrences"],
        reverse=True
    )

    return emerging_risks