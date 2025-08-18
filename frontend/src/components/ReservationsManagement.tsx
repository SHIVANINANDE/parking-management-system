import React, { useState } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  CardActions,
  Button,
  Chip,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Divider,
  Fab,
  Collapse,
  Avatar,
} from '@mui/material';
import {
  Add,
  Edit,
  Search,
  DirectionsCar,
  AccessTime,
  Person,
  Phone,
  Email,
  LocationOn,
  AttachMoney,
  CheckCircle,
  Cancel,
  Schedule,
  Warning,
  Refresh,
  Download,
  ExpandMore,
  ExpandLess,
} from '@mui/icons-material';

// Mock data for reservations
const mockReservations = [
  {
    id: 'RES-001',
    userId: 'user123',
    userName: 'John Smith',
    userEmail: 'john.smith@email.com',
    userPhone: '+1 (555) 123-4567',
    lotName: 'Downtown Plaza',
    spotNumber: 'A-15',
    vehicleInfo: '2023 Toyota Camry - ABC123',
    startTime: '2024-01-15T14:00:00Z',
    endTime: '2024-01-15T18:00:00Z',
    duration: 4,
    amount: 25.00,
    status: 'active',
    paymentStatus: 'paid',
    createdAt: '2024-01-15T10:30:00Z',
    checkedIn: true,
    notes: 'Regular customer, VIP parking'
  },
  {
    id: 'RES-002',
    userId: 'user456',
    userName: 'Sarah Johnson',
    userEmail: 'sarah.j@email.com',
    userPhone: '+1 (555) 987-6543',
    lotName: 'Mall Parking',
    spotNumber: 'B-32',
    vehicleInfo: '2022 Honda Civic - XYZ789',
    startTime: '2024-01-15T16:00:00Z',
    endTime: '2024-01-15T20:00:00Z',
    duration: 4,
    amount: 20.00,
    status: 'confirmed',
    paymentStatus: 'pending',
    createdAt: '2024-01-15T12:15:00Z',
    checkedIn: false,
    notes: ''
  },
  {
    id: 'RES-003',
    userId: 'user789',
    userName: 'Mike Wilson',
    userEmail: 'mike.wilson@email.com',
    userPhone: '+1 (555) 456-7890',
    lotName: 'Airport Terminal',
    spotNumber: 'C-07',
    vehicleInfo: '2021 Ford Explorer - DEF456',
    startTime: '2024-01-14T08:00:00Z',
    endTime: '2024-01-14T18:00:00Z',
    duration: 10,
    amount: 75.00,
    status: 'completed',
    paymentStatus: 'paid',
    createdAt: '2024-01-14T06:45:00Z',
    checkedIn: true,
    notes: 'Extended parking, business trip'
  },
  {
    id: 'RES-004',
    userId: 'user321',
    userName: 'Emma Davis',
    userEmail: 'emma.davis@email.com',
    userPhone: '+1 (555) 234-5678',
    lotName: 'University Campus',
    spotNumber: 'D-19',
    vehicleInfo: '2020 Nissan Altima - GHI789',
    startTime: '2024-01-16T09:00:00Z',
    endTime: '2024-01-16T17:00:00Z',
    duration: 8,
    amount: 30.00,
    status: 'cancelled',
    paymentStatus: 'refunded',
    createdAt: '2024-01-15T20:30:00Z',
    checkedIn: false,
    notes: 'Cancelled due to schedule change'
  },
];

interface ReservationDetailsDialogProps {
  reservation: typeof mockReservations[0] | null;
  open: boolean;
  onClose: () => void;
  onEdit: (reservation: typeof mockReservations[0]) => void;
  onCancel: (reservationId: string) => void;
}

