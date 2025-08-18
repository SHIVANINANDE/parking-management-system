import { createSlice, PayloadAction } from '@reduxjs/toolkit';

export interface OccupancyPattern {
  id: string;
  lotId: string;
  pattern: 'peak_hours' | 'seasonal' | 'weekend' | 'event_driven';
  timeRange: {
    start: string;
    end: string;
  };
  averageOccupancy: number;
  peakOccupancy: number;
  confidence: number;
  metadata: Record<string, any>;
}

export interface DemandForecast {
  id: string;
  lotId: string;
  timestamp: string;
  predictedOccupancy: number;
  confidence: number;
  modelType: 'random_forest' | 'gradient_boosting' | 'linear_regression';
  factors: {
    weather?: string;
    events?: string[];
    dayOfWeek: number;
    hour: number;
    historical: number;
  };
}

export interface PerformanceMetric {
  id: string;
  metricType: 'response_time' | 'cache_hit_rate' | 'database_connections' | 'memory_usage' | 'cpu_usage';
  value: number;
  timestamp: string;
  threshold?: number;
  status: 'normal' | 'warning' | 'critical';
  metadata: Record<string, any>;
}

export interface AnalyticsData {
  timeRange: {
    start: string;
    end: string;
  };
  occupancyTrends: Array<{
    timestamp: string;
    totalSpots: number;
    occupiedSpots: number;
    occupancyRate: number;
    lotBreakdown: Array<{
      lotId: string;
      occupiedSpots: number;
      totalSpots: number;
    }>;
  }>;
  revenueTrends: Array<{
    timestamp: string;
    totalRevenue: number;
    averageSessionDuration: number;
    totalSessions: number;
  }>;
  patterns: OccupancyPattern[];
  forecasts: DemandForecast[];
  performance: PerformanceMetric[];
}

export interface AnalyticsState {
  // Data
  data: AnalyticsData | null;
  isLoading: boolean;
  error: string | null;
  
  // Time range selection
  selectedTimeRange: {
    start: string;
    end: string;
    preset: 'hour' | 'day' | 'week' | 'month' | 'year' | 'custom';
  };
  
  // Chart configurations
  charts: {
    occupancy: {
      visible: boolean;
      type: 'line' | 'bar' | 'area';
      aggregation: 'hour' | 'day' | 'week';
    };
    revenue: {
      visible: boolean;
      type: 'line' | 'bar' | 'area';
      aggregation: 'hour' | 'day' | 'week';
    };
    performance: {
      visible: boolean;
      selectedMetrics: string[];
    };
    heatmap: {
      visible: boolean;
      metric: 'occupancy' | 'revenue' | 'duration';
    };
  };
  
  // Filters
  filters: {
    lotIds: string[];
    spotTypes: string[];
    includeWeekends: boolean;
    includeHolidays: boolean;
  };
  
  // Real-time analytics
  realtime: {
    enabled: boolean;
    currentOccupancy: number;
    currentRevenue: number;
    activeSessions: number;
    lastUpdate: string | null;
    updateInterval: number;
  };
  
  // Insights and alerts
  insights: Array<{
    id: string;
    type: 'trend' | 'anomaly' | 'prediction' | 'recommendation';
    title: string;
    description: string;
    severity: 'low' | 'medium' | 'high';
    timestamp: string;
    data: Record<string, any>;
  }>;
  
  // Exports and reports
  exports: {
    isExporting: boolean;
    format: 'pdf' | 'excel' | 'csv';
    includedSections: string[];
  };
}

const initialState: AnalyticsState = {
  data: null,
  isLoading: false,
  error: null,
  selectedTimeRange: {
    start: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(), // Last 24 hours
    end: new Date().toISOString(),
    preset: 'day',
  },
  charts: {
    occupancy: {
      visible: true,
      type: 'line',
      aggregation: 'hour',
    },
    revenue: {
      visible: true,
      type: 'line',
      aggregation: 'hour',
    },
    performance: {
      visible: false,
      selectedMetrics: ['response_time', 'cache_hit_rate'],
    },
    heatmap: {
      visible: false,
      metric: 'occupancy',
    },
  },
  filters: {
    lotIds: [],
    spotTypes: [],
    includeWeekends: true,
    includeHolidays: true,
  },
  realtime: {
    enabled: true,
    currentOccupancy: 0,
    currentRevenue: 0,
    activeSessions: 0,
    lastUpdate: null,
    updateInterval: 5000, // 5 seconds
  },
  insights: [],
  exports: {
    isExporting: false,
    format: 'pdf',
    includedSections: ['overview', 'trends', 'patterns'],
  },
};

