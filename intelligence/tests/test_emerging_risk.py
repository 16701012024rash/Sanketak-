from intelligence.barrier_drift.emerging_risk import detect_emerging_risks


historical_reports = [
    {
        "report_id": "OLD001",
        "barrier_failures": []
    }
]

recent_reports = [
    {
        "report_id": "R001",
        "barrier_failures": [
            {
                "barrier": "BAR_FIRE_WATCH",
                "failure_mode": "FM_ABSENT"
            }
        ]
    },
    {
        "report_id": "R002",
        "barrier_failures": [
            {
                "barrier": "BAR_FIRE_WATCH",
                "failure_mode": "FM_ABSENT"
            }
        ]
    }
]


risks = detect_emerging_risks(
    historical_reports,
    recent_reports
)

print("Emerging Risks:")
for risk in risks:
    print(risk)