const ReservationDetailsDialog: React.FC<ReservationDetailsDialogProps> = ({
  reservation,
  open,
  onClose,
  onEdit,
  onCancel,
}) => {
  if (!reservation) return null;

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'success';
      case 'confirmed': return 'info';
      case 'completed': return 'default';
      case 'cancelled': return 'error';
      default: return 'default';
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6">Reservation Details</Typography>
          <Chip 
            label={reservation.status.toUpperCase()} 
            color={getStatusColor(reservation.status) as any}
            size="small"
          />
        </Box>
      </DialogTitle>
      
      <DialogContent>
        <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
          {/* Customer Information */}
          <Card sx={{ flex: '1 1 300px', minWidth: 300 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Person />
                Customer Information
              </Typography>
              
              <Box sx={{ mt: 2 }}>
                <Typography variant="body1" gutterBottom>
                  <strong>Name:</strong> {reservation.userName}
                </Typography>
                <Typography variant="body2" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Email fontSize="small" />
                  {reservation.userEmail}
                </Typography>
                <Typography variant="body2" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Phone fontSize="small" />
                  {reservation.userPhone}
                </Typography>
                <Typography variant="body2" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <DirectionsCar fontSize="small" />
                  {reservation.vehicleInfo}
                </Typography>
              </Box>
            </CardContent>
          </Card>

          {/* Parking Information */}
          <Card sx={{ flex: '1 1 300px', minWidth: 300 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <LocationOn />
                Parking Information
              </Typography>
              
              <Box sx={{ mt: 2 }}>
                <Typography variant="body1" gutterBottom>
                  <strong>Location:</strong> {reservation.lotName}
                </Typography>
                <Typography variant="body1" gutterBottom>
                  <strong>Spot:</strong> {reservation.spotNumber}
                </Typography>
                <Typography variant="body2" gutterBottom>
                  <strong>Start:</strong> {new Date(reservation.startTime).toLocaleString()}
                </Typography>
                <Typography variant="body2" gutterBottom>
                  <strong>End:</strong> {new Date(reservation.endTime).toLocaleString()}
                </Typography>
                <Typography variant="body2" gutterBottom>
                  <strong>Duration:</strong> {reservation.duration} hours
                </Typography>
                <Typography variant="body1" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <AttachMoney fontSize="small" />
                  <strong>${reservation.amount.toFixed(2)}</strong>
                  <Chip 
                    label={reservation.paymentStatus} 
                    color={reservation.paymentStatus === 'paid' ? 'success' : reservation.paymentStatus === 'pending' ? 'warning' : 'default'}
                    size="small"
                  />
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Box>

        {/* Additional Information */}
        {reservation.notes && (
          <Card sx={{ mt: 2 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>Notes</Typography>
              <Typography variant="body2">{reservation.notes}</Typography>
            </CardContent>
          </Card>
        )}

        {/* Status Information */}
        <Card sx={{ mt: 2 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>Status Information</Typography>
            <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
              <Chip 
                icon={reservation.checkedIn ? <CheckCircle /> : <Schedule />}
                label={reservation.checkedIn ? 'Checked In' : 'Not Checked In'}
                color={reservation.checkedIn ? 'success' : 'warning'}
              />
              <Chip 
                label={`Created: ${new Date(reservation.createdAt).toLocaleDateString()}`}
                variant="outlined"
              />
              <Chip 
                label={`ID: ${reservation.id}`}
                variant="outlined"
              />
            </Box>
          </CardContent>
        </Card>
      </DialogContent>
      
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
        {reservation.status === 'confirmed' && (
          <Button 
            onClick={() => onCancel(reservation.id)} 
            color="error"
            startIcon={<Cancel />}
          >
            Cancel Reservation
          </Button>
        )}
        {(reservation.status === 'active' || reservation.status === 'confirmed') && (
          <Button 
            onClick={() => onEdit(reservation)} 
            variant="contained"
            startIcon={<Edit />}
          >
            Edit Reservation
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
};

const ReservationsManagement: React.FC = () => {
  const [reservations, setReservations] = useState(mockReservations);
  const [filteredReservations, setFilteredReservations] = useState(mockReservations);
  const [selectedReservation, setSelectedReservation] = useState<typeof mockReservations[0] | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [paymentFilter, setPaymentFilter] = useState('all');
  const [expandedCard, setExpandedCard] = useState<string | null>(null);

  // Filter reservations based on search and filters
  React.useEffect(() => {
    let filtered = reservations;

    if (searchTerm) {
      filtered = filtered.filter(reservation =>
        reservation.userName.toLowerCase().includes(searchTerm.toLowerCase()) ||
        reservation.userEmail.toLowerCase().includes(searchTerm.toLowerCase()) ||
        reservation.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
        reservation.lotName.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    if (statusFilter !== 'all') {
      filtered = filtered.filter(reservation => reservation.status === statusFilter);
    }

    if (paymentFilter !== 'all') {
      filtered = filtered.filter(reservation => reservation.paymentStatus === paymentFilter);
    }

    setFilteredReservations(filtered);
  }, [reservations, searchTerm, statusFilter, paymentFilter]);

  const handleViewDetails = (reservation: typeof mockReservations[0]) => {
    setSelectedReservation(reservation);
    setDetailsOpen(true);
  };

  const handleEditReservation = (reservation: typeof mockReservations[0]) => {
    console.log('Edit reservation:', reservation.id);
    setDetailsOpen(false);
  };

  const handleCancelReservation = (reservationId: string) => {
    setReservations(prev => 
      prev.map(res => 
        res.id === reservationId 
          ? { ...res, status: 'cancelled', paymentStatus: 'refunded' }
          : res
      )
    );
    setDetailsOpen(false);
  };

  const handleCreateReservation = () => {
    console.log('Create new reservation');
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'success';
      case 'confirmed': return 'info';
      case 'completed': return 'default';
      case 'cancelled': return 'error';
      default: return 'default';
    }
  };

  const statusCounts = {
    all: reservations.length,
    active: reservations.filter(r => r.status === 'active').length,
    confirmed: reservations.filter(r => r.status === 'confirmed').length,
    completed: reservations.filter(r => r.status === 'completed').length,
    cancelled: reservations.filter(r => r.status === 'cancelled').length,
  };

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" component="h1" gutterBottom>
            Reservations Management
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Manage and track all parking reservations
          </Typography>
        </Box>
        
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button variant="outlined" startIcon={<Refresh />}>
            Refresh
          </Button>
          <Button variant="outlined" startIcon={<Download />}>
            Export
          </Button>
          <Button variant="contained" startIcon={<Add />} onClick={handleCreateReservation}>
            New Reservation
          </Button>
        </Box>
      </Box>

      {/* Status Summary */}
      <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
        {Object.entries(statusCounts).map(([status, count]) => (
          <Card key={status} sx={{ flex: '1 1 150px', minWidth: 150 }}>
            <CardContent sx={{ textAlign: 'center', py: 2 }}>
              <Typography variant="h4" color={status === 'all' ? 'primary' : getStatusColor(status) + '.main'}>
                {count}
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ textTransform: 'capitalize' }}>
                {status} Reservations
              </Typography>
            </CardContent>
          </Card>
        ))}
      </Box>

      {/* Filters and Search */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
            <TextField
              size="small"
              placeholder="Search reservations..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              InputProps={{
                startAdornment: <Search sx={{ mr: 1, color: 'action.active' }} />,
              }}
              sx={{ minWidth: 200 }}
            />
            
            <FormControl size="small" sx={{ minWidth: 120 }}>
              <InputLabel>Status</InputLabel>
              <Select
                value={statusFilter}
                label="Status"
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <MenuItem value="all">All Status</MenuItem>
                <MenuItem value="active">Active</MenuItem>
                <MenuItem value="confirmed">Confirmed</MenuItem>
                <MenuItem value="completed">Completed</MenuItem>
                <MenuItem value="cancelled">Cancelled</MenuItem>
              </Select>
            </FormControl>
            
            <FormControl size="small" sx={{ minWidth: 120 }}>
              <InputLabel>Payment</InputLabel>
              <Select
                value={paymentFilter}
                label="Payment"
                onChange={(e) => setPaymentFilter(e.target.value)}
              >
                <MenuItem value="all">All Payments</MenuItem>
                <MenuItem value="paid">Paid</MenuItem>
                <MenuItem value="pending">Pending</MenuItem>
                <MenuItem value="refunded">Refunded</MenuItem>
              </Select>
            </FormControl>
            
            <Typography variant="body2" color="text.secondary" sx={{ ml: 'auto' }}>
              Showing {filteredReservations.length} of {reservations.length} reservations
            </Typography>
          </Box>
        </CardContent>
      </Card>

      {/* Reservations List */}
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        {filteredReservations.map((reservation) => (
          <Card key={reservation.id}>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                  <Avatar sx={{ bgcolor: getStatusColor(reservation.status) + '.main' }}>
                    {reservation.userName.charAt(0)}
                  </Avatar>
                  <Box>
                    <Typography variant="h6">{reservation.userName}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      {reservation.id} • {reservation.lotName} - {reservation.spotNumber}
                    </Typography>
                  </Box>
                </Box>
                
                <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                  <Chip 
                    label={reservation.status.toUpperCase()} 
                    color={getStatusColor(reservation.status) as any}
                    size="small"
                  />
                  <Chip 
                    label={`$${reservation.amount.toFixed(2)}`} 
                    variant="outlined"
                    size="small"
                  />
                  <IconButton 
                    size="small"
                    onClick={() => setExpandedCard(expandedCard === reservation.id ? null : reservation.id)}
                  >
                    {expandedCard === reservation.id ? <ExpandLess /> : <ExpandMore />}
                  </IconButton>
                </Box>
              </Box>
              
              <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap', mb: 2 }}>
                <Typography variant="body2" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  <AccessTime fontSize="small" />
                  {new Date(reservation.startTime).toLocaleDateString()} - {reservation.duration}h
                </Typography>
                <Typography variant="body2" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  <DirectionsCar fontSize="small" />
                  {reservation.vehicleInfo}
                </Typography>
                {reservation.checkedIn && (
                  <Chip icon={<CheckCircle />} label="Checked In" color="success" size="small" />
                )}
              </Box>

              <Collapse in={expandedCard === reservation.id}>
                <Divider sx={{ my: 2 }} />
                <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
                  <Box>
                    <Typography variant="body2" color="text.secondary">Contact</Typography>
                    <Typography variant="body2">{reservation.userEmail}</Typography>
                    <Typography variant="body2">{reservation.userPhone}</Typography>
                  </Box>
                  <Box>
                    <Typography variant="body2" color="text.secondary">Payment</Typography>
                    <Typography variant="body2">Status: {reservation.paymentStatus}</Typography>
                    <Typography variant="body2">Amount: ${reservation.amount.toFixed(2)}</Typography>
                  </Box>
                  <Box>
                    <Typography variant="body2" color="text.secondary">Timing</Typography>
                    <Typography variant="body2">
                      Start: {new Date(reservation.startTime).toLocaleString()}
                    </Typography>
                    <Typography variant="body2">
                      End: {new Date(reservation.endTime).toLocaleString()}
                    </Typography>
                  </Box>
                </Box>
                {reservation.notes && (
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="body2" color="text.secondary">Notes</Typography>
                    <Typography variant="body2">{reservation.notes}</Typography>
                  </Box>
                )}
              </Collapse>
            </CardContent>
            
            <CardActions>
              <Button size="small" onClick={() => handleViewDetails(reservation)}>
                View Details
              </Button>
              {(reservation.status === 'active' || reservation.status === 'confirmed') && (
                <Button size="small" startIcon={<Edit />}>
                  Edit
                </Button>
              )}
              {reservation.status === 'confirmed' && (
                <Button size="small" color="error" startIcon={<Cancel />}>
                  Cancel
                </Button>
              )}
            </CardActions>
          </Card>
        ))}
      </Box>

      {/* Empty State */}
      {filteredReservations.length === 0 && (
        <Box sx={{ textAlign: 'center', py: 6 }}>
          <Warning sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" color="text.secondary" gutterBottom>
            No reservations found
          </Typography>
          <Typography variant="body2" color="text.secondary" paragraph>
            {searchTerm || statusFilter !== 'all' || paymentFilter !== 'all'
              ? 'Try adjusting your search criteria or filters'
              : 'No reservations have been made yet'
            }
          </Typography>
          {!searchTerm && statusFilter === 'all' && paymentFilter === 'all' && (
            <Button variant="contained" startIcon={<Add />} onClick={handleCreateReservation}>
              Create First Reservation
            </Button>
          )}
        </Box>
      )}

      {/* Floating Action Button */}
      <Fab
        color="primary"
        aria-label="add reservation"
        sx={{ position: 'fixed', bottom: 16, right: 16 }}
        onClick={handleCreateReservation}
      >
        <Add />
      </Fab>

      {/* Reservation Details Dialog */}
      <ReservationDetailsDialog
        reservation={selectedReservation}
        open={detailsOpen}
        onClose={() => setDetailsOpen(false)}
        onEdit={handleEditReservation}
        onCancel={handleCancelReservation}
      />
    </Box>
  );
};

export default ReservationsManagement;
