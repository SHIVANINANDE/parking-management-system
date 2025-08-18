"""
Event Handlers for Real-time System
Handles events for notifications, state changes, and system responses
"""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from app.db.database import get_db
from app.db.redis import get_redis_client
from app.models.parking_spot import ParkingSpot, SpotStatus
from app.models.reservation import Reservation, ReservationStatus
from app.models.user import User
from app.services.event_service import Event, EventType, EventPriority

logger = logging.getLogger(__name__)

@dataclass
class NotificationChannel:
    """Notification delivery channel"""
    type: str  # email, sms, push, websocket
    address: str
    enabled: bool = True
    priority: int = 1

@dataclass
class NotificationTemplate:
    """Notification message template"""
    event_type: EventType
    channels: List[str]
    subject_template: str
    body_template: str
    urgency: str = "normal"  # low, normal, high, critical

class NotificationService:
    """Handles real-time notifications"""
    
    def __init__(self):
        self.redis_client = get_redis_client()
        self.templates = self._load_notification_templates()
        self.websocket_connections = {}  # user_id -> websocket connection
    
    def _load_notification_templates(self) -> Dict[EventType, NotificationTemplate]:
        """Load notification templates for different event types"""
        return {
            EventType.RESERVATION_CREATED: NotificationTemplate(
                event_type=EventType.RESERVATION_CREATED,
                channels=["email", "push", "websocket"],
                subject_template="Reservation Created - {reservation_number}",
                body_template="Your parking reservation {reservation_number} has been created for {start_time}. Confirmation code: {confirmation_code}",
                urgency="normal"
            ),
            
            EventType.RESERVATION_CONFIRMED: NotificationTemplate(
                event_type=EventType.RESERVATION_CONFIRMED,
                channels=["email", "push", "websocket"],
                subject_template="Reservation Confirmed - {reservation_number}",
                body_template="Your parking reservation {reservation_number} has been confirmed. Spot: {spot_number}, Time: {start_time} - {end_time}",
                urgency="high"
            ),
            
            EventType.RESERVATION_EXPIRED: NotificationTemplate(
                event_type=EventType.RESERVATION_EXPIRED,
                channels=["email", "sms", "push", "websocket"],
                subject_template="Reservation Expired - {reservation_number}",
                body_template="Your parking reservation {reservation_number} has expired. Please create a new reservation if needed.",
                urgency="high"
            ),
            
            EventType.SPOT_OCCUPIED: NotificationTemplate(
                event_type=EventType.SPOT_OCCUPIED,
                channels=["websocket"],
                subject_template="Parking Spot Occupied",
                body_template="Parking spot {spot_number} is now occupied",
                urgency="normal"
            ),
            
            EventType.SPOT_VACATED: NotificationTemplate(
                event_type=EventType.SPOT_VACATED,
                channels=["websocket"],
                subject_template="Parking Spot Available",
                body_template="Parking spot {spot_number} is now available",
                urgency="normal"
            ),
            
            EventType.USER_ARRIVED: NotificationTemplate(
                event_type=EventType.USER_ARRIVED,
                channels=["websocket"],
                subject_template="User Arrived",
                body_template="User has arrived at parking spot {spot_number}",
                urgency="normal"
            ),
            
            EventType.CAPACITY_THRESHOLD: NotificationTemplate(
                event_type=EventType.CAPACITY_THRESHOLD,
                channels=["websocket", "email"],
                subject_template="Parking Lot Capacity Alert",
                body_template="Parking lot {lot_name} is at {capacity_percentage}% capacity",
                urgency="high"
            ),
        }
    
    async def register_websocket(self, user_id: int, websocket):
        """Register websocket connection for user"""
        self.websocket_connections[user_id] = websocket
        logger.info(f"Registered websocket for user {user_id}")
    
    async def unregister_websocket(self, user_id: int):
        """Unregister websocket connection"""
        if user_id in self.websocket_connections:
            del self.websocket_connections[user_id]
            logger.info(f"Unregistered websocket for user {user_id}")
    
    async def send_notification(self, user_id: int, event: Event):
        """Send notification to user based on event"""
        try:
            template = self.templates.get(event.event_type)
            if not template:
                logger.warning(f"No template found for event type {event.event_type}")
                return
            
            # Get user notification preferences
            preferences = await self._get_user_notification_preferences(user_id)
            
            # Format message
            message_data = await self._format_notification_message(template, event)
            
            # Send through enabled channels
            for channel in template.channels:
                if channel in preferences and preferences[channel]:
                    await self._send_through_channel(user_id, channel, message_data, template.urgency)
            
        except Exception as e:
            logger.error(f"Failed to send notification to user {user_id}: {e}")
    
    async def broadcast_notification(self, event: Event, target_users: Optional[List[int]] = None):
        """Broadcast notification to multiple users"""
        try:
            template = self.templates.get(event.event_type)
            if not template:
                return
            
            # If no target users specified, send to all websocket connections
            if target_users is None:
                target_users = list(self.websocket_connections.keys())
            
            message_data = await self._format_notification_message(template, event)
            
            # Send to all target users
            tasks = []
            for user_id in target_users:
                if user_id in self.websocket_connections:
                    tasks.append(
                        self._send_websocket_message(user_id, message_data)
                    )
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            
        except Exception as e:
            logger.error(f"Failed to broadcast notification: {e}")
    
    async def _get_user_notification_preferences(self, user_id: int) -> Dict[str, bool]:
        """Get user notification preferences from Redis cache or database"""
        try:
            # Try Redis first
            prefs_key = f"user_notifications:{user_id}"
            cached_prefs = await self.redis_client.get(prefs_key)
            
            if cached_prefs:
                return json.loads(cached_prefs)
            
            # Fallback to database
            async with get_db() as session:
                from sqlalchemy import select
                result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                user = result.scalar_one_or_none()
                
                if user:
                    prefs = {
                        "email": True,  # Default preferences
                        "sms": False,
                        "push": True,
                        "websocket": True
                    }
                    
                    # Cache for 1 hour
                    await self.redis_client.setex(
                        prefs_key, 3600, json.dumps(prefs)
                    )
                    
                    return prefs
            
            return {"websocket": True}  # Minimal default
            
        except Exception as e:
            logger.error(f"Failed to get notification preferences for user {user_id}: {e}")
            return {"websocket": True}
    
    async def _format_notification_message(self, template: NotificationTemplate, 
                                         event: Event) -> Dict[str, Any]:
        """Format notification message using template and event data"""
        try:
            # Extract common data from event
            data = event.event_data.copy()
            data.update({
                "event_id": event.event_id,
                "event_type": event.event_type.value,
                "timestamp": event.timestamp.isoformat()
            })
            
            # Format subject and body
            subject = template.subject_template.format(**data)
            body = template.body_template.format(**data)
            
            return {
                "id": event.event_id,
                "type": event.event_type.value,
                "subject": subject,
                "body": body,
                "urgency": template.urgency,
                "timestamp": event.timestamp.isoformat(),
                "data": data
            }
            
        except Exception as e:
            logger.error(f"Failed to format notification message: {e}")
            return {
                "id": event.event_id,
                "type": event.event_type.value,
                "subject": "Parking System Notification",
                "body": "A parking system event occurred",
                "urgency": "normal",
                "timestamp": event.timestamp.isoformat()
            }
    
    async def _send_through_channel(self, user_id: int, channel: str, 
                                  message_data: Dict[str, Any], urgency: str):
        """Send notification through specific channel"""
        try:
            if channel == "websocket":
                await self._send_websocket_message(user_id, message_data)
            elif channel == "email":
                await self._send_email_notification(user_id, message_data)
            elif channel == "push":
                await self._send_push_notification(user_id, message_data)
            elif channel == "sms":
                await self._send_sms_notification(user_id, message_data)
                
        except Exception as e:
            logger.error(f"Failed to send notification via {channel} to user {user_id}: {e}")
    
    async def _send_websocket_message(self, user_id: int, message_data: Dict[str, Any]):
        """Send real-time notification via WebSocket"""
        if user_id in self.websocket_connections:
            try:
                websocket = self.websocket_connections[user_id]
                await websocket.send_text(json.dumps({
                    "type": "notification",
                    "data": message_data
                }))
            except Exception as e:
                logger.error(f"Failed to send websocket message to user {user_id}: {e}")
                # Remove broken connection
                await self.unregister_websocket(user_id)
    
    async def _send_email_notification(self, user_id: int, message_data: Dict[str, Any]):
        """Send email notification (placeholder)"""
        # This would integrate with actual email service
        logger.info(f"Email notification to user {user_id}: {message_data['subject']}")
    
    async def _send_push_notification(self, user_id: int, message_data: Dict[str, Any]):
        """Send push notification (placeholder)"""
        # This would integrate with FCM or similar service
        logger.info(f"Push notification to user {user_id}: {message_data['subject']}")
    
    async def _send_sms_notification(self, user_id: int, message_data: Dict[str, Any]):
        """Send SMS notification (placeholder)"""
        # This would integrate with Twilio or similar service
        logger.info(f"SMS notification to user {user_id}: {message_data['body']}")

