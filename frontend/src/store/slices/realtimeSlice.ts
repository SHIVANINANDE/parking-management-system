import { createSlice, PayloadAction } from '@reduxjs/toolkit';

export interface RealtimeConnection {
  id: string;
  status: 'connecting' | 'connected' | 'disconnected' | 'error';
  url: string;
  lastConnected: string | null;
  reconnectAttempts: number;
  maxReconnectAttempts: number;
}

export interface RealtimeMessage {
  id: string;
  type: 'spot_status_update' | 'lot_capacity_update' | 'reservation_update' | 'payment_update' | 'analytics_update' | 'system_alert';
  timestamp: string;
  data: any;
  processed: boolean;
}

export interface SpotStatusUpdate {
  spotId: string;
  lotId: string;
  previousStatus: 'available' | 'occupied' | 'reserved' | 'maintenance';
  newStatus: 'available' | 'occupied' | 'reserved' | 'maintenance';
  timestamp: string;
  vehicleId?: string;
  reservationId?: string;
  userId?: string;
}

export interface LotCapacityUpdate {
  lotId: string;
  availableSpots: number;
  occupiedSpots: number;
  reservedSpots: number;
  maintenanceSpots: number;
  totalSpots: number;
  timestamp: string;
}

export interface SystemAlert {
  id: string;
  type: 'info' | 'warning' | 'error' | 'success';
  title: string;
  message: string;
  timestamp: string;
  autoHide: boolean;
  duration?: number;
  actions?: Array<{
    label: string;
    action: string;
    style: 'primary' | 'secondary' | 'danger';
  }>;
}

export interface RealtimeState {
  // Connection management
  connections: {
    main: RealtimeConnection;
    analytics: RealtimeConnection;
    notifications: RealtimeConnection;
  };
  
  // Message queue
  messageQueue: RealtimeMessage[];
  unprocessedMessages: number;
  
  // Real-time data
  spotUpdates: SpotStatusUpdate[];
  lotUpdates: LotCapacityUpdate[];
  
  // Notifications and alerts
  alerts: SystemAlert[];
  unreadAlerts: number;
  
  // Subscription management
  subscriptions: {
    spotUpdates: boolean;
    lotUpdates: boolean;
    reservationUpdates: boolean;
    paymentUpdates: boolean;
    analyticsUpdates: boolean;
    systemAlerts: boolean;
  };
  
  // Performance tracking
  performance: {
    messageRate: number; // messages per second
    averageLatency: number; // in milliseconds
    lastLatencyCheck: string | null;
    connectionUptime: number; // in seconds
  };
  
  // Settings
  settings: {
    autoReconnect: boolean;
    reconnectInterval: number;
    messageRetention: number; // number of messages to keep
    alertRetention: number; // number of alerts to keep
    enableDebugLogging: boolean;
  };
  
  // Debug information
  debug: {
    enabled: boolean;
    logs: Array<{
      timestamp: string;
      level: 'debug' | 'info' | 'warn' | 'error';
      message: string;
      data?: any;
    }>;
  };
}

const initialConnection: RealtimeConnection = {
  id: '',
  status: 'disconnected',
  url: '',
  lastConnected: null,
  reconnectAttempts: 0,
  maxReconnectAttempts: 5,
};

const initialState: RealtimeState = {
  connections: {
    main: { ...initialConnection, id: 'main', url: 'ws://localhost:8000/ws/main' },
    analytics: { ...initialConnection, id: 'analytics', url: 'ws://localhost:8000/ws/analytics' },
    notifications: { ...initialConnection, id: 'notifications', url: 'ws://localhost:8000/ws/notifications' },
  },
  messageQueue: [],
  unprocessedMessages: 0,
  spotUpdates: [],
  lotUpdates: [],
  alerts: [],
  unreadAlerts: 0,
  subscriptions: {
    spotUpdates: true,
    lotUpdates: true,
    reservationUpdates: true,
    paymentUpdates: false,
    analyticsUpdates: false,
    systemAlerts: true,
  },
  performance: {
    messageRate: 0,
    averageLatency: 0,
    lastLatencyCheck: null,
    connectionUptime: 0,
  },
  settings: {
    autoReconnect: true,
    reconnectInterval: 5000,
    messageRetention: 1000,
    alertRetention: 50,
    enableDebugLogging: false,
  },
  debug: {
    enabled: false,
    logs: [],
  },
};