const analyticsSlice = createSlice({
  name: 'analytics',
  initialState,
  reducers: {
    // Data loading
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.isLoading = action.payload;
    },
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
    },
    setAnalyticsData: (state, action: PayloadAction<AnalyticsData>) => {
      state.data = action.payload;
    },
    
    // Time range
    setTimeRange: (state, action: PayloadAction<{ start: string; end: string; preset: AnalyticsState['selectedTimeRange']['preset'] }>) => {
      state.selectedTimeRange = action.payload;
    },
    setTimeRangePreset: (state, action: PayloadAction<AnalyticsState['selectedTimeRange']['preset']>) => {
      const now = new Date();
      let start: Date;
      
      switch (action.payload) {
        case 'hour':
          start = new Date(now.getTime() - 60 * 60 * 1000);
          break;
        case 'day':
          start = new Date(now.getTime() - 24 * 60 * 60 * 1000);
          break;
        case 'week':
          start = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
          break;
        case 'month':
          start = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
          break;
        case 'year':
          start = new Date(now.getTime() - 365 * 24 * 60 * 60 * 1000);
          break;
        default:
          start = new Date(now.getTime() - 24 * 60 * 60 * 1000);
      }
      
      state.selectedTimeRange = {
        start: start.toISOString(),
        end: now.toISOString(),
        preset: action.payload,
      };
    },
    
    // Chart configurations
    setChartVisibility: (state, action: PayloadAction<{ chart: keyof AnalyticsState['charts']; visible: boolean }>) => {
      state.charts[action.payload.chart].visible = action.payload.visible;
    },
    setChartType: (state, action: PayloadAction<{ chart: 'occupancy' | 'revenue'; type: 'line' | 'bar' | 'area' }>) => {
      (state.charts[action.payload.chart] as any).type = action.payload.type;
    },
    setChartAggregation: (state, action: PayloadAction<{ chart: 'occupancy' | 'revenue'; aggregation: 'hour' | 'day' | 'week' }>) => {
      (state.charts[action.payload.chart] as any).aggregation = action.payload.aggregation;
    },
    setPerformanceMetrics: (state, action: PayloadAction<string[]>) => {
      state.charts.performance.selectedMetrics = action.payload;
    },
    setHeatmapMetric: (state, action: PayloadAction<'occupancy' | 'revenue' | 'duration'>) => {
      state.charts.heatmap.metric = action.payload;
    },
    
    // Filters
    setLotFilters: (state, action: PayloadAction<string[]>) => {
      state.filters.lotIds = action.payload;
    },
    setSpotTypeFilters: (state, action: PayloadAction<string[]>) => {
      state.filters.spotTypes = action.payload;
    },
    setIncludeWeekends: (state, action: PayloadAction<boolean>) => {
      state.filters.includeWeekends = action.payload;
    },
    setIncludeHolidays: (state, action: PayloadAction<boolean>) => {
      state.filters.includeHolidays = action.payload;
    },
    resetFilters: (state) => {
      state.filters = initialState.filters;
    },
    
    // Real-time data
    setRealtimeEnabled: (state, action: PayloadAction<boolean>) => {
      state.realtime.enabled = action.payload;
    },
    updateRealtimeData: (state, action: PayloadAction<{ 
      occupancy: number; 
      revenue: number; 
      sessions: number; 
      timestamp: string;
    }>) => {
      state.realtime.currentOccupancy = action.payload.occupancy;
      state.realtime.currentRevenue = action.payload.revenue;
      state.realtime.activeSessions = action.payload.sessions;
      state.realtime.lastUpdate = action.payload.timestamp;
    },
    setRealtimeUpdateInterval: (state, action: PayloadAction<number>) => {
      state.realtime.updateInterval = action.payload;
    },
    
    // Insights and alerts
    addInsight: (state, action: PayloadAction<AnalyticsState['insights'][0]>) => {
      state.insights.unshift(action.payload);
      // Keep only last 50 insights
      if (state.insights.length > 50) {
        state.insights = state.insights.slice(0, 50);
      }
    },
    removeInsight: (state, action: PayloadAction<string>) => {
      state.insights = state.insights.filter(insight => insight.id !== action.payload);
    },
    clearInsights: (state) => {
      state.insights = [];
    },
    
    // Export functionality
    setExportFormat: (state, action: PayloadAction<'pdf' | 'excel' | 'csv'>) => {
      state.exports.format = action.payload;
    },
    setExportSections: (state, action: PayloadAction<string[]>) => {
      state.exports.includedSections = action.payload;
    },
    setExporting: (state, action: PayloadAction<boolean>) => {
      state.exports.isExporting = action.payload;
    },
    
    // Data updates
    addOccupancyPattern: (state, action: PayloadAction<OccupancyPattern>) => {
      if (state.data) {
        state.data.patterns.push(action.payload);
      }
    },
    updateOccupancyPattern: (state, action: PayloadAction<OccupancyPattern>) => {
      if (state.data) {
        const index = state.data.patterns.findIndex(p => p.id === action.payload.id);
        if (index !== -1) {
          state.data.patterns[index] = action.payload;
        }
      }
    },
    addDemandForecast: (state, action: PayloadAction<DemandForecast>) => {
      if (state.data) {
        state.data.forecasts.push(action.payload);
        // Keep only latest 100 forecasts
        if (state.data.forecasts.length > 100) {
          state.data.forecasts = state.data.forecasts.slice(-100);
        }
      }
    },
    addPerformanceMetric: (state, action: PayloadAction<PerformanceMetric>) => {
      if (state.data) {
        state.data.performance.push(action.payload);
        // Keep only latest 1000 metrics
        if (state.data.performance.length > 1000) {
          state.data.performance = state.data.performance.slice(-1000);
        }
      }
    },
  },
});

export const {
  setLoading,
  setError,
  setAnalyticsData,
  setTimeRange,
  setTimeRangePreset,
  setChartVisibility,
  setChartType,
  setChartAggregation,
  setPerformanceMetrics,
  setHeatmapMetric,
  setLotFilters,
  setSpotTypeFilters,
  setIncludeWeekends,
  setIncludeHolidays,
  resetFilters,
  setRealtimeEnabled,
  updateRealtimeData,
  setRealtimeUpdateInterval,
  addInsight,
  removeInsight,
  clearInsights,
  setExportFormat,
  setExportSections,
  setExporting,
  addOccupancyPattern,
  updateOccupancyPattern,
  addDemandForecast,
  addPerformanceMetric,
} = analyticsSlice.actions;

export default analyticsSlice.reducer;
