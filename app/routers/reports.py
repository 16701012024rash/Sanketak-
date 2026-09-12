from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.db import SessionLocal
from app.models.report import Report
from app.core.security import get_current_user
from app.services.analysis import analyse_report
import uuid

router = APIRouter(prefix="/reports", tags=["reports"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/")
def create_report(raw_text: str, language: str, db: Session = Depends(get_db)):
    analysis = analyse_report(raw_text)
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
def list_reports(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    reports = db.query(Report).all()
    return reports

@router.get("/{report_id}")
def get_report(report_id: str, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        return {"error": "Report not found"}
    return report