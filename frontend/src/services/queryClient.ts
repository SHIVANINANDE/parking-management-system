import { QueryClient, DefaultOptions } from '@tanstack/react-query';

// Default options for all queries
const queryConfig: DefaultOptions = {
  queries: {
    // Time before data is considered stale
    staleTime: 5 * 60 * 1000, // 5 minutes
    
    // Time before inactive queries are garbage collected
    gcTime: 10 * 60 * 1000, // 10 minutes (formerly cacheTime)
    
    // Retry failed requests
    retry: (failureCount, error: any) => {
      // Don't retry on 4xx errors except 429 (rate limit)
      if (error?.response?.status >= 400 && error?.response?.status < 500 && error?.response?.status !== 429) {
        return false;
      }
      // Retry up to 3 times for other errors
      return failureCount < 3;
    },
    
    // Retry delay with exponential backoff
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    
    // Refetch on window focus for critical data
    refetchOnWindowFocus: true,
    
    // Refetch on reconnect
    refetchOnReconnect: true,
    
    // Refetch on mount if data is stale
    refetchOnMount: true,
  },
  mutations: {
    // Retry failed mutations
    retry: 1,
    
    // Retry delay for mutations
    retryDelay: 1000,
  },
};

// Create the query client
export const queryClient = new QueryClient({
  defaultOptions: queryConfig,
});

// Query keys for consistent caching
export const queryKeys = {
  // Authentication
  auth: {
    user: ['auth', 'user'] as const,
    permissions: ['auth', 'permissions'] as const,
  },
  
  // Parking lots
  parkingLots: {
    all: ['parking-lots'] as const,
    list: (filters?: any) => ['parking-lots', 'list', filters] as const,
    detail: (id: string) => ['parking-lots', 'detail', id] as const,
    spots: (lotId: string) => ['parking-lots', 'spots', lotId] as const,
    availability: (lotId: string) => ['parking-lots', 'availability', lotId] as const,
    search: (query: string, filters?: any) => ['parking-lots', 'search', query, filters] as const,
  },
  
  // Parking spots
  parkingSpots: {
    all: ['parking-spots'] as const,
    list: (filters?: any) => ['parking-spots', 'list', filters] as const,
    detail: (id: string) => ['parking-spots', 'detail', id] as const,
    status: (id: string) => ['parking-spots', 'status', id] as const,
    nearby: (lat: number, lng: number, radius: number) => 
      ['parking-spots', 'nearby', lat, lng, radius] as const,
  },
  
  // Reservations
  reservations: {
    all: ['reservations'] as const,
    list: (filters?: any) => ['reservations', 'list', filters] as const,
    detail: (id: string) => ['reservations', 'detail', id] as const,
    user: (userId: string) => ['reservations', 'user', userId] as const,
    current: ['reservations', 'current'] as const,
    history: (userId: string) => ['reservations', 'history', userId] as const,
  },
  
  // Payments
  payments: {
    all: ['payments'] as const,
    list: (filters?: any) => ['payments', 'list', filters] as const,
    detail: (id: string) => ['payments', 'detail', id] as const,
    user: (userId: string) => ['payments', 'user', userId] as const,
    methods: ['payments', 'methods'] as const,
  },
  
  // Analytics
  analytics: {
    all: ['analytics'] as const,
    comprehensive: (timeRange: { start: string; end: string }) => 
      ['analytics', 'comprehensive', timeRange] as const,
    occupancy: (timeRange: { start: string; end: string }, lotIds?: string[]) => 
      ['analytics', 'occupancy', timeRange, lotIds] as const,
    revenue: (timeRange: { start: string; end: string }, lotIds?: string[]) => 
      ['analytics', 'revenue', timeRange, lotIds] as const,
    patterns: (lotId?: string) => ['analytics', 'patterns', lotId] as const,
    forecasts: (lotId: string, hours: number) => 
      ['analytics', 'forecasts', lotId, hours] as const,
    performance: ['analytics', 'performance'] as const,
    realtime: ['analytics', 'realtime'] as const,
  },
  
  // User management
  users: {
    all: ['users'] as const,
    list: (filters?: any) => ['users', 'list', filters] as const,
    detail: (id: string) => ['users', 'detail', id] as const,
    profile: ['users', 'profile'] as const,
    vehicles: (userId: string) => ['users', 'vehicles', userId] as const,
  },
  
  // Vehicles
  vehicles: {
    all: ['vehicles'] as const,
    list: (userId: string) => ['vehicles', 'list', userId] as const,
    detail: (id: string) => ['vehicles', 'detail', id] as const,
  },
  
  // System
  system: {
    health: ['system', 'health'] as const,
    config: ['system', 'config'] as const,
    notifications: ['system', 'notifications'] as const,
  },
} as const;

