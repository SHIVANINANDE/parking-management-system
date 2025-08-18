"""Add analytics and optimization tables

Revision ID: 005_analytics_optimization
Revises: 004_reservation_versioning
Create Date: 2025-08-18 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '005_analytics_optimization'
down_revision = '004_reservation_versioning'
branch_labels = None
depends_on = None


def upgrade():
    # Create occupancy_patterns table
    op.create_table(
        'occupancy_patterns',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('parking_lot_id', sa.Integer, sa.ForeignKey('parking_lots.id'), nullable=False),
        sa.Column('pattern_type', sa.String(50), nullable=False),
        sa.Column('pattern_name', sa.String(100)),
        sa.Column('confidence_score', sa.Float, default=0.0),
        sa.Column('time_context', postgresql.JSONB),
        sa.Column('recurring_schedule', postgresql.JSONB),
        sa.Column('expected_occupancy_rate', sa.Float, default=0.0),
        sa.Column('occupancy_variance', sa.Float, default=0.0),
        sa.Column('demand_level', sa.String(20)),
        sa.Column('historical_data_points', sa.Integer, default=0),
        sa.Column('pattern_strength', sa.Float, default=0.0),
        sa.Column('seasonal_factors', postgresql.JSONB),
        sa.Column('prediction_accuracy', sa.Float),
        sa.Column('last_validation_date', sa.DateTime),
        sa.Column('validation_count', sa.Integer, default=0),
        sa.Column('first_detected', sa.DateTime, default=sa.func.now()),
        sa.Column('last_observed', sa.DateTime, default=sa.func.now()),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('detection_algorithm', sa.String(50)),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now())
    )
    
    # Create demand_forecasts table
    op.create_table(
        'demand_forecasts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('parking_lot_id', sa.Integer, sa.ForeignKey('parking_lots.id'), nullable=False),
        sa.Column('forecast_created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('forecast_start_time', sa.DateTime, nullable=False),
        sa.Column('forecast_end_time', sa.DateTime, nullable=False),
        sa.Column('forecast_horizon_hours', sa.Integer, nullable=False),
        sa.Column('model_name', sa.String(50), nullable=False),
        sa.Column('model_version', sa.String(20), default='1.0'),
        sa.Column('training_data_points', sa.Integer),
        sa.Column('predicted_demand', postgresql.JSONB),
        sa.Column('confidence_intervals', postgresql.JSONB),
        sa.Column('peak_demand_time', sa.DateTime),
        sa.Column('peak_demand_value', sa.Float),
        sa.Column('prediction_confidence', sa.Float, default=0.0),
        sa.Column('weather_factors', postgresql.JSONB),
        sa.Column('event_factors', postgresql.JSONB),
        sa.Column('seasonal_adjustments', postgresql.JSONB),
        sa.Column('actual_demand', postgresql.JSONB),
        sa.Column('forecast_accuracy', sa.Float),
        sa.Column('accuracy_computed_at', sa.DateTime),
        sa.Column('mae_score', sa.Float),
        sa.Column('rmse_score', sa.Float),
        sa.Column('mape_score', sa.Float),
        sa.Column('status', sa.String(20), default='pending'),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now())
    )
    
    # Create performance_metrics table
    op.create_table(
        'performance_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('metric_category', sa.String(50), nullable=False),
        sa.Column('metric_name', sa.String(100), nullable=False),
        sa.Column('measurement_time', sa.DateTime, default=sa.func.now()),
        sa.Column('measurement_period_start', sa.DateTime),
        sa.Column('measurement_period_end', sa.DateTime),
        sa.Column('metric_value', sa.Float, nullable=False),
        sa.Column('metric_unit', sa.String(20)),
        sa.Column('context_data', postgresql.JSONB),
        sa.Column('baseline_value', sa.Float),
        sa.Column('target_value', sa.Float),
        sa.Column('performance_rating', sa.String(20)),
        sa.Column('aggregation_level', sa.String(20)),
        sa.Column('collection_method', sa.String(50)),
        sa.Column('created_at', sa.DateTime, default=sa.func.now())
    )
    
    # Create indexes for better query performance
    op.create_index('idx_occupancy_patterns_lot_type', 'occupancy_patterns', 
                   ['parking_lot_id', 'pattern_type'])
    op.create_index('idx_occupancy_patterns_active', 'occupancy_patterns', 
                   ['is_active', 'confidence_score'])
    
    op.create_index('idx_demand_forecasts_lot_time', 'demand_forecasts', 
                   ['parking_lot_id', 'forecast_start_time'])
    op.create_index('idx_demand_forecasts_status', 'demand_forecasts', 
                   ['status', 'model_name'])
    
    op.create_index('idx_performance_metrics_category', 'performance_metrics', 
                   ['metric_category', 'measurement_time'])
    op.create_index('idx_performance_metrics_rating', 'performance_metrics', 
                   ['performance_rating', 'metric_name'])
    
    # Add analytics optimization indexes to existing tables
    op.create_index('idx_reservations_analytics_optimized', 'reservations',
                   ['parking_lot_id', 'status', 'start_time', 'end_time'],
                   postgresql_where=sa.text("status = 'confirmed'"))
    
    op.create_index('idx_occupancy_analytics_period', 'occupancy_analytics',
                   ['parking_lot_id', 'period_type', 'analysis_date'])
    
    op.create_index('idx_revenue_analytics_period', 'revenue_analytics',
                   ['parking_lot_id', 'period_type', 'analysis_date'])


def downgrade():
    # Drop indexes
    op.drop_index('idx_revenue_analytics_period')
    op.drop_index('idx_occupancy_analytics_period')
    op.drop_index('idx_reservations_analytics_optimized')
    op.drop_index('idx_performance_metrics_rating')
    op.drop_index('idx_performance_metrics_category')
    op.drop_index('idx_demand_forecasts_status')
    op.drop_index('idx_demand_forecasts_lot_time')
    op.drop_index('idx_occupancy_patterns_active')
    op.drop_index('idx_occupancy_patterns_lot_type')
    
    # Drop tables
    op.drop_table('performance_metrics')
    op.drop_table('demand_forecasts')
    op.drop_table('occupancy_patterns')
