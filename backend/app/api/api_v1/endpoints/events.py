"""
Real-time Event System API Endpoints
Provides REST and WebSocket endpoints for event streaming and reservation management
"""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from uuid import uuid4
from sqlalchemy import select, func, and_

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.user import User
from app.models.reservation import Reservation, ReservationStatus
from app.models.parking_spot import ParkingSpot, SpotStatus
from app.services.event_service import EventService, EventType, EventPriority, event_service
from app.services.cqrs_service import CQRSService, CreateReservationCommand, UpdateSpotStatusCommand, cqrs_service
from app.services.reservation_service import (
    ConcurrentReservationManager, ReservationRequest, ReservationPriority, 
    ReservationResult, reservation_manager
)
from app.services.event_handlers import notification_service, system_event_handler

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()

# Pydantic models for request/response

class ReservationRequestModel(BaseModel):
    user_id: int
    vehicle_id: int
    parking_lot_id: int
    start_time: datetime
    end_time: datetime
    preferred_spot_id: Optional[int] = None
    requires_ev_charging: bool = False
    requires_handicapped_access: bool = False
    special_requests: Optional[str] = None
    priority: str = "normal"  # low, normal, high, vip, emergency
    max_wait_time_seconds: int = Field(default=300, ge=30, le=1800)  # 30 seconds to 30 minutes

class ReservationResponseModel(BaseModel):
    success: bool
    request_id: Optional[str] = None
    reservation_id: Optional[int] = None
    spot_id: Optional[int] = None
    queue_position: Optional[int] = None
    estimated_wait_time: Optional[int] = None
    error_message: Optional[str] = None

class SpotStatusUpdateModel(BaseModel):
    spot_id: int
    new_status: str  # available, occupied, reserved, out_of_order, maintenance
    user_id: Optional[int] = None
    vehicle_id: Optional[int] = None
    reason: Optional[str] = None

class EventStreamFilterModel(BaseModel):
    event_types: Optional[List[str]] = None
    parking_lot_ids: Optional[List[int]] = None
    user_id: Optional[int] = None
    priority_levels: Optional[List[str]] = None

class QueueStatusModel(BaseModel):
    queue_size: int
    active_processing: int
    is_processing: bool
    average_wait_time: Optional[float] = None

class EventStatisticsModel(BaseModel):
    total_events_today: int
    events_by_type: Dict[str, int]
    events_last_hour: int
    active_reservations: int
    processing_queue_size: int

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_connections: Dict[int, List[str]] = {}
    
    async def connect(self, websocket: WebSocket, connection_id: str, user_id: Optional[int] = None):
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = []
            self.user_connections[user_id].append(connection_id)
            
            # Register with notification service
            await notification_service.register_websocket(user_id, websocket)
        
        logger.info(f"WebSocket connected: {connection_id}, user: {user_id}")
    
    def disconnect(self, connection_id: str, user_id: Optional[int] = None):
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        
        if user_id and user_id in self.user_connections:
            if connection_id in self.user_connections[user_id]:
                self.user_connections[user_id].remove(connection_id)
            
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
                # Unregister from notification service
                asyncio.create_task(notification_service.unregister_websocket(user_id))
        
        logger.info(f"WebSocket disconnected: {connection_id}, user: {user_id}")
    
    async def send_personal_message(self, message: str, connection_id: str):
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.error(f"Failed to send message to {connection_id}: {e}")
                # Remove broken connection
                if connection_id in self.active_connections:
                    del self.active_connections[connection_id]
    
    async def broadcast(self, message: str, exclude_connections: Optional[List[str]] = None):
        if exclude_connections is None:
            exclude_connections = []
        
        tasks = []
        for connection_id, websocket in self.active_connections.items():
            if connection_id not in exclude_connections:
                tasks.append(self._safe_send(websocket, message, connection_id))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _safe_send(self, websocket: WebSocket, message: str, connection_id: str):
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Failed to send message to {connection_id}: {e}")
            # Remove broken connection
            if connection_id in self.active_connections:
                del self.active_connections[connection_id]

connection_manager = ConnectionManager()

# Initialize services
async def get_current_user(token: str = Depends(security)) -> User:
    """Get current authenticated user (simplified)"""
    # This would typically validate JWT token and return user
    # For demo purposes, returning a mock user
    return User(id=1, email="demo@example.com", full_name="Demo User")

# REST API Endpoints

