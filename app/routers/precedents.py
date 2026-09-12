from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.db import SessionLocal
from app.models.precedent import HistoricalPrecedent
from app.models.report import Report
import random

router = APIRouter(prefix="/precedents", tags=["precedents"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def mock_embedding(text: str):
    seed = sum(ord(c) for c in text) if text else 0
    random.seed(seed)
    return [random.uniform(-1, 1) for _ in range(8)]

@router.get("/{report_id}")
def get_precedents(report_id: str, limit: int = 3, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        return {"error": "Report not found"}

    query_embedding = mock_embedding(report.raw_text)

    matches = (
        db.query(HistoricalPrecedent)
        .order_by(HistoricalPrecedent.embedding.l2_distance(query_embedding))
        .limit(limit)
        .all()
    )
    return {
        "report_id": report_id,
        "matches": [
            {"name": m.name, "description": m.description, "source": m.source}
            for m in matches
        ],
    }