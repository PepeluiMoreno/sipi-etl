from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session
from db.connection import SessionLocal
from core.notification_service import NotificationService

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class NotificationResponse(BaseModel):
    id: int
    module_name: str
    type: str
    priority: str
    title: str
    message: str
    created_at: str
    is_read: bool
    metadata: dict

@router.get("/", response_model=List[NotificationResponse])
async def get_notifications(module: str = Query(None), unread_only: bool = Query(True), db: Session = Depends(get_db)):
    service = NotificationService()
    service.db = db
    return service.get_unread(module)

@router.patch("/{notification_id}/read")
async def mark_notification_read(notification_id: int, db: Session = Depends(get_db)):
    service = NotificationService()
    service.db = db
    service.mark_as_read(notification_id)
    return {"status": "marked_as_read"}
