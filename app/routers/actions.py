from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.db import SessionLocal
from app.models.action import CorrectiveAction
from app.core.security import get_current_user
import uuid

router = APIRouter(prefix="/actions", tags=["actions"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/")
def create_action(report_id: str, description: str, owner: str = None, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    action = CorrectiveAction(
        id=str(uuid.uuid4()), report_id=report_id, description=description, owner=owner
    )
    db.add(action)
    db.commit()
    db.refresh(action)
    return action

@router.patch("/{action_id}")
def update_action(action_id: str, status: str, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    action = db.query(CorrectiveAction).filter(CorrectiveAction.id == action_id).first()
    if not action:
        return {"error": "Action not found"}
    action.status = status
    db.commit()
    db.refresh(action)
    return action