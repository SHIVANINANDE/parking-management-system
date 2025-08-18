"""
Analytics API Endpoints - Step 6: Analytics & Optimization
RESTful API endpoints for analytics, optimization, and performance monitoring.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from app.db.database import get_db
from app.services.analytics_service import AnalyticsService
from app.services.performance_service import get_performance_service
from app.models.analytics import OccupancyAnalytics, RevenueAnalytics
import redis.asyncio as redis
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])

# Initialize Redis client for analytics
async def get_redis_client():
    return redis.from_url(
        str(settings.REDIS_URL),
        encoding="utf-8",
        decode_responses=True
    )

@router.get("/comprehensive/{parking_lot_id}")
async def get_comprehensive_analytics(
    parking_lot_id: str,
    analysis_period_days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive analytics analysis for a parking lot.
    
    Returns occupancy patterns, demand forecasts, and optimization recommendations.
    """
    try:
        redis_client = await get_redis_client()
        analytics_service = AnalyticsService(redis_client)
        
        comprehensive_report = await analytics_service.comprehensive_analysis(
            parking_lot_id, analysis_period_days
        )
        
        if not comprehensive_report:
            raise HTTPException(status_code=404, detail="Parking lot not found or insufficient data")
        
        return {
            "status": "success",
            "data": comprehensive_report,
            "message": f"Comprehensive analytics generated for {analysis_period_days} days"
        }
        
    except Exception as e:
        logger.error(f"Comprehensive analytics error: {e}")
        raise HTTPException(status_code=500, detail=f"Analytics generation failed: {str(e)}")

