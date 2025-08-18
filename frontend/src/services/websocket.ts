import { io, Socket } from 'socket.io-client';
import { store } from '../store';
import type { RootState } from '../store';
import {
  setConnectionStatus,
  addMessage,
  addSpotUpdate,
  addLotUpdate,
  addAlert,
  updatePerformanceMetrics,
  addDebugLog,
  RealtimeMessage,
  SpotStatusUpdate,
  LotCapacityUpdate,
  SystemAlert,
  RealtimeState,
} from '../store/slices/realtimeSlice';
import { updateSpotStatus, updateMultipleSpots } from '../store/slices/mapSlice';
import { updateRealtimeData } from '../store/slices/analyticsSlice';
import { v4 as uuidv4 } from 'uuid';

interface WebSocketConfig {
  url: string;
  options?: {
    transports?: string[];
    upgrade?: boolean;
    rememberUpgrade?: boolean;
    timeout?: number;
    forceNew?: boolean;
    multiplex?: boolean;
    reconnection?: boolean;
    reconnectionAttempts?: number;
    reconnectionDelay?: number;
    reconnectionDelayMax?: number;
    randomizationFactor?: number;
  };
}

class WebSocketService {
  private sockets: Map<string, Socket> = new Map();
  private messageRate: number = 0;
  private messageCount: number = 0;
  private lastRateCalculation: number = Date.now();
  private performanceInterval?: number;

  constructor() {
    this.setupPerformanceTracking();
  }

  /**
   * Connect to a WebSocket endpoint
   */
  connect(connectionId: string, config: WebSocketConfig): Socket {
    // Disconnect existing connection if any
    this.disconnect(connectionId);

    store.dispatch(addDebugLog({
      level: 'info',
      message: `Attempting to connect to ${connectionId}`,
      data: { url: config.url }
    }));

    // Create new socket connection
    const socket = io(config.url, {
      transports: ['websocket'],
      upgrade: true,
      rememberUpgrade: true,
      timeout: 20000,
      forceNew: true,
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      randomizationFactor: 0.5,
      ...config.options,
    });

    // Store socket reference
    this.sockets.set(connectionId, socket);

    // Set up event handlers
    this.setupSocketEventHandlers(connectionId, socket);

    return socket;
  }

  /**
   * Disconnect from a WebSocket endpoint
   */
  disconnect(connectionId: string): void {
    const socket = this.sockets.get(connectionId);
    if (socket) {
      store.dispatch(addDebugLog({
        level: 'info',
        message: `Disconnecting from ${connectionId}`
      }));

      socket.disconnect();
      this.sockets.delete(connectionId);
      store.dispatch(setConnectionStatus({ connectionId: connectionId as any, status: 'disconnected' }));
    }
  }

  /**
   * Send message to a specific connection
   */
  emit(connectionId: string, event: string, data?: any): void {
    const socket = this.sockets.get(connectionId);
    if (socket && socket.connected) {
      socket.emit(event, data);
      
      store.dispatch(addDebugLog({
        level: 'debug',
        message: `Sent ${event} to ${connectionId}`,
        data
      }));
    } else {
      store.dispatch(addDebugLog({
        level: 'warn',
        message: `Cannot send ${event} to ${connectionId}: not connected`
      }));
    }
  }

  /**
   * Subscribe to specific event types
   */
  subscribe(connectionId: string, subscriptions: string[]): void {
    this.emit(connectionId, 'subscribe', { events: subscriptions });
  }

  /**
   * Unsubscribe from specific event types
   */
  unsubscribe(connectionId: string, subscriptions: string[]): void {
    this.emit(connectionId, 'unsubscribe', { events: subscriptions });
  }

  /**
   * Get connection status
   */
  getConnectionStatus(connectionId: string): string {
    const socket = this.sockets.get(connectionId);
    if (!socket) return 'disconnected';
    
    if (socket.connected) return 'connected';
    if (socket.disconnected) return 'disconnected';
    return 'connecting';
  }

  /**
   * Get all connection statuses
   */
  getAllConnectionStatuses(): Record<string, string> {
    const statuses: Record<string, string> = {};
    this.sockets.forEach((_, connectionId) => {
      statuses[connectionId] = this.getConnectionStatus(connectionId);
    });
    return statuses;
  }

