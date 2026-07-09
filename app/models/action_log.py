from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func

from app.db.base import Base

class ActionLog(Base):
    __tablename__ = "action_logs"

    action = Column(String, index=True)
    campaign_id = Column(Integer, nullable=True)
    details = Column(String)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())