import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { ParkingSpot, ParkingLot, Reservation, FilterOptions } from '@/types';

interface ParkingState {
  spots: ParkingSpot[];
  lots: ParkingLot[];
  reservations: Reservation[];
  selectedSpot: ParkingSpot | null;
  selectedLot: ParkingLot | null;
  filters: FilterOptions;
  loading: boolean;
  error: string | null;
}

const initialState: ParkingState = {
  spots: [],
  lots: [],
  reservations: [],
  selectedSpot: null,
  selectedLot: null,
  filters: {},
  loading: false,
  error: null,
};

export const fetchParkingSpots = createAsyncThunk(
  'parking/fetchSpots',
  async (lotId?: string) => {
    const url = lotId ? `/api/v1/parking/spots?lotId=${lotId}` : '/api/v1/parking/spots';
    const response = await fetch(url);
    
    if (!response.ok) {
      throw new Error('Failed to fetch parking spots');
    }
    
    return response.json();
  }
);

export const fetchParkingLots = createAsyncThunk(
  'parking/fetchLots',
  async () => {
    const response = await fetch('/api/v1/parking/lots');
    
    if (!response.ok) {
      throw new Error('Failed to fetch parking lots');
    }
    
    return response.json();
  }
);

export const reserveSpot = createAsyncThunk(
  'parking/reserveSpot',
  async (data: { spotId: string; startTime: Date; endTime: Date }) => {
    const response = await fetch('/api/v1/parking/reservations', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    
    if (!response.ok) {
      throw new Error('Failed to reserve spot');
    }
    
    return response.json();
  }
);

const parkingSlice = createSlice({
  name: 'parking',
  initialState,
  reducers: {
    setFilters: (state, action: PayloadAction<FilterOptions>) => {
      state.filters = { ...state.filters, ...action.payload };
    },
    clearFilters: (state) => {
      state.filters = {};
    },
    setSelectedSpot: (state, action: PayloadAction<ParkingSpot | null>) => {
      state.selectedSpot = action.payload;
    },
    setSelectedLot: (state, action: PayloadAction<ParkingLot | null>) => {
      state.selectedLot = action.payload;
    },
    updateSpotStatus: (state, action: PayloadAction<{ spotId: string; status: ParkingSpot['status'] }>) => {
      const spot = state.spots.find(s => s.id === action.payload.spotId);
      if (spot) {
        spot.status = action.payload.status;
      }
    },
    clearError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchParkingSpots.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchParkingSpots.fulfilled, (state, action) => {
        state.loading = false;
        state.spots = action.payload.data;
      })
      .addCase(fetchParkingSpots.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch spots';
      })
      .addCase(fetchParkingLots.fulfilled, (state, action) => {
        state.lots = action.payload.data;
      })
      .addCase(reserveSpot.fulfilled, (state, action) => {
        state.reservations.push(action.payload.data);
      });
  },
});

export const {
  setFilters,
  clearFilters,
  setSelectedSpot,
  setSelectedLot,
  updateSpotStatus,
  clearError,
} = parkingSlice.actions;

export default parkingSlice.reducer;