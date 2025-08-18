import React, { useState } from 'react';
import {
  Box,
  Paper,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  Typography,
  Button,
  Slider,
  Card,
  CardContent,
  CardActions,
  Rating,
  Fab,
  Drawer,
  useTheme,
  useMediaQuery,
  Container,
  Stack,
} from '@mui/material';
import {
  Search as SearchIcon,
  FilterList as FilterIcon,
  LocationOn as LocationIcon,
  Wifi as WifiIcon,
  Security as SecurityIcon,
  EvStation as EvIcon,
  Close as CloseIcon,
} from '@mui/icons-material';
import { DateTimePicker } from '@mui/x-date-pickers/DateTimePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { useAppSelector, useAppDispatch } from '../hooks';
import { setFilters } from '../store/slices/parkingSlice';

interface ParkingSpotDisplay {
  id: string;
  name: string;
  location: string;
  address: string;
  hourlyRate: number;
  distanceKm: number;
  rating: number;
  reviewCount: number;
  totalSpots: number;
  availableSpots: number;
  amenities: string[];
  imageUrl: string;
  status: 'available' | 'full' | 'closed';
}

const ParkingSpotSearch: React.FC = () => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  
  const dispatch = useAppDispatch();

  // Local state for search and filter form
  const [searchTerm, setSearchTerm] = useState('');
  const [startDate, setStartDate] = useState<Date | null>(new Date());
  const [endDate, setEndDate] = useState<Date | null>(new Date(Date.now() + 3600000)); // +1 hour
  const [vehicleType, setVehicleType] = useState('');
  const [priceRange, setPriceRange] = useState<number[]>([0, 50]);
  const [radiusRange, setRadiusRange] = useState(5);
  const [selectedAmenities, setSelectedAmenities] = useState<string[]>([]);
  const [sortBy, setSortBy] = useState('distance');
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);

  // Mock data for demonstration
  const [displayedSpots, setDisplayedSpots] = useState<ParkingSpotDisplay[]>([
    {
      id: '1',
      name: 'Downtown Plaza Parking',
      location: 'Downtown',
      address: '123 Main St, Downtown',
      hourlyRate: 8.50,
      distanceKm: 0.5,
      rating: 4.5,
      reviewCount: 128,
      totalSpots: 45,
      availableSpots: 12,
      amenities: ['wifi', 'security', 'ev-charging'],
      imageUrl: '/placeholder-parking.jpg',
      status: 'available'
    },
    {
      id: '2',
      name: 'City Center Garage',
      location: 'City Center',
      address: '456 Business Ave, City Center',
      hourlyRate: 12.00,
      distanceKm: 1.2,
      rating: 4.2,
      reviewCount: 89,
      totalSpots: 120,
      availableSpots: 35,
      amenities: ['security', 'covered'],
      imageUrl: '/placeholder-parking.jpg',
      status: 'available'
    },
    {
      id: '3',
      name: 'Metro Station Parking',
      location: 'Metro District',
      address: '789 Transit Blvd, Metro District',
      hourlyRate: 6.75,
      distanceKm: 2.1,
      rating: 4.0,
      reviewCount: 156,
      totalSpots: 80,
      availableSpots: 8,
      amenities: ['metro-access', 'security'],
      imageUrl: '/placeholder-parking.jpg',
      status: 'available'
    },
  ]);

  const amenityOptions = [
    { id: 'wifi', label: 'WiFi', icon: WifiIcon },
    { id: 'security', label: 'Security', icon: SecurityIcon },
    { id: 'ev-charging', label: 'EV Charging', icon: EvIcon },
    { id: 'covered', label: 'Covered', icon: SecurityIcon },
    { id: 'metro-access', label: 'Metro Access', icon: LocationIcon },
  ];

  const vehicleTypes = ['Sedan', 'SUV', 'Truck', 'Motorcycle', 'Electric'];
  const sortOptions = [
    { value: 'distance', label: 'Distance' },
    { value: 'price', label: 'Price' },
    { value: 'rating', label: 'Rating' },
    { value: 'availability', label: 'Availability' },
  ];

  const handleAmenityToggle = (amenityId: string) => {
    setSelectedAmenities(prev => 
      prev.includes(amenityId) 
        ? prev.filter(id => id !== amenityId)
        : [...prev, amenityId]
    );
  };

  const handleSearch = () => {
    // For demo, filter the mock data
    let filtered = displayedSpots.filter(spot => {
      const matchesSearch = !searchTerm || 
        spot.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        spot.location.toLowerCase().includes(searchTerm.toLowerCase());
      
      const matchesPrice = spot.hourlyRate >= priceRange[0] && spot.hourlyRate <= priceRange[1];
      const matchesDistance = spot.distanceKm <= radiusRange;
      const matchesAmenities = selectedAmenities.length === 0 || 
        selectedAmenities.some(amenity => spot.amenities.includes(amenity));
      
      return matchesSearch && matchesPrice && matchesDistance && matchesAmenities;
    });

    // Sort results
    switch (sortBy) {
      case 'price':
        filtered.sort((a, b) => a.hourlyRate - b.hourlyRate);
        break;
      case 'rating':
        filtered.sort((a, b) => b.rating - a.rating);
        break;
      case 'availability':
        filtered.sort((a, b) => b.availableSpots - a.availableSpots);
        break;
      default: // distance
        filtered.sort((a, b) => a.distanceKm - b.distanceKm);
    }

    setDisplayedSpots(filtered);
    if (isMobile) setMobileFiltersOpen(false);
  };

  const handleClearFilters = () => {
    setSearchTerm('');
    setStartDate(new Date());
    setEndDate(new Date(Date.now() + 3600000));
    setVehicleType('');
    setPriceRange([0, 50]);
    setRadiusRange(5);
    setSelectedAmenities([]);
    setSortBy('distance');
  };

  const FilterContent = () => (
    <Box sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom>
        Filters
      </Typography>
      
      {/* Date and Time Selection */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="subtitle1" gutterBottom>
          Date & Time
        </Typography>
        <LocalizationProvider dateAdapter={AdapterDateFns}>
          <Stack spacing={2}>
            <DateTimePicker
              label="Start Date & Time"
              value={startDate}
              onChange={setStartDate}
              slotProps={{ textField: { fullWidth: true, size: 'small' } }}
            />
            <DateTimePicker
              label="End Date & Time"
              value={endDate}
              onChange={setEndDate}
              slotProps={{ textField: { fullWidth: true, size: 'small' } }}
            />
          </Stack>
        </LocalizationProvider>
      </Box>

      {/* Vehicle Type */}
      <Box sx={{ mb: 3 }}>
        <FormControl fullWidth size="small">
          <InputLabel>Vehicle Type</InputLabel>
          <Select
            value={vehicleType}
            label="Vehicle Type"
            onChange={(e) => setVehicleType(e.target.value)}
          >
            <MenuItem value="">Any Vehicle</MenuItem>
            {vehicleTypes.map((type) => (
              <MenuItem key={type} value={type}>
                {type}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>

      {/* Price Range */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="subtitle1" gutterBottom>
          Price Range (per hour)
        </Typography>
        <Slider
          value={priceRange}
          onChange={(_, newValue) => setPriceRange(newValue as number[])}
          valueLabelDisplay="auto"
          min={0}
          max={50}
          step={1}
          marks={[
            { value: 0, label: '$0' },
            { value: 25, label: '$25' },
            { value: 50, label: '$50' },
          ]}
          valueLabelFormat={(value) => `$${value}`}
        />
      </Box>

      {/* Search Radius */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="subtitle1" gutterBottom>
          Search Radius: {radiusRange} km
        </Typography>
        <Slider
          value={radiusRange}
          onChange={(_, newValue) => setRadiusRange(newValue as number)}
          valueLabelDisplay="auto"
          min={1}
          max={25}
          step={1}
          marks={[
            { value: 1, label: '1km' },
            { value: 10, label: '10km' },
            { value: 25, label: '25km' },
          ]}
        />
      </Box>

      {/* Amenities */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="subtitle1" gutterBottom>
          Amenities
        </Typography>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
          {amenityOptions.map((amenity) => (
            <Chip
              key={amenity.id}
              icon={<amenity.icon />}
              label={amenity.label}
              clickable
              color={selectedAmenities.includes(amenity.id) ? "primary" : "default"}
              onClick={() => handleAmenityToggle(amenity.id)}
              variant={selectedAmenities.includes(amenity.id) ? "filled" : "outlined"}
            />
          ))}
        </Box>
      </Box>

      {/* Sort By */}
      <Box sx={{ mb: 3 }}>
        <FormControl fullWidth size="small">
          <InputLabel>Sort By</InputLabel>
          <Select
            value={sortBy}
            label="Sort By"
            onChange={(e) => setSortBy(e.target.value)}
          >
            {sortOptions.map((option) => (
              <MenuItem key={option.value} value={option.value}>
                {option.label}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>

      {/* Action Buttons */}
      <Stack direction="row" spacing={2}>
        <Button
          variant="outlined"
          fullWidth
          onClick={handleClearFilters}
        >
          Clear
        </Button>
        <Button
          variant="contained"
          fullWidth
          onClick={handleSearch}
          startIcon={<SearchIcon />}
        >
          Search
        </Button>
      </Stack>
    </Box>
  );

  const SpotCard = ({ spot }: { spot: ParkingSpotDisplay }) => (
    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <CardContent sx={{ flexGrow: 1 }}>
        <Typography variant="h6" component="h2" gutterBottom>
          {spot.name}
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
          <LocationIcon fontSize="small" color="action" />
          <Typography variant="body2" color="text.secondary" sx={{ ml: 0.5 }}>
            {spot.address}
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
          <Typography variant="body2" color="text.secondary">
            {spot.distanceKm} km away
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <Rating value={spot.rating} readOnly size="small" />
          <Typography variant="body2" color="text.secondary" sx={{ ml: 1 }}>
            ({spot.reviewCount} reviews)
          </Typography>
        </Box>
        <Typography variant="h6" color="primary" gutterBottom>
          ${spot.hourlyRate}/hour
        </Typography>
        <Typography 
          variant="body2" 
          color={spot.availableSpots > 10 ? "success.main" : spot.availableSpots > 0 ? "warning.main" : "error.main"}
        >
          {spot.availableSpots} of {spot.totalSpots} spots available
        </Typography>
        <Box sx={{ mt: 1, display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
          {spot.amenities.slice(0, 3).map((amenity) => {
            const amenityOption = amenityOptions.find(a => a.id === amenity);
            return (
              <Chip
                key={amenity}
                size="small"
                label={amenityOption?.label || amenity}
              />
            );
          })}
        </Box>
      </CardContent>
      <CardActions>
        <Button size="small" color="primary" fullWidth variant="contained">
          Book Now
        </Button>
      </CardActions>
    </Card>
  );

  return (
    <Container maxWidth="lg">
      <Box sx={{ py: 4 }}>
        {/* Header */}
        <Typography variant="h4" component="h1" gutterBottom>
          Find Parking Spots
        </Typography>
        
        {/* Search Bar */}
        <Paper sx={{ p: 2, mb: 3 }}>
          <Stack spacing={2}>
            <TextField
              fullWidth
              placeholder="Search by location, parking lot name..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              InputProps={{
                startAdornment: <SearchIcon color="action" sx={{ mr: 1 }} />,
              }}
            />
            <Stack direction="row" spacing={2}>
              <Button
                variant="contained"
                onClick={handleSearch}
                startIcon={<SearchIcon />}
                sx={{ minWidth: 120 }}
              >
                Search
              </Button>
              <Button
                variant="outlined"
                onClick={() => setMobileFiltersOpen(true)}
                startIcon={<FilterIcon />}
                sx={{ display: { md: 'none' }, minWidth: 120 }}
              >
                Filters
              </Button>
            </Stack>
          </Stack>
        </Paper>

        {/* Main Content */}
        <Box sx={{ display: 'flex', gap: 3 }}>
          {/* Desktop Filters Sidebar */}
          <Box sx={{ width: 300, flexShrink: 0, display: { xs: 'none', md: 'block' } }}>
            <Paper sx={{ position: 'sticky', top: 20 }}>
              <FilterContent />
            </Paper>
          </Box>

          {/* Results */}
          <Box sx={{ flexGrow: 1 }}>
            <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="h6">
                {displayedSpots.length} parking spots found
              </Typography>
            </Box>
            
            {/* Results Grid */}
            <Box 
              sx={{ 
                display: 'grid', 
                gridTemplateColumns: {
                  xs: '1fr',
                  sm: 'repeat(2, 1fr)',
                  lg: 'repeat(3, 1fr)'
                },
                gap: 3 
              }}
            >
              {displayedSpots.map((spot) => (
                <SpotCard key={spot.id} spot={spot} />
              ))}
            </Box>

            {displayedSpots.length === 0 && (
              <Paper sx={{ p: 4, textAlign: 'center' }}>
                <Typography variant="h6" color="text.secondary">
                  No parking spots found
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Try adjusting your search criteria
                </Typography>
              </Paper>
            )}
          </Box>
        </Box>

        {/* Mobile Filters Drawer */}
        <Drawer
          anchor="bottom"
          open={mobileFiltersOpen}
          onClose={() => setMobileFiltersOpen(false)}
          sx={{ display: { md: 'none' } }}
        >
          <Box sx={{ minHeight: '50vh', maxHeight: '90vh', overflow: 'auto' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', p: 2, borderBottom: 1, borderColor: 'divider' }}>
              <Typography variant="h6">Filters</Typography>
              <Button onClick={() => setMobileFiltersOpen(false)}>
                <CloseIcon />
              </Button>
            </Box>
            <FilterContent />
          </Box>
        </Drawer>

        {/* Mobile Filter FAB */}
        <Fab
          color="primary"
          aria-label="filters"
          onClick={() => setMobileFiltersOpen(true)}
          sx={{
            position: 'fixed',
            bottom: 16,
            right: 16,
            display: { md: 'none' }
          }}
        >
          <FilterIcon />
        </Fab>
      </Box>
    </Container>
  );
};

export default ParkingSpotSearch;