  /**
   * Set up socket event handlers
   */
  private setupSocketEventHandlers(connectionId: string, socket: Socket): void {
    // Connection events
    socket.on('connect', () => {
      store.dispatch(setConnectionStatus({ connectionId: connectionId as any, status: 'connected' }));
      store.dispatch(addDebugLog({
        level: 'info',
        message: `Connected to ${connectionId}`,
        data: { socketId: socket.id }
      }));

      // Subscribe to default events based on connection type
      this.setupDefaultSubscriptions(connectionId);
    });

    socket.on('disconnect', (reason) => {
      store.dispatch(setConnectionStatus({ connectionId: connectionId as any, status: 'disconnected' }));
      store.dispatch(addDebugLog({
        level: 'warn',
        message: `Disconnected from ${connectionId}`,
        data: { reason }
      }));
    });

    socket.on('connect_error', (error) => {
      store.dispatch(setConnectionStatus({ connectionId: connectionId as any, status: 'error' }));
      store.dispatch(addDebugLog({
        level: 'error',
        message: `Connection error for ${connectionId}`,
        data: { error: error.message }
      }));
    });

    socket.on('reconnect', (attemptNumber) => {
      store.dispatch(addDebugLog({
        level: 'info',
        message: `Reconnected to ${connectionId}`,
        data: { attemptNumber }
      }));
    });

    socket.on('reconnect_attempt', (attemptNumber) => {
      store.dispatch(addDebugLog({
        level: 'debug',
        message: `Reconnection attempt ${attemptNumber} for ${connectionId}`
      }));
    });

    socket.on('reconnect_error', (error) => {
      store.dispatch(addDebugLog({
        level: 'error',
        message: `Reconnection error for ${connectionId}`,
        data: { error: error.message }
      }));
    });

    socket.on('reconnect_failed', () => {
      store.dispatch(addDebugLog({
        level: 'error',
        message: `Reconnection failed for ${connectionId}`
      }));
      store.dispatch(addAlert({
        id: uuidv4(),
        type: 'error',
        title: 'Connection Failed',
        message: `Failed to reconnect to ${connectionId}. Please check your internet connection.`,
        timestamp: new Date().toISOString(),
        autoHide: false,
      }));
    });

    // Data events
    socket.on('spot_status_update', (data: SpotStatusUpdate) => {
      this.handleSpotStatusUpdate(data);
    });

    socket.on('lot_capacity_update', (data: LotCapacityUpdate) => {
      this.handleLotCapacityUpdate(data);
    });

    socket.on('system_alert', (data: SystemAlert) => {
      this.handleSystemAlert(data);
    });

    socket.on('analytics_update', (data: any) => {
      this.handleAnalyticsUpdate(data);
    });

    socket.on('bulk_spot_updates', (data: { updates: SpotStatusUpdate[] }) => {
      this.handleBulkSpotUpdates(data.updates);
    });

    // Generic message handler
    socket.onAny((eventName: string, data: any) => {
      this.trackMessage();
      
      const message: RealtimeMessage = {
        id: uuidv4(),
        type: eventName as any,
        timestamp: new Date().toISOString(),
        data,
        processed: false,
      };

      store.dispatch(addMessage(message));
    });
  }

  /**
   * Set up default subscriptions based on connection type
   */
  private setupDefaultSubscriptions(connectionId: string): void {
    const state = store.getState() as RootState;
    const realtimeState = state.realtime as any;
    const subscriptions: string[] = [];

    if (realtimeState?.subscriptions?.spotUpdates && connectionId === 'main') {
      subscriptions.push('spot_status_update', 'bulk_spot_updates');
    }

    if (realtimeState?.subscriptions?.lotUpdates && connectionId === 'main') {
      subscriptions.push('lot_capacity_update');
    }

    if (realtimeState?.subscriptions?.reservationUpdates && connectionId === 'main') {
      subscriptions.push('reservation_update');
    }

    if (realtimeState?.subscriptions?.paymentUpdates && connectionId === 'main') {
      subscriptions.push('payment_update');
    }

    if (realtimeState?.subscriptions?.analyticsUpdates && connectionId === 'analytics') {
      subscriptions.push('analytics_update', 'performance_metrics');
    }

    if (realtimeState?.subscriptions?.systemAlerts && connectionId === 'notifications') {
      subscriptions.push('system_alert', 'notification');
    }

    if (subscriptions.length > 0) {
      this.subscribe(connectionId, subscriptions);
    }
  }

