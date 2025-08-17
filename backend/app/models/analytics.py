from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, Numeric, ForeignKey, Text, JSON, Date
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base
import enum
from datetime import datetime, date

class AnalyticsPeriod(enum.Enum):
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"

class OccupancyAnalytics(Base):
    """Track parking spot occupancy metrics over time"""
    __tablename__ = "occupancy_analytics"

    id = Column(Integer, primary_key=True, index=True)
    
    # Reference Information
    parking_lot_id = Column(Integer, ForeignKey("parking_lots.id"), nullable=False, index=True)
    parking_spot_id = Column(Integer, ForeignKey("parking_spots.id"), nullable=True, index=True)  # Null for lot-wide stats
    
    # Time Period
    period_type = Column(Enum(AnalyticsPeriod), nullable=False, index=True)
    period_start = Column(DateTime(timezone=True), nullable=False, index=True)
    period_end = Column(DateTime(timezone=True), nullable=False, index=True)
    analysis_date = Column(Date, nullable=False, index=True)  # Date for easier querying
    
    # Occupancy Metrics
    total_spots = Column(Integer, nullable=False, default=0)
    total_minutes_available = Column(Integer, nullable=False, default=0)  # Total available minutes in period
    total_minutes_occupied = Column(Integer, nullable=False, default=0)   # Total occupied minutes in period
    total_minutes_reserved = Column(Integer, nullable=False, default=0)   # Total reserved minutes in period
    
    # Occupancy Rates (percentages)
    occupancy_rate = Column(Numeric(5, 2), nullable=False, default=0.00)  # (occupied_time / available_time) * 100
    utilization_rate = Column(Numeric(5, 2), nullable=False, default=0.00)  # (occupied + reserved) / available * 100
    availability_rate = Column(Numeric(5, 2), nullable=False, default=100.00)  # Available time percentage
    
    # Peak Usage Analysis
    peak_occupancy = Column(Integer, nullable=False, default=0)           # Max spots occupied simultaneously
    peak_occupancy_time = Column(DateTime(timezone=True), nullable=True) # When peak occurred
    average_occupancy = Column(Numeric(8, 2), nullable=False, default=0.00)  # Average spots occupied
    
    # Traffic Metrics
    total_arrivals = Column(Integer, nullable=False, default=0)           # Number of vehicles that arrived
    total_departures = Column(Integer, nullable=False, default=0)         # Number of vehicles that departed
    total_reservations = Column(Integer, nullable=False, default=0)       # Number of reservations made
    no_show_count = Column(Integer, nullable=False, default=0)           # Reservations with no-show
    
    # Duration Analysis (in minutes)
    avg_parking_duration = Column(Numeric(8, 2), nullable=False, default=0.00)  # Average parking duration
    min_parking_duration = Column(Integer, nullable=False, default=0)            # Shortest parking duration
    max_parking_duration = Column(Integer, nullable=False, default=0)            # Longest parking duration
    median_parking_duration = Column(Numeric(8, 2), nullable=False, default=0.00)
    
    # Turnover Metrics
    turnover_rate = Column(Numeric(5, 2), nullable=False, default=0.00)   # Number of vehicles per spot
    avg_vacancy_duration = Column(Numeric(8, 2), nullable=False, default=0.00)  # Average time spot stays empty
    
    # Spot Type Breakdown
    regular_spot_occupancy = Column(Numeric(5, 2), nullable=False, default=0.00)
    handicapped_spot_occupancy = Column(Numeric(5, 2), nullable=False, default=0.00)
    electric_spot_occupancy = Column(Numeric(5, 2), nullable=False, default=0.00)
    motorcycle_spot_occupancy = Column(Numeric(5, 2), nullable=False, default=0.00)
    
    # Time-based Patterns
    morning_peak_occupancy = Column(Numeric(5, 2), nullable=False, default=0.00)  # 6AM-10AM
    midday_occupancy = Column(Numeric(5, 2), nullable=False, default=0.00)        # 10AM-2PM
    afternoon_peak_occupancy = Column(Numeric(5, 2), nullable=False, default=0.00)  # 2PM-6PM
    evening_occupancy = Column(Numeric(5, 2), nullable=False, default=0.00)       # 6PM-10PM
    overnight_occupancy = Column(Numeric(5, 2), nullable=False, default=0.00)     # 10PM-6AM
    
    # Day-of-week Patterns (for weekly/monthly periods)
    weekday_avg_occupancy = Column(Numeric(5, 2), nullable=False, default=0.00)
    weekend_avg_occupancy = Column(Numeric(5, 2), nullable=False, default=0.00)
    
    # Weather Impact (if weather data available)
    weather_condition = Column(String(50), nullable=True)  # sunny, rainy, snowy, etc.
    temperature_avg = Column(Numeric(5, 2), nullable=True)  # Average temperature in Celsius
    
    # Data Quality
    data_completeness = Column(Numeric(5, 2), nullable=False, default=100.00)  # Percentage of complete data
    sensor_uptime = Column(Numeric(5, 2), nullable=False, default=100.00)      # Sensor availability percentage
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    parking_lot = relationship("ParkingLot")
    parking_spot = relationship("ParkingSpot")
    
    def __repr__(self):
        return f"<OccupancyAnalytics(id={self.id}, lot_id={self.parking_lot_id}, period='{self.period_type.value}', date='{self.analysis_date}')>"

