from intelligence.precedent.precedent_engine import find_precedents
from intelligence.barrier_drift.barrier_drift import detect_barrier_drift
from intelligence.barrier_drift.emerging_risk import detect_emerging_risks
from intelligence.data.postgres_repository import load_historical_reports


def analyze_report(new_report, recent_reports):

    historical_reports = load_historical_reports()

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