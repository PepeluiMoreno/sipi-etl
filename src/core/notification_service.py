from db.models.notification import NotificationEvent
from db.connection import SessionLocal
from typing import Dict, List, Optional

class NotificationService:
    MODULE_NAME = "osmwikidata"
    
    def __init__(self):
        self.db = SessionLocal()
    
    def create(self, **kwargs) -> int:
        notif = NotificationEvent(module_name=self.MODULE_NAME, **kwargs)
        self.db.add(notif)
        self.db.commit()
        self.db.refresh(notif)
        return notif.id
    
    def get_unread(self, module_name: Optional[str] = None) -> List[Dict]:
        query = self.db.query(NotificationEvent).filter_by(is_read=False)
        if module_name:
            query = query.filter_by(module_name=module_name)
        return [n.to_dict() for n in query.order_by(NotificationEvent.created_at.desc()).all()]
