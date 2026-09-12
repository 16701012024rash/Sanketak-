from sqlalchemy import Column, String, Text, DateTime, Float, func
from app.core.db import Base
import uuid

class Report(Base):
    __tablename__ = "reports"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    anon_token = Column(String, unique=True, index=True)
    raw_text = Column(Text)
    language = Column(String)
    status = Column(String, default="pending")
    submitted_at = Column(DateTime, server_default=func.now())

    # Placeholder analysis fields (Phase 3 stub — real values come from AI team in Phase 4)
    risk_score = Column(Float, nullable=True)
    barrier_category = Column(String, nullable=True)
    equipment_tag = Column(String, nullable=True)
    site_tag = Column(String, nullable=True)