"""
CQRS (Command Query Responsibility Segregation) Service
Implements read/write separation for parking management system
"""

import asyncio
import json
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union, Generic, TypeVar
from enum import Enum

from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.db.redis import get_redis_client
from app.models.parking_spot import ParkingSpot, SpotStatus
from app.models.reservation import Reservation, ReservationStatus
from app.models.parking_lot import ParkingLot
from app.models.user import User
from app.models.vehicle import Vehicle
from app.services.event_service import EventService, EventType, EventPriority

logger = logging.getLogger(__name__)

T = TypeVar('T')

class CommandStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class CommandResult:
    """Result of command execution"""
    command_id: str
    status: CommandStatus
    result: Optional[Any] = None
    error_message: Optional[str] = None
    execution_time_ms: Optional[int] = None
    events_generated: List[str] = None

    def __post_init__(self):
        if self.events_generated is None:
            self.events_generated = []

class Command(ABC):
    """Base command interface"""
    
    def __init__(self, command_id: str = None, correlation_id: str = None):
        self.command_id = command_id or str(uuid.uuid4())
        self.correlation_id = correlation_id
        self.timestamp = datetime.now(timezone.utc)
    
    @abstractmethod
    async def execute(self, session: AsyncSession, event_service: EventService) -> CommandResult:
        """Execute the command"""
        pass
    
    @abstractmethod
    def validate(self) -> bool:
        """Validate command parameters"""
        pass

class Query(ABC):
    """Base query interface"""
    
    @abstractmethod
    async def execute(self, session: AsyncSession) -> Any:
        """Execute the query"""
        pass

# Command Implementations

@dataclass
class CreateReservationCommand(Command):
    """Command to create a new reservation"""
    user_id: int
    vehicle_id: int
    parking_lot_id: int
    start_time: datetime
    end_time: datetime
    parking_spot_id: Optional[int] = None
    requires_ev_charging: bool = False
    requires_handicapped_access: bool = False
    special_requests: Optional[str] = None
    
    def validate(self) -> bool:
        """Validate reservation parameters"""
        if self.start_time >= self.end_time:
            return False
        if self.start_time < datetime.now(timezone.utc):
            return False
        return True
    
    async def execute(self, session: AsyncSession, event_service: EventService) -> CommandResult:
        """Execute reservation creation"""
        import uuid
        from app.models.reservation import ReservationType
        
        start_time = datetime.now(timezone.utc)
        
        try:
            # Validate command
            if not self.validate():
                return CommandResult(
                    command_id=self.command_id,
                    status=CommandStatus.FAILED,
                    error_message="Invalid reservation parameters"
                )
            
            # Generate reservation number and confirmation code
            reservation_number = f"RES-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
            confirmation_code = str(uuid.uuid4())[:8].upper()
            
            # Create reservation
            reservation = Reservation(
                user_id=self.user_id,
                vehicle_id=self.vehicle_id,
                parking_lot_id=self.parking_lot_id,
                parking_spot_id=self.parking_spot_id,
                reservation_number=reservation_number,
                confirmation_code=confirmation_code,
                reservation_type=ReservationType.SCHEDULED,
                start_time=self.start_time,
                end_time=self.end_time,
                requires_ev_charging=self.requires_ev_charging,
                requires_handicapped_access=self.requires_handicapped_access,
                special_requests=self.special_requests,
                status=ReservationStatus.PENDING
            )
            
            session.add(reservation)
            await session.flush()  # Get the ID
            
            # Generate event
            event = await event_service.publish_event(
                event_type=EventType.RESERVATION_CREATED,
                aggregate_type="reservation",
                aggregate_id=str(reservation.id),
                event_data={
                    "reservation_id": reservation.id,
                    "user_id": self.user_id,
                    "vehicle_id": self.vehicle_id,
                    "parking_lot_id": self.parking_lot_id,
                    "parking_spot_id": self.parking_spot_id,
                    "start_time": self.start_time.isoformat(),
                    "end_time": self.end_time.isoformat(),
                    "reservation_number": reservation_number,
                    "confirmation_code": confirmation_code
                },
                correlation_id=self.correlation_id
            )
            
            await session.commit()
            
            execution_time = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            
            return CommandResult(
                command_id=self.command_id,
                status=CommandStatus.SUCCESS,
                result={
                    "reservation_id": reservation.id,
                    "reservation_number": reservation_number,
                    "confirmation_code": confirmation_code
                },
                execution_time_ms=execution_time,
                events_generated=[event.event_id]
            )
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to create reservation: {e}")
            
            execution_time = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            
            return CommandResult(
                command_id=self.command_id,
                status=CommandStatus.FAILED,
                error_message=str(e),
                execution_time_ms=execution_time
            )

