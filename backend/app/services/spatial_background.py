"""
Background task processor for spatial and geofencing operations
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from app.core.config import settings
from app.services.spatial_service import GeofenceService, SpatialService
from app.services.kafka_service import KafkaService


logger = logging.getLogger(__name__)


class SpatialTaskProcessor:
    """Background processor for spatial and geofencing tasks"""
    
    def __init__(self):
        # Create async engine for background tasks
        self.engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            pool_pre_ping=True,
            pool_recycle=300
        )
        self.async_session = sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        self.kafka_service = KafkaService()
        self.is_running = False
    
    async def start(self):
        """Start the background processor"""
        self.is_running = True
        logger.info("Starting Spatial Task Processor")
        
        # Start concurrent tasks
        await asyncio.gather(
            self.process_geofence_events(),
            self.refresh_spatial_analytics(),
            self.cleanup_old_events(),
            self.monitor_spatial_performance(),
            return_exceptions=True
        )
    
    async def stop(self):
        """Stop the background processor"""
        self.is_running = False
        logger.info("Stopping Spatial Task Processor")
        await self.engine.dispose()
    
    async def process_geofence_events(self):
        """Process unprocessed geofence events"""
        while self.is_running:
            try:
                async with self.async_session() as session:
                    geofence_service = GeofenceService(session)
                    
                    # Get unprocessed events
                    events = await geofence_service.get_unprocessed_events(limit=50)
                    
                    for event in events:
                        await self._process_single_event(event, session)
                    
                    if events:
                        logger.info(f"Processed {len(events)} geofence events")
                
                # Wait before next batch
                await asyncio.sleep(5)  # Process every 5 seconds
                
            except Exception as e:
                logger.error(f"Error processing geofence events: {e}")
                await asyncio.sleep(10)  # Wait longer on error
    
    async def _process_single_event(self, event: Dict[str, Any], session: AsyncSession):
        """Process a single geofence event"""
        try:
            event_id = event["id"]
            event_type = event["event_type"]
            
            # Handle different event types
            if event_type == "geofence_entry":
                await self._handle_lot_entry(event, session)
            elif event_type == "geofence_exit":
                await self._handle_lot_exit(event, session)
            elif event_type == "spot_occupied":
                await self._handle_spot_occupation(event, session)
            elif event_type == "spot_vacated":
                await self._handle_spot_vacation(event, session)
            elif event_type == "reservation_start":
                await self._handle_reservation_start(event, session)
            elif event_type == "reservation_end":
                await self._handle_reservation_end(event, session)
            
            # Mark event as processed
            geofence_service = GeofenceService(session)
            await geofence_service.mark_event_processed(event_id)
            
            # Send to Kafka for real-time updates
            await self._send_event_to_kafka(event)
            
        except Exception as e:
            logger.error(f"Error processing event {event.get('id')}: {e}")
    
    async def _handle_lot_entry(self, event: Dict[str, Any], session: AsyncSession):
        """Handle vehicle entering parking lot"""
        parking_lot_id = event["parking_lot_id"]
        vehicle_id = event.get("vehicle_id")
        
        if vehicle_id:
            # Update vehicle location
            await session.execute(
                text("""
                    UPDATE vehicles 
                    SET current_parking_lot_id = :lot_id,
                        last_location_update = NOW(),
                        location = ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)
                    WHERE id = :vehicle_id
                """),
                {
                    "lot_id": parking_lot_id,
                    "vehicle_id": vehicle_id,
                    "lat": event["latitude"],
                    "lng": event["longitude"]
                }
            )
        
        # Log analytics event
        await self._log_analytics_event("lot_entry", event)
    
    async def _handle_lot_exit(self, event: Dict[str, Any], session: AsyncSession):
        """Handle vehicle exiting parking lot"""
        vehicle_id = event.get("vehicle_id")
        
        if vehicle_id:
            # Clear vehicle location
            await session.execute(
                text("""
                    UPDATE vehicles 
                    SET current_parking_lot_id = NULL,
                        current_parking_spot_id = NULL,
                        last_location_update = NOW(),
                        location = ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)
                    WHERE id = :vehicle_id
                """),
                {
                    "vehicle_id": vehicle_id,
                    "lat": event["latitude"],
                    "lng": event["longitude"]
                }
            )
        
        await self._log_analytics_event("lot_exit", event)
    
    async def _handle_spot_occupation(self, event: Dict[str, Any], session: AsyncSession):
        """Handle parking spot being occupied"""
        spot_id = event.get("parking_spot_id")
        vehicle_id = event.get("vehicle_id")
        
        if spot_id:
            # Update spot status
            await session.execute(
                text("""
                    UPDATE parking_spots 
                    SET status = 'occupied',
                        current_vehicle_id = :vehicle_id,
                        occupied_since = NOW(),
                        last_occupied_at = NOW(),
                        status_changed_at = NOW()
                    WHERE id = :spot_id
                """),
                {"spot_id": spot_id, "vehicle_id": vehicle_id}
            )
            
            # Update lot availability
            await session.execute(
                text("""
                    UPDATE parking_lots 
                    SET available_spots = available_spots - 1,
                        last_occupancy_update = NOW()
                    WHERE id = (
                        SELECT parking_lot_id FROM parking_spots WHERE id = :spot_id
                    )
                """),
                {"spot_id": spot_id}
            )
        
        await self._log_analytics_event("spot_occupied", event)
    
    async def _handle_spot_vacation(self, event: Dict[str, Any], session: AsyncSession):
        """Handle parking spot being vacated"""
        spot_id = event.get("parking_spot_id")
        
        if spot_id:
            # Update spot status
            await session.execute(
                text("""
                    UPDATE parking_spots 
                    SET status = 'available',
                        current_vehicle_id = NULL,
                        occupied_since = NULL,
                        status_changed_at = NOW(),
                        total_occupancy_time = total_occupancy_time + 
                            EXTRACT(EPOCH FROM (NOW() - occupied_since))/60
                    WHERE id = :spot_id
                """),
                {"spot_id": spot_id}
            )
            
            # Update lot availability
            await session.execute(
                text("""
                    UPDATE parking_lots 
                    SET available_spots = available_spots + 1,
                        last_occupancy_update = NOW()
                    WHERE id = (
                        SELECT parking_lot_id FROM parking_spots WHERE id = :spot_id
                    )
                """),
                {"spot_id": spot_id}
            )
        
        await self._log_analytics_event("spot_vacated", event)
    
    async def _handle_reservation_start(self, event: Dict[str, Any], session: AsyncSession):
        """Handle reservation activation"""
        reservation_id = event.get("reservation_id")
        spot_id = event.get("parking_spot_id")
        
        if spot_id:
            await session.execute(
                text("""
                    UPDATE parking_spots 
                    SET status = 'reserved',
                        status_changed_at = NOW()
                    WHERE id = :spot_id
                """),
                {"spot_id": spot_id}
            )
        
        await self._log_analytics_event("reservation_start", event)
    
    async def _handle_reservation_end(self, event: Dict[str, Any], session: AsyncSession):
        """Handle reservation completion"""
        spot_id = event.get("parking_spot_id")
        
        if spot_id:
            await session.execute(
                text("""
                    UPDATE parking_spots 
                    SET status = 'available',
                        status_changed_at = NOW()
                    WHERE id = :spot_id
                """),
                {"spot_id": spot_id}
            )
        
        await self._log_analytics_event("reservation_end", event)
    
    async def _send_event_to_kafka(self, event: Dict[str, Any]):
        """Send processed event to Kafka for real-time updates"""
        try:
            topic = f"parking.events.{event['event_type']}"
            await self.kafka_service.publish_message(topic, event)
        except Exception as e:
            logger.error(f"Failed to send event to Kafka: {e}")
    
    async def _log_analytics_event(self, event_type: str, event_data: Dict[str, Any]):
        """Log event for analytics purposes"""
        try:
            analytics_data = {
                "event_type": event_type,
                "timestamp": datetime.utcnow().isoformat(),
                "parking_lot_id": event_data.get("parking_lot_id"),
                "parking_spot_id": event_data.get("parking_spot_id"),
                "vehicle_id": event_data.get("vehicle_id"),
                "user_id": event_data.get("user_id"),
                "location": {
                    "latitude": event_data.get("latitude"),
                    "longitude": event_data.get("longitude")
                },
                "metadata": event_data.get("metadata", {})
            }
            
            # Send to analytics topic
            await self.kafka_service.publish_message("parking.analytics", analytics_data)
            
        except Exception as e:
            logger.error(f"Failed to log analytics event: {e}")
    
    async def refresh_spatial_analytics(self):
        """Refresh spatial analytics materialized views"""
        while self.is_running:
            try:
                async with self.async_session() as session:
                    # Refresh parking density grid
                    await session.execute(text("SELECT refresh_spatial_analytics()"))
                    await session.commit()
                    
                    logger.info("Spatial analytics refreshed")
                
                # Refresh every 5 minutes
                await asyncio.sleep(300)
                
            except Exception as e:
                logger.error(f"Error refreshing spatial analytics: {e}")
                await asyncio.sleep(60)  # Retry after 1 minute
    
    async def cleanup_old_events(self):
        """Clean up old processed events"""
        while self.is_running:
            try:
                async with self.async_session() as session:
                    # Delete events older than 7 days
                    cutoff_date = datetime.utcnow() - timedelta(days=7)
                    
                    result = await session.execute(
                        text("""
                            DELETE FROM parking_events 
                            WHERE processed = TRUE 
                            AND created_at < :cutoff_date
                        """),
                        {"cutoff_date": cutoff_date}
                    )
                    
                    deleted_count = result.rowcount
                    await session.commit()
                    
                    if deleted_count > 0:
                        logger.info(f"Cleaned up {deleted_count} old events")
                
                # Run cleanup every hour
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")
                await asyncio.sleep(300)  # Retry after 5 minutes
    
    async def monitor_spatial_performance(self):
        """Monitor spatial query performance and optimize indexes"""
        while self.is_running:
            try:
                async with self.async_session() as session:
                    # Check slow spatial queries
                    slow_queries = await session.execute(
                        text("""
                            SELECT query, mean_time, calls
                            FROM pg_stat_statements
                            WHERE query ILIKE '%ST_%'
                            AND mean_time > 1000  -- Queries taking more than 1 second
                            ORDER BY mean_time DESC
                            LIMIT 10
                        """)
                    )
                    
                    for query in slow_queries:
                        logger.warning(
                            f"Slow spatial query detected: {query.mean_time:.2f}ms, "
                            f"calls: {query.calls}, query: {query.query[:100]}..."
                        )
                    
                    # Check index usage
                    index_usage = await session.execute(
                        text("""
                            SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read
                            FROM pg_stat_user_indexes
                            WHERE tablename IN ('parking_lots', 'parking_spots', 'parking_events')
                            AND indexname ILIKE '%gist%'
                            ORDER BY idx_scan DESC
                        """)
                    )
                    
                    for idx in index_usage:
                        if idx.idx_scan == 0:
                            logger.warning(f"Unused spatial index: {idx.indexname} on {idx.tablename}")
                
                # Monitor every 15 minutes
                await asyncio.sleep(900)
                
            except Exception as e:
                logger.error(f"Error monitoring spatial performance: {e}")
                await asyncio.sleep(300)


# Background task runner
spatial_processor = SpatialTaskProcessor()


async def start_spatial_processor():
    """Start the spatial background processor"""
    await spatial_processor.start()


async def stop_spatial_processor():
    """Stop the spatial background processor"""
    await spatial_processor.stop()


# Utility functions for manual operations
async def trigger_spatial_refresh():
    """Manually trigger spatial analytics refresh"""
    async with spatial_processor.async_session() as session:
        await session.execute(text("SELECT refresh_spatial_analytics()"))
        await session.commit()
        return {"status": "success", "message": "Spatial analytics refreshed"}


async def get_spatial_performance_stats():
    """Get spatial query performance statistics"""
    async with spatial_processor.async_session() as session:
        # Get spatial query performance
        performance_stats = await session.execute(
            text("""
                SELECT 
                    COUNT(*) as total_spatial_queries,
                    AVG(mean_time) as avg_execution_time,
                    MAX(mean_time) as max_execution_time,
                    SUM(calls) as total_calls
                FROM pg_stat_statements
                WHERE query ILIKE '%ST_%'
            """)
        )
        
        # Get index statistics
        index_stats = await session.execute(
            text("""
                SELECT 
                    tablename,
                    COUNT(*) as spatial_indexes,
                    SUM(idx_scan) as total_index_scans,
                    SUM(idx_tup_read) as total_tuples_read
                FROM pg_stat_user_indexes
                WHERE indexname ILIKE '%gist%'
                GROUP BY tablename
            """)
        )
        
        perf_row = performance_stats.first()
        index_rows = [dict(row._mapping) for row in index_stats]
        
        return {
            "query_performance": {
                "total_spatial_queries": perf_row.total_spatial_queries or 0,
                "avg_execution_time_ms": float(perf_row.avg_execution_time or 0),
                "max_execution_time_ms": float(perf_row.max_execution_time or 0),
                "total_calls": perf_row.total_calls or 0
            },
            "index_statistics": index_rows
        }
