import React, { useEffect, useRef, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMapEvents } from 'react-leaflet';
import { Icon, DivIcon, LatLngBounds } from 'leaflet';
import MarkerClusterGroup from 'react-leaflet-cluster';
import { Box, Card, CardContent, Typography, Chip, Button, IconButton, Tooltip } from '@mui/material';
import { Layers } from '@mui/icons-material';
import { useAppSelector, useAppDispatch } from '../hooks';
import { 
  setMapCenter, 
  setMapZoom, 
  setMapBounds,
  selectParkingLot,
  selectParkingSpot,
  toggleHeatmap,
  toggleLayer,
  ParkingLotMarker,
  ParkingSpotMarker 
} from '../store/slices/mapSlice';
import type { RootState } from '../store';
import 'leaflet/dist/leaflet.css';
import 'leaflet.markercluster/dist/MarkerCluster.css';
import 'leaflet.markercluster/dist/MarkerCluster.Default.css';

// Fix Leaflet default markers
delete (Icon.Default.prototype as any)._getIconUrl;
Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

// Custom icons for different spot types and statuses
const createSpotIcon = (type: string, status: string): DivIcon => {
  const colors = {
    available: '#4caf50',
    occupied: '#f44336',
    reserved: '#ff9800',
    maintenance: '#9e9e9e',
  };

  const getTypeIcon = (spotType: string): string => {
    switch (spotType) {
      case 'disabled': return '♿';
      case 'electric': return '⚡';
      case 'compact': return '🅿️';
      default: return '🚗';
    }
  };

  return new DivIcon({
    html: `
      <div class="spot-marker ${status}" style="
        width: 24px;
        height: 24px;
        background-color: ${colors[status as keyof typeof colors]};
        border-radius: 50%;
        border: 2px solid #fff;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-size: 12px;
      ">
        ${getTypeIcon(type)}
      </div>
    `,
    className: 'custom-div-icon',
    iconSize: [24, 24],
    iconAnchor: [12, 12],
    popupAnchor: [0, -12],
  });
};

const createLotIcon = (lot: ParkingLotMarker): DivIcon => {
  const occupancyRate = lot.totalSpots > 0 ? (lot.occupiedSpots / lot.totalSpots) : 0;
  const color = occupancyRate > 0.8 ? '#f44336' : occupancyRate > 0.5 ? '#ff9800' : '#4caf50';

  return new DivIcon({
    html: `
      <div style="
        background-color: ${color};
        border: 3px solid #fff;
        border-radius: 50%;
        width: 40px;
        height: 40px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: bold;
        font-size: 12px;
        box-shadow: 0 3px 12px rgba(0,0,0,0.3);
      ">
        ${lot.availableSpots}
      </div>
    `,
    className: 'custom-div-icon',
    iconSize: [40, 40],
    iconAnchor: [20, 20],
    popupAnchor: [0, -20],
  });
};

// Map event handler component
const MapEventHandler: React.FC = () => {
  const dispatch = useAppDispatch();
  
  const map = useMapEvents({
    moveend: () => {
      const center = map.getCenter();
      const zoom = map.getZoom();
      const bounds = map.getBounds();
      
      dispatch(setMapCenter([center.lat, center.lng]));
      dispatch(setMapZoom(zoom));
      dispatch(setMapBounds([
        [bounds.getSouth(), bounds.getWest()],
        [bounds.getNorth(), bounds.getEast()],
      ]));
    },
  });

  return null;
};

// Parking Lot Popup Component
const ParkingLotPopup: React.FC<{ lot: ParkingLotMarker }> = ({ lot }) => {
  const dispatch = useAppDispatch();

  return (
    <Card sx={{ minWidth: 280, maxWidth: 320 }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          {lot.name}
        </Typography>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          {lot.address}
        </Typography>
        
        <Box sx={{ my: 2 }}>
          <Typography variant="body2">
            <strong>Available:</strong> {lot.availableSpots} / {lot.totalSpots}
          </Typography>
          <Typography variant="body2">
            <strong>Rate:</strong> ${lot.pricing.hourly}/hr, ${lot.pricing.daily}/day
          </Typography>
          <Typography variant="body2">
            <strong>Hours:</strong> {lot.operatingHours.open} - {lot.operatingHours.close}
          </Typography>
        </Box>

        {lot.amenities.length > 0 && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="body2" gutterBottom>
              <strong>Amenities:</strong>
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
              {lot.amenities.map((amenity) => (
                <Chip key={amenity} label={amenity} size="small" />
              ))}
            </Box>
          </Box>
        )}

        <Button
          variant="contained"
          fullWidth
          onClick={() => dispatch(selectParkingLot(lot.id))}
        >
          View Details
        </Button>
      </CardContent>
    </Card>
  );
};

