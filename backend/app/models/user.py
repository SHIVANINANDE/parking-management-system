from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base
import enum

class UserRole(enum.Enum):
    USER = "user"
    ADMIN = "admin"
    MANAGER = "manager"
    OPERATOR = "operator"

class UserStatus(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=True)
    
    # Authentication
    hashed_password = Column(String(255), nullable=False)
    salt = Column(String(100), nullable=False)
    
    # Profile Information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone_number = Column(String(20), nullable=True)
    date_of_birth = Column(DateTime, nullable=True)
    
    # Account Management
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    status = Column(Enum(UserStatus), default=UserStatus.PENDING_VERIFICATION, nullable=False)
    is_email_verified = Column(Boolean, default=False, nullable=False)
    is_phone_verified = Column(Boolean, default=False, nullable=False)
    
    # Security
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    last_login_at = Column(DateTime, nullable=True)
    password_reset_token = Column(String(255), nullable=True)
    password_reset_expires = Column(DateTime, nullable=True)
    email_verification_token = Column(String(255), nullable=True)
    
    # Additional Info
    profile_picture_url = Column(String(500), nullable=True)
    timezone = Column(String(50), default="UTC", nullable=False)
    language = Column(String(10), default="en", nullable=False)
    notifications_enabled = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_activity_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    vehicles = relationship("Vehicle", back_populates="owner", cascade="all, delete-orphan")
    reservations = relationship("Reservation", back_populates="user", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', role='{self.role.value}')>"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def is_active(self):
        return self.status == UserStatus.ACTIVE and self.is_email_verified