@dataclass
class UpdateSpotStatusCommand(Command):
    """Command to update parking spot status"""
    spot_id: int
    new_status: SpotStatus
    user_id: Optional[int] = None
    vehicle_id: Optional[int] = None
    reason: Optional[str] = None
    
    def validate(self) -> bool:
        return self.spot_id > 0 and isinstance(self.new_status, SpotStatus)
    
    async def execute(self, session: AsyncSession, event_service: EventService) -> CommandResult:
        start_time = datetime.now(timezone.utc)
        
        try:
            if not self.validate():
                return CommandResult(
                    command_id=self.command_id,
                    status=CommandStatus.FAILED,
                    error_message="Invalid spot status update parameters"
                )
            
            # Get current spot
            result = await session.execute(
                select(ParkingSpot).where(ParkingSpot.id == self.spot_id)
            )
            spot = result.scalar_one_or_none()
            
            if not spot:
                return CommandResult(
                    command_id=self.command_id,
                    status=CommandStatus.FAILED,
                    error_message=f"Parking spot {self.spot_id} not found"
                )
            
            old_status = spot.status
            
            # Update spot status
            spot.status = self.new_status
            spot.status_changed_at = datetime.now(timezone.utc)
            
            if self.new_status == SpotStatus.OCCUPIED:
                spot.current_vehicle_id = self.vehicle_id
                spot.occupied_since = datetime.now(timezone.utc)
            elif self.new_status == SpotStatus.AVAILABLE:
                if spot.occupied_since:
                    # Calculate occupancy time
                    occupancy_time = (datetime.now(timezone.utc) - spot.occupied_since).total_seconds() / 60
                    spot.total_occupancy_time += int(occupancy_time)
                
                spot.current_vehicle_id = None
                spot.occupied_since = None
                spot.last_occupied_at = datetime.now(timezone.utc)
            
            # Generate appropriate event
            if self.new_status == SpotStatus.OCCUPIED:
                event_type = EventType.SPOT_OCCUPIED
            elif self.new_status == SpotStatus.AVAILABLE and old_status == SpotStatus.OCCUPIED:
                event_type = EventType.SPOT_VACATED
            else:
                event_type = EventType.SPOT_STATUS_CHANGED
            
            event = await event_service.publish_event(
                event_type=event_type,
                aggregate_type="parking_spot",
                aggregate_id=str(self.spot_id),
                event_data={
                    "spot_id": self.spot_id,
                    "old_status": old_status.value,
                    "new_status": self.new_status.value,
                    "user_id": self.user_id,
                    "vehicle_id": self.vehicle_id,
                    "reason": self.reason,
                    "parking_lot_id": spot.parking_lot_id
                },
                correlation_id=self.correlation_id
            )
            
            await session.commit()
            
            execution_time = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            
            return CommandResult(
                command_id=self.command_id,
                status=CommandStatus.SUCCESS,
                result={
                    "spot_id": self.spot_id,
                    "old_status": old_status.value,
                    "new_status": self.new_status.value
                },
                execution_time_ms=execution_time,
                events_generated=[event.event_id]
            )
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to update spot status: {e}")
            
            execution_time = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            
            return CommandResult(
                command_id=self.command_id,
                status=CommandStatus.FAILED,
                error_message=str(e),
                execution_time_ms=execution_time
            )

