from app.core.db import SessionLocal
from app.models.report import Report
import uuid

db = SessionLocal()

demo_reports = [
    # Scenario 1: Precedent-match demo (gas/pressure incident, high risk)
    {
        "raw_text": "Worker reported strong gas smell near the main pipeline valve, pressure gauge reading abnormally high, evacuation was not immediately triggered.",
        "language": "english",
        "risk_score": 0.91,
        "sif_probability": 0.91,
        "risk_level": "HIGH",
        "barrier_category": "equipment failure",
        "equipment_tag": "pipeline",
        "site_tag": "site-1",
    },
    # Scenario 2: Repeating-pattern demo (3 reports, same equipment tag)
    {
        "raw_text": "Scaffold missing guardrails on level 3, reported during morning inspection.",
        "language": "english",
        "risk_score": 0.62,
        "sif_probability": 0.62,
        "risk_level": "MEDIUM",
        "barrier_category": "PPE non-compliance",
        "equipment_tag": "scaffold",
        "site_tag": "site-2",
    },
    {
        "raw_text": "Another scaffold near block B found without proper guardrails, same issue as last week.",
        "language": "english",
        "risk_score": 0.58,
        "sif_probability": 0.58,
        "risk_level": "MEDIUM",
        "barrier_category": "PPE non-compliance",
        "equipment_tag": "scaffold",
        "site_tag": "site-2",
    },
    {
        "raw_text": "Scaffold at the east wing again missing safety rails, third time this month.",
        "language": "english",
        "risk_score": 0.65,
        "sif_probability": 0.65,
        "risk_level": "MEDIUM",
        "barrier_category": "PPE non-compliance",
        "equipment_tag": "scaffold",
        "site_tag": "site-2",
    },
    # Scenario 3: Multilingual demo (Hindi report)
    {
        "raw_text": "काम की जगह पर बिजली के तार खुले पड़े हैं, यह खतरनाक हो सकता है।",
        "language": "hindi",
        "risk_score": 0.74,
        "sif_probability": 0.74,
        "risk_level": "HIGH",
        "barrier_category": "equipment failure",
        "equipment_tag": "electrical",
        "site_tag": "site-4",
    },
]

for r in demo_reports:
    report = Report(
        id=str(uuid.uuid4()),
        anon_token=str(uuid.uuid4()),
        raw_text=r["raw_text"],
        language=r["language"],
        status="pending",
        risk_score=r["risk_score"],
        sif_probability=r["sif_probability"],
        risk_level=r["risk_level"],
        barrier_category=r["barrier_category"],
        equipment_tag=r["equipment_tag"],
        site_tag=r["site_tag"],
    )
    db.add(report)
    print(f"Seeded: {r['raw_text'][:50]}... | token: {report.anon_token}")

db.commit()
print("\nAll demo reports seeded successfully.")