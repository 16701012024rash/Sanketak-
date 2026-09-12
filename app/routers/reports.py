from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.db import SessionLocal
from app.models.report import Report
import uuid
import random

router = APIRouter(prefix="/reports", tags=["reports"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

EQUIPMENT_TAGS = ["pump", "scaffold", "crane", "pipeline", "electrical"]
BARRIER_CATEGORIES = ["PPE non-compliance", "procedure violation", "equipment failure", "near miss"]

def mock_analyze(raw_text: str):
    seed = sum(ord(c) for c in raw_text) if raw_text else 0
    random.seed(seed)
    return {
        "risk_score": round(random.uniform(0.1, 0.95), 2),
        "barrier_category": random.choice(BARRIER_CATEGORIES),
        "equipment_tag": random.choice(EQUIPMENT_TAGS),
        "site_tag": f"site-{seed % 5 + 1}",
    }

@router.post("/")
def create_report(raw_text: str, language: str, db: Session = Depends(get_db)):
    analysis = mock_analyze(raw_text)
    report = Report(
        anon_token=str(uuid.uuid4()),
        raw_text=raw_text,
        language=language,
        **analysis,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return {"anon_token": report.anon_token, "status": report.status}

@router.get("/worker/{token}")
def check_status(token: str, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.anon_token == token).first()
    if not report:
        return {"error": "Invalid token or report not found"}
    return {
        "status": report.status,
        "language": report.language,
        "submitted_at": report.submitted_at
    }

@router.get("/")
def list_reports(db: Session = Depends(get_db)):
    reports = db.query(Report).all()
    return reports

@router.get("/{report_id}")
def get_report(report_id: str, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        return {"error": "Report not found"}
    return report