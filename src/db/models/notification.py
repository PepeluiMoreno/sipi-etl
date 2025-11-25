from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON
from sqlalchemy.dialects.postgresql import JSONB
from db.models.base import Base
from datetime import datetime

NOTIFICATION_TYPE = ("etl_success", "etl_failed", "etl_no_changes", "etl_warning")
PRIORITY_TYPE = ("low", "medium", "high", "critical")

class NotificationEvent(Base):
    __tablename__ = "events"
    __table_args__ = {"schema": "notifications"}
    
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    module_name = Column(String(50), nullable=False)
    run_id = Column(Integer, nullable=True)
    type = Column(String(50), nullable=False)
    priority = Column(String(20), default="medium")
    title = Column(String(255), nullable=False)
    message = Column(String)
    metadata = Column(JSONB)
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime)
    
    def to_dict(self):
        return {"id": self.id, "created_at": self.created_at.isoformat(), "module_name": self.module_name, "type": self.type, "priority": self.priority, "title": self.title, "message": self.message or "", "metadata": self.metadata or {}, "is_read": self.is_read}