@router.post("/reservations/request", response_model=ReservationResponseModel)
async def request_reservation(
    request: ReservationRequestModel,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    Request a parking reservation with priority queuing and concurrent handling
    """
    try:
        # Map string priority to enum
        priority_mapping = {
            "low": ReservationPriority.LOW,
            "normal": ReservationPriority.NORMAL,
            "high": ReservationPriority.HIGH,
            "vip": ReservationPriority.VIP,
            "emergency": ReservationPriority.EMERGENCY
        }
        
        priority = priority_mapping.get(request.priority.lower(), ReservationPriority.NORMAL)
        
        # Create reservation request
        reservation_request = ReservationRequest(
            request_id=str(uuid4()),
            user_id=request.user_id,
            vehicle_id=request.vehicle_id,
            parking_lot_id=request.parking_lot_id,
            start_time=request.start_time,
            end_time=request.end_time,
            priority=priority,
            preferred_spot_id=request.preferred_spot_id,
            requires_ev_charging=request.requires_ev_charging,
            requires_handicapped_access=request.requires_handicapped_access,
            special_requests=request.special_requests,
            max_wait_time_seconds=request.max_wait_time_seconds
        )
        
        # Submit to reservation manager
        result = await reservation_manager.request_reservation(reservation_request)
        
        # Estimate wait time based on queue position
        estimated_wait_time = None
        if result.queue_position:
            # Rough estimate: 30 seconds per position ahead
            estimated_wait_time = result.queue_position * 30
        
        return ReservationResponseModel(
            success=result.success,
            request_id=reservation_request.request_id,
            reservation_id=result.reservation_id,
            spot_id=result.spot_id,
            queue_position=result.queue_position,
            estimated_wait_time=estimated_wait_time,
            error_message=result.error_message
        )
        
    except Exception as e:
        logger.error(f"Failed to request reservation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/reservations/request/{request_id}")
async def get_reservation_request_status(
    request_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get status of a reservation request
    """
    try:
        status = await reservation_manager.get_request_status(request_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="Reservation request not found")
        
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get request status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/reservations/request/{request_id}")
async def cancel_reservation_request(
    request_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Cancel a pending reservation request
    """
    try:
        cancelled = await reservation_manager.cancel_reservation_request(request_id)
        
        if not cancelled:
            raise HTTPException(status_code=404, detail="Reservation request not found or cannot be cancelled")
        
        return {"success": True, "message": "Reservation request cancelled"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel request: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/parking-spots/status", response_model=Dict[str, Any])
async def update_spot_status(
    update: SpotStatusUpdateModel,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    Update parking spot status with event generation
    """
    try:
        # Map string status to enum
        status_mapping = {
            "available": SpotStatus.AVAILABLE,
            "occupied": SpotStatus.OCCUPIED,
            "reserved": SpotStatus.RESERVED,
            "out_of_order": SpotStatus.OUT_OF_ORDER,
            "maintenance": SpotStatus.MAINTENANCE
        }
        
        new_status = status_mapping.get(update.new_status.lower())
        if not new_status:
            raise HTTPException(status_code=400, detail="Invalid spot status")
        
        # Create command
        command = UpdateSpotStatusCommand(
            spot_id=update.spot_id,
            new_status=new_status,
            user_id=update.user_id,
            vehicle_id=update.vehicle_id,
            reason=update.reason
        )
        
        # Execute command
        result = await cqrs_service.execute_command(command)
        
        if result.status.value != "success":
            raise HTTPException(status_code=400, detail=result.error_message)
        
        return {
            "success": True,
            "command_id": result.command_id,
            "result": result.result,
            "events_generated": result.events_generated
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update spot status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/queue/status", response_model=QueueStatusModel)
async def get_queue_status(current_user: User = Depends(get_current_user)):
    """
    Get current reservation queue statistics
    """
    try:
        stats = await reservation_manager.get_queue_statistics()
        
        return QueueStatusModel(
            queue_size=stats.get("queue_size", 0),
            active_processing=stats.get("active_processing", 0),
            is_processing=stats.get("is_processing", False),
            average_wait_time=stats.get("average_wait_time")
        )
        
    except Exception as e:
        logger.error(f"Failed to get queue status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/events/statistics", response_model=EventStatisticsModel)
async def get_event_statistics(current_user: User = Depends(get_current_user)):
    """
    Get event processing statistics
    """
    try:
        stats = await event_service.get_event_statistics()
        queue_stats = await reservation_manager.get_queue_statistics()
        
        # Count active reservations
        async with get_db() as session:
            from sqlalchemy import select, func
            
            active_reservations_result = await session.execute(
                select(func.count(Reservation.id)).where(
                    Reservation.status.in_([
                        ReservationStatus.CONFIRMED,
                        ReservationStatus.ACTIVE
                    ])
                )
            )
            active_reservations = active_reservations_result.scalar() or 0
        
        return EventStatisticsModel(
            total_events_today=stats.get("daily_total", 0),
            events_by_type=stats,
            events_last_hour=0,  # Would need to implement hourly tracking
            active_reservations=active_reservations,
            processing_queue_size=queue_stats.get("queue_size", 0)
        )
        
    except Exception as e:
        logger.error(f"Failed to get event statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/events/publish")
async def publish_custom_event(
    event_data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    Publish a custom system event (admin only)
    """
    try:
        # This would typically require admin permissions
        
        event_type_str = event_data.get("event_type")
        if not event_type_str:
            raise HTTPException(status_code=400, detail="event_type is required")
        
        try:
            event_type = EventType(event_type_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid event_type")
        
        # Publish event
        event = await event_service.publish_event(
            event_type=event_type,
            aggregate_type=event_data.get("aggregate_type", "system"),
            aggregate_id=event_data.get("aggregate_id", "manual"),
            event_data=event_data.get("data", {}),
            priority=EventPriority.NORMAL
        )
        
        return {
            "success": True,
            "event_id": event.event_id,
            "message": "Event published successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to publish custom event: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket endpoints

@router.websocket("/ws/events")
async def websocket_event_stream(
    websocket: WebSocket,
    user_id: Optional[int] = None,
    parking_lot_id: Optional[int] = None
):
    """
    WebSocket endpoint for real-time event streaming
    """
    connection_id = str(uuid4())
    
    try:
        await connection_manager.connect(websocket, connection_id, user_id)
        
        # Send welcome message
        await websocket.send_text(json.dumps({
            "type": "connection",
            "message": "Connected to event stream",
            "connection_id": connection_id
        }))
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for client messages with timeout
                message = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                
                # Handle client messages (ping, filter updates, etc.)
                try:
                    data = json.loads(message)
                    await handle_websocket_message(websocket, data, user_id)
                except json.JSONDecodeError:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON message"
                    }))
                
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                await websocket.send_text(json.dumps({
                    "type": "ping",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }))
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        connection_manager.disconnect(connection_id, user_id)

@router.websocket("/ws/reservations/{user_id}")
async def websocket_user_reservations(websocket: WebSocket, user_id: int):
    """
    WebSocket endpoint for user-specific reservation updates
    """
    connection_id = str(uuid4())
    
    try:
        await connection_manager.connect(websocket, connection_id, user_id)
        
        # Send current user reservations
        async with get_db() as session:
            from sqlalchemy import select
            
            result = await session.execute(
                select(Reservation).where(
                    and_(
                        Reservation.user_id == user_id,
                        Reservation.status.in_([
                            ReservationStatus.PENDING,
                            ReservationStatus.CONFIRMED,
                            ReservationStatus.ACTIVE
                        ])
                    )
                )
            )
            reservations = result.scalars().all()
            
            await websocket.send_text(json.dumps({
                "type": "user_reservations",
                "data": [
                    {
                        "id": res.id,
                        "reservation_number": res.reservation_number,
                        "status": res.status.value,
                        "start_time": res.start_time.isoformat(),
                        "end_time": res.end_time.isoformat(),
                        "parking_spot_id": res.parking_spot_id
                    }
                    for res in reservations
                ]
            }))
        
        # Keep connection alive
        while True:
            await asyncio.sleep(30)
            await websocket.send_text(json.dumps({
                "type": "heartbeat",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }))
            
    except WebSocketDisconnect:
        logger.info(f"User WebSocket disconnected: {user_id}")
    except Exception as e:
        logger.error(f"User WebSocket error: {e}")
    finally:
        connection_manager.disconnect(connection_id, user_id)

async def handle_websocket_message(websocket: WebSocket, data: Dict[str, Any], user_id: Optional[int]):
    """Handle incoming WebSocket messages"""
    try:
        message_type = data.get("type")
        
        if message_type == "ping":
            await websocket.send_text(json.dumps({
                "type": "pong",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }))
        
        elif message_type == "subscribe":
            # Handle subscription to specific event types
            event_types = data.get("event_types", [])
            await websocket.send_text(json.dumps({
                "type": "subscription_confirmed",
                "event_types": event_types
            }))
        
        elif message_type == "unsubscribe":
            # Handle unsubscription
            await websocket.send_text(json.dumps({
                "type": "unsubscription_confirmed"
            }))
        
    except Exception as e:
        logger.error(f"Failed to handle WebSocket message: {e}")
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": "Failed to process message"
        }))

# Background task to initialize services
async def initialize_event_system():
    """Initialize the event system and start background processing"""
    try:
        # Initialize event service
        await event_service.initialize()
        
        # Register event handlers
        event_service.register_event_handler(EventType.SPOT_STATUS_CHANGED, system_event_handler.handle_spot_status_change)
        event_service.register_event_handler(EventType.SPOT_OCCUPIED, system_event_handler.handle_spot_status_change)
        event_service.register_event_handler(EventType.SPOT_VACATED, system_event_handler.handle_spot_status_change)
        event_service.register_event_handler(EventType.RESERVATION_CREATED, system_event_handler.handle_reservation_created)
        event_service.register_event_handler(EventType.CAPACITY_THRESHOLD, system_event_handler.handle_capacity_threshold)
        event_service.register_event_handler(EventType.USER_ARRIVED, system_event_handler.handle_user_arrival)
        
        # Initialize CQRS service
        from app.services.cqrs_service import cqrs_service
        global cqrs_service
        
        # Initialize reservation manager with CQRS service
        global reservation_manager
        reservation_manager.cqrs_service = cqrs_service
        
        # Start reservation processing
        await reservation_manager.start_processing()
        
        logger.info("Event system initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize event system: {e}")
        raise

# Startup event handler would call this
# initialize_event_system()
