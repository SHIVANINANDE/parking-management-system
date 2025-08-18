import { createSlice, PayloadAction } from '@reduxjs/toolkit';

export interface ParkingSpotMarker {
  id: string;
  position: [number, number];
  status: 'available' | 'occupied' | 'reserved' | 'maintenance';
  type: 'standard' | 'disabled' | 'electric' | 'compact';
  parkingLotId: string;
  lastUpdated: string;
  reservationId?: string;
  vehicleId?: string;
  spotNumber: string;
  zone: string;
}

export interface ParkingLotMarker {
  id: string;
  name: string;
  position: [number, number];
  totalSpots: number;
  availableSpots: number;
  occupiedSpots: number;
  reservedSpots: number;
  maintenanceSpots: number;
  address: string;
  amenities: string[];
  pricing: {
    hourly: number;
    daily: number;
    monthly: number;
  };
  operatingHours: {
    open: string;
    close: string;
  };
  capacity: {
    standard: number;
    disabled: number;
    electric: number;
    compact: number;
  };
}

export interface MapState {
  // Map view settings
  center: [number, number];
  zoom: number;
  bounds?: [[number, number], [number, number]];
  
  // Map data
  parkingLots: ParkingLotMarker[];
  parkingSpots: ParkingSpotMarker[];
  
  // UI state
  isLoading: boolean;
  error: string | null;
  selectedLotId: string | null;
  selectedSpotId: string | null;
  showHeatmap: boolean;
  showClusters: boolean;
  
  // Filters
  filters: {
    status: ('available' | 'occupied' | 'reserved' | 'maintenance')[];
    type: ('standard' | 'disabled' | 'electric' | 'compact')[];
    priceRange: [number, number];
    amenities: string[];
  };
  
  // Search
  searchQuery: string;
  searchResults: ParkingLotMarker[];
  
  // Real-time updates
  lastUpdateTime: string | null;
  updateInterval: number;
  
  // Layer visibility
  layers: {
    parkingLots: boolean;
    parkingSpots: boolean;
    heatmap: boolean;
    traffic: boolean;
    zones: boolean;
  };
}

const initialState: MapState = {
  center: [37.7749, -122.4194], // San Francisco default
  zoom: 13,
  parkingLots: [],
  parkingSpots: [],
  isLoading: false,
  error: null,
  selectedLotId: null,
  selectedSpotId: null,
  showHeatmap: false,
  showClusters: true,
  filters: {
    status: ['available'],
    type: ['standard', 'disabled', 'electric', 'compact'],
    priceRange: [0, 50],
    amenities: [],
  },
  searchQuery: '',
  searchResults: [],
  lastUpdateTime: null,
  updateInterval: 30000, // 30 seconds
  layers: {
    parkingLots: true,
    parkingSpots: true,
    heatmap: false,
    traffic: false,
    zones: true,
  },
};

