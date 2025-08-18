"""
Advanced Reservation Service
Implements concurrent reservation handling, PostgreSQL row-level locking,
timeout management, double-booking prevention, and optimistic concurrency control.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
import heapq
from contextlib import asynccontextmanager

from sqlalchemy import select, update, delete, and_, or_, text, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.dialects.postgresql import insert

from app.db.database import get_db
from app.db.redis import get_redis_client
from app.models.parking_spot import ParkingSpot, SpotStatus, SpotType
from app.models.reservation import Reservation, ReservationStatus, ReservationType
from app.models.parking_lot import ParkingLot
from app.models.user import User
from app.models.vehicle import Vehicle
from app.services.event_service import EventService, EventType, EventPriority, event_service
from app.services.cqrs_service import CQRSService, CreateReservationCommand, ConfirmReservationCommand

logger = logging.getLogger(__name__)

class ReservationPriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    VIP = 4
    EMERGENCY = 5

class LockTimeout(Exception):
    """Raised when lock acquisition times out"""
    pass

class ReservationConflict(Exception):
    """Raised when reservation conflicts with existing booking"""
    pass

class InsufficientCapacity(Exception):
    """Raised when no spots available"""
    pass

@dataclass
class ReservationRequest:
    """Priority queue item for reservation requests"""
    request_id: str
    user_id: int
    vehicle_id: int
    parking_lot_id: int
    start_time: datetime
    end_time: datetime
    priority: ReservationPriority
    preferred_spot_id: Optional[int] = None
    requires_ev_charging: bool = False
    requires_handicapped_access: bool = False
    special_requests: Optional[str] = None
    max_wait_time_seconds: int = 300  # 5 minutes default
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
    
    def __lt__(self, other):
        """Priority queue comparison - higher priority first"""
        return self.priority.value > other.priority.value

@dataclass
class ReservationResult:
    """Result of reservation attempt"""
    success: bool
    reservation_id: Optional[int] = None
    spot_id: Optional[int] = None
    error_message: Optional[str] = None
    wait_time_seconds: Optional[float] = None
    queue_position: Optional[int] = None

class DistributedLock:
    """Distributed lock using Redis"""
    
    def __init__(self, redis_client, key: str, timeout: int = 30, retry_delay: float = 0.1):
        self.redis_client = redis_client
        self.key = f"lock:{key}"
        self.timeout = timeout
        self.retry_delay = retry_delay
        self.token = str(uuid.uuid4())
    
    async def __aenter__(self):
        return await self.acquire()
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.release()
    
    async def acquire(self) -> bool:
        """Acquire distributed lock with timeout"""
        end_time = datetime.now(timezone.utc) + timedelta(seconds=self.timeout)
        
        while datetime.now(timezone.utc) < end_time:
            if await self.redis_client.set(self.key, self.token, nx=True, ex=self.timeout):
                return True
            await asyncio.sleep(self.retry_delay)
        
        raise LockTimeout(f"Could not acquire lock for {self.key}")
    
    async def release(self):
        """Release distributed lock"""
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        await self.redis_client.eval(lua_script, 1, self.key, self.token)

class ReservationQueue:
    """Priority queue for reservation requests"""
    
    def __init__(self):
        self.queue = []
        self.requests = {}  # request_id -> ReservationRequest
        self.lock = asyncio.Lock()
    
    async def add_request(self, request: ReservationRequest) -> int:
        """Add reservation request to priority queue"""
        async with self.lock:
            heapq.heappush(self.queue, request)
            self.requests[request.request_id] = request
            return len(self.queue)
    
    async def get_next_request(self) -> Optional[ReservationRequest]:
        """Get next highest priority request"""
        async with self.lock:
            if self.queue:
                request = heapq.heappop(self.queue)
                del self.requests[request.request_id]
                return request
            return None
    
    async def remove_request(self, request_id: str) -> bool:
        """Remove specific request from queue"""
        async with self.lock:
            if request_id in self.requests:
                request = self.requests[request_id]
                try:
                    self.queue.remove(request)
                    heapq.heapify(self.queue)
                    del self.requests[request_id]
                    return True
                except ValueError:
                    pass
            return False
    
    async def get_queue_position(self, request_id: str) -> Optional[int]:
        """Get position of request in queue"""
        async with self.lock:
            if request_id not in self.requests:
                return None
            
            # Find position in priority queue
            request = self.requests[request_id]
            position = 1
            for queued_request in self.queue:
                if queued_request.request_id == request_id:
                    return position
                if queued_request.priority.value > request.priority.value:
                    position += 1
            
            return position
    
    async def get_queue_size(self) -> int:
        """Get current queue size"""
        async with self.lock:
            return len(self.queue)

class ConcurrentReservationManager:
    """Manages concurrent reservation requests with sophisticated locking and conflict resolution"""
    
    def __init__(self, event_service: EventService, cqrs_service: CQRSService):
        self.event_service = event_service
        self.cqrs_service = cqrs_service
        self.redis_client = get_redis_client()
        self.reservation_queue = ReservationQueue()
        self.processing_tasks = {}
        self.executor = ThreadPoolExecutor(max_workers=20)
        self.is_processing = False
    
    async def start_processing(self):
        """Start background processing of reservation queue"""
        if self.is_processing:
            return
        
        self.is_processing = True
        asyncio.create_task(self._process_reservation_queue())
        logger.info("Started reservation queue processing")
    
    async def stop_processing(self):
        """Stop background processing"""
        self.is_processing = False
        
        # Cancel any ongoing tasks
        for task in self.processing_tasks.values():
            task.cancel()
        
        # Wait for tasks to complete
        if self.processing_tasks:
            await asyncio.gather(*self.processing_tasks.values(), return_exceptions=True)
        
        self.executor.shutdown(wait=True)
        logger.info("Stopped reservation queue processing")
    
    async def request_reservation(self, request: ReservationRequest) -> ReservationResult:
        """Request a reservation with priority queuing"""
        try:
            # Validate request
            if not self._validate_request(request):
                return ReservationResult(
                    success=False,
                    error_message="Invalid reservation request parameters"
                )
            
            # Check for immediate availability if high priority
            if request.priority.value >= ReservationPriority.HIGH.value:
                result = await self._try_immediate_reservation(request)
                if result.success:
                    return result
            
            # Add to priority queue
            queue_position = await self.reservation_queue.add_request(request)
            
            # Store request metadata in Redis
            await self.redis_client.setex(
                f"reservation_request:{request.request_id}",
                request.max_wait_time_seconds,
                json.dumps({
                    "user_id": request.user_id,
                    "created_at": request.created_at.isoformat(),
                    "priority": request.priority.value,
                    "status": "queued"
                })
            )
            
            return ReservationResult(
                success=False,  # Not yet processed
                queue_position=queue_position,
                wait_time_seconds=0
            )
            
        except Exception as e:
            logger.error(f"Failed to request reservation: {e}")
            return ReservationResult(
                success=False,
                error_message=str(e)
            )
    
    async def cancel_reservation_request(self, request_id: str) -> bool:
        """Cancel a pending reservation request"""
        try:
            # Remove from queue
            removed = await self.reservation_queue.remove_request(request_id)
            
            # Clean up Redis
            await self.redis_client.delete(f"reservation_request:{request_id}")
            
            return removed
            
        except Exception as e:
            logger.error(f"Failed to cancel reservation request {request_id}: {e}")
            return False
    
    async def get_request_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get status of reservation request"""
        try:
            # Check Redis for request data
            request_data = await self.redis_client.get(f"reservation_request:{request_id}")
            if not request_data:
                return None
            
            data = json.loads(request_data)
            
            # Get queue position
            queue_position = await self.reservation_queue.get_queue_position(request_id)
            
            return {
                "request_id": request_id,
                "status": data.get("status", "unknown"),
                "queue_position": queue_position,
                "created_at": data.get("created_at"),
                "priority": data.get("priority")
            }
            
        except Exception as e:
            logger.error(f"Failed to get request status for {request_id}: {e}")
            return None
    
    def _validate_request(self, request: ReservationRequest) -> bool:
        """Validate reservation request"""
        now = datetime.now(timezone.utc)
        
        # Check time validity
        if request.start_time <= now:
            return False
        
        if request.start_time >= request.end_time:
            return False
        
        # Check duration (max 24 hours)
        if (request.end_time - request.start_time).total_seconds() > 24 * 3600:
            return False
        
        return True
    
    async def _try_immediate_reservation(self, request: ReservationRequest) -> ReservationResult:
        """Try to make immediate reservation for high priority requests"""
        try:
            async with get_db() as session:
                # Use row-level locking to prevent conflicts
                result = await self._find_and_lock_available_spot(
                    session, request, lock_timeout=5
                )
                
                if result.success:
                    # Create reservation immediately
                    command = CreateReservationCommand(
                        user_id=request.user_id,
                        vehicle_id=request.vehicle_id,
                        parking_lot_id=request.parking_lot_id,
                        start_time=request.start_time,
                        end_time=request.end_time,
                        parking_spot_id=result.spot_id,
                        requires_ev_charging=request.requires_ev_charging,
                        requires_handicapped_access=request.requires_handicapped_access,
                        special_requests=request.special_requests
                    )
                    
                    command_result = await self.cqrs_service.execute_command(command)
                    
                    if command_result.status.value == "success":
                        return ReservationResult(
                            success=True,
                            reservation_id=command_result.result["reservation_id"],
                            spot_id=result.spot_id
                        )
                
                return result
                
        except Exception as e:
            logger.error(f"Immediate reservation failed: {e}")
            return ReservationResult(
                success=False,
                error_message=str(e)
            )
    
    async def _process_reservation_queue(self):
        """Background task to process reservation queue"""
        while self.is_processing:
            try:
                request = await self.reservation_queue.get_next_request()
                if not request:
                    await asyncio.sleep(1)  # No requests, wait
                    continue
                
                # Check if request has expired
                now = datetime.now(timezone.utc)
                if (now - request.created_at).total_seconds() > request.max_wait_time_seconds:
                    await self._handle_expired_request(request)
                    continue
                
                # Process request
                task = asyncio.create_task(self._process_single_request(request))
                self.processing_tasks[request.request_id] = task
                
                # Don't await here to allow concurrent processing
                
            except Exception as e:
                logger.error(f"Error in reservation queue processing: {e}")
                await asyncio.sleep(1)
    
    async def _process_single_request(self, request: ReservationRequest):
        """Process a single reservation request"""
        try:
            start_time = datetime.now(timezone.utc)
            
            # Update status to processing
            await self.redis_client.setex(
                f"reservation_request:{request.request_id}",
                request.max_wait_time_seconds,
                json.dumps({
                    "user_id": request.user_id,
                    "created_at": request.created_at.isoformat(),
                    "priority": request.priority.value,
                    "status": "processing"
                })
            )
            
            async with get_db() as session:
                result = await self._find_and_lock_available_spot(
                    session, request, lock_timeout=30
                )
                
                if result.success:
                    # Create reservation
                    command = CreateReservationCommand(
                        user_id=request.user_id,
                        vehicle_id=request.vehicle_id,
                        parking_lot_id=request.parking_lot_id,
                        start_time=request.start_time,
                        end_time=request.end_time,
                        parking_spot_id=result.spot_id,
                        requires_ev_charging=request.requires_ev_charging,
                        requires_handicapped_access=request.requires_handicapped_access,
                        special_requests=request.special_requests
                    )
                    
                    command_result = await self.cqrs_service.execute_command(command)
                    
                    if command_result.status.value == "success":
                        # Update status to completed
                        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
                        
                        await self.redis_client.setex(
                            f"reservation_request:{request.request_id}",
                            3600,  # Keep result for 1 hour
                            json.dumps({
                                "user_id": request.user_id,
                                "created_at": request.created_at.isoformat(),
                                "priority": request.priority.value,
                                "status": "completed",
                                "reservation_id": command_result.result["reservation_id"],
                                "spot_id": result.spot_id,
                                "processing_time": processing_time
                            })
                        )
                        
                        # Send notification event
                        await self.event_service.publish_event(
                            event_type=EventType.RESERVATION_CREATED,
                            aggregate_type="reservation_request",
                            aggregate_id=request.request_id,
                            event_data={
                                "request_id": request.request_id,
                                "reservation_id": command_result.result["reservation_id"],
                                "user_id": request.user_id,
                                "spot_id": result.spot_id,
                                "processing_time": processing_time
                            },
                            priority=EventPriority.HIGH
                        )
                    else:
                        await self._handle_failed_request(request, command_result.error_message)
                else:
                    await self._handle_failed_request(request, result.error_message)
        
        except Exception as e:
            logger.error(f"Failed to process reservation request {request.request_id}: {e}")
            await self._handle_failed_request(request, str(e))
        
        finally:
            # Clean up task reference
            if request.request_id in self.processing_tasks:
                del self.processing_tasks[request.request_id]
    
    async def _find_and_lock_available_spot(self, session: AsyncSession, 
                                          request: ReservationRequest,
                                          lock_timeout: int = 30) -> ReservationResult:
        """Find and lock an available parking spot with sophisticated conflict resolution"""
        try:
            # Use distributed lock for spot allocation
            lock_key = f"spot_allocation:{request.parking_lot_id}"
            
            async with DistributedLock(self.redis_client, lock_key, timeout=lock_timeout):
                # Start transaction with explicit locking
                await session.execute(text("BEGIN"))
                
                # Build base query for available spots
                base_query = select(ParkingSpot).where(
                    and_(
                        ParkingSpot.parking_lot_id == request.parking_lot_id,
                        ParkingSpot.status == SpotStatus.AVAILABLE,
                        ParkingSpot.is_active == True,
                        ParkingSpot.is_reservable == True
                    )
                )
                
                # Apply specific requirements
                if request.requires_ev_charging:
                    base_query = base_query.where(ParkingSpot.has_ev_charging == True)
                
                if request.requires_handicapped_access:
                    base_query = base_query.where(ParkingSpot.is_handicapped_accessible == True)
                
                # Add row-level locking to prevent concurrent modifications
                base_query = base_query.with_for_update(skip_locked=True)
                
                # Try preferred spot first if specified
                if request.preferred_spot_id:
                    preferred_query = base_query.where(ParkingSpot.id == request.preferred_spot_id)
                    result = await session.execute(preferred_query)
                    preferred_spot = result.scalar_one_or_none()
                    
                    if preferred_spot:
                        # Check for time conflicts
                        if await self._check_spot_availability(
                            session, preferred_spot.id, request.start_time, request.end_time
                        ):
                            await session.commit()
                            return ReservationResult(
                                success=True,
                                spot_id=preferred_spot.id
                            )
                
                # Find any available spot
                result = await session.execute(base_query.limit(10))  # Limit for performance
                available_spots = result.scalars().all()
                
                if not available_spots:
                    await session.rollback()
                    return ReservationResult(
                        success=False,
                        error_message="No available spots matching requirements"
                    )
                
                # Check each spot for time conflicts
                for spot in available_spots:
                    if await self._check_spot_availability(
                        session, spot.id, request.start_time, request.end_time
                    ):
                        await session.commit()
                        return ReservationResult(
                            success=True,
                            spot_id=spot.id
                        )
                
                await session.rollback()
                return ReservationResult(
                    success=False,
                    error_message="No spots available for the requested time period"
                )
        
        except LockTimeout:
            return ReservationResult(
                success=False,
                error_message="Could not acquire lock for spot allocation"
            )
        except Exception as e:
            await session.rollback()
            logger.error(f"Error finding available spot: {e}")
            return ReservationResult(
                success=False,
                error_message=str(e)
            )
    
    async def _check_spot_availability(self, session: AsyncSession, spot_id: int,
                                     start_time: datetime, end_time: datetime) -> bool:
        """Check if spot is available for the given time period"""
        try:
            # Check for conflicting reservations using optimistic concurrency control
            conflict_query = select(func.count(Reservation.id)).where(
                and_(
                    Reservation.parking_spot_id == spot_id,
                    Reservation.status.in_([
                        ReservationStatus.CONFIRMED,
                        ReservationStatus.ACTIVE,
                        ReservationStatus.PENDING  # Include pending to prevent double booking
                    ]),
                    or_(
                        # Overlap conditions
                        and_(
                            Reservation.start_time <= start_time,
                            Reservation.end_time > start_time
                        ),
                        and_(
                            Reservation.start_time < end_time,
                            Reservation.end_time >= end_time
                        ),
                        and_(
                            Reservation.start_time >= start_time,
                            Reservation.end_time <= end_time
                        )
                    )
                )
            )
            
            result = await session.execute(conflict_query)
            conflict_count = result.scalar()
            
            return conflict_count == 0
            
        except Exception as e:
            logger.error(f"Error checking spot availability: {e}")
            return False
    
    async def _handle_expired_request(self, request: ReservationRequest):
        """Handle expired reservation request"""
        try:
            await self.redis_client.setex(
                f"reservation_request:{request.request_id}",
                3600,
                json.dumps({
                    "user_id": request.user_id,
                    "created_at": request.created_at.isoformat(),
                    "priority": request.priority.value,
                    "status": "expired",
                    "error_message": "Request expired due to timeout"
                })
            )
            
            # Send notification
            await self.event_service.publish_event(
                event_type=EventType.RESERVATION_EXPIRED,
                aggregate_type="reservation_request",
                aggregate_id=request.request_id,
                event_data={
                    "request_id": request.request_id,
                    "user_id": request.user_id,
                    "reason": "timeout"
                },
                priority=EventPriority.NORMAL
            )
            
        except Exception as e:
            logger.error(f"Failed to handle expired request {request.request_id}: {e}")
    
    async def _handle_failed_request(self, request: ReservationRequest, error_message: str):
        """Handle failed reservation request"""
        try:
            await self.redis_client.setex(
                f"reservation_request:{request.request_id}",
                3600,
                json.dumps({
                    "user_id": request.user_id,
                    "created_at": request.created_at.isoformat(),
                    "priority": request.priority.value,
                    "status": "failed",
                    "error_message": error_message
                })
            )
            
        except Exception as e:
            logger.error(f"Failed to handle failed request {request.request_id}: {e}")
    
    async def get_queue_statistics(self) -> Dict[str, Any]:
        """Get reservation queue statistics"""
        try:
            queue_size = await self.reservation_queue.get_queue_size()
            active_tasks = len(self.processing_tasks)
            
            return {
                "queue_size": queue_size,
                "active_processing": active_tasks,
                "is_processing": self.is_processing
            }
            
        except Exception as e:
            logger.error(f"Failed to get queue statistics: {e}")
            return {}

# Global reservation manager instance
reservation_manager = ConcurrentReservationManager(event_service, None)  # Will be initialized properly