  /**
   * Handle spot status updates
   */
  private handleSpotStatusUpdate(data: SpotStatusUpdate): void {
    store.dispatch(addSpotUpdate(data));
    store.dispatch(updateSpotStatus({
      id: data.spotId,
      status: data.newStatus,
      lastUpdated: data.timestamp,
    }));

    store.dispatch(addDebugLog({
      level: 'debug',
      message: 'Spot status updated',
      data
    }));
  }

  /**
   * Handle bulk spot updates for efficiency
   */
  private handleBulkSpotUpdates(updates: SpotStatusUpdate[]): void {
    // Add all updates to the spot updates array
    updates.forEach(update => {
      store.dispatch(addSpotUpdate(update));
    });

    // Batch update map state
    const mapUpdates = updates.map(update => ({
      id: update.spotId,
      status: update.newStatus,
      lastUpdated: update.timestamp,
    }));

    store.dispatch(updateMultipleSpots(mapUpdates));

    store.dispatch(addDebugLog({
      level: 'debug',
      message: `Bulk spot updates processed`,
      data: { count: updates.length }
    }));
  }

  /**
   * Handle lot capacity updates
   */
  private handleLotCapacityUpdate(data: LotCapacityUpdate): void {
    store.dispatch(addLotUpdate(data));

    store.dispatch(addDebugLog({
      level: 'debug',
      message: 'Lot capacity updated',
      data
    }));
  }

  /**
   * Handle system alerts
   */
  private handleSystemAlert(data: SystemAlert): void {
    store.dispatch(addAlert({
      ...data,
      id: data.id || uuidv4(),
    }));

    store.dispatch(addDebugLog({
      level: 'info',
      message: 'System alert received',
      data
    }));
  }

  /**
   * Handle analytics updates
   */
  private handleAnalyticsUpdate(data: any): void {
    if (data.realtime) {
      store.dispatch(updateRealtimeData({
        occupancy: data.realtime.occupancy || 0,
        revenue: data.realtime.revenue || 0,
        sessions: data.realtime.sessions || 0,
        timestamp: new Date().toISOString(),
      }));
    }

    store.dispatch(addDebugLog({
      level: 'debug',
      message: 'Analytics data updated',
      data
    }));
  }

  /**
   * Track message rate for performance monitoring
   */
  private trackMessage(): void {
    this.messageCount++;
    const now = Date.now();
    const timeDiff = now - this.lastRateCalculation;

    // Calculate rate every 5 seconds
    if (timeDiff >= 5000) {
      this.messageRate = (this.messageCount / timeDiff) * 1000; // messages per second
      this.messageCount = 0;
      this.lastRateCalculation = now;

      store.dispatch(updatePerformanceMetrics({
        messageRate: this.messageRate,
      }));
    }
  }

  /**
   * Set up performance tracking
   */
  private setupPerformanceTracking(): void {
    this.performanceInterval = window.setInterval(() => {
      // Calculate connection uptime
      const connectedSockets = Array.from(this.sockets.values()).filter(s => s.connected);
      const totalUptime = connectedSockets.length > 0 ? Date.now() : 0;

      // Measure latency with a ping
      if (connectedSockets.length > 0) {
        const startTime = Date.now();
        connectedSockets[0].emit('ping', startTime, () => {
          const latency = Date.now() - startTime;
          store.dispatch(updatePerformanceMetrics({
            latency,
            uptime: totalUptime,
          }));
        });
      }
    }, 30000); // Every 30 seconds
  }

  /**
   * Cleanup resources
   */
  destroy(): void {
    // Disconnect all sockets
    this.sockets.forEach((_, connectionId) => {
      this.disconnect(connectionId);
    });

    // Clear performance tracking
    if (this.performanceInterval) {
      clearInterval(this.performanceInterval);
    }
  }
}

// Create singleton instance
export const webSocketService = new WebSocketService();

// Initialize default connections
export const initializeWebSockets = () => {
  const wsBaseUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

  // Main connection for parking data
  webSocketService.connect('main', {
    url: `${wsBaseUrl}/ws/main`,
    options: {
      transports: ['websocket'],
      timeout: 20000,
    },
  });

  // Analytics connection for analytics data
  webSocketService.connect('analytics', {
    url: `${wsBaseUrl}/ws/analytics`,
    options: {
      transports: ['websocket'],
      timeout: 20000,
    },
  });

  // Notifications connection for alerts and notifications
  webSocketService.connect('notifications', {
    url: `${wsBaseUrl}/ws/notifications`,
    options: {
      transports: ['websocket'],
      timeout: 20000,
    },
  });
};

export default webSocketService;
