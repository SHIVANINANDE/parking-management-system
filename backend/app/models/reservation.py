from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, Numeric, ForeignKey, Text, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base
import enum
from datetime import datetime, timedelta

class ReservationStatus(enum.Enum):
    PENDING = "pending"           # Just created, payment pending
    CONFIRMED = "confirmed"       # Payment successful, reservation active
    ACTIVE = "active"            # User has arrived, currently using the spot
    COMPLETED = "completed"      # Successfully finished
    CANCELLED = "cancelled"      # Cancelled by user
    EXPIRED = "expired"          # Time passed without showing up
    NO_SHOW = "no_show"         # Didn't show up within grace period
    OVERSTAYED = "overstayed"   # Exceeded reserved time

class ReservationType(enum.Enum):
    IMMEDIATE = "immediate"      # Reserve for immediate use
    SCHEDULED = "scheduled"      # Reserve for future time
    RECURRING = "recurring"      # Recurring reservation (daily, weekly, etc.)

class Reservation(Base):
    __tablename__ = "reservations"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False, index=True)
    parking_lot_id = Column(Integer, ForeignKey("parking_lots.id"), nullable=False, index=True)
    parking_spot_id = Column(Integer, ForeignKey("parking_spots.id"), nullable=True, index=True)
    
    # Reservation Identification
    reservation_number = Column(String(50), unique=True, index=True, nullable=False)
    confirmation_code = Column(String(20), unique=True, index=True, nullable=False)
    
    # Time Management
    reservation_type = Column(Enum(ReservationType), default=ReservationType.IMMEDIATE, nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    end_time = Column(DateTime(timezone=True), nullable=False, index=True)
    actual_arrival_time = Column(DateTime(timezone=True), nullable=True)
    actual_departure_time = Column(DateTime(timezone=True), nullable=True)
    
    # Grace Periods and Extensions
    grace_period_minutes = Column(Integer, default=15, nullable=False)  # Late arrival tolerance
    max_extension_hours = Column(Integer, default=2, nullable=False)    # Maximum extension allowed
    extended_until = Column(DateTime(timezone=True), nullable=True)     # If extended
    extension_count = Column(Integer, default=0, nullable=False)
    
    # Status and State
    status = Column(Enum(ReservationStatus), default=ReservationStatus.PENDING, nullable=False, index=True)
    is_recurring = Column(Boolean, default=False, nullable=False)
    parent_reservation_id = Column(Integer, ForeignKey("reservations.id"), nullable=True)  # For recurring reservations
    
    # Pricing and Payment
    base_cost = Column(Numeric(10, 2), nullable=False, default=0.00)
    total_cost = Column(Numeric(10, 2), nullable=False, default=0.00)
    tax_amount = Column(Numeric(10, 2), nullable=False, default=0.00)
    discount_amount = Column(Numeric(10, 2), nullable=False, default=0.00)
    extension_cost = Column(Numeric(10, 2), nullable=False, default=0.00)
    penalty_cost = Column(Numeric(10, 2), nullable=False, default=0.00)
    
    # Payment Status
    is_paid = Column(Boolean, default=False, nullable=False)
    payment_due_at = Column(DateTime(timezone=True), nullable=True)
    refund_amount = Column(Numeric(10, 2), nullable=True)
    
    # Special Requirements
    requires_ev_charging = Column(Boolean, default=False, nullable=False)
    requires_handicapped_access = Column(Boolean, default=False, nullable=False)
    preferred_spot_type = Column(String(50), nullable=True)
    special_requests = Column(Text, nullable=True)
    
    # Cancellation and Refunds
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancellation_reason = Column(String(200), nullable=True)
    is_refundable = Column(Boolean, default=True, nullable=False)
    cancellation_fee = Column(Numeric(10, 2), nullable=False, default=0.00)
    
    # Recurring Reservation Settings
    recurrence_pattern = Column(JSON, nullable=True)  # Pattern for recurring reservations
    recurrence_end_date = Column(DateTime(timezone=True), nullable=True)
    next_occurrence_date = Column(DateTime(timezone=True), nullable=True)
    
    # Notification and Communication
    reminder_sent = Column(Boolean, default=False, nullable=False)
    arrival_notification_sent = Column(Boolean, default=False, nullable=False)
    departure_reminder_sent = Column(Boolean, default=False, nullable=False)
    
    # Check-in/Check-out
    qr_code = Column(String(200), nullable=True)  # QR code for easy check-in
    check_in_method = Column(String(50), nullable=True)  # "app", "qr", "sensor", "manual"
    check_out_method = Column(String(50), nullable=True)
    
    # Validation and Verification
    license_plate_verified = Column(Boolean, default=False, nullable=False)
    spot_verified = Column(Boolean, default=False, nullable=False)
    
    # Additional Information
    notes = Column(Text, nullable=True)
    internal_notes = Column(Text, nullable=True)  # For staff use
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="reservations")
    vehicle = relationship("Vehicle", back_populates="reservations")
    parking_lot = relationship("ParkingLot", back_populates="reservations")
    parking_spot = relationship("ParkingSpot", back_populates="reservations")
    payments = relationship("Payment", back_populates="reservation")
    parent_reservation = relationship("Reservation", remote_side=[id])
    child_reservations = relationship("Reservation", back_populates="parent_reservation")
    
    def __repr__(self):
        return f"<Reservation(id={self.id}, number='{self.reservation_number}', status='{self.status.value}')>"
    
    @property
    def duration_hours(self):
        """Calculate duration in hours"""
        delta = self.end_time - self.start_time
        return delta.total_seconds() / 3600
    
    @property
    def actual_duration_hours(self):
        """Calculate actual duration if both arrival and departure times are set"""
        if self.actual_arrival_time and self.actual_departure_time:
            delta = self.actual_departure_time - self.actual_arrival_time
            return delta.total_seconds() / 3600
        return None
    
    @property
    def is_expired(self):
        """Check if reservation has expired"""
        now = datetime.utcnow()
        grace_end = self.start_time + timedelta(minutes=self.grace_period_minutes)
        return now > grace_end and self.status in [ReservationStatus.PENDING, ReservationStatus.CONFIRMED]
    
    @property
    def is_overdue(self):
        """Check if vehicle has overstayed the reservation"""
        if not self.actual_arrival_time:
            return False
        
        now = datetime.utcnow()
        end_time = self.extended_until if self.extended_until else self.end_time
        return now > end_time and self.status == ReservationStatus.ACTIVE
    
    @property
    def time_until_start(self):
        """Time until reservation starts"""
        now = datetime.utcnow()
        if now < self.start_time:
            return self.start_time - now
        return timedelta(0)
    
    @property
    def time_until_end(self):
        """Time until reservation ends"""
        now = datetime.utcnow()
        end_time = self.extended_until if self.extended_until else self.end_time
        if now < end_time:
            return end_time - now
        return timedelta(0)
    
    @property
    def can_be_cancelled(self):
        """Check if reservation can be cancelled"""
        if self.status in [ReservationStatus.COMPLETED, ReservationStatus.CANCELLED, ReservationStatus.EXPIRED]:
            return False
        
        # Can't cancel if already checked in
        if self.status == ReservationStatus.ACTIVE:
            return False
        
        # Check if within cancellation window (e.g., 30 minutes before start)
        now = datetime.utcnow()
        cancellation_deadline = self.start_time - timedelta(minutes=30)
        return now < cancellation_deadline
    
    @property
    def can_be_extended(self):
        """Check if reservation can be extended"""
        if self.status != ReservationStatus.ACTIVE:
            return False
        
        if self.extension_count >= 3:  # Maximum 3 extensions
            return False
        
        # Check if max extension time would be exceeded
        now = datetime.utcnow()
        current_end = self.extended_until if self.extended_until else self.end_time
        max_end = self.start_time + timedelta(hours=self.max_extension_hours)
        
        return current_end < max_end
    
    def extend_reservation(self, additional_hours: int):
        """Extend the reservation by additional hours"""
        if not self.can_be_extended:
            raise ValueError("Reservation cannot be extended")
        
        current_end = self.extended_until if self.extended_until else self.end_time
        self.extended_until = current_end + timedelta(hours=additional_hours)
        self.extension_count += 1
        
        # Calculate additional cost
        hourly_rate = self.base_cost / self.duration_hours if self.duration_hours > 0 else 0
        self.extension_cost += hourly_rate * additional_hours
        self.total_cost += hourly_rate * additional_hours