from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base
import enum

class VehicleType(enum.Enum):
    CAR = "car"
    MOTORCYCLE = "motorcycle" 
    TRUCK = "truck"
    VAN = "van"
    ELECTRIC_CAR = "electric_car"
    ELECTRIC_MOTORCYCLE = "electric_motorcycle"
    BICYCLE = "bicycle"
    SCOOTER = "scooter"

class FuelType(enum.Enum):
    GASOLINE = "gasoline"
    DIESEL = "diesel"
    ELECTRIC = "electric"
    HYBRID = "hybrid"
    PLUG_IN_HYBRID = "plug_in_hybrid"
    CNG = "cng"
    LPG = "lpg"

class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Vehicle Identification
    license_plate = Column(String(20), unique=True, index=True, nullable=False)
    vin = Column(String(17), unique=True, nullable=True)  # Vehicle Identification Number
    
    # Vehicle Details
    make = Column(String(50), nullable=False)
    model = Column(String(100), nullable=False)
    year = Column(Integer, nullable=True)
    color = Column(String(30), nullable=False)
    vehicle_type = Column(Enum(VehicleType), nullable=False)
    fuel_type = Column(Enum(FuelType), nullable=True)
    
    # Physical Specifications
    length_cm = Column(Integer, nullable=True)  # Length in centimeters
    width_cm = Column(Integer, nullable=True)   # Width in centimeters
    height_cm = Column(Integer, nullable=True)  # Height in centimeters
    weight_kg = Column(Integer, nullable=True)  # Weight in kilograms
    
    # Electric Vehicle Specific
    battery_capacity_kwh = Column(Integer, nullable=True)  # Battery capacity in kWh
    charging_port_type = Column(String(50), nullable=True)  # Type 1, Type 2, CCS, CHAdeMO, etc.
    
    # Registration & Insurance
    registration_number = Column(String(50), nullable=True)
    registration_expiry = Column(DateTime, nullable=True)
    insurance_number = Column(String(100), nullable=True)
    insurance_expiry = Column(DateTime, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    # Additional Info
    nickname = Column(String(100), nullable=True)  # User-defined nickname for the vehicle
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    owner = relationship("User", back_populates="vehicles")
    reservations = relationship("Reservation", back_populates="vehicle")
    
    def __repr__(self):
        return f"<Vehicle(id={self.id}, license_plate='{self.license_plate}', make='{self.make}', model='{self.model}')>"
    
    @property
    def display_name(self):
        if self.nickname:
            return f"{self.nickname} ({self.license_plate})"
        return f"{self.make} {self.model} ({self.license_plate})"
    
    @property
    def is_electric(self):
        return self.fuel_type in [FuelType.ELECTRIC, FuelType.PLUG_IN_HYBRID]
    
    @property
    def requires_charging(self):
        return self.vehicle_type in [VehicleType.ELECTRIC_CAR, VehicleType.ELECTRIC_MOTORCYCLE] or self.is_electric