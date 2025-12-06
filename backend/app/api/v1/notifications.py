"""
Notification Management API endpoints
"""

from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.models.loan import Notification
from app.models.user import User
from app.models.branch import Group, Branch
from app.core.permissions import UserRole
from app.services.notification import notification_service
from app.schemas.notification import (
    NotificationCreate,
    NotificationResponse,
    BulkNotificationRequest
)
from app.api.deps import (
    get_current_active_user,
    require_permission
)

router = APIRouter()


@router.get("/", response_model=List[NotificationResponse])
def get_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    unread_only: bool = Query(False),
    notification_type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100)
) -> Any:
    """Get user notifications"""
    
    query = db.query(Notification).filter(Notification.recipient_id == current_user.id)
    
    if unread_only:
        query = query.filter(Notification.is_read == False)
    
    if notification_type:
        query = query.filter(Notification.notification_type == notification_type)
    
    notifications = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit).all()
    
    return notifications


@router.post("/mark-read/{notification_id}")
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Mark notification as read"""
    
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.recipient_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    notification.is_read = True
    db.commit()
    
    return {"message": "Notification marked as read"}


@router.post("/mark-all-read")
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Mark all notifications as read"""
    
    db.query(Notification).filter(
        Notification.recipient_id == current_user.id,
        Notification.is_read == False
    ).update({"is_read": True})
    
    db.commit()
    
    return {"message": "All notifications marked as read"}


@router.post("/send", response_model=NotificationResponse)
async def send_notification(
    notification_data: NotificationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("notifications:send_individual"))
) -> Any:
    """Send notification to a user"""
    
    # Verify recipient exists
    recipient = db.query(User).filter(User.id == notification_data.recipient_id).first()
    if not recipient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipient not found"
        )
    
    # Check if sender can send to this recipient
    if current_user.role != UserRole.ADMIN:
        if recipient.branch_id != current_user.branch_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only send notifications to users in your branch"
            )
    
    # Send notification
    result = await notification_service.send_notification(
        recipient_id=notification_data.recipient_id,
        title=notification_data.title,
        message=notification_data.message,
        notification_type=notification_data.notification_type,
        sender_id=current_user.id,
        send_sms=notification_data.send_sms
    )
    
    if result["success"]:
        # Get the created notification
        notification = db.query(Notification).filter(
            Notification.id == result["notification_id"]
        ).first()
        return notification
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["error"]
        )


@router.post("/send-bulk")
async def send_bulk_notification(
    bulk_data: BulkNotificationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Send notification to multiple recipients"""
    
    result = {"success": False, "error": "Unknown target type"}
    
    if bulk_data.target_type == "group":
        if not current_user or not require_permission("notifications:send_group"):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        result = await notification_service.send_group_notification(
            group_id=bulk_data.target_id,
            title=bulk_data.title,
            message=bulk_data.message,
            notification_type=bulk_data.notification_type,
            sender_id=current_user.id,
            send_sms=bulk_data.send_sms
        )
    
    elif bulk_data.target_type == "branch":
        if not current_user or not require_permission("notifications:send_branch"):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        result = await notification_service.send_branch_notification(
            branch_id=bulk_data.target_id,
            title=bulk_data.title,
            message=bulk_data.message,
            notification_type=bulk_data.notification_type,
            sender_id=current_user.id,
            roles=bulk_data.roles,
            send_sms=bulk_data.send_sms
        )
    
    elif bulk_data.target_type == "all":
        if not current_user or not require_permission("notifications:send_all"):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        result = await notification_service.send_system_notification(
            title=bulk_data.title,
            message=bulk_data.message,
            notification_type=bulk_data.notification_type,
            sender_id=current_user.id,
            roles=bulk_data.roles,
            send_sms=bulk_data.send_sms
        )
    
    if result["success"]:
        return {
            "message": "Bulk notification sent successfully",
            "notification_id": result["notification_id"],
            "recipients": result.get("successful_sends", 0)
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["error"]
        )


@router.get("/unread-count")
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Get count of unread notifications"""
    
    unread_count = db.query(Notification).filter(
        Notification.recipient_id == current_user.id,
        Notification.is_read == False
    ).count()
    
    return {"unread_count": unread_count}