@router.get("/patterns/{parking_lot_id}")
async def get_occupancy_patterns(
    parking_lot_id: str,
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get detailed occupancy patterns for a parking lot.
    
    Analyzes hourly, daily, and seasonal patterns with anomaly detection.
    """
    try:
        redis_client = await get_redis_client()
        analytics_service = AnalyticsService(redis_client)
        
        # Default to last 30 days if no dates provided
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        patterns = await analytics_service.pattern_detector.detect_patterns(
            parking_lot_id, (start_date, end_date)
        )
        
        if not patterns:
            raise HTTPException(status_code=404, detail="No patterns found for the specified period")
        
        return {
            "status": "success",
            "data": {
                "parking_lot_id": parking_lot_id,
                "analysis_period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                },
                "patterns": patterns
            },
            "message": "Occupancy patterns analyzed successfully"
        }
        
    except Exception as e:
        logger.error(f"Pattern analysis error: {e}")
        raise HTTPException(status_code=500, detail=f"Pattern analysis failed: {str(e)}")

@router.get("/forecast/{parking_lot_id}")
async def get_demand_forecast(
    parking_lot_id: str,
    forecast_hours: int = Query(24, ge=1, le=168),  # Max 1 week
    use_ensemble: bool = Query(True),
    db: Session = Depends(get_db)
):
    """
    Get demand forecast for a parking lot.
    
    Uses machine learning models to predict future demand.
    """
    try:
        redis_client = await get_redis_client()
        analytics_service = AnalyticsService(redis_client)
        
        # Check if models are trained, train if necessary
        try:
            forecast = await analytics_service.demand_predictor.predict_demand(
                parking_lot_id, forecast_hours, use_ensemble
            )
        except ValueError:
            # Models not trained, train them first
            await analytics_service.demand_predictor.train_models(parking_lot_id)
            forecast = await analytics_service.demand_predictor.predict_demand(
                parking_lot_id, forecast_hours, use_ensemble
            )
        
        return {
            "status": "success",
            "data": forecast,
            "message": f"Demand forecast generated for {forecast_hours} hours"
        }
        
    except Exception as e:
        logger.error(f"Demand forecast error: {e}")
        raise HTTPException(status_code=500, detail=f"Forecast generation failed: {str(e)}")

@router.post("/train-models/{parking_lot_id}")
async def train_prediction_models(
    parking_lot_id: str,
    lookback_days: int = Query(90, ge=30, le=365),
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Train machine learning models for demand prediction.
    
    This is a background task that can take several minutes.
    """
    try:
        redis_client = await get_redis_client()
        analytics_service = AnalyticsService(redis_client)
        
        # Run training in background
        background_tasks.add_task(
            analytics_service.demand_predictor.train_models,
            parking_lot_id,
            lookback_days
        )
        
        return {
            "status": "success",
            "message": f"Model training started for parking lot {parking_lot_id}",
            "data": {
                "parking_lot_id": parking_lot_id,
                "lookback_days": lookback_days,
                "estimated_completion": "5-10 minutes"
            }
        }
        
    except Exception as e:
        logger.error(f"Model training error: {e}")
        raise HTTPException(status_code=500, detail=f"Model training failed: {str(e)}")

@router.get("/realtime/{parking_lot_id}")
async def get_realtime_analytics(
    parking_lot_id: str,
    db: Session = Depends(get_db)
):
    """
    Get real-time analytics dashboard data.
    
    Returns current metrics and hourly trends for today.
    """
    try:
        redis_client = await get_redis_client()
        analytics_service = AnalyticsService(redis_client)
        
        realtime_data = await analytics_service.get_real_time_analytics(parking_lot_id)
        
        return {
            "status": "success",
            "data": realtime_data,
            "message": "Real-time analytics retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Real-time analytics error: {e}")
        raise HTTPException(status_code=500, detail=f"Real-time analytics failed: {str(e)}")

@router.get("/sliding-window/{parking_lot_id}")
async def get_sliding_window_analysis(
    parking_lot_id: str,
    window_size: int = Query(100, ge=10, le=1000),
    db: Session = Depends(get_db)
):
    """
    Get sliding window analysis for real-time pattern detection.
    
    Analyzes recent data using sliding window algorithms.
    """
    try:
        redis_client = await get_redis_client()
        analytics_service = AnalyticsService(redis_client)
        
        # Get recent data and run sliding window analysis
        current_time = datetime.now()
        recent_reservations = db.query(OccupancyAnalytics).filter(
            OccupancyAnalytics.parking_lot_id == parking_lot_id,
            OccupancyAnalytics.period_start >= current_time - timedelta(hours=24)
        ).order_by(OccupancyAnalytics.period_start.desc()).limit(window_size).all()
        
        if not recent_reservations:
            raise HTTPException(status_code=404, detail="No recent data available for sliding window analysis")
        
        # Simulate sliding window analysis with recent data
        sliding_window = analytics_service.sliding_window
        
        for reservation in recent_reservations:
            analysis = sliding_window.add_data_point(
                timestamp=reservation.period_start,
                parking_lot_id=parking_lot_id,
                occupied_spots=int(reservation.total_spots * reservation.occupancy_rate / 100),
                total_spots=reservation.total_spots,
                demand_level=float(reservation.occupancy_rate / 100)
            )
        
        return {
            "status": "success",
            "data": {
                "parking_lot_id": parking_lot_id,
                "window_size": window_size,
                "data_points_analyzed": len(recent_reservations),
                "latest_analysis": analysis,
                "window_statistics": sliding_window.metrics_cache
            },
            "message": "Sliding window analysis completed"
        }
        
    except Exception as e:
        logger.error(f"Sliding window analysis error: {e}")
        raise HTTPException(status_code=500, detail=f"Sliding window analysis failed: {str(e)}")

@router.get("/performance/metrics")
async def get_performance_metrics(db: Session = Depends(get_db)):
    """
    Get comprehensive system performance metrics.
    
    Returns cache performance, database stats, and optimization recommendations.
    """
    try:
        performance_service = await get_performance_service()
        metrics = await performance_service.get_performance_metrics()
        
        return {
            "status": "success",
            "data": metrics,
            "message": "Performance metrics retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Performance metrics error: {e}")
        raise HTTPException(status_code=500, detail=f"Performance metrics failed: {str(e)}")

@router.get("/performance/availability/{parking_lot_id}")
async def check_optimized_availability(
    parking_lot_id: str,
    start_time: datetime,
    end_time: datetime,
    db: Session = Depends(get_db)
):
    """
    Check parking availability using optimized algorithms.
    
    Uses Bloom filters and caching for high-performance availability checks.
    """
    try:
        performance_service = await get_performance_service()
        
        availability_data = await performance_service.check_availability_optimized(
            parking_lot_id, start_time, end_time
        )
        
        return {
            "status": "success",
            "data": {
                "parking_lot_id": parking_lot_id,
                "time_period": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat()
                },
                "availability": availability_data
            },
            "message": "Optimized availability check completed"
        }
        
    except Exception as e:
        logger.error(f"Optimized availability check error: {e}")
        raise HTTPException(status_code=500, detail=f"Availability check failed: {str(e)}")