@dataclass
class ConfirmReservationCommand(Command):
    """Command to confirm a reservation after payment"""
    reservation_id: int
    payment_id: Optional[int] = None
    
    def validate(self) -> bool:
        return self.reservation_id > 0
    
    async def execute(self, session: AsyncSession, event_service: EventService) -> CommandResult:
        start_time = datetime.now(timezone.utc)
        
        try:
            if not self.validate():
                return CommandResult(
                    command_id=self.command_id,
                    status=CommandStatus.FAILED,
                    error_message="Invalid reservation confirmation parameters"
                )
            
            # Get reservation
            result = await session.execute(
                select(Reservation).where(Reservation.id == self.reservation_id)
            )
            reservation = result.scalar_one_or_none()
            
            if not reservation:
                return CommandResult(
                    command_id=self.command_id,
                    status=CommandStatus.FAILED,
                    error_message=f"Reservation {self.reservation_id} not found"
                )
            
            if reservation.status != ReservationStatus.PENDING:
                return CommandResult(
                    command_id=self.command_id,
                    status=CommandStatus.FAILED,
                    error_message=f"Reservation {self.reservation_id} is not in pending status"
                )
            
            # Update reservation status
            reservation.status = ReservationStatus.CONFIRMED
            reservation.confirmed_at = datetime.now(timezone.utc)
            reservation.is_paid = True
            
            # If specific spot assigned, mark it as reserved
            if reservation.parking_spot_id:
                spot_result = await session.execute(
                    select(ParkingSpot).where(ParkingSpot.id == reservation.parking_spot_id)
                )
                spot = spot_result.scalar_one_or_none()
                if spot and spot.status == SpotStatus.AVAILABLE:
                    spot.status = SpotStatus.RESERVED
                    spot.status_changed_at = datetime.now(timezone.utc)
            
            # Generate events
            events = []
            
            # Reservation confirmed event
            confirm_event = await event_service.publish_event(
                event_type=EventType.RESERVATION_CONFIRMED,
                aggregate_type="reservation",
                aggregate_id=str(self.reservation_id),
                event_data={
                    "reservation_id": self.reservation_id,
                    "payment_id": self.payment_id,
                    "confirmed_at": reservation.confirmed_at.isoformat(),
                    "parking_spot_id": reservation.parking_spot_id
                },
                correlation_id=self.correlation_id
            )
            events.append(confirm_event.event_id)
            
            # Spot reserved event if applicable
            if reservation.parking_spot_id:
                spot_event = await event_service.publish_event(
                    event_type=EventType.SPOT_RESERVED,
                    aggregate_type="parking_spot",
                    aggregate_id=str(reservation.parking_spot_id),
                    event_data={
                        "spot_id": reservation.parking_spot_id,
                        "reservation_id": self.reservation_id,
                        "user_id": reservation.user_id,
                        "start_time": reservation.start_time.isoformat(),
                        "end_time": reservation.end_time.isoformat()
                    },
                    correlation_id=self.correlation_id
                )
                events.append(spot_event.event_id)
            
            await session.commit()
            
            execution_time = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            
            return CommandResult(
                command_id=self.command_id,
                status=CommandStatus.SUCCESS,
                result={
                    "reservation_id": self.reservation_id,
                    "status": "confirmed",
                    "confirmed_at": reservation.confirmed_at.isoformat()
                },
                execution_time_ms=execution_time,
                events_generated=events
            )
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to confirm reservation: {e}")
            
            execution_time = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            
            return CommandResult(
                command_id=self.command_id,
                status=CommandStatus.FAILED,
                error_message=str(e),
                execution_time_ms=execution_time
            )

# Query Implementations

class GetAvailableSpotsQuery(Query):
    """Query to get available parking spots"""
    
    def __init__(self, parking_lot_id: Optional[int] = None, 
                 requires_ev_charging: bool = False,
                 requires_handicapped_access: bool = False,
                 start_time: Optional[datetime] = None,
                 end_time: Optional[datetime] = None):
        self.parking_lot_id = parking_lot_id
        self.requires_ev_charging = requires_ev_charging
        self.requires_handicapped_access = requires_handicapped_access
        self.start_time = start_time
        self.end_time = end_time
    
    async def execute(self, session: AsyncSession) -> List[Dict[str, Any]]:
        """Get available spots with filters"""
        query = select(ParkingSpot).where(
            and_(
                ParkingSpot.status == SpotStatus.AVAILABLE,
                ParkingSpot.is_active == True,
                ParkingSpot.is_reservable == True
            )
        )
        
        # Apply filters
        if self.parking_lot_id:
            query = query.where(ParkingSpot.parking_lot_id == self.parking_lot_id)
        
        if self.requires_ev_charging:
            query = query.where(ParkingSpot.has_ev_charging == True)
        
        if self.requires_handicapped_access:
            query = query.where(ParkingSpot.is_handicapped_accessible == True)
        
        # Include parking lot information
        query = query.options(selectinload(ParkingSpot.parking_lot))
        
        result = await session.execute(query)
        spots = result.scalars().all()
        
        # If time range specified, check for conflicting reservations
        if self.start_time and self.end_time:
            available_spots = []
            for spot in spots:
                conflicts = await session.execute(
                    select(Reservation).where(
                        and_(
                            Reservation.parking_spot_id == spot.id,
                            Reservation.status.in_([
                                ReservationStatus.CONFIRMED,
                                ReservationStatus.ACTIVE
                            ]),
                            or_(
                                and_(
                                    Reservation.start_time <= self.start_time,
                                    Reservation.end_time > self.start_time
                                ),
                                and_(
                                    Reservation.start_time < self.end_time,
                                    Reservation.end_time >= self.end_time
                                ),
                                and_(
                                    Reservation.start_time >= self.start_time,
                                    Reservation.end_time <= self.end_time
                                )
                            )
                        )
                    )
                )
                
                if not conflicts.scalars().first():
                    available_spots.append(spot)
            
            spots = available_spots
        
        return [
            {
                "id": spot.id,
                "spot_number": spot.spot_number,
                "spot_type": spot.spot_type.value,
                "floor": spot.floor,
                "section": spot.section,
                "has_ev_charging": spot.has_ev_charging,
                "is_handicapped_accessible": spot.is_handicapped_accessible,
                "is_covered": spot.is_covered,
                "hourly_rate": float(spot.hourly_rate) if spot.hourly_rate else None,
                "parking_lot": {
                    "id": spot.parking_lot.id,
                    "name": spot.parking_lot.name,
                    "address": spot.parking_lot.address
                } if spot.parking_lot else None,
                "coordinates": spot.coordinates
            }
            for spot in spots
        ]

