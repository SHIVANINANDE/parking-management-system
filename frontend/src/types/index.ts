export interface ParkingSpot {
  id: string;
  number: string;
  status: 'available' | 'occupied' | 'reserved' | 'disabled';
  location: {
    latitude: number;
    longitude: number;
  };
  floor?: number;
  section?: string;
  type: 'regular' | 'handicapped' | 'electric' | 'motorcycle';
  reservedUntil?: Date;
  occupiedSince?: Date;
}

export interface User {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  role: 'user' | 'admin' | 'manager';
  vehicle?: Vehicle;
  createdAt: Date;
}

export interface Vehicle {
  id: string;
  licensePlate: string;
  make: string;
  model: string;
  color: string;
  type: 'car' | 'motorcycle' | 'truck' | 'electric';
}

export interface Reservation {
  id: string;
  userId: string;
  spotId: string;
  startTime: Date;
  endTime: Date;
  status: 'active' | 'completed' | 'cancelled';
  cost: number;
}

export interface ParkingLot {
  id: string;
  name: string;
  address: string;
  location: {
    latitude: number;
    longitude: number;
  };
  totalSpots: number;
  availableSpots: number;
  hourlyRate: number;
  operatingHours: {
    open: string;
    close: string;
  };
  amenities: string[];
}

export interface ApiResponse<T> {
  data: T;
  message?: string;
  success: boolean;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

export interface FilterOptions {
  status?: ParkingSpot['status'];
  type?: ParkingSpot['type'];
  floor?: number;
  section?: string;
}