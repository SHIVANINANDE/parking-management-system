import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';

// API Configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
const TIMEOUT = 10000; // 10 seconds

// Create axios instance with default configuration
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for adding auth token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('accessToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for handling common errors
apiClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error) => {
    const originalRequest = error.config;

    // Handle 401 errors (unauthorized)
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      // Try to refresh token
      const refreshToken = localStorage.getItem('refreshToken');
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          });
          
          const { access_token } = response.data;
          localStorage.setItem('accessToken', access_token);
          
          // Retry original request with new token
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return apiClient(originalRequest);
        } catch (refreshError) {
          // Refresh failed, redirect to login
          localStorage.removeItem('accessToken');
          localStorage.removeItem('refreshToken');
          window.location.href = '/login';
        }
      } else {
        // No refresh token, redirect to login
        localStorage.removeItem('accessToken');
        window.location.href = '/login';
      }
    }

    return Promise.reject(error);
  }
);

// Generic API methods
const api = {
  get: <T>(url: string, config?: AxiosRequestConfig): Promise<T> =>
    apiClient.get(url, config).then((response) => response.data),
  
  post: <T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> =>
    apiClient.post(url, data, config).then((response) => response.data),
  
  put: <T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> =>
    apiClient.put(url, data, config).then((response) => response.data),
  
  patch: <T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> =>
    apiClient.patch(url, data, config).then((response) => response.data),
  
  delete: <T>(url: string, config?: AxiosRequestConfig): Promise<T> =>
    apiClient.delete(url, config).then((response) => response.data),
};

