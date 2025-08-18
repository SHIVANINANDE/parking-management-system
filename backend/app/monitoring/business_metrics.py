"""
Business metrics collection and monitoring for the parking management system.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import text, func
import structlog
from prometheus_client import Gauge, Counter, Histogram
from ..db.database import get_db
from ..models import ParkingLot, ParkingSpot, Reservation, Payment, User, Vehicle

logger = structlog.get_logger(__name__)

# Business-specific Prometheus metrics
PARKING_REVENUE = Gauge(
    'parking_revenue_total',
    'Total parking revenue',
    ['period', 'lot_id', 'payment_method']
)

CUSTOMER_SATISFACTION = Gauge(
    'customer_satisfaction_score',
    'Customer satisfaction score',
    ['lot_id', 'period']
)

AVERAGE_PARKING_DURATION = Histogram(
    'parking_duration_minutes',
    'Average parking duration in minutes',
    ['lot_id', 'vehicle_type'],
    buckets=[15, 30, 60, 120, 240, 480, 720, 1440]  # 15min to 24h
)

PEAK_OCCUPANCY_RATE = Gauge(
    'peak_occupancy_rate',
    'Peak occupancy rate during time periods',
    ['lot_id', 'time_period']
)

USER_ACQUISITION_RATE = Counter(
    'new_users_total',
    'Total number of new user registrations',
    ['source', 'period']
)

RESERVATION_CONVERSION_RATE = Gauge(
    'reservation_conversion_rate',
    'Rate of reservations converted to actual usage',
    ['lot_id']
)

VEHICLE_TYPE_DISTRIBUTION = Gauge(
    'vehicle_type_distribution',
    'Distribution of vehicle types',
    ['vehicle_type', 'lot_id']
)

OPERATIONAL_EFFICIENCY = Gauge(
    'operational_efficiency_score',
    'Operational efficiency score',
    ['lot_id', 'metric_type']
)

class BusinessMetricsCollector:
    """Collector for business-specific metrics and KPIs."""
    
    def __init__(self):
        self.db_session = None
        self.collection_interval = 300  # 5 minutes
        self.daily_collection_time = "02:00"  # 2 AM daily collection
    
    async def start_collection(self):
        """Start the metrics collection loop."""
        logger.info("Starting business metrics collection")
        
        # Start periodic collection
        asyncio.create_task(self._periodic_collection_loop())
        asyncio.create_task(self._daily_collection_loop())
    
    async def _periodic_collection_loop(self):
        """Run periodic metrics collection."""
        while True:
            try:
                await self.collect_real_time_metrics()
                await asyncio.sleep(self.collection_interval)
            except Exception as e:
                logger.error("Error in periodic metrics collection", error=str(e))
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    async def _daily_collection_loop(self):
        """Run daily metrics collection at specified time."""
        while True:
            try:
                now = datetime.now()
                # Calculate next 2 AM
                next_collection = now.replace(hour=2, minute=0, second=0, microsecond=0)
                if next_collection <= now:
                    next_collection += timedelta(days=1)
                
                # Wait until next collection time
                wait_seconds = (next_collection - now).total_seconds()
                await asyncio.sleep(wait_seconds)
                
                # Collect daily metrics
                await self.collect_daily_metrics()
                
            except Exception as e:
                logger.error("Error in daily metrics collection", error=str(e))
                await asyncio.sleep(3600)  # Wait 1 hour on error
    
    async def collect_real_time_metrics(self):
        """Collect real-time business metrics."""
        async for db in get_db():
            self.db_session = db
            break
        
        if not self.db_session:
            logger.error("Could not get database session for metrics collection")
            return
        
        try:
            await self._collect_current_occupancy_metrics()
            await self._collect_revenue_metrics()
            await self._collect_reservation_metrics()
            await self._collect_user_metrics()
            
        except Exception as e:
            logger.error("Error collecting real-time metrics", error=str(e))
    
    async def collect_daily_metrics(self):
        """Collect daily business metrics and analytics."""
        async for db in get_db():
            self.db_session = db
            break
        
        if not self.db_session:
            logger.error("Could not get database session for daily metrics")
            return
        
        try:
            await self._collect_daily_revenue_analytics()
            await self._collect_customer_satisfaction_metrics()
            await self._collect_operational_efficiency_metrics()
            await self._collect_parking_duration_analytics()
            await self._collect_vehicle_distribution_metrics()
            
        except Exception as e:
            logger.error("Error collecting daily metrics", error=str(e))
    
    async def _collect_current_occupancy_metrics(self):
        """Collect current parking occupancy metrics."""
        try:
            # Get occupancy by lot and time period
            now = datetime.now()
            hour = now.hour
            
            # Determine time period
            if 6 <= hour < 12:
                time_period = "morning"
            elif 12 <= hour < 18:
                time_period = "afternoon"
            elif 18 <= hour < 22:
                time_period = "evening"
            else:
                time_period = "night"
            
            # Query occupancy rates by lot
            occupancy_query = text("""
                SELECT 
                    pl.id as lot_id,
                    COUNT(CASE WHEN ps.status = 'occupied' THEN 1 END)::float / 
                    COUNT(*)::float as occupancy_rate
                FROM parking_lots pl
                LEFT JOIN parking_spots ps ON pl.id = ps.lot_id
                GROUP BY pl.id
            """)
            
            result = await self.db_session.execute(occupancy_query)
            for row in result:
                PEAK_OCCUPANCY_RATE.labels(
                    lot_id=str(row.lot_id),
                    time_period=time_period
                ).set(row.occupancy_rate or 0.0)
            
            logger.debug("Collected occupancy metrics", time_period=time_period)
            
        except Exception as e:
            logger.error("Error collecting occupancy metrics", error=str(e))
    
    async def _collect_revenue_metrics(self):
        """Collect current revenue metrics."""
        try:
            now = datetime.now()
            today = now.date()
            
            # Today's revenue by lot and payment method
            revenue_query = text("""
                SELECT 
                    r.lot_id,
                    p.payment_method,
                    SUM(p.amount) as total_revenue
                FROM payments p
                JOIN reservations r ON p.reservation_id = r.id
                WHERE DATE(p.created_at) = :today
                AND p.status = 'completed'
                GROUP BY r.lot_id, p.payment_method
            """)
            
            result = await self.db_session.execute(revenue_query, {"today": today})
            for row in result:
                PARKING_REVENUE.labels(
                    period="daily",
                    lot_id=str(row.lot_id),
                    payment_method=row.payment_method
                ).set(float(row.total_revenue or 0))
            
            # Hourly revenue
            hour_start = now.replace(minute=0, second=0, microsecond=0)
            hourly_revenue_query = text("""
                SELECT 
                    r.lot_id,
                    p.payment_method,
                    SUM(p.amount) as hourly_revenue
                FROM payments p
                JOIN reservations r ON p.reservation_id = r.id
                WHERE p.created_at >= :hour_start
                AND p.status = 'completed'
                GROUP BY r.lot_id, p.payment_method
            """)
            
            result = await self.db_session.execute(hourly_revenue_query, {"hour_start": hour_start})
            for row in result:
                PARKING_REVENUE.labels(
                    period="hourly",
                    lot_id=str(row.lot_id),
                    payment_method=row.payment_method
                ).set(float(row.hourly_revenue or 0))
            
            logger.debug("Collected revenue metrics")
            
        except Exception as e:
            logger.error("Error collecting revenue metrics", error=str(e))
    
    async def _collect_reservation_metrics(self):
        """Collect reservation-related metrics."""
        try:
            # Reservation conversion rate (reservations that were actually used)
            conversion_query = text("""
                SELECT 
                    lot_id,
                    COUNT(CASE WHEN status IN ('completed', 'active') THEN 1 END)::float /
                    COUNT(*)::float as conversion_rate
                FROM reservations
                WHERE created_at >= NOW() - INTERVAL '24 hours'
                GROUP BY lot_id
            """)
            
            result = await self.db_session.execute(conversion_query)
            for row in result:
                RESERVATION_CONVERSION_RATE.labels(
                    lot_id=str(row.lot_id)
                ).set(row.conversion_rate or 0.0)
            
            logger.debug("Collected reservation metrics")
            
        except Exception as e:
            logger.error("Error collecting reservation metrics", error=str(e))
    
    async def _collect_user_metrics(self):
        """Collect user acquisition and activity metrics."""
        try:
            # New user registrations today
            today = datetime.now().date()
            new_users_query = text("""
                SELECT 
                    COUNT(*) as new_users
                FROM users
                WHERE DATE(created_at) = :today
            """)
            
            result = await self.db_session.execute(new_users_query, {"today": today})
            new_users = result.scalar() or 0
            
            USER_ACQUISITION_RATE.labels(
                source="web",  # Could be enhanced to track actual sources
                period="daily"
            ).inc(new_users)
            
            logger.debug("Collected user metrics", new_users=new_users)
            
        except Exception as e:
            logger.error("Error collecting user metrics", error=str(e))
    
    async def _collect_daily_revenue_analytics(self):
        """Collect detailed daily revenue analytics."""
        try:
            yesterday = (datetime.now() - timedelta(days=1)).date()
            
            # Revenue analytics for yesterday
            analytics_query = text("""
                SELECT 
                    r.lot_id,
                    p.payment_method,
                    COUNT(*) as transaction_count,
                    SUM(p.amount) as total_revenue,
                    AVG(p.amount) as avg_transaction,
                    MIN(p.amount) as min_transaction,
                    MAX(p.amount) as max_transaction
                FROM payments p
                JOIN reservations r ON p.reservation_id = r.id
                WHERE DATE(p.created_at) = :yesterday
                AND p.status = 'completed'
                GROUP BY r.lot_id, p.payment_method
            """)
            
            result = await self.db_session.execute(analytics_query, {"yesterday": yesterday})
            for row in result:
                # Store detailed analytics (could be sent to separate analytics system)
                logger.info(
                    "Daily revenue analytics",
                    date=str(yesterday),
                    lot_id=row.lot_id,
                    payment_method=row.payment_method,
                    transaction_count=row.transaction_count,
                    total_revenue=float(row.total_revenue),
                    avg_transaction=float(row.avg_transaction)
                )
            
        except Exception as e:
            logger.error("Error collecting daily revenue analytics", error=str(e))
    
    async def _collect_customer_satisfaction_metrics(self):
        """Collect customer satisfaction metrics."""
        try:
            # This would typically come from customer feedback/ratings
            # For now, we'll calculate based on reservation completion rates and usage patterns
            
            satisfaction_query = text("""
                SELECT 
                    lot_id,
                    AVG(CASE 
                        WHEN status = 'completed' THEN 5.0
                        WHEN status = 'cancelled' THEN 2.0
                        WHEN status = 'no_show' THEN 1.0
                        ELSE 3.0
                    END) as satisfaction_score
                FROM reservations
                WHERE created_at >= NOW() - INTERVAL '7 days'
                GROUP BY lot_id
            """)
            
            result = await self.db_session.execute(satisfaction_query)
            for row in result:
                CUSTOMER_SATISFACTION.labels(
                    lot_id=str(row.lot_id),
                    period="weekly"
                ).set(row.satisfaction_score or 3.0)
            
            logger.debug("Collected customer satisfaction metrics")
            
        except Exception as e:
            logger.error("Error collecting customer satisfaction metrics", error=str(e))
    
    async def _collect_operational_efficiency_metrics(self):
        """Collect operational efficiency metrics."""
        try:
            # Calculate various efficiency metrics
            
            # Spot utilization efficiency
            utilization_query = text("""
                SELECT 
                    pl.id as lot_id,
                    AVG(
                        CASE WHEN ps.status = 'occupied' THEN 1.0 ELSE 0.0 END
                    ) as utilization_rate
                FROM parking_lots pl
                LEFT JOIN parking_spots ps ON pl.id = ps.lot_id
                GROUP BY pl.id
            """)
            
            result = await self.db_session.execute(utilization_query)
            for row in result:
                OPERATIONAL_EFFICIENCY.labels(
                    lot_id=str(row.lot_id),
                    metric_type="utilization"
                ).set(row.utilization_rate or 0.0)
            
            # Revenue per spot efficiency
            revenue_efficiency_query = text("""
                SELECT 
                    pl.id as lot_id,
                    COALESCE(SUM(p.amount), 0) / COUNT(ps.id) as revenue_per_spot
                FROM parking_lots pl
                LEFT JOIN parking_spots ps ON pl.id = ps.lot_id
                LEFT JOIN reservations r ON ps.id = r.spot_id
                LEFT JOIN payments p ON r.id = p.reservation_id
                WHERE p.created_at >= NOW() - INTERVAL '24 hours'
                OR p.created_at IS NULL
                GROUP BY pl.id
            """)
            
            result = await self.db_session.execute(revenue_efficiency_query)
            for row in result:
                OPERATIONAL_EFFICIENCY.labels(
                    lot_id=str(row.lot_id),
                    metric_type="revenue_per_spot"
                ).set(float(row.revenue_per_spot or 0))
            
            logger.debug("Collected operational efficiency metrics")
            
        except Exception as e:
            logger.error("Error collecting operational efficiency metrics", error=str(e))
    
    async def _collect_parking_duration_analytics(self):
        """Collect parking duration analytics."""
        try:
            duration_query = text("""
                SELECT 
                    r.lot_id,
                    v.vehicle_type,
                    EXTRACT(EPOCH FROM (r.end_time - r.start_time))/60 as duration_minutes
                FROM reservations r
                JOIN vehicles v ON r.vehicle_id = v.id
                WHERE r.status = 'completed'
                AND r.end_time IS NOT NULL
                AND r.created_at >= NOW() - INTERVAL '24 hours'
            """)
            
            result = await self.db_session.execute(duration_query)
            for row in result:
                AVERAGE_PARKING_DURATION.labels(
                    lot_id=str(row.lot_id),
                    vehicle_type=row.vehicle_type
                ).observe(row.duration_minutes or 0)
            
            logger.debug("Collected parking duration analytics")
            
        except Exception as e:
            logger.error("Error collecting parking duration analytics", error=str(e))
    
    async def _collect_vehicle_distribution_metrics(self):
        """Collect vehicle type distribution metrics."""
        try:
            distribution_query = text("""
                SELECT 
                    r.lot_id,
                    v.vehicle_type,
                    COUNT(*) as count
                FROM reservations r
                JOIN vehicles v ON r.vehicle_id = v.id
                WHERE r.created_at >= NOW() - INTERVAL '24 hours'
                GROUP BY r.lot_id, v.vehicle_type
            """)
            
            result = await self.db_session.execute(distribution_query)
            for row in result:
                VEHICLE_TYPE_DISTRIBUTION.labels(
                    vehicle_type=row.vehicle_type,
                    lot_id=str(row.lot_id)
                ).set(row.count)
            
            logger.debug("Collected vehicle distribution metrics")
            
        except Exception as e:
            logger.error("Error collecting vehicle distribution metrics", error=str(e))

# Global business metrics collector instance
business_metrics_collector = BusinessMetricsCollector()