class GetUserReservationsQuery(Query):
    """Query to get user reservations"""
    
    def __init__(self, user_id: int, status: Optional[ReservationStatus] = None,
                 include_history: bool = False):
        self.user_id = user_id
        self.status = status
        self.include_history = include_history
    
    async def execute(self, session: AsyncSession) -> List[Dict[str, Any]]:
        """Get user reservations"""
        query = select(Reservation).where(Reservation.user_id == self.user_id)
        
        if self.status:
            query = query.where(Reservation.status == self.status)
        elif not self.include_history:
            # Only active/future reservations
            query = query.where(
                Reservation.status.in_([
                    ReservationStatus.PENDING,
                    ReservationStatus.CONFIRMED,
                    ReservationStatus.ACTIVE
                ])
            )
        
        query = query.options(
            selectinload(Reservation.parking_spot),
            selectinload(Reservation.parking_lot),
            selectinload(Reservation.vehicle)
        ).order_by(Reservation.start_time.desc())
        
        result = await session.execute(query)
        reservations = result.scalars().all()
        
        return [
            {
                "id": res.id,
                "reservation_number": res.reservation_number,
                "confirmation_code": res.confirmation_code,
                "status": res.status.value,
                "start_time": res.start_time.isoformat(),
                "end_time": res.end_time.isoformat(),
                "total_cost": float(res.total_cost),
                "parking_spot": {
                    "id": res.parking_spot.id,
                    "spot_number": res.parking_spot.spot_number,
                    "floor": res.parking_spot.floor,
                    "section": res.parking_spot.section
                } if res.parking_spot else None,
                "parking_lot": {
                    "id": res.parking_lot.id,
                    "name": res.parking_lot.name,
                    "address": res.parking_lot.address
                } if res.parking_lot else None,
                "vehicle": {
                    "id": res.vehicle.id,
                    "license_plate": res.vehicle.license_plate,
                    "make": res.vehicle.make,
                    "model": res.vehicle.model
                } if res.vehicle else None
            }
            for res in reservations
        ]

class CQRSService:
    """CQRS service orchestrating commands and queries"""
    
    def __init__(self, event_service: EventService):
        self.event_service = event_service
        self.redis_client = get_redis_client()
        
        # Command handlers registry
        self.command_handlers = {}
        self.query_handlers = {}
        
        # Register default handlers
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """Register default command and query handlers"""
        # This would typically be done via dependency injection
        pass
    
    async def execute_command(self, command: Command) -> CommandResult:
        """Execute a command"""
        start_time = datetime.now(timezone.utc)
        
        try:
            # Store command execution start
            await self.redis_client.setex(
                f"command:{command.command_id}:status",
                3600,  # 1 hour TTL
                CommandStatus.PROCESSING.value
            )
            
            # Get database session
            async with get_db() as session:
                result = await command.execute(session, self.event_service)
            
            # Store command result
            await self.redis_client.setex(
                f"command:{command.command_id}:result",
                3600,
                json.dumps(asdict(result))
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            
            execution_time = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            
            error_result = CommandResult(
                command_id=command.command_id,
                status=CommandStatus.FAILED,
                error_message=str(e),
                execution_time_ms=execution_time
            )
            
            # Store error result
            await self.redis_client.setex(
                f"command:{command.command_id}:result",
                3600,
                json.dumps(asdict(error_result))
            )
            
            return error_result
    
    async def execute_query(self, query: Query) -> Any:
        """Execute a query"""
        try:
            async with get_db() as session:
                return await query.execute(session)
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise
    
    async def get_command_status(self, command_id: str) -> Optional[CommandStatus]:
        """Get command execution status"""
        try:
            status = await self.redis_client.get(f"command:{command_id}:status")
            return CommandStatus(status) if status else None
        except Exception:
            return None
    
    async def get_command_result(self, command_id: str) -> Optional[CommandResult]:
        """Get command execution result"""
        try:
            result_data = await self.redis_client.get(f"command:{command_id}:result")
            if result_data:
                data = json.loads(result_data)
                return CommandResult(**data)
            return None
        except Exception:
            return None

# Global CQRS service instance
from app.services.event_service import event_service
cqrs_service = CQRSService(event_service)
