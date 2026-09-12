from fastapi import FastAPI
from pydantic import BaseModel
import joblib
import re

app = FastAPI(title="Sanketak SIF API")

MODEL_PATH = "output/sif_classifier.joblib"
model = joblib.load(MODEL_PATH)


class IncidentRequest(BaseModel):
    incident_text: str


def predict_sif(text):
    probability = model.predict_proba([text])[0][1]

    lower = text.lower()

    no_exposure = bool(re.search(
        r"\b(no employees?|no workers?|no personnel|"
        r"no one was|no one injured|unoccupied|"
        r"no person|no people|not working in (the )?area)\b",
        lower
    ))

    minor_event = bool(re.search(
        r"\b(minor cut|minor scratch|minor bruise|"
        r"first aid only|no injury|no injuries)\b",
        lower
    ))

    severe_event = bool(re.search(
        r"\b(trapped|entrapped|pinned|crushed|"
        r"buried|engulfed|electrocuted|"
        r"fatal|killed|died|amputation|"
        r"roof collapse|roof fall|rollover|"
        r"overturned|explosion|inundation|drowning)\b",
        lower
    ))

    if no_exposure and not severe_event:
        probability = min(probability, 0.25)

    elif minor_event and not severe_event:
        probability = min(probability, 0.25)

    elif severe_event:
        probability = max(probability, 0.75)

    if probability >= 0.75:
        risk_level = "HIGH"
    elif probability >= 0.40:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    reasons = []

    if severe_event:
        reasons.append("Severe/high-consequence mechanism detected")

    if no_exposure:
        reasons.append("No worker exposure indicated")

    if minor_event:
        reasons.append("Minor event indicators detected")

    if not reasons:
        reasons.append("Risk estimated from incident patterns")

    return {
        "sif_probability": round(float(probability), 4),
        "risk_level": risk_level,
        "reason": reasons
    }


@app.get("/")
def root():
    return {"message": "Sanketak SIF API Running"}


@app.post("/predict")
def predict(request: IncidentRequest):
    return predict_sif(request.incident_text)