class RevenueAnalytics(Base):
    """Track revenue and financial metrics over time"""
    __tablename__ = "revenue_analytics"

    id = Column(Integer, primary_key=True, index=True)
    
    # Reference Information
    parking_lot_id = Column(Integer, ForeignKey("parking_lots.id"), nullable=False, index=True)
    
    # Time Period
    period_type = Column(Enum(AnalyticsPeriod), nullable=False, index=True)
    period_start = Column(DateTime(timezone=True), nullable=False, index=True)
    period_end = Column(DateTime(timezone=True), nullable=False, index=True)
    analysis_date = Column(Date, nullable=False, index=True)
    
    # Revenue Metrics
    total_revenue = Column(Numeric(12, 2), nullable=False, default=0.00)
    parking_revenue = Column(Numeric(12, 2), nullable=False, default=0.00)     # Core parking fees
    penalty_revenue = Column(Numeric(12, 2), nullable=False, default=0.00)     # Penalty fees
    extension_revenue = Column(Numeric(12, 2), nullable=False, default=0.00)   # Extension fees
    cancellation_revenue = Column(Numeric(12, 2), nullable=False, default=0.00) # Cancellation fees
    
    # Payment Method Breakdown
    cash_revenue = Column(Numeric(12, 2), nullable=False, default=0.00)
    card_revenue = Column(Numeric(12, 2), nullable=False, default=0.00)
    digital_wallet_revenue = Column(Numeric(12, 2), nullable=False, default=0.00)
    mobile_payment_revenue = Column(Numeric(12, 2), nullable=False, default=0.00)
    
    # Transaction Metrics
    total_transactions = Column(Integer, nullable=False, default=0)
    successful_transactions = Column(Integer, nullable=False, default=0)
    failed_transactions = Column(Integer, nullable=False, default=0)
    refunded_transactions = Column(Integer, nullable=False, default=0)
    
    # Transaction Values
    avg_transaction_value = Column(Numeric(8, 2), nullable=False, default=0.00)
    min_transaction_value = Column(Numeric(8, 2), nullable=False, default=0.00)
    max_transaction_value = Column(Numeric(8, 2), nullable=False, default=0.00)
    median_transaction_value = Column(Numeric(8, 2), nullable=False, default=0.00)
    
    # Cost Analysis
    processing_fees = Column(Numeric(10, 2), nullable=False, default=0.00)     # Payment processing fees
    operational_costs = Column(Numeric(10, 2), nullable=False, default=0.00)   # Operational costs
    net_revenue = Column(Numeric(12, 2), nullable=False, default=0.00)         # Revenue minus costs
    
    # Pricing Analysis
    avg_hourly_rate = Column(Numeric(8, 2), nullable=False, default=0.00)
    avg_daily_rate = Column(Numeric(8, 2), nullable=False, default=0.00)
    discount_amount = Column(Numeric(10, 2), nullable=False, default=0.00)     # Total discounts given
    promotion_usage = Column(Integer, nullable=False, default=0)               # Number of promotions used
    
    # Refund Analysis
    total_refunds = Column(Numeric(10, 2), nullable=False, default=0.00)
    refund_rate = Column(Numeric(5, 2), nullable=False, default=0.00)          # Percentage of transactions refunded
    avg_refund_amount = Column(Numeric(8, 2), nullable=False, default=0.00)
    
    # Customer Metrics
    unique_customers = Column(Integer, nullable=False, default=0)              # Unique users who paid
    repeat_customers = Column(Integer, nullable=False, default=0)              # Returning customers
    new_customers = Column(Integer, nullable=False, default=0)                 # First-time customers
    
    # Revenue per Metrics
    revenue_per_spot = Column(Numeric(8, 2), nullable=False, default=0.00)     # Revenue divided by total spots
    revenue_per_hour = Column(Numeric(8, 2), nullable=False, default=0.00)     # Revenue per operating hour
    revenue_per_customer = Column(Numeric(8, 2), nullable=False, default=0.00) # Average revenue per customer
    
    # Time-based Revenue Patterns
    morning_revenue = Column(Numeric(10, 2), nullable=False, default=0.00)     # 6AM-10AM
    midday_revenue = Column(Numeric(10, 2), nullable=False, default=0.00)      # 10AM-2PM
    afternoon_revenue = Column(Numeric(10, 2), nullable=False, default=0.00)   # 2PM-6PM
    evening_revenue = Column(Numeric(10, 2), nullable=False, default=0.00)     # 6PM-10PM
    overnight_revenue = Column(Numeric(10, 2), nullable=False, default=0.00)   # 10PM-6AM
    
    # Day-of-week Revenue
    weekday_revenue = Column(Numeric(10, 2), nullable=False, default=0.00)
    weekend_revenue = Column(Numeric(10, 2), nullable=False, default=0.00)
    
    # Subscription and Recurring Revenue
    subscription_revenue = Column(Numeric(10, 2), nullable=False, default=0.00)
    one_time_revenue = Column(Numeric(10, 2), nullable=False, default=0.00)
    
    # Predictions and Forecasting
    predicted_revenue = Column(Numeric(12, 2), nullable=True)                  # AI/ML predicted revenue
    forecast_accuracy = Column(Numeric(5, 2), nullable=True)                   # Accuracy of previous predictions
    
    # Currency and Localization
    currency = Column(String(3), nullable=False, default="USD")
    exchange_rate = Column(Numeric(10, 6), nullable=True)                      # If multiple currencies
    
    # Data Quality
    data_completeness = Column(Numeric(5, 2), nullable=False, default=100.00)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    parking_lot = relationship("ParkingLot")
    
    def __repr__(self):
        return f"<RevenueAnalytics(id={self.id}, lot_id={self.parking_lot_id}, period='{self.period_type.value}', revenue={self.total_revenue})>"
    
    @property
    def profit_margin(self):
        """Calculate profit margin percentage"""
        if self.total_revenue == 0:
            return 0.00
        return ((self.net_revenue / self.total_revenue) * 100)
    
    @property
    def transaction_success_rate(self):
        """Calculate transaction success rate percentage"""
        if self.total_transactions == 0:
            return 0.00
        return ((self.successful_transactions / self.total_transactions) * 100)
    
    @property
    def customer_retention_rate(self):
        """Calculate customer retention rate"""
        if self.unique_customers == 0:
            return 0.00
        return ((self.repeat_customers / self.unique_customers) * 100)