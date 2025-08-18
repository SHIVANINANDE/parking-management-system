"""
Analytics Service - Step 6: Analytics & Optimization
Implements sliding window algorithms, occupancy pattern detection, and demand prediction.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from collections import deque, defaultdict
import json

import numpy as np
from scipy import stats, signal
from scipy.stats import poisson, norm
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error

from sqlalchemy.orm import Session
from sqlalchemy import text, func
import redis.asyncio as redis

from app.db.database import get_db
from app.models.parking_spot import ParkingSpot
from app.models.reservation import Reservation
from app.models.parking_lot import ParkingLot
from app.models.analytics import Analytics, OccupancyPattern, DemandForecast

logger = logging.getLogger(__name__)

class SlidingWindowAnalyzer:
    """Implements sliding window algorithms for real-time demand analysis."""
    
    def __init__(self, window_size: int = 100, step_size: int = 10):
        self.window_size = window_size
        self.step_size = step_size
        self.data_buffer = deque(maxlen=window_size * 2)  # Double buffer for overlap
        self.metrics_cache = {}
        
    def add_data_point(self, timestamp: datetime, parking_lot_id: str, 
                       occupied_spots: int, total_spots: int, demand_level: float):
        """Add new data point to sliding window."""
        data_point = {
            'timestamp': timestamp,
            'parking_lot_id': parking_lot_id,
            'occupied_spots': occupied_spots,
            'total_spots': total_spots,
            'occupancy_rate': occupied_spots / total_spots if total_spots > 0 else 0,
            'demand_level': demand_level
        }
        self.data_buffer.append(data_point)
        
        # Trigger analysis if window is full
        if len(self.data_buffer) >= self.window_size:
            return self._analyze_current_window()
        return None
    
    def _analyze_current_window(self) -> Dict[str, Any]:
        """Analyze current sliding window for patterns and metrics."""
        if len(self.data_buffer) < self.window_size:
            return {}
        
        # Extract recent window
        window_data = list(self.data_buffer)[-self.window_size:]
        
        # Convert to numpy arrays for efficient computation
        occupancy_rates = np.array([d['occupancy_rate'] for d in window_data])
        demand_levels = np.array([d['demand_level'] for d in window_data])
        timestamps = [d['timestamp'] for d in window_data]
        
        analysis = {
            'window_start': timestamps[0],
            'window_end': timestamps[-1],
            'mean_occupancy': np.mean(occupancy_rates),
            'std_occupancy': np.std(occupancy_rates),
            'peak_occupancy': np.max(occupancy_rates),
            'min_occupancy': np.min(occupancy_rates),
            'occupancy_trend': self._calculate_trend(occupancy_rates),
            'demand_volatility': np.std(demand_levels),
            'peak_periods': self._detect_peaks(occupancy_rates, timestamps),
            'pattern_score': self._calculate_pattern_score(occupancy_rates),
            'prediction_confidence': self._calculate_confidence(occupancy_rates)
        }
        
        return analysis
    
    def _calculate_trend(self, data: np.ndarray) -> float:
        """Calculate trend using linear regression."""
        if len(data) < 2:
            return 0.0
        
        x = np.arange(len(data))
        slope, _, r_value, _, _ = stats.linregress(x, data)
        return slope * (r_value ** 2)  # Weight by R-squared
    
    def _detect_peaks(self, data: np.ndarray, timestamps: List[datetime]) -> List[Dict]:
        """Detect peak usage periods using scipy signal processing."""
        if len(data) < 10:
            return []
        
        # Find peaks with minimum height and distance
        peaks, properties = signal.find_peaks(
            data, 
            height=np.mean(data) + 0.5 * np.std(data),
            distance=5
        )
        
        peak_periods = []
        for peak_idx in peaks:
            if peak_idx < len(timestamps):
                peak_periods.append({
                    'timestamp': timestamps[peak_idx],
                    'occupancy_rate': data[peak_idx],
                    'prominence': properties.get('prominences', [0])[0] if 'prominences' in properties else 0
                })
        
        return peak_periods
    
    def _calculate_pattern_score(self, data: np.ndarray) -> float:
        """Calculate pattern regularity score using autocorrelation."""
        if len(data) < 20:
            return 0.0
        
        # Calculate autocorrelation
        autocorr = np.correlate(data, data, mode='full')
        autocorr = autocorr[len(autocorr)//2:]
        
        # Find periodic patterns
        if len(autocorr) > 1:
            # Normalize and find secondary peaks
            autocorr_norm = autocorr / autocorr[0]
            secondary_peaks = autocorr_norm[1:20]  # Look for patterns in first 20 lags
            return np.max(secondary_peaks) if len(secondary_peaks) > 0 else 0.0
        
        return 0.0
    
    def _calculate_confidence(self, data: np.ndarray) -> float:
        """Calculate prediction confidence based on data stability."""
        if len(data) < 5:
            return 0.0
        
        # Calculate coefficient of variation (stability metric)
        cv = np.std(data) / np.mean(data) if np.mean(data) > 0 else float('inf')
        
        # Convert to confidence score (inverse relationship)
        confidence = 1.0 / (1.0 + cv)
        return min(1.0, max(0.0, confidence))

class OccupancyPatternDetector:
    """Detects and analyzes occupancy patterns using advanced statistical methods."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        self.pattern_cache = {}
        self.scaler = StandardScaler()
        
    async def detect_patterns(self, parking_lot_id: str, 
                            time_range: Tuple[datetime, datetime]) -> Dict[str, Any]:
        """Detect occupancy patterns for a specific parking lot and time range."""
        
        # Check cache first
        cache_key = f"occupancy_patterns:{parking_lot_id}:{time_range[0].date()}"
        cached_result = await self.redis_client.get(cache_key)
        if cached_result:
            return json.loads(cached_result)
        
        # Fetch historical data
        async with get_db() as db:
            occupancy_data = await self._fetch_occupancy_data(db, parking_lot_id, time_range)
        
        if not occupancy_data:
            return {}
        
        patterns = await self._analyze_patterns(occupancy_data)
        
        # Cache results for 1 hour
        await self.redis_client.setex(
            cache_key, 
            3600, 
            json.dumps(patterns, default=str)
        )
        
        return patterns
    
    async def _fetch_occupancy_data(self, db: Session, parking_lot_id: str, 
                                  time_range: Tuple[datetime, datetime]) -> List[Dict]:
        """Fetch occupancy data from database."""
        
        query = text("""
            SELECT 
                DATE_TRUNC('hour', r.start_time) as hour_slot,
                COUNT(*) as reservations_count,
                pl.total_spots,
                (COUNT(*) * 100.0 / pl.total_spots) as occupancy_percentage,
                EXTRACT(hour FROM r.start_time) as hour_of_day,
                EXTRACT(dow FROM r.start_time) as day_of_week
            FROM reservations r
            JOIN parking_lots pl ON r.parking_lot_id = pl.id
            WHERE r.parking_lot_id = :parking_lot_id
            AND r.start_time BETWEEN :start_time AND :end_time
            AND r.status = 'confirmed'
            GROUP BY 
                DATE_TRUNC('hour', r.start_time),
                pl.total_spots,
                EXTRACT(hour FROM r.start_time),
                EXTRACT(dow FROM r.start_time)
            ORDER BY hour_slot
        """)
        
        result = db.execute(query, {
            'parking_lot_id': parking_lot_id,
            'start_time': time_range[0],
            'end_time': time_range[1]
        })
        
        return [dict(row) for row in result.fetchall()]
    
    async def _analyze_patterns(self, data: List[Dict]) -> Dict[str, Any]:
        """Analyze occupancy patterns using statistical methods."""
        
        if not data:
            return {}
        
        df = pd.DataFrame(data)
        
        patterns = {
            'hourly_patterns': self._analyze_hourly_patterns(df),
            'daily_patterns': self._analyze_daily_patterns(df),
            'seasonal_patterns': self._analyze_seasonal_patterns(df),
            'anomalies': self._detect_anomalies(df),
            'trend_analysis': self._analyze_trends(df),
            'peak_characteristics': self._analyze_peak_characteristics(df)
        }
        
        return patterns
    
    def _analyze_hourly_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze hourly occupancy patterns."""
        
        hourly_stats = df.groupby('hour_of_day')['occupancy_percentage'].agg([
            'mean', 'std', 'min', 'max', 'count'
        ]).round(2)
        
        # Find peak hours
        peak_hours = hourly_stats['mean'].nlargest(3).index.tolist()
        
        # Find low utilization hours
        low_hours = hourly_stats['mean'].nsmallest(3).index.tolist()
        
        return {
            'hourly_averages': hourly_stats.to_dict(),
            'peak_hours': peak_hours,
            'low_utilization_hours': low_hours,
            'peak_occupancy': float(hourly_stats['mean'].max()),
            'off_peak_occupancy': float(hourly_stats['mean'].min()),
            'utilization_variance': float(hourly_stats['std'].mean())
        }
    
    def _analyze_daily_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze daily occupancy patterns (day of week)."""
        
        daily_stats = df.groupby('day_of_week')['occupancy_percentage'].agg([
            'mean', 'std', 'count'
        ]).round(2)
        
        # Map day numbers to names
        day_names = {0: 'Sunday', 1: 'Monday', 2: 'Tuesday', 3: 'Wednesday', 
                    4: 'Thursday', 5: 'Friday', 6: 'Saturday'}
        
        daily_named = {day_names[idx]: stats for idx, stats in daily_stats.iterrows()}
        
        busiest_days = daily_stats['mean'].nlargest(3).index.tolist()
        quietest_days = daily_stats['mean'].nsmallest(3).index.tolist()
        
        return {
            'daily_averages': daily_named,
            'busiest_days': [day_names[day] for day in busiest_days],
            'quietest_days': [day_names[day] for day in quietest_days],
            'weekday_vs_weekend': self._compare_weekday_weekend(df)
        }
    
    def _analyze_seasonal_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze seasonal patterns if sufficient data."""
        
        if len(df) < 30:  # Need at least a month of data
            return {'message': 'Insufficient data for seasonal analysis'}
        
        # Convert hour_slot to datetime if it's not already
        df['date'] = pd.to_datetime(df['hour_slot']).dt.date
        daily_occupancy = df.groupby('date')['occupancy_percentage'].mean()
        
        # Simple trend analysis
        x = np.arange(len(daily_occupancy))
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, daily_occupancy.values)
        
        return {
            'trend_slope': float(slope),
            'trend_direction': 'increasing' if slope > 0 else 'decreasing',
            'trend_strength': float(r_value ** 2),
            'trend_significance': float(p_value),
            'average_daily_occupancy': float(daily_occupancy.mean()),
            'occupancy_volatility': float(daily_occupancy.std())
        }
    
    def _detect_anomalies(self, df: pd.DataFrame) -> List[Dict]:
        """Detect anomalous occupancy patterns using statistical methods."""
        
        # Use IQR method for anomaly detection
        Q1 = df['occupancy_percentage'].quantile(0.25)
        Q3 = df['occupancy_percentage'].quantile(0.75)
        IQR = Q3 - Q1
        
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        anomalies = df[
            (df['occupancy_percentage'] < lower_bound) | 
            (df['occupancy_percentage'] > upper_bound)
        ]
        
        return [
            {
                'timestamp': row['hour_slot'],
                'occupancy_percentage': row['occupancy_percentage'],
                'type': 'high' if row['occupancy_percentage'] > upper_bound else 'low',
                'severity': abs(row['occupancy_percentage'] - df['occupancy_percentage'].mean()) / df['occupancy_percentage'].std()
            }
            for _, row in anomalies.iterrows()
        ]
    
    def _analyze_trends(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze long-term trends in occupancy."""
        
        if len(df) < 10:
            return {}
        
        # Sort by time
        df_sorted = df.sort_values('hour_slot')
        
        # Calculate moving averages
        occupancy_values = df_sorted['occupancy_percentage'].values
        
        # Short-term trend (last 25% of data)
        short_term_size = max(3, len(occupancy_values) // 4)
        short_term_data = occupancy_values[-short_term_size:]
        
        # Long-term trend (all data)
        x_all = np.arange(len(occupancy_values))
        x_short = np.arange(len(short_term_data))
        
        long_slope, _, long_r2, _, _ = stats.linregress(x_all, occupancy_values)
        short_slope, _, short_r2, _, _ = stats.linregress(x_short, short_term_data)
        
        return {
            'long_term_trend': {
                'slope': float(long_slope),
                'direction': 'increasing' if long_slope > 0 else 'decreasing',
                'strength': float(long_r2)
            },
            'short_term_trend': {
                'slope': float(short_slope),
                'direction': 'increasing' if short_slope > 0 else 'decreasing',
                'strength': float(short_r2)
            },
            'trend_consistency': float(np.corrcoef([long_slope], [short_slope])[0, 1])
        }
    
    def _analyze_peak_characteristics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze characteristics of peak usage periods."""
        
        mean_occupancy = df['occupancy_percentage'].mean()
        std_occupancy = df['occupancy_percentage'].std()
        
        # Define peaks as values above mean + 1 std
        peak_threshold = mean_occupancy + std_occupancy
        peaks = df[df['occupancy_percentage'] >= peak_threshold]
        
        if peaks.empty:
            return {'message': 'No significant peaks detected'}
        
        return {
            'peak_threshold': float(peak_threshold),
            'peak_frequency': len(peaks) / len(df),
            'average_peak_occupancy': float(peaks['occupancy_percentage'].mean()),
            'peak_duration_analysis': self._analyze_peak_duration(peaks),
            'peak_timing_patterns': {
                'common_peak_hours': peaks['hour_of_day'].value_counts().head(3).to_dict(),
                'common_peak_days': peaks['day_of_week'].value_counts().head(3).to_dict()
            }
        }
    
    def _analyze_peak_duration(self, peaks_df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze duration characteristics of peak periods."""
        
        if len(peaks_df) < 2:
            return {'message': 'Insufficient peak data for duration analysis'}
        
        # Sort by time
        peaks_sorted = peaks_df.sort_values('hour_slot')
        
        # Calculate gaps between consecutive peaks
        time_diffs = pd.to_datetime(peaks_sorted['hour_slot']).diff().dt.total_seconds() / 3600  # Convert to hours
        
        return {
            'average_gap_between_peaks_hours': float(time_diffs.mean()),
            'median_gap_between_peaks_hours': float(time_diffs.median()),
            'peak_clustering_tendency': float(1.0 / (1.0 + time_diffs.std())) if time_diffs.std() > 0 else 1.0
        }
    
    def _compare_weekday_weekend(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Compare weekday vs weekend patterns."""
        
        # 0 = Sunday, 6 = Saturday
        weekend_data = df[df['day_of_week'].isin([0, 6])]
        weekday_data = df[df['day_of_week'].isin([1, 2, 3, 4, 5])]
        
        if weekend_data.empty or weekday_data.empty:
            return {'message': 'Insufficient data for weekday/weekend comparison'}
        
        return {
            'weekday_average_occupancy': float(weekday_data['occupancy_percentage'].mean()),
            'weekend_average_occupancy': float(weekend_data['occupancy_percentage'].mean()),
            'weekday_peak_occupancy': float(weekday_data['occupancy_percentage'].max()),
            'weekend_peak_occupancy': float(weekend_data['occupancy_percentage'].max()),
            'preference': 'weekend' if weekend_data['occupancy_percentage'].mean() > weekday_data['occupancy_percentage'].mean() else 'weekday'
        }

class DemandPredictionEngine:
    """Advanced demand prediction using machine learning models."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        self.models = {
            'random_forest': RandomForestRegressor(n_estimators=100, random_state=42),
            'gradient_boosting': GradientBoostingRegressor(n_estimators=100, random_state=42),
            'linear_regression': LinearRegression()
        }
        self.scaler = StandardScaler()
        self.feature_columns = [
            'hour_of_day', 'day_of_week', 'is_weekend', 'month',
            'historical_avg', 'recent_trend', 'seasonal_factor'
        ]
        self.is_trained = False
        
    async def train_models(self, parking_lot_id: str, lookback_days: int = 90):
        """Train prediction models using historical data."""
        
        logger.info(f"Training demand prediction models for parking lot {parking_lot_id}")
        
        # Fetch training data
        async with get_db() as db:
            training_data = await self._prepare_training_data(db, parking_lot_id, lookback_days)
        
        if len(training_data) < 50:  # Need minimum data for training
            raise ValueError("Insufficient historical data for model training")
        
        # Prepare features and target
        X, y = self._prepare_features_target(training_data)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, shuffle=False
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train models and evaluate
        model_performance = {}
        
        for model_name, model in self.models.items():
            logger.info(f"Training {model_name}")
            
            # Train model
            model.fit(X_train_scaled, y_train)
            
            # Evaluate
            y_pred = model.predict(X_test_scaled)
            mae = mean_absolute_error(y_test, y_pred)
            rmse = np.sqrt(mean_squared_error(y_test, y_pred))
            
            model_performance[model_name] = {
                'mae': float(mae),
                'rmse': float(rmse),
                'train_score': float(model.score(X_train_scaled, y_train)),
                'test_score': float(model.score(X_test_scaled, y_test))
            }
            
            logger.info(f"{model_name} - MAE: {mae:.3f}, RMSE: {rmse:.3f}")
        
        self.is_trained = True
        
        # Cache model performance
        cache_key = f"model_performance:{parking_lot_id}"
        await self.redis_client.setex(
            cache_key,
            86400,  # 24 hours
            json.dumps(model_performance)
        )
        
        return model_performance
    
    async def _prepare_training_data(self, db: Session, parking_lot_id: str, 
                                   lookback_days: int) -> pd.DataFrame:
        """Prepare training data with features and target variable."""
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)
        
        query = text("""
            WITH hourly_occupancy AS (
                SELECT 
                    DATE_TRUNC('hour', r.start_time) as hour_slot,
                    COUNT(*) as demand,
                    pl.total_spots,
                    (COUNT(*) * 100.0 / pl.total_spots) as occupancy_percentage,
                    EXTRACT(hour FROM r.start_time) as hour_of_day,
                    EXTRACT(dow FROM r.start_time) as day_of_week,
                    EXTRACT(month FROM r.start_time) as month
                FROM reservations r
                JOIN parking_lots pl ON r.parking_lot_id = pl.id
                WHERE r.parking_lot_id = :parking_lot_id
                AND r.start_time BETWEEN :start_date AND :end_date
                AND r.status = 'confirmed'
                GROUP BY 
                    DATE_TRUNC('hour', r.start_time),
                    pl.total_spots,
                    EXTRACT(hour FROM r.start_time),
                    EXTRACT(dow FROM r.start_time),
                    EXTRACT(month FROM r.start_time)
                ORDER BY hour_slot
            )
            SELECT 
                hour_slot,
                demand,
                total_spots,
                occupancy_percentage,
                hour_of_day,
                day_of_week,
                month,
                CASE WHEN day_of_week IN (0, 6) THEN 1 ELSE 0 END as is_weekend
            FROM hourly_occupancy
        """)
        
        result = db.execute(query, {
            'parking_lot_id': parking_lot_id,
            'start_date': start_date,
            'end_date': end_date
        })
        
        df = pd.DataFrame([dict(row) for row in result.fetchall()])
        
        if df.empty:
            return df
        
        # Add engineered features
        df = self._engineer_features(df)
        
        return df
    
    def _engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Engineer additional features for better prediction."""
        
        # Sort by time
        df = df.sort_values('hour_slot').reset_index(drop=True)
        
        # Historical average for same hour and day
        df['historical_avg'] = df.groupby(['hour_of_day', 'day_of_week'])['demand'].transform('mean')
        
        # Recent trend (slope of last 7 days)
        df['recent_trend'] = df['demand'].rolling(window=min(168, len(df)), min_periods=10).apply(
            lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) >= 10 else 0
        )
        
        # Seasonal factor (monthly average vs overall average)
        monthly_avg = df.groupby('month')['demand'].transform('mean')
        overall_avg = df['demand'].mean()
        df['seasonal_factor'] = monthly_avg / overall_avg if overall_avg > 0 else 1.0
        
        # Fill NaN values
        df = df.fillna(method='ffill').fillna(0)
        
        return df
    
    def _prepare_features_target(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare feature matrix and target vector."""
        
        # Ensure we have the required columns
        missing_cols = set(self.feature_columns) - set(df.columns)
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        X = df[self.feature_columns].values
        y = df['demand'].values
        
        return X, y
    
    async def predict_demand(self, parking_lot_id: str, 
                           prediction_hours: int = 24,
                           use_ensemble: bool = True) -> Dict[str, Any]:
        """Predict future demand for specified hours ahead."""
        
        if not self.is_trained:
            raise ValueError("Models must be trained before making predictions")
        
        # Get recent data for context
        async with get_db() as db:
            recent_data = await self._get_recent_context(db, parking_lot_id)
        
        # Generate future time slots
        future_slots = self._generate_future_slots(prediction_hours)
        
        # Prepare features for prediction
        prediction_features = self._prepare_prediction_features(recent_data, future_slots)
        
        # Scale features
        X_pred_scaled = self.scaler.transform(prediction_features)
        
        # Generate predictions
        predictions = {}
        
        if use_ensemble:
            # Ensemble prediction (weighted average)
            weights = {'random_forest': 0.4, 'gradient_boosting': 0.4, 'linear_regression': 0.2}
            ensemble_pred = np.zeros(len(X_pred_scaled))
            
            for model_name, weight in weights.items():
                model_pred = self.models[model_name].predict(X_pred_scaled)
                ensemble_pred += weight * model_pred
            
            predictions['ensemble'] = ensemble_pred.tolist()
        
        # Individual model predictions
        for model_name, model in self.models.items():
            model_pred = model.predict(X_pred_scaled)
            predictions[model_name] = model_pred.tolist()
        
        # Add confidence intervals
        ensemble_pred = predictions.get('ensemble', predictions['random_forest'])
        confidence_intervals = self._calculate_confidence_intervals(ensemble_pred, X_pred_scaled)
        
        result = {
            'parking_lot_id': parking_lot_id,
            'prediction_timestamp': datetime.now().isoformat(),
            'prediction_horizon_hours': prediction_hours,
            'time_slots': [slot.isoformat() for slot in future_slots],
            'predictions': predictions,
            'confidence_intervals': confidence_intervals,
            'summary': {
                'peak_demand': float(max(ensemble_pred)),
                'average_demand': float(np.mean(ensemble_pred)),
                'peak_time': future_slots[np.argmax(ensemble_pred)].isoformat(),
                'demand_variance': float(np.var(ensemble_pred))
            }
        }
        
        # Cache predictions
        cache_key = f"demand_predictions:{parking_lot_id}:{prediction_hours}h"
        await self.redis_client.setex(
            cache_key,
            1800,  # 30 minutes
            json.dumps(result, default=str)
        )
        
        return result
    
    async def _get_recent_context(self, db: Session, parking_lot_id: str) -> pd.DataFrame:
        """Get recent data for prediction context."""
        
        end_time = datetime.now()
        start_time = end_time - timedelta(days=7)  # Last week for context
        
        query = text("""
            SELECT 
                DATE_TRUNC('hour', r.start_time) as hour_slot,
                COUNT(*) as demand,
                EXTRACT(hour FROM r.start_time) as hour_of_day,
                EXTRACT(dow FROM r.start_time) as day_of_week,
                EXTRACT(month FROM r.start_time) as month
            FROM reservations r
            WHERE r.parking_lot_id = :parking_lot_id
            AND r.start_time BETWEEN :start_time AND :end_time
            AND r.status = 'confirmed'
            GROUP BY 
                DATE_TRUNC('hour', r.start_time),
                EXTRACT(hour FROM r.start_time),
                EXTRACT(dow FROM r.start_time),
                EXTRACT(month FROM r.start_time)
            ORDER BY hour_slot DESC
            LIMIT 168  -- Last week's hourly data
        """)
        
        result = db.execute(query, {
            'parking_lot_id': parking_lot_id,
            'start_time': start_time,
            'end_time': end_time
        })
        
        df = pd.DataFrame([dict(row) for row in result.fetchall()])
        
        if not df.empty:
            df['is_weekend'] = df['day_of_week'].isin([0, 6]).astype(int)
            df = self._engineer_features(df)
        
        return df
    
    def _generate_future_slots(self, hours: int) -> List[datetime]:
        """Generate future time slots for prediction."""
        
        current_time = datetime.now().replace(minute=0, second=0, microsecond=0)
        future_slots = []
        
        for i in range(1, hours + 1):
            future_slot = current_time + timedelta(hours=i)
            future_slots.append(future_slot)
        
        return future_slots
    
    def _prepare_prediction_features(self, recent_data: pd.DataFrame, 
                                   future_slots: List[datetime]) -> np.ndarray:
        """Prepare features for future time slots."""
        
        features = []
        
        for slot in future_slots:
            hour_of_day = slot.hour
            day_of_week = slot.weekday()
            if day_of_week == 6:  # Sunday in pandas is 6, we want it as 0
                day_of_week = 0
            else:
                day_of_week += 1
            
            is_weekend = 1 if day_of_week in [0, 6] else 0
            month = slot.month
            
            # Calculate historical average from recent data
            if not recent_data.empty:
                similar_hours = recent_data[
                    (recent_data['hour_of_day'] == hour_of_day) & 
                    (recent_data['day_of_week'] == day_of_week)
                ]
                historical_avg = similar_hours['demand'].mean() if not similar_hours.empty else recent_data['demand'].mean()
                
                # Recent trend from last few data points
                recent_trend = recent_data['demand'].tail(10).diff().mean() if len(recent_data) >= 10 else 0
                
                # Seasonal factor
                monthly_data = recent_data[recent_data['month'] == month]
                seasonal_factor = monthly_data['demand'].mean() / recent_data['demand'].mean() if not monthly_data.empty and recent_data['demand'].mean() > 0 else 1.0
            else:
                historical_avg = 0
                recent_trend = 0
                seasonal_factor = 1.0
            
            features.append([
                hour_of_day,
                day_of_week,
                is_weekend,
                month,
                historical_avg,
                recent_trend,
                seasonal_factor
            ])
        
        return np.array(features)
    
    def _calculate_confidence_intervals(self, predictions: List[float], 
                                     features: np.ndarray) -> Dict[str, List[float]]:
        """Calculate confidence intervals for predictions."""
        
        # Simple confidence interval based on prediction uncertainty
        # In a production system, you'd use more sophisticated methods
        
        pred_array = np.array(predictions)
        
        # Estimate uncertainty based on feature similarity to training data
        # This is a simplified approach
        uncertainty = np.std(pred_array) * 0.5  # 50% of standard deviation as base uncertainty
        
        lower_bound = pred_array - 1.96 * uncertainty  # 95% confidence interval
        upper_bound = pred_array + 1.96 * uncertainty
        
        return {
            'lower_95': np.maximum(0, lower_bound).tolist(),  # Demand can't be negative
            'upper_95': upper_bound.tolist()
        }