const realtimeSlice = createSlice({
  name: 'realtime',
  initialState,
  reducers: {
    // Connection management
    setConnectionStatus: (state, action: PayloadAction<{ connectionId: keyof RealtimeState['connections']; status: RealtimeConnection['status'] }>) => {
      const connection = state.connections[action.payload.connectionId];
      connection.status = action.payload.status;
      
      if (action.payload.status === 'connected') {
        connection.lastConnected = new Date().toISOString();
        connection.reconnectAttempts = 0;
      } else if (action.payload.status === 'error') {
        connection.reconnectAttempts++;
      }
    },
    
    setConnectionUrl: (state, action: PayloadAction<{ connectionId: keyof RealtimeState['connections']; url: string }>) => {
      state.connections[action.payload.connectionId].url = action.payload.url;
    },
    
    incrementReconnectAttempts: (state, action: PayloadAction<keyof RealtimeState['connections']>) => {
      state.connections[action.payload].reconnectAttempts++;
    },
    
    resetReconnectAttempts: (state, action: PayloadAction<keyof RealtimeState['connections']>) => {
      state.connections[action.payload].reconnectAttempts = 0;
    },
    
    // Message handling
    addMessage: (state, action: PayloadAction<RealtimeMessage>) => {
      state.messageQueue.push(action.payload);
      if (!action.payload.processed) {
        state.unprocessedMessages++;
      }
      
      // Maintain message retention limit
      if (state.messageQueue.length > state.settings.messageRetention) {
        const removedMessage = state.messageQueue.shift();
        if (removedMessage && !removedMessage.processed) {
          state.unprocessedMessages--;
        }
      }
    },
    
    markMessageProcessed: (state, action: PayloadAction<string>) => {
      const message = state.messageQueue.find(m => m.id === action.payload);
      if (message && !message.processed) {
        message.processed = true;
        state.unprocessedMessages--;
      }
    },
    
    clearProcessedMessages: (state) => {
      state.messageQueue = state.messageQueue.filter(m => !m.processed);
    },
    
    // Spot updates
    addSpotUpdate: (state, action: PayloadAction<SpotStatusUpdate>) => {
      state.spotUpdates.push(action.payload);
      // Keep only last 100 updates
      if (state.spotUpdates.length > 100) {
        state.spotUpdates = state.spotUpdates.slice(-100);
      }
    },
    
    clearSpotUpdates: (state) => {
      state.spotUpdates = [];
    },
    
    // Lot updates
    addLotUpdate: (state, action: PayloadAction<LotCapacityUpdate>) => {
      // Replace existing update for the same lot or add new one
      const existingIndex = state.lotUpdates.findIndex(update => update.lotId === action.payload.lotId);
      if (existingIndex !== -1) {
        state.lotUpdates[existingIndex] = action.payload;
      } else {
        state.lotUpdates.push(action.payload);
      }
    },
    
    clearLotUpdates: (state) => {
      state.lotUpdates = [];
    },
    
    // Alerts and notifications
    addAlert: (state, action: PayloadAction<SystemAlert>) => {
      state.alerts.unshift(action.payload);
      state.unreadAlerts++;
      
      // Maintain alert retention limit
      if (state.alerts.length > state.settings.alertRetention) {
        state.alerts = state.alerts.slice(0, state.settings.alertRetention);
      }
    },
    
    markAlertRead: (state, action: PayloadAction<string>) => {
      const alert = state.alerts.find(a => a.id === action.payload);
      if (alert) {
        // Mark as read (we could add a 'read' property to SystemAlert interface)
        state.unreadAlerts = Math.max(0, state.unreadAlerts - 1);
      }
    },
    
    removeAlert: (state, action: PayloadAction<string>) => {
      const alertIndex = state.alerts.findIndex(a => a.id === action.payload);
      if (alertIndex !== -1) {
        state.alerts.splice(alertIndex, 1);
        state.unreadAlerts = Math.max(0, state.unreadAlerts - 1);
      }
    },
    
    clearAllAlerts: (state) => {
      state.alerts = [];
      state.unreadAlerts = 0;
    },
    
    markAllAlertsRead: (state) => {
      state.unreadAlerts = 0;
    },
    
    // Subscription management
    setSubscription: (state, action: PayloadAction<{ type: keyof RealtimeState['subscriptions']; enabled: boolean }>) => {
      state.subscriptions[action.payload.type] = action.payload.enabled;
    },
    
    toggleSubscription: (state, action: PayloadAction<keyof RealtimeState['subscriptions']>) => {
      state.subscriptions[action.payload] = !state.subscriptions[action.payload];
    },
    
    // Performance tracking
    updatePerformanceMetrics: (state, action: PayloadAction<{ 
      messageRate?: number; 
      latency?: number; 
      uptime?: number;
    }>) => {
      if (action.payload.messageRate !== undefined) {
        state.performance.messageRate = action.payload.messageRate;
      }
      if (action.payload.latency !== undefined) {
        state.performance.averageLatency = action.payload.latency;
        state.performance.lastLatencyCheck = new Date().toISOString();
      }
      if (action.payload.uptime !== undefined) {
        state.performance.connectionUptime = action.payload.uptime;
      }
    },
    
    // Settings
    updateSettings: (state, action: PayloadAction<Partial<RealtimeState['settings']>>) => {
      state.settings = { ...state.settings, ...action.payload };
    },
    
    setAutoReconnect: (state, action: PayloadAction<boolean>) => {
      state.settings.autoReconnect = action.payload;
    },
    
    setReconnectInterval: (state, action: PayloadAction<number>) => {
      state.settings.reconnectInterval = action.payload;
    },
    
    // Debug functionality
    enableDebug: (state, action: PayloadAction<boolean>) => {
      state.debug.enabled = action.payload;
      state.settings.enableDebugLogging = action.payload;
    },
    
    addDebugLog: (state, action: PayloadAction<{ 
      level: 'debug' | 'info' | 'warn' | 'error'; 
      message: string; 
      data?: any;
    }>) => {
      if (state.debug.enabled) {
        state.debug.logs.push({
          timestamp: new Date().toISOString(),
          level: action.payload.level,
          message: action.payload.message,
          data: action.payload.data,
        });
        
        // Keep only last 500 debug logs
        if (state.debug.logs.length > 500) {
          state.debug.logs = state.debug.logs.slice(-500);
        }
      }
    },
    
    clearDebugLogs: (state) => {
      state.debug.logs = [];
    },
    
    // Utility actions
    resetState: (state) => {
      // Keep connection URLs but reset everything else
      const urls = {
        main: state.connections.main.url,
        analytics: state.connections.analytics.url,
        notifications: state.connections.notifications.url,
      };
      
      Object.assign(state, initialState);
      
      state.connections.main.url = urls.main;
      state.connections.analytics.url = urls.analytics;
      state.connections.notifications.url = urls.notifications;
    },
  },
});

export const {
  setConnectionStatus,
  setConnectionUrl,
  incrementReconnectAttempts,
  resetReconnectAttempts,
  addMessage,
  markMessageProcessed,
  clearProcessedMessages,
  addSpotUpdate,
  clearSpotUpdates,
  addLotUpdate,
  clearLotUpdates,
  addAlert,
  markAlertRead,
  removeAlert,
  clearAllAlerts,
  markAllAlertsRead,
  setSubscription,
  toggleSubscription,
  updatePerformanceMetrics,
  updateSettings,
  setAutoReconnect,
  setReconnectInterval,
  enableDebug,
  addDebugLog,
  clearDebugLogs,
  resetState,
} = realtimeSlice.actions;

export default realtimeSlice.reducer;
