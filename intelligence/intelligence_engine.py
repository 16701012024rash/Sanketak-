from intelligence.precedent.precedent_engine import find_precedents
from intelligence.barrier_drift.barrier_drift import detect_barrier_drift
from intelligence.barrier_drift.emerging_risk import detect_emerging_risks
from intelligence.data.report_repository import load_historical_reports


def analyze_report(new_report, historical_reports=None, recent_reports=None):
    """Run the three analyses over one fingerprint.

    `historical_reports` is injectable rather than always loaded internally.
    Loading it inside the function made the engine untestable without a live
    database, and the signature had already drifted from the callers — the test
    passed three positional arguments to a function taking two.

    Left as None it loads from `report_repository`, which reads the committed
    JSON. That keeps the engine runnable on a laptop with no Postgres. Swap the
    import for `postgres_repository` when a database is actually present; both
    modules expose the same `load_historical_reports()`.
    """

    if historical_reports is None:
        historical_reports = load_historical_reports()

    if recent_reports is None:
        recent_reports = []

    precedents = find_precedents(
        new_report,
        historical_reports
    )

    barrier_drift = detect_barrier_drift(
    historical_reports,
    activity=new_report.get("activity"),
    hazard=new_report.get("hazard")
)

    emerging_risks = detect_emerging_risks(
        historical_reports,
        recent_reports
    )

    return {
        "engine": "intelligence",
        "precedents": precedents,
        "barrier_drift": barrier_drift,
        "emerging_risks": emerging_risks
    }