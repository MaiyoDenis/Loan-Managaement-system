"""
Real-time Notification Service with WebSocket support
"""

import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.loan import Notification
from app.models.user import User
from app.models.branch import Group, Branch
from app.core.permissions import UserRole


class NotificationService:
    """Real-time notification service"""
    
    def __init__(self):
        self.active_connections: Dict[int, List] = {}  # user_id -> [websocket connections]
    
    async def connect_user(self, user_id: int, websocket):
        """Connect user to WebSocket for real-time notifications"""
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        
        self.active_connections[user_id].append(websocket)
        
        # Send pending notifications
        await self._send_pending_notifications(user_id)
    
    async def disconnect_user(self, user_id: int, websocket):
        """Disconnect user WebSocket"""
        if user_id in self.active_connections:
            try:
                self.active_connections[user_id].remove(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
            except ValueError:
                pass
    
    async def send_notification(self, recipient_id: int, title: str, message: str,
                              notification_type: str = "system", sender_id: Optional[int] = None,
                              send_sms: bool = False) -> Dict[str, Any]:
        """Send notification to a specific user"""
        db = SessionLocal()
        try:
            # Create notification record
            notification = Notification(
                recipient_id=recipient_id,
                sender_id=sender_id,
                title=title,
                message=message,
                notification_type=notification_type,
                target_type="individual"
            )
            
            db.add(notification)
            db.commit()
            db.refresh(notification)
            
            # Send real-time notification
            await self._send_realtime_notification(recipient_id, {
                "id": notification.id,
                "title": title,
                "message": message,
                "type": notification_type,
                "timestamp": notification.created_at.isoformat(),
                "is_read": False
            })
            
            # Send SMS if requested
            if send_sms:
                recipient = db.query(User).filter(User.id == recipient_id).first()
                if recipient and recipient.phone_number:
                    from app.services.sms import sms_service
                    await sms_service.send_sms(
                        recipient.phone_number, 
                        f"{title}\n{message}",
                        notification.id
                    )
                    notification.sent_via_sms = True
                    db.commit()
            
            return {"success": True, "notification_id": notification.id}
            
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}
        finally:
            db.close()
    
    async def send_group_notification(self, group_id: int, title: str, message: str,
                                    notification_type: str = "system", sender_id: Optional[int] = None,
                                    send_sms: bool = False) -> Dict[str, Any]:
        """Send notification to all members of a group"""
        db = SessionLocal()
        try:
            # Get group members
            from app.models.branch import GroupMembership
            
            memberships = db.query(GroupMembership).filter(
                GroupMembership.group_id == group_id,
                GroupMembership.is_active == True
            ).all()
            
            member_ids = [membership.member_id for membership in memberships]
            
            # Create notification record
            notification = Notification(
                sender_id=sender_id,
                title=title,
                message=message,
                notification_type=notification_type,
                target_type="group",
                target_id=group_id
            )
            
            db.add(notification)
            db.commit()
            db.refresh(notification)
            
            # Send to each member
            successful_sends = 0
            for member_id in member_ids:
                try:
                    result = await self.send_notification(
                        recipient_id=member_id,
                        title=title,
                        message=message,
                        notification_type=notification_type,
                        sender_id=sender_id,
                        send_sms=send_sms
                    )
                    if result["success"]:
                        successful_sends += 1
                except Exception as e:
                    print(f"Error sending notification to member {member_id}: {e}")
            
            return {
                "success": True,
                "notification_id": notification.id,
                "total_members": len(member_ids),
                "successful_sends": successful_sends
            }
            
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}
        finally:
            db.close()
    
    async def send_branch_notification(self, branch_id: int, title: str, message: str,
                                     notification_type: str = "system", sender_id: Optional[int] = None,
                                     roles: Optional[List[str]] = None, send_sms: bool = False) -> Dict[str, Any]:
        """Send notification to all users in a branch"""
        db = SessionLocal()
        try:
            # Get branch users
            query = db.query(User).filter(
                User.branch_id == branch_id,
                User.is_active == True
            )
            
            if roles:
                query = query.filter(User.role.in_(roles))
            
            branch_users = query.all()
            user_ids = [user.id for user in branch_users]
            
            # Create notification record
            notification = Notification(
                sender_id=sender_id,
                title=title,
                message=message,
                notification_type=notification_type,
                target_type="branch",
                target_id=branch_id
            )
            
            db.add(notification)
            db.commit()
            db.refresh(notification)
            
            # Send to each user
            successful_sends = 0
            for user_id in user_ids:
                try:
                    result = await self.send_notification(
                        recipient_id=user_id,
                        title=title,
                        message=message,
                        notification_type=notification_type,
                        sender_id=sender_id,
                        send_sms=send_sms
                    )
                    if result["success"]:
                        successful_sends += 1
                except Exception as e:
                    print(f"Error sending notification to user {user_id}: {e}")
            
            return {
                "success": True,
                "notification_id": notification.id,
                "total_users": len(user_ids),
                "successful_sends": successful_sends
            }
            
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}
        finally:
            db.close()
    
    async def send_system_notification(self, title: str, message: str,
                                     notification_type: str = "system", sender_id: Optional[int] = None,
                                     roles: Optional[List[str]] = None, send_sms: bool = False) -> Dict[str, Any]:
        """Send system-wide notification"""
        db = SessionLocal()
        try:
            # Get all active users
            query = db.query(User).filter(User.is_active == True)
            
            if roles:
                query = query.filter(User.role.in_(roles))
            
            all_users = query.all()
            user_ids = [user.id for user in all_users]
            
            # Create notification record
            notification = Notification(
                sender_id=sender_id,
                title=title,
                message=message,
                notification_type=notification_type,
                target_type="all"
            )
            
            db.add(notification)
            db.commit()
            db.refresh(notification)
            
            # Send to each user
            successful_sends = 0
            for user_id in user_ids:
                try:
                    result = await self.send_notification(
                        recipient_id=user_id,
                        title=title,
                        message=message,
                        notification_type=notification_type,
                        sender_id=sender_id,
                        send_sms=send_sms
                    )
                    if result["success"]:
                        successful_sends += 1
                except Exception as e:
                    print(f"Error sending notification to user {user_id}: {e}")
            
            return {
                "success": True,
                "notification_id": notification.id,
                "total_users": len(user_ids),
                "successful_sends": successful_sends
            }
            
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}
        finally:
            db.close()
    
    async def _send_realtime_notification(self, user_id: int, notification_data: Dict[str, Any]):
        """Send real-time notification via WebSocket"""
        if user_id in self.active_connections:
            disconnected_connections = []
            
            for websocket in self.active_connections[user_id]:
                try:
                    await websocket.send_text(json.dumps({
                        "type": "notification",
                        "data": notification_data
                    }))
                except Exception:
                    # Mark connection as disconnected
                    disconnected_connections.append(websocket)
            
            # Remove disconnected connections
            for conn in disconnected_connections:
                try:
                    self.active_connections[user_id].remove(conn)
                except ValueError:
                    pass
            
            # Clean up empty connection lists
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
    
    async def _send_pending_notifications(self, user_id: int):
        """Send pending unread notifications to newly connected user"""
        db = SessionLocal()
        try:
            # Get unread notifications
            unread_notifications = db.query(Notification).filter(
                Notification.recipient_id == user_id,
                Notification.is_read == False
            ).order_by(Notification.created_at.desc()).limit(20).all()
            
            for notification in unread_notifications:
                await self._send_realtime_notification(user_id, {
                    "id": notification.id,
                    "title": notification.title,
                    "message": notification.message,
                    "type": notification.notification_type,
                    "timestamp": notification.created_at.isoformat(),
                    "is_read": False
                })
        
        except Exception as e:
            print(f"Error sending pending notifications: {e}")
        finally:
            db.close()
    
    def get_user_notifications(self, user_id: int, limit: int = 50, 
                              unread_only: bool = False) -> List[Dict[str, Any]]:
        """Get user notifications"""
        db = SessionLocal()
        try:
            query = db.query(Notification).filter(Notification.recipient_id == user_id)
            
            if unread_only:
                query = query.filter(Notification.is_read == False)
            
            notifications = query.order_by(Notification.created_at.desc()).limit(limit).all()
            
            return [
                {
                    "id": notif.id,
                    "title": notif.title,
                    "message": notif.message,
                    "type": notif.notification_type,
                    "timestamp": notif.created_at.isoformat(),
                    "is_read": notif.is_read
                }
                for notif in notifications
            ]
            
        finally:
            db.close()
    
    def mark_notification_as_read(self, notification_id: int, user_id: int) -> bool:
        """Mark notification as read"""
        db = SessionLocal()
        try:
            notification = db.query(Notification).filter(
                Notification.id == notification_id,
                Notification.recipient_id == user_id
            ).first()
            
            if notification:
                notification.is_read = True
                db.commit()
                return True
            
            return False
            
        except Exception as e:
            print(f"Error marking notification as read: {e}")
            return False
        finally:
            db.close()


# Initialize notification service
notification_service = NotificationService()