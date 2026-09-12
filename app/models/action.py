from sqlalchemy import Column, String, DateTime
from app.core.db import Base
import uuid

class CorrectiveAction(Base):
    __tablename__ = "corrective_actions"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    report_id = Column(String, index=True)
    description = Column(String)
    status = Column(String, default="open")
    owner = Column(String, nullable=True)
    due_date = Column(DateTime, nullable=True)