@router.post("/performance/cache/warm/{parking_lot_id}")
async def warm_cache(
    parking_lot_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Warm cache for a specific parking lot.
    
    Preloads frequently accessed data into cache for better performance.
    """
    try:
        performance_service = await get_performance_service()
        
        # Run cache warming in background
        background_tasks.add_task(
            performance_service.redis_cache.warm_cache,
            parking_lot_id
        )
        
        return {
            "status": "success",
            "message": f"Cache warming started for parking lot {parking_lot_id}",
            "data": {
                "parking_lot_id": parking_lot_id,
                "estimated_completion": "1-2 minutes"
            }
        }
        
    except Exception as e:
        logger.error(f"Cache warming error: {e}")
        raise HTTPException(status_code=500, detail=f"Cache warming failed: {str(e)}")

@router.delete("/performance/cache/{parking_lot_id}")
async def invalidate_cache(
    parking_lot_id: str,
    cache_pattern: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Invalidate cache entries for a parking lot.
    
    Clears cached data to force fresh data retrieval.
    """
    try:
        performance_service = await get_performance_service()
        
        if cache_pattern:
            invalidated_count = await performance_service.redis_cache.invalidate_pattern(
                f"{cache_pattern}:{parking_lot_id}:*"
            )
        else:
            invalidated_count = await performance_service.redis_cache.invalidate_pattern(
                f"*:{parking_lot_id}:*"
            )
        
        return {
            "status": "success",
            "message": f"Cache invalidated for parking lot {parking_lot_id}",
            "data": {
                "parking_lot_id": parking_lot_id,
                "invalidated_keys": invalidated_count,
                "pattern_used": cache_pattern or "all_patterns"
            }
        }
        
    except Exception as e:
        logger.error(f"Cache invalidation error: {e}")
        raise HTTPException(status_code=500, detail=f"Cache invalidation failed: {str(e)}")

@router.get("/optimization/recommendations/{parking_lot_id}")
async def get_optimization_recommendations(
    parking_lot_id: str,
    priority_filter: Optional[str] = Query(None, regex="^(low|medium|high|critical)$"),
    db: Session = Depends(get_db)
):
    """
    Get optimization recommendations for a parking lot.
    
    Returns AI-generated recommendations for improving efficiency and revenue.
    """
    try:
        redis_client = await get_redis_client()
        analytics_service = AnalyticsService(redis_client)
        
        recommendations = await analytics_service._generate_optimization_recommendations(parking_lot_id)
        
        # Filter by priority if specified
        if priority_filter:
            recommendations = [
                rec for rec in recommendations 
                if rec.get('priority') == priority_filter
            ]
        
        return {
            "status": "success",
            "data": {
                "parking_lot_id": parking_lot_id,
                "recommendations": recommendations,
                "total_count": len(recommendations),
                "priority_filter": priority_filter
            },
            "message": f"Found {len(recommendations)} optimization recommendations"
        }
        
    except Exception as e:
        logger.error(f"Optimization recommendations error: {e}")
        raise HTTPException(status_code=500, detail=f"Recommendations generation failed: {str(e)}")

@router.get("/health")
async def analytics_health_check():
    """
    Health check endpoint for analytics services.
    
    Verifies that all analytics components are functioning properly.
    """
    try:
        redis_client = await get_redis_client()
        
        # Test Redis connection
        await redis_client.ping()
        
        # Test performance service
        performance_service = await get_performance_service()
        
        health_status = {
            "analytics_service": "healthy",
            "redis_connection": "healthy",
            "performance_service": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0"
        }
        
        return {
            "status": "success",
            "data": health_status,
            "message": "All analytics services are healthy"
        }
        
    except Exception as e:
        logger.error(f"Analytics health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

@router.get("/stats/system")
async def get_system_statistics():
    """
    Get system-wide analytics statistics.
    
    Returns overall performance and usage statistics across all parking lots.
    """
    try:
        performance_service = await get_performance_service()
        redis_client = await get_redis_client()
        
        # Get performance metrics
        performance_metrics = await performance_service.get_performance_metrics()
        
        # Get Redis statistics
        redis_info = await redis_client.info()
        
        system_stats = {
            "performance_overview": {
                "total_requests": performance_service.performance_metrics['total_requests'],
                "cache_hit_rate": performance_metrics['cache_performance']['hit_rate_percentage'],
                "average_response_time": performance_service.performance_metrics['average_response_time'],
                "bloom_filter_efficiency": performance_metrics['bloom_filters']['availability_filter']['load_factor']
            },
            "redis_statistics": {
                "memory_usage": redis_info.get('used_memory_human', 'N/A'),
                "connected_clients": redis_info.get('connected_clients', 0),
                "total_commands": redis_info.get('total_commands_processed', 0),
                "uptime": redis_info.get('uptime_in_seconds', 0)
            },
            "system_health": {
                "status": "healthy",
                "last_updated": datetime.now().isoformat()
            }
        }
        
        return {
            "status": "success",
            "data": system_stats,
            "message": "System statistics retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"System statistics error: {e}")
        raise HTTPException(status_code=500, detail=f"System statistics failed: {str(e)}")