// Type definitions
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface User {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  phone?: string;
  role: 'user' | 'admin' | 'operator';
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface ParkingLot {
  id: string;
  name: string;
  address: string;
  latitude: number;
  longitude: number;
  totalSpots: number;
  availableSpots: number;
  occupiedSpots: number;
  reservedSpots: number;
  maintenanceSpots: number;
  hourlyRate: number;
  dailyRate: number;
  monthlyRate: number;
  operatingHours: {
    open: string;
    close: string;
  };
  amenities: string[];
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface ParkingSpot {
  id: string;
  spotNumber: string;
  parkingLotId: string;
  type: 'standard' | 'disabled' | 'electric' | 'compact';
  status: 'available' | 'occupied' | 'reserved' | 'maintenance';
  zone: string;
  isActive: boolean;
  lastUpdated: string;
  createdAt: string;
  updatedAt: string;
}

export interface Reservation {
  id: string;
  userId: string;
  parkingSpotId: string;
  vehicleId: string;
  startTime: string;
  endTime: string;
  status: 'pending' | 'confirmed' | 'active' | 'completed' | 'cancelled';
  totalAmount: number;
  paymentStatus: 'pending' | 'completed' | 'failed' | 'refunded';
  createdAt: string;
  updatedAt: string;
  parkingSpot?: ParkingSpot;
  vehicle?: Vehicle;
}

export interface Vehicle {
  id: string;
  userId: string;
  licensePlate: string;
  make: string;
  model: string;
  year: number;
  color: string;
  type: 'car' | 'motorcycle' | 'truck' | 'van';
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface Payment {
  id: string;
  reservationId: string;
  amount: number;
  currency: string;
  method: 'credit_card' | 'debit_card' | 'cash' | 'mobile_payment';
  status: 'pending' | 'completed' | 'failed' | 'refunded';
  transactionId?: string;
  processedAt?: string;
  createdAt: string;
  updatedAt: string;
}

// Authentication API
export const authAPI = {
  login: (email: string, password: string) =>
    api.post<{ access_token: string; refresh_token: string; user: User }>('/auth/login', {
      email,
      password,
    }),
  
  register: (userData: {
    email: string;
    password: string;
    firstName: string;
    lastName: string;
    phone?: string;
  }) => api.post<{ user: User }>('/auth/register', userData),
  
  refreshToken: (refreshToken: string) =>
    api.post<{ access_token: string }>('/auth/refresh', {
      refresh_token: refreshToken,
    }),
  
  logout: () => api.post('/auth/logout'),
  
  getCurrentUser: () => api.get<User>('/auth/me'),
  
  forgotPassword: (email: string) =>
    api.post('/auth/forgot-password', { email }),
  
  resetPassword: (token: string, password: string) =>
    api.post('/auth/reset-password', { token, password }),
};

// Parking Lots API
export const parkingLotsAPI = {
  getAll: (params?: {
    page?: number;
    size?: number;
    search?: string;
    city?: string;
    amenities?: string[];
  }) => api.get<PaginatedResponse<ParkingLot>>('/parking-lots', { params }),
  
  getById: (id: string) => api.get<ParkingLot>(`/parking-lots/${id}`),
  
  create: (data: Omit<ParkingLot, 'id' | 'createdAt' | 'updatedAt' | 'availableSpots' | 'occupiedSpots' | 'reservedSpots' | 'maintenanceSpots'>) =>
    api.post<ParkingLot>('/parking-lots', data),
  
  update: (id: string, data: Partial<ParkingLot>) =>
    api.patch<ParkingLot>(`/parking-lots/${id}`, data),
  
  delete: (id: string) => api.delete(`/parking-lots/${id}`),
  
  getSpots: (lotId: string, params?: {
    status?: string[];
    type?: string[];
    zone?: string;
  }) => api.get<ParkingSpot[]>(`/parking-lots/${lotId}/spots`, { params }),
  
  getAvailability: (lotId: string) =>
    api.get<{
      totalSpots: number;
      availableSpots: number;
      occupiedSpots: number;
      reservedSpots: number;
      maintenanceSpots: number;
    }>(`/parking-lots/${lotId}/availability`),
  
  search: (params: {
    latitude: number;
    longitude: number;
    radius?: number;
    startTime?: string;
    endTime?: string;
    spotType?: string[];
    amenities?: string[];
  }) => api.get<ParkingLot[]>('/parking-lots/search', { params }),
};

// Parking Spots API
export const parkingSpotsAPI = {
  getAll: (params?: {
    page?: number;
    size?: number;
    lotId?: string;
    status?: string[];
    type?: string[];
  }) => api.get<PaginatedResponse<ParkingSpot>>('/parking-spots', { params }),
  
  getById: (id: string) => api.get<ParkingSpot>(`/parking-spots/${id}`),
  
  create: (data: Omit<ParkingSpot, 'id' | 'createdAt' | 'updatedAt' | 'lastUpdated'>) =>
    api.post<ParkingSpot>('/parking-spots', data),
  
  update: (id: string, data: Partial<ParkingSpot>) =>
    api.patch<ParkingSpot>(`/parking-spots/${id}`, data),
  
  delete: (id: string) => api.delete(`/parking-spots/${id}`),
  
  updateStatus: (id: string, status: ParkingSpot['status']) =>
    api.patch<ParkingSpot>(`/parking-spots/${id}/status`, { status }),
  
  getNearby: (latitude: number, longitude: number, radius: number = 1000) =>
    api.get<ParkingSpot[]>('/parking-spots/nearby', {
      params: { latitude, longitude, radius },
    }),
};

// Reservations API
export const reservationsAPI = {
  getAll: (params?: {
    page?: number;
    size?: number;
    userId?: string;
    status?: string[];
    startDate?: string;
    endDate?: string;
  }) => api.get<PaginatedResponse<Reservation>>('/reservations', { params }),
  
  getById: (id: string) => api.get<Reservation>(`/reservations/${id}`),
  
  create: (data: {
    parkingSpotId: string;
    vehicleId: string;
    startTime: string;
    endTime: string;
  }) => api.post<Reservation>('/reservations', data),
  
  update: (id: string, data: Partial<Reservation>) =>
    api.patch<Reservation>(`/reservations/${id}`, data),
  
  cancel: (id: string) => api.patch<Reservation>(`/reservations/${id}/cancel`),
  
  confirm: (id: string) => api.patch<Reservation>(`/reservations/${id}/confirm`),
  
  complete: (id: string) => api.patch<Reservation>(`/reservations/${id}/complete`),
  
  getCurrentUserReservations: () => api.get<Reservation[]>('/reservations/me'),
  
  getUserHistory: (userId?: string) => 
    api.get<Reservation[]>(`/reservations/${userId ? `user/${userId}` : 'me'}/history`),
};

// Vehicles API
export const vehiclesAPI = {
  getAll: (userId?: string) => 
    api.get<Vehicle[]>(`/vehicles${userId ? `?userId=${userId}` : ''}`),
  
  getById: (id: string) => api.get<Vehicle>(`/vehicles/${id}`),
  
  create: (data: Omit<Vehicle, 'id' | 'userId' | 'createdAt' | 'updatedAt'>) =>
    api.post<Vehicle>('/vehicles', data),
  
  update: (id: string, data: Partial<Vehicle>) =>
    api.patch<Vehicle>(`/vehicles/${id}`, data),
  
  delete: (id: string) => api.delete(`/vehicles/${id}`),
  
  getUserVehicles: () => api.get<Vehicle[]>('/vehicles/me'),
};

// Payments API
export const paymentsAPI = {
  getAll: (params?: {
    page?: number;
    size?: number;
    userId?: string;
    status?: string[];
    method?: string[];
  }) => api.get<PaginatedResponse<Payment>>('/payments', { params }),
  
  getById: (id: string) => api.get<Payment>(`/payments/${id}`),
  
  create: (data: {
    reservationId: string;
    amount: number;
    method: Payment['method'];
  }) => api.post<Payment>('/payments', data),
  
  processPayment: (id: string, paymentData: any) =>
    api.post<Payment>(`/payments/${id}/process`, paymentData),
  
  refund: (id: string, amount?: number) =>
    api.post<Payment>(`/payments/${id}/refund`, { amount }),
  
  getUserPayments: () => api.get<Payment[]>('/payments/me'),
};

// Analytics API
export const analyticsAPI = {
  getComprehensiveData: (params: {
    start_time: string;
    end_time: string;
    lot_ids?: string[];
    include_patterns?: boolean;
    include_forecasts?: boolean;
  }) => api.get('/analytics/comprehensive', { params }),
  
  getOccupancyTrends: (params: {
    start_time: string;
    end_time: string;
    lot_ids?: string[];
    aggregation?: 'hour' | 'day' | 'week';
  }) => api.get('/analytics/occupancy', { params }),
  
  getRevenueTrends: (params: {
    start_time: string;
    end_time: string;
    lot_ids?: string[];
    aggregation?: 'hour' | 'day' | 'week';
  }) => api.get('/analytics/revenue', { params }),
  
  getOccupancyPatterns: (lotId?: string) =>
    api.get('/analytics/patterns', { params: lotId ? { lot_id: lotId } : {} }),
  
  getDemandForecasts: (lotId: string, hours: number = 24) =>
    api.get('/analytics/forecast', { params: { lot_id: lotId, hours } }),
  
  getPerformanceMetrics: () => api.get('/analytics/performance'),
  
  getRealtimeData: () => api.get('/analytics/realtime'),
  
  trainModel: (modelType: 'random_forest' | 'gradient_boosting' | 'linear_regression') =>
    api.post('/analytics/train-model', { model_type: modelType }),
  
  getOptimizationRecommendations: (lotId?: string) =>
    api.get('/analytics/optimize', { params: lotId ? { lot_id: lotId } : {} }),
};

// Users API (Admin)
export const usersAPI = {
  getAll: (params?: {
    page?: number;
    size?: number;
    search?: string;
    role?: string;
    isActive?: boolean;
  }) => api.get<PaginatedResponse<User>>('/users', { params }),
  
  getById: (id: string) => api.get<User>(`/users/${id}`),
  
  create: (data: Omit<User, 'id' | 'createdAt' | 'updatedAt'>) =>
    api.post<User>('/users', data),
  
  update: (id: string, data: Partial<User>) =>
    api.patch<User>(`/users/${id}`, data),
  
  delete: (id: string) => api.delete(`/users/${id}`),
  
  updateProfile: (data: Partial<User>) => api.patch<User>('/users/me', data),
  
  changePassword: (currentPassword: string, newPassword: string) =>
    api.patch('/users/me/password', { currentPassword, newPassword }),
};

// System API
export const systemAPI = {
  getHealth: () => api.get('/system/health'),
  
  getConfig: () => api.get('/system/config'),
  
  getNotifications: () => api.get('/system/notifications'),
  
  markNotificationRead: (id: string) =>
    api.patch(`/system/notifications/${id}/read`),
};

export default api;