class SystemEventHandler:
    """Handles system-level events and state management"""
    
    def __init__(self, notification_service: NotificationService):
        self.notification_service = notification_service
        self.redis_client = get_redis_client()
    
    async def handle_spot_status_change(self, event: Event):
        """Handle parking spot status changes"""
        try:
            spot_id = event.event_data.get("spot_id")
            new_status = event.event_data.get("new_status")
            parking_lot_id = event.event_data.get("parking_lot_id")
            
            # Update real-time spot status in Redis
            await self.redis_client.setex(
                f"spot_status:{spot_id}",
                3600,  # 1 hour TTL
                json.dumps({
                    "status": new_status,
                    "updated_at": event.timestamp.isoformat(),
                    "parking_lot_id": parking_lot_id
                })
            )
            
            # Broadcast to interested users (admin, nearby users)
            await self.notification_service.broadcast_notification(event)
            
            # Update parking lot capacity statistics
            await self._update_lot_capacity_stats(parking_lot_id)
            
        except Exception as e:
            logger.error(f"Failed to handle spot status change: {e}")
    
    async def handle_reservation_created(self, event: Event):
        """Handle new reservation creation"""
        try:
            user_id = event.event_data.get("user_id")
            reservation_id = event.event_data.get("reservation_id")
            
            # Send notification to user
            if user_id:
                await self.notification_service.send_notification(user_id, event)
            
            # Update reservation statistics
            await self._update_reservation_stats(event.timestamp)
            
        except Exception as e:
            logger.error(f"Failed to handle reservation created: {e}")
    
    async def handle_capacity_threshold(self, event: Event):
        """Handle parking lot capacity threshold alerts"""
        try:
            parking_lot_id = event.event_data.get("parking_lot_id")
            capacity_percentage = event.event_data.get("capacity_percentage")
            
            # Get admin users for this parking lot
            admin_users = await self._get_lot_admin_users(parking_lot_id)
            
            # Send alert notifications
            for admin_user_id in admin_users:
                await self.notification_service.send_notification(admin_user_id, event)
            
            # Log capacity alert
            await self.redis_client.lpush(
                f"capacity_alerts:{parking_lot_id}",
                json.dumps({
                    "timestamp": event.timestamp.isoformat(),
                    "capacity_percentage": capacity_percentage,
                    "event_id": event.event_id
                })
            )
            
            # Keep only last 100 alerts
            await self.redis_client.ltrim(f"capacity_alerts:{parking_lot_id}", 0, 99)
            
        except Exception as e:
            logger.error(f"Failed to handle capacity threshold: {e}")
    
    async def handle_user_arrival(self, event: Event):
        """Handle user arrival at parking spot"""
        try:
            user_id = event.event_data.get("user_id")
            spot_id = event.event_data.get("spot_id")
            reservation_id = event.event_data.get("reservation_id")
            
            # Update reservation status if applicable
            if reservation_id:
                async with get_db() as session:
                    from sqlalchemy import select, update
                    
                    # Update reservation to active
                    await session.execute(
                        update(Reservation)
                        .where(Reservation.id == reservation_id)
                        .values(
                            status=ReservationStatus.ACTIVE,
                            actual_arrival_time=event.timestamp
                        )
                    )
                    await session.commit()
            
            # Send confirmation to user
            if user_id:
                await self.notification_service.send_notification(user_id, event)
            
        except Exception as e:
            logger.error(f"Failed to handle user arrival: {e}")
    
    async def _update_lot_capacity_stats(self, parking_lot_id: int):
        """Update parking lot capacity statistics"""
        try:
            async with get_db() as session:
                from sqlalchemy import select, func
                
                # Get total and occupied spots
                total_spots = await session.execute(
                    select(func.count(ParkingSpot.id))
                    .where(
                        and_(
                            ParkingSpot.parking_lot_id == parking_lot_id,
                            ParkingSpot.is_active == True
                        )
                    )
                )
                total_count = total_spots.scalar()
                
                occupied_spots = await session.execute(
                    select(func.count(ParkingSpot.id))
                    .where(
                        and_(
                            ParkingSpot.parking_lot_id == parking_lot_id,
                            ParkingSpot.status.in_([SpotStatus.OCCUPIED, SpotStatus.RESERVED]),
                            ParkingSpot.is_active == True
                        )
                    )
                )
                occupied_count = occupied_spots.scalar()
                
                available_count = total_count - occupied_count
                capacity_percentage = (occupied_count / total_count * 100) if total_count > 0 else 0
                
                # Store in Redis
                capacity_data = {
                    "total_spots": total_count,
                    "occupied_spots": occupied_count,
                    "available_spots": available_count,
                    "capacity_percentage": round(capacity_percentage, 2),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                
                await self.redis_client.setex(
                    f"lot_capacity:{parking_lot_id}",
                    300,  # 5 minutes TTL
                    json.dumps(capacity_data)
                )
                
                # Check threshold alerts (80% and 95%)
                if capacity_percentage >= 95:
                    await self._trigger_capacity_alert(parking_lot_id, capacity_percentage, "critical")
                elif capacity_percentage >= 80:
                    await self._trigger_capacity_alert(parking_lot_id, capacity_percentage, "high")
                
        except Exception as e:
            logger.error(f"Failed to update lot capacity stats: {e}")
    
    async def _trigger_capacity_alert(self, parking_lot_id: int, capacity_percentage: float, level: str):
        """Trigger capacity threshold alert"""
        try:
            from app.services.event_service import event_service
            
            await event_service.publish_event(
                event_type=EventType.CAPACITY_THRESHOLD,
                aggregate_type="parking_lot",
                aggregate_id=str(parking_lot_id),
                event_data={
                    "parking_lot_id": parking_lot_id,
                    "capacity_percentage": capacity_percentage,
                    "level": level
                },
                priority=EventPriority.HIGH if level == "critical" else EventPriority.NORMAL
            )
            
        except Exception as e:
            logger.error(f"Failed to trigger capacity alert: {e}")
    
    async def _update_reservation_stats(self, timestamp: datetime):
        """Update reservation statistics"""
        try:
            # Daily reservation count
            date_key = timestamp.strftime("%Y-%m-%d")
            await self.redis_client.incr(f"reservations_daily:{date_key}")
            await self.redis_client.expire(f"reservations_daily:{date_key}", 86400 * 7)  # 7 days
            
            # Hourly reservation count
            hour_key = timestamp.strftime("%Y-%m-%d:%H")
            await self.redis_client.incr(f"reservations_hourly:{hour_key}")
            await self.redis_client.expire(f"reservations_hourly:{hour_key}", 86400)  # 24 hours
            
        except Exception as e:
            logger.error(f"Failed to update reservation stats: {e}")
    
    async def _get_lot_admin_users(self, parking_lot_id: int) -> List[int]:
        """Get admin user IDs for a parking lot"""
        try:
            # This would typically query the database for admin users
            # For now, return empty list
            return []
            
        except Exception as e:
            logger.error(f"Failed to get lot admin users: {e}")
            return []

# Global instances
notification_service = NotificationService()
system_event_handler = SystemEventHandler(notification_service)
