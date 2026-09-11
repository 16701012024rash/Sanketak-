from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.db import SessionLocal
from app.models.report import Report
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
    report = Report(anon_token=str(uuid.uuid4()), raw_text=raw_text, language=language)
    db.add(report)
    db.commit()
    db.refresh(report)
    return {"anon_token": report.anon_token, "status": report.status}