const mapSlice = createSlice({
  name: 'map',
  initialState,
  reducers: {
    // Map view actions
    setMapCenter: (state, action: PayloadAction<[number, number]>) => {
      state.center = action.payload;
    },
    setMapZoom: (state, action: PayloadAction<number>) => {
      state.zoom = action.payload;
    },
    setMapBounds: (state, action: PayloadAction<[[number, number], [number, number]]>) => {
      state.bounds = action.payload;
    },
    
    // Data loading actions
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.isLoading = action.payload;
    },
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
    },
    
    // Parking lots actions
    setParkingLots: (state, action: PayloadAction<ParkingLotMarker[]>) => {
      state.parkingLots = action.payload;
    },
    addParkingLot: (state, action: PayloadAction<ParkingLotMarker>) => {
      state.parkingLots.push(action.payload);
    },
    updateParkingLot: (state, action: PayloadAction<Partial<ParkingLotMarker> & { id: string }>) => {
      const index = state.parkingLots.findIndex(lot => lot.id === action.payload.id);
      if (index !== -1) {
        state.parkingLots[index] = { ...state.parkingLots[index], ...action.payload };
      }
    },
    removeParkingLot: (state, action: PayloadAction<string>) => {
      state.parkingLots = state.parkingLots.filter(lot => lot.id !== action.payload);
    },
    
    // Parking spots actions
    setParkingSpots: (state, action: PayloadAction<ParkingSpotMarker[]>) => {
      state.parkingSpots = action.payload;
    },
    addParkingSpot: (state, action: PayloadAction<ParkingSpotMarker>) => {
      state.parkingSpots.push(action.payload);
    },
    updateParkingSpot: (state, action: PayloadAction<Partial<ParkingSpotMarker> & { id: string }>) => {
      const index = state.parkingSpots.findIndex(spot => spot.id === action.payload.id);
      if (index !== -1) {
        state.parkingSpots[index] = { ...state.parkingSpots[index], ...action.payload };
      }
    },
    removeParkingSpot: (state, action: PayloadAction<string>) => {
      state.parkingSpots = state.parkingSpots.filter(spot => spot.id !== action.payload);
    },
    
    // Real-time spot status updates
    updateSpotStatus: (state, action: PayloadAction<{ id: string; status: ParkingSpotMarker['status']; lastUpdated: string }>) => {
      const spot = state.parkingSpots.find(s => s.id === action.payload.id);
      if (spot) {
        spot.status = action.payload.status;
        spot.lastUpdated = action.payload.lastUpdated;
      }
      
      // Update lot availability counts
      const lot = state.parkingLots.find(l => l.id === spot?.parkingLotId);
      if (lot && spot) {
        const lotSpots = state.parkingSpots.filter(s => s.parkingLotId === lot.id);
        lot.availableSpots = lotSpots.filter(s => s.status === 'available').length;
        lot.occupiedSpots = lotSpots.filter(s => s.status === 'occupied').length;
        lot.reservedSpots = lotSpots.filter(s => s.status === 'reserved').length;
        lot.maintenanceSpots = lotSpots.filter(s => s.status === 'maintenance').length;
      }
    },
    
    // Bulk spot updates for efficiency
    updateMultipleSpots: (state, action: PayloadAction<Array<{ id: string; status: ParkingSpotMarker['status']; lastUpdated: string }>>) => {
      action.payload.forEach(update => {
        const spot = state.parkingSpots.find(s => s.id === update.id);
        if (spot) {
          spot.status = update.status;
          spot.lastUpdated = update.lastUpdated;
        }
      });
      
      // Recalculate all lot availability counts
      state.parkingLots.forEach(lot => {
        const lotSpots = state.parkingSpots.filter(s => s.parkingLotId === lot.id);
        lot.availableSpots = lotSpots.filter(s => s.status === 'available').length;
        lot.occupiedSpots = lotSpots.filter(s => s.status === 'occupied').length;
        lot.reservedSpots = lotSpots.filter(s => s.status === 'reserved').length;
        lot.maintenanceSpots = lotSpots.filter(s => s.status === 'maintenance').length;
      });
    },
    
    // Selection actions
    selectParkingLot: (state, action: PayloadAction<string | null>) => {
      state.selectedLotId = action.payload;
      if (action.payload) {
        state.selectedSpotId = null; // Clear spot selection when selecting lot
      }
    },
    selectParkingSpot: (state, action: PayloadAction<string | null>) => {
      state.selectedSpotId = action.payload;
    },
    
    // UI state actions
    toggleHeatmap: (state) => {
      state.showHeatmap = !state.showHeatmap;
    },
    toggleClusters: (state) => {
      state.showClusters = !state.showClusters;
    },
    
    // Filter actions
    setStatusFilter: (state, action: PayloadAction<MapState['filters']['status']>) => {
      state.filters.status = action.payload;
    },
    setTypeFilter: (state, action: PayloadAction<MapState['filters']['type']>) => {
      state.filters.type = action.payload;
    },
    setPriceRangeFilter: (state, action: PayloadAction<[number, number]>) => {
      state.filters.priceRange = action.payload;
    },
    setAmenitiesFilter: (state, action: PayloadAction<string[]>) => {
      state.filters.amenities = action.payload;
    },
    resetFilters: (state) => {
      state.filters = initialState.filters;
    },
    
    // Search actions
    setSearchQuery: (state, action: PayloadAction<string>) => {
      state.searchQuery = action.payload;
    },
    setSearchResults: (state, action: PayloadAction<ParkingLotMarker[]>) => {
      state.searchResults = action.payload;
    },
    clearSearch: (state) => {
      state.searchQuery = '';
      state.searchResults = [];
    },
    
    // Layer visibility actions
    toggleLayer: (state, action: PayloadAction<keyof MapState['layers']>) => {
      state.layers[action.payload] = !state.layers[action.payload];
    },
    setLayerVisibility: (state, action: PayloadAction<{ layer: keyof MapState['layers']; visible: boolean }>) => {
      state.layers[action.payload.layer] = action.payload.visible;
    },
    
    // Real-time update actions
    setLastUpdateTime: (state, action: PayloadAction<string>) => {
      state.lastUpdateTime = action.payload;
    },
    setUpdateInterval: (state, action: PayloadAction<number>) => {
      state.updateInterval = action.payload;
    },
  },
});

export const {
  setMapCenter,
  setMapZoom,
  setMapBounds,
  setLoading,
  setError,
  setParkingLots,
  addParkingLot,
  updateParkingLot,
  removeParkingLot,
  setParkingSpots,
  addParkingSpot,
  updateParkingSpot,
  removeParkingSpot,
  updateSpotStatus,
  updateMultipleSpots,
  selectParkingLot,
  selectParkingSpot,
  toggleHeatmap,
  toggleClusters,
  setStatusFilter,
  setTypeFilter,
  setPriceRangeFilter,
  setAmenitiesFilter,
  resetFilters,
  setSearchQuery,
  setSearchResults,
  clearSearch,
  toggleLayer,
  setLayerVisibility,
  setLastUpdateTime,
  setUpdateInterval,
} = mapSlice.actions;

export default mapSlice.reducer;
