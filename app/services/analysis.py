import random

# --- Fields used for demo/UI purposes (risk-radar, patterns) ---
EQUIPMENT_TAGS = ["pump", "scaffold", "crane", "pipeline", "electrical"]
BARRIER_CATEGORIES = ["PPE non-compliance", "procedure violation", "equipment failure", "near miss"]

def analyse_report(raw_text: str) -> dict:
    """
    Runs analysis on report text and returns a result matching
    the AI/ML team's real contract: sif_probability + risk_level.

    Currently mocked. Swap the internals of this function for a real
    call to the AI/ML team's model once their pipeline is delivered —
    every caller of this function (routes, create_report) stays unchanged.
    """
    seed = sum(ord(c) for c in raw_text) if raw_text else 0
    random.seed(seed)

    sif_probability = round(random.uniform(0.05, 0.95), 2)

    if sif_probability >= 0.7:
        risk_level = "HIGH"
    elif sif_probability >= 0.4:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    return {
        "sif_probability": sif_probability,
        "risk_level": risk_level,
        # kept for existing demo endpoints (risk-radar, patterns)
        "risk_score": sif_probability,
        "barrier_category": random.choice(BARRIER_CATEGORIES),
        "equipment_tag": random.choice(EQUIPMENT_TAGS),
        "site_tag": f"site-{seed % 5 + 1}",
    }