// Parking Spot Popup Component
const ParkingSpotPopup: React.FC<{ spot: ParkingSpotMarker }> = ({ spot }) => {
  const dispatch = useAppDispatch();

  const statusColors = {
    available: 'success',
    occupied: 'error',
    reserved: 'warning',
    maintenance: 'default',
  } as const;

  return (
    <Card sx={{ minWidth: 250 }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Spot {spot.spotNumber}
        </Typography>
        
        <Box sx={{ mb: 2 }}>
          <Chip
            label={spot.status.toUpperCase()}
            color={statusColors[spot.status]}
            size="small"
            sx={{ mr: 1 }}
          />
          <Chip
            label={spot.type.toUpperCase()}
            variant="outlined"
            size="small"
          />
        </Box>

        <Typography variant="body2" gutterBottom>
          <strong>Zone:</strong> {spot.zone}
        </Typography>
        <Typography variant="body2" gutterBottom>
          <strong>Last Updated:</strong> {new Date(spot.lastUpdated).toLocaleTimeString()}
        </Typography>

        {spot.status === 'available' && (
          <Button
            variant="contained"
            fullWidth
            sx={{ mt: 1 }}
            onClick={() => dispatch(selectParkingSpot(spot.id))}
          >
            Reserve Spot
          </Button>
        )}
      </CardContent>
    </Card>
  );
};

// Map Controls Component
const MapControls: React.FC = () => {
  const dispatch = useAppDispatch();
  const mapState = useAppSelector((state: RootState) => state.map);
  const { showHeatmap, layers } = mapState as any;
  const [showControls, setShowControls] = useState(false);

  return (
    <Box
      sx={{
        position: 'absolute',
        top: 10,
        right: 10,
        zIndex: 1000,
        display: 'flex',
        flexDirection: 'column',
        gap: 1,
      }}
    >
      <Tooltip title="Map Controls">
        <IconButton
          onClick={() => setShowControls(!showControls)}
          sx={{
            backgroundColor: 'white',
            boxShadow: 1,
            '&:hover': { backgroundColor: 'grey.50' },
          }}
        >
          <Layers />
        </IconButton>
      </Tooltip>

      {showControls && (
        <Card sx={{ p: 1, minWidth: 200 }}>
          <Typography variant="subtitle2" gutterBottom>
            Map Layers
          </Typography>
          
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            <Button
              size="small"
              variant={showHeatmap ? 'contained' : 'outlined'}
              onClick={() => dispatch(toggleHeatmap())}
            >
              Heatmap
            </Button>
            
            <Button
              size="small"
              variant={layers?.parkingLots ? 'contained' : 'outlined'}
              onClick={() => dispatch(toggleLayer('parkingLots'))}
            >
              Parking Lots
            </Button>
            
            <Button
              size="small"
              variant={layers?.parkingSpots ? 'contained' : 'outlined'}
              onClick={() => dispatch(toggleLayer('parkingSpots'))}
            >
              Parking Spots
            </Button>
            
            <Button
              size="small"
              variant={layers?.traffic ? 'contained' : 'outlined'}
              onClick={() => dispatch(toggleLayer('traffic'))}
            >
              Traffic
            </Button>
          </Box>
        </Card>
      )}
    </Box>
  );
};

// Main Map Component
interface MapComponentProps {
  height?: string | number;
  showControls?: boolean;
  interactive?: boolean;
}

const MapComponent: React.FC<MapComponentProps> = ({ 
  height = '100%', 
  showControls = true,
  interactive = true 
}) => {
  const mapRef = useRef<any>(null);
  
  const mapState = useAppSelector((state: RootState) => state.map) as any;
  const {
    center,
    zoom,
    parkingLots,
    parkingSpots,
    showClusters,
    layers,
    filters,
  } = mapState;

  // Filter parking lots based on current filters
  const filteredLots = parkingLots?.filter(() => {
    return true; // For now, show all lots
  }) || [];

  // Filter parking spots based on current filters
  const filteredSpots = parkingSpots?.filter((spot: any) => {
    return (
      filters?.status?.includes(spot.status) &&
      filters?.type?.includes(spot.type)
    );
  }) || [];

  useEffect(() => {
    // Fit map to show all parking lots when they load
    if (mapRef.current && filteredLots.length > 0) {
      const bounds = new LatLngBounds(
        filteredLots.map((lot: any) => lot.position as [number, number])
      );
      mapRef.current.fitBounds(bounds, { padding: [20, 20] });
    }
  }, [filteredLots.length]);

  return (
    <Box sx={{ position: 'relative', height }}>
      <MapContainer
        ref={mapRef}
        center={center || [37.7749, -122.4194]}
        zoom={zoom || 13}
        style={{ height: '100%', width: '100%' }}
        scrollWheelZoom={interactive}
        dragging={interactive}
        touchZoom={interactive}
        doubleClickZoom={interactive}
        boxZoom={interactive}
        keyboard={interactive}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <MapEventHandler />

        {/* Parking Lots */}
        {layers?.parkingLots && (
          <>
            {showClusters ? (
              <MarkerClusterGroup chunkedLoading>
                {filteredLots.map((lot: any) => (
                  <Marker
                    key={lot.id}
                    position={lot.position}
                    icon={createLotIcon(lot)}
                  >
                    <Popup>
                      <ParkingLotPopup lot={lot} />
                    </Popup>
                  </Marker>
                ))}
              </MarkerClusterGroup>
            ) : (
              filteredLots.map((lot: any) => (
                <Marker
                  key={lot.id}
                  position={lot.position}
                  icon={createLotIcon(lot)}
                >
                  <Popup>
                    <ParkingLotPopup lot={lot} />
                  </Popup>
                </Marker>
              ))
            )}
          </>
        )}

        {/* Parking Spots */}
        {layers?.parkingSpots && (
          <>
            {showClusters ? (
              <MarkerClusterGroup chunkedLoading>
                {filteredSpots.map((spot: any) => (
                  <Marker
                    key={spot.id}
                    position={spot.position}
                    icon={createSpotIcon(spot.type, spot.status)}
                  >
                    <Popup>
                      <ParkingSpotPopup spot={spot} />
                    </Popup>
                  </Marker>
                ))}
              </MarkerClusterGroup>
            ) : (
              filteredSpots.map((spot: any) => (
                <Marker
                  key={spot.id}
                  position={spot.position}
                  icon={createSpotIcon(spot.type, spot.status)}
                >
                  <Popup>
                    <ParkingSpotPopup spot={spot} />
                  </Popup>
                </Marker>
              ))
            )}
          </>
        )}
      </MapContainer>

      {/* Map Controls */}
      {showControls && <MapControls />}
    </Box>
  );
};

export default MapComponent;