class AnalyticsService:
    """Main analytics service coordinating all analytics components."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        self.sliding_window = SlidingWindowAnalyzer()
        self.pattern_detector = OccupancyPatternDetector(redis_client)
        self.demand_predictor = DemandPredictionEngine(redis_client)
        
    async def comprehensive_analysis(self, parking_lot_id: str, 
                                   analysis_period_days: int = 30) -> Dict[str, Any]:
        """Perform comprehensive analytics analysis for a parking lot."""
        
        logger.info(f"Starting comprehensive analysis for parking lot {parking_lot_id}")
        
        end_time = datetime.now()
        start_time = end_time - timedelta(days=analysis_period_days)
        
        # Run analyses in parallel
        tasks = [
            self.pattern_detector.detect_patterns(parking_lot_id, (start_time, end_time)),
            self._get_current_metrics(parking_lot_id),
            self._generate_optimization_recommendations(parking_lot_id)
        ]
        
        patterns, current_metrics, recommendations = await asyncio.gather(*tasks)
        
        # Train prediction models if enough data
        try:
            model_performance = await self.demand_predictor.train_models(parking_lot_id)
            
            # Generate predictions
            demand_forecast = await self.demand_predictor.predict_demand(parking_lot_id, 48)
        except ValueError as e:
            logger.warning(f"Could not train prediction models: {e}")
            model_performance = {}
            demand_forecast = {}
        
        comprehensive_report = {
            'parking_lot_id': parking_lot_id,
            'analysis_period': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat(),
                'days': analysis_period_days
            },
            'current_metrics': current_metrics,
            'occupancy_patterns': patterns,
            'demand_forecast': demand_forecast,
            'model_performance': model_performance,
            'optimization_recommendations': recommendations,
            'generated_at': datetime.now().isoformat()
        }
        
        # Cache comprehensive report
        cache_key = f"comprehensive_analysis:{parking_lot_id}"
        await self.redis_client.setex(
            cache_key,
            3600,  # 1 hour
            json.dumps(comprehensive_report, default=str)
        )
        
        logger.info(f"Comprehensive analysis completed for parking lot {parking_lot_id}")
        
        return comprehensive_report
    
    async def _get_current_metrics(self, parking_lot_id: str) -> Dict[str, Any]:
        """Get current real-time metrics."""
        
        async with get_db() as db:
            # Current occupancy
            current_query = text("""
                SELECT 
                    pl.total_spots,
                    COUNT(r.id) as occupied_spots,
                    (COUNT(r.id) * 100.0 / pl.total_spots) as current_occupancy_rate
                FROM parking_lots pl
                LEFT JOIN reservations r ON r.parking_lot_id = pl.id 
                    AND r.status = 'confirmed'
                    AND NOW() BETWEEN r.start_time AND r.end_time
                WHERE pl.id = :parking_lot_id
                GROUP BY pl.id, pl.total_spots
            """)
            
            result = db.execute(current_query, {'parking_lot_id': parking_lot_id})
            current_data = result.fetchone()
            
            if not current_data:
                return {}
            
            # Today's statistics
            today_query = text("""
                SELECT 
                    COUNT(*) as total_reservations_today,
                    AVG(EXTRACT(EPOCH FROM (end_time - start_time))/3600) as avg_duration_hours,
                    MAX(created_at) as last_reservation_time
                FROM reservations 
                WHERE parking_lot_id = :parking_lot_id 
                AND DATE(start_time) = CURRENT_DATE
                AND status = 'confirmed'
            """)
            
            today_result = db.execute(today_query, {'parking_lot_id': parking_lot_id})
            today_data = today_result.fetchone()
            
            return {
                'current_occupancy': {
                    'total_spots': int(current_data.total_spots),
                    'occupied_spots': int(current_data.occupied_spots),
                    'available_spots': int(current_data.total_spots - current_data.occupied_spots),
                    'occupancy_rate': float(current_data.current_occupancy_rate)
                },
                'today_statistics': {
                    'total_reservations': int(today_data.total_reservations_today) if today_data.total_reservations_today else 0,
                    'average_duration_hours': float(today_data.avg_duration_hours) if today_data.avg_duration_hours else 0,
                    'last_reservation': today_data.last_reservation_time.isoformat() if today_data.last_reservation_time else None
                }
            }
    
    async def _generate_optimization_recommendations(self, parking_lot_id: str) -> List[Dict[str, Any]]:
        """Generate optimization recommendations based on analysis."""
        
        recommendations = []
        
        # Get recent patterns
        end_time = datetime.now()
        start_time = end_time - timedelta(days=7)
        patterns = await self.pattern_detector.detect_patterns(parking_lot_id, (start_time, end_time))
        
        if not patterns:
            return recommendations
        
        # Analyze utilization efficiency
        hourly_patterns = patterns.get('hourly_patterns', {})
        if hourly_patterns:
            peak_occupancy = hourly_patterns.get('peak_occupancy', 0)
            off_peak_occupancy = hourly_patterns.get('off_peak_occupancy', 0)
            
            if peak_occupancy > 90:
                recommendations.append({
                    'type': 'capacity_optimization',
                    'priority': 'high',
                    'title': 'Peak Hour Congestion Detected',
                    'description': f'Occupancy reaches {peak_occupancy:.1f}% during peak hours',
                    'recommendation': 'Consider dynamic pricing during peak hours or capacity expansion',
                    'impact': 'Reduce congestion and improve user experience'
                })
            
            if off_peak_occupancy < 20:
                recommendations.append({
                    'type': 'utilization_optimization',
                    'priority': 'medium',
                    'title': 'Low Off-Peak Utilization',
                    'description': f'Occupancy drops to {off_peak_occupancy:.1f}% during off-peak hours',
                    'recommendation': 'Implement promotional pricing or alternative uses during off-peak hours',
                    'impact': 'Increase revenue and utilization efficiency'
                })
        
        # Analyze demand patterns
        daily_patterns = patterns.get('daily_patterns', {})
        if daily_patterns:
            weekday_weekend = daily_patterns.get('weekday_vs_weekend', {})
            if weekday_weekend:
                weekday_avg = weekday_weekend.get('weekday_average_occupancy', 0)
                weekend_avg = weekday_weekend.get('weekend_average_occupancy', 0)
                
                if abs(weekday_avg - weekend_avg) > 30:
                    recommendations.append({
                        'type': 'pricing_strategy',
                        'priority': 'medium',
                        'title': 'Weekday/Weekend Usage Imbalance',
                        'description': f'Significant difference in usage patterns: Weekday {weekday_avg:.1f}% vs Weekend {weekend_avg:.1f}%',
                        'recommendation': 'Implement differentiated pricing strategies for weekdays vs weekends',
                        'impact': 'Balance demand and optimize revenue'
                    })
        
        # Check for anomalies
        anomalies = patterns.get('anomalies', [])
        if len(anomalies) > 5:  # More than 5 anomalies in the period
            recommendations.append({
                'type': 'operational_optimization',
                'priority': 'medium',
                'title': 'Frequent Usage Anomalies Detected',
                'description': f'{len(anomalies)} unusual usage patterns detected',
                'recommendation': 'Review operational procedures and consider implementing automated anomaly alerts',
                'impact': 'Improve operational efficiency and customer satisfaction'
            })
        
        return recommendations
    
    async def get_real_time_analytics(self, parking_lot_id: str) -> Dict[str, Any]:
        """Get real-time analytics dashboard data."""
        
        # Check cache first
        cache_key = f"realtime_analytics:{parking_lot_id}"
        cached_data = await self.redis_client.get(cache_key)
        if cached_data:
            return json.loads(cached_data)
        
        current_metrics = await self._get_current_metrics(parking_lot_id)
        
        # Get hourly trends for today
        async with get_db() as db:
            hourly_trend_query = text("""
                SELECT 
                    EXTRACT(hour FROM start_time) as hour,
                    COUNT(*) as reservations,
                    AVG(EXTRACT(EPOCH FROM (end_time - start_time))/3600) as avg_duration
                FROM reservations 
                WHERE parking_lot_id = :parking_lot_id 
                AND DATE(start_time) = CURRENT_DATE
                AND status = 'confirmed'
                GROUP BY EXTRACT(hour FROM start_time)
                ORDER BY hour
            """)
            
            result = db.execute(hourly_trend_query, {'parking_lot_id': parking_lot_id})
            hourly_data = [dict(row) for row in result.fetchall()]
        
        real_time_data = {
            'parking_lot_id': parking_lot_id,
            'timestamp': datetime.now().isoformat(),
            'current_metrics': current_metrics,
            'hourly_trends_today': hourly_data,
            'status': 'active'
        }
        
        # Cache for 5 minutes
        await self.redis_client.setex(
            cache_key,
            300,
            json.dumps(real_time_data, default=str)
        )
        
        return real_time_data