// Utility functions for query management
export const queryUtils = {
  // Invalidate all parking lot related queries
  invalidateParkingLots: () => {
    queryClient.invalidateQueries({ queryKey: queryKeys.parkingLots.all });
  },
  
  // Invalidate specific parking lot
  invalidateParkingLot: (lotId: string) => {
    queryClient.invalidateQueries({ queryKey: queryKeys.parkingLots.detail(lotId) });
    queryClient.invalidateQueries({ queryKey: queryKeys.parkingLots.spots(lotId) });
    queryClient.invalidateQueries({ queryKey: queryKeys.parkingLots.availability(lotId) });
  },
  
  // Update parking spot status optimistically
  updateSpotStatus: (spotId: string, newStatus: 'available' | 'occupied' | 'reserved' | 'maintenance') => {
    // Update spot detail cache
    queryClient.setQueryData(
      queryKeys.parkingSpots.detail(spotId),
      (old: any) => old ? { ...old, status: newStatus, lastUpdated: new Date().toISOString() } : old
    );
    
    // Update spot status cache
    queryClient.setQueryData(
      queryKeys.parkingSpots.status(spotId),
      { status: newStatus, lastUpdated: new Date().toISOString() }
    );
    
    // Invalidate related queries
    queryClient.invalidateQueries({ queryKey: queryKeys.parkingSpots.list() });
    queryClient.invalidateQueries({ queryKey: queryKeys.analytics.realtime });
  },
  
  // Update parking lot availability
  updateLotAvailability: (lotId: string, availability: { available: number; total: number }) => {
    queryClient.setQueryData(
      queryKeys.parkingLots.availability(lotId),
      availability
    );
    
    // Update lot detail cache
    queryClient.setQueryData(
      queryKeys.parkingLots.detail(lotId),
      (old: any) => old ? { 
        ...old, 
        availableSpots: availability.available,
        totalSpots: availability.total,
        lastUpdated: new Date().toISOString()
      } : old
    );
  },
  
  // Prefetch parking lot details
  prefetchParkingLot: (lotId: string) => {
    queryClient.prefetchQuery({
      queryKey: queryKeys.parkingLots.detail(lotId),
      staleTime: 2 * 60 * 1000, // 2 minutes
    });
  },
  
  // Remove user data on logout
  clearUserData: () => {
    queryClient.removeQueries({ queryKey: queryKeys.auth.user });
    queryClient.removeQueries({ queryKey: queryKeys.reservations.current });
    queryClient.removeQueries({ queryKey: queryKeys.users.profile });
    queryClient.removeQueries({ queryKey: ['reservations', 'user'] });
    queryClient.removeQueries({ queryKey: ['payments', 'user'] });
    queryClient.removeQueries({ queryKey: ['vehicles', 'list'] });
  },
  
  // Refresh critical data
  refreshCriticalData: () => {
    queryClient.invalidateQueries({ queryKey: queryKeys.parkingLots.all });
    queryClient.invalidateQueries({ queryKey: queryKeys.analytics.realtime });
    queryClient.invalidateQueries({ queryKey: queryKeys.reservations.current });
  },
  
  // Get cached data
  getCachedParkingLots: () => {
    return queryClient.getQueryData(queryKeys.parkingLots.list());
  },
  
  getCachedUserProfile: () => {
    return queryClient.getQueryData(queryKeys.users.profile);
  },
  
  // Check if data exists in cache
  hasCachedData: (queryKey: any[]) => {
    return queryClient.getQueryState(queryKey)?.data !== undefined;
  },
  
  // Manually set cache data
  setCacheData: (queryKey: any[], data: any) => {
    queryClient.setQueryData(queryKey, data);
  },
  
  // Background refresh for specific data
  backgroundRefresh: (queryKey: any[]) => {
    queryClient.invalidateQueries({ 
      queryKey, 
      refetchType: 'active' // Only refetch if component is mounted
    });
  },
};

// Error handling utilities
export const queryErrorUtils = {
  // Check if error is a network error
  isNetworkError: (error: any) => {
    return !error?.response && error?.code !== 'ABORT_ERR';
  },
  
  // Check if error is unauthorized
  isUnauthorizedError: (error: any) => {
    return error?.response?.status === 401;
  },
  
  // Check if error is forbidden
  isForbiddenError: (error: any) => {
    return error?.response?.status === 403;
  },
  
  // Check if error is a server error
  isServerError: (error: any) => {
    return error?.response?.status >= 500;
  },
  
  // Get user-friendly error message
  getErrorMessage: (error: any) => {
    if (queryErrorUtils.isNetworkError(error)) {
      return 'Network connection error. Please check your internet connection.';
    }
    
    if (queryErrorUtils.isUnauthorizedError(error)) {
      return 'Your session has expired. Please log in again.';
    }
    
    if (queryErrorUtils.isForbiddenError(error)) {
      return 'You do not have permission to perform this action.';
    }
    
    if (queryErrorUtils.isServerError(error)) {
      return 'Server error. Please try again later.';
    }
    
    return error?.response?.data?.message || error?.message || 'An unexpected error occurred.';
  },
};

export default queryClient;
