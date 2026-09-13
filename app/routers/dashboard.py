from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.db import SessionLocal
from app.models.report import Report
from app.models.action import CorrectiveAction
from app.core.security import get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get(
    "/summary",
    summary="Get dashboard summary stats (HSE staff only)",
    description="Returns combined summary statistics for the HSE dashboard's overview cards: "
                "total reports, high-risk report count, and open corrective actions. "
                "Requires a valid HSE staff login token.",
)
def dashboard_summary(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    total_reports = db.query(Report).count()
    high_risk_count = db.query(Report).filter(Report.risk_score >= 0.6).count()
    open_actions = db.query(CorrectiveAction).filter(CorrectiveAction.status == "open").count()
    total_actions = db.query(CorrectiveAction).count()

    return {
        "total_reports": total_reports,
        "high_risk_count": high_risk_count,
        "open_actions": open_actions,
        "total_actions": total_actions,
    }