import React, { useState } from 'react';
import {
  Box,
  Container,
  Typography,
  Card,
  CardContent,
  CardActions,
  Button,
  Chip,
  Avatar,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Tabs,
  Tab,
  Stack,
  Divider,
  Alert,
} from '@mui/material';
import {
  Person as PersonIcon,
  DirectionsCar as CarIcon,
  Payment as PaymentIcon,
  History as HistoryIcon,
  Cancel as CancelIcon,
  Edit as EditIcon,
  Receipt as ReceiptIcon,
  QrCode as QrCodeIcon,
} from '@mui/icons-material';

interface Booking {
  id: string;
  spotName: string;
  spotAddress: string;
  startTime: Date;
  endTime: Date;
  duration: number;
  totalCost: number;
  status: 'active' | 'completed' | 'cancelled' | 'upcoming';
  vehicleType: string;
  licensePlate: string;
  paymentMethod: string;
  bookingDate: Date;
}

interface Vehicle {
  id: string;
  licensePlate: string;
  make: string;
  model: string;
  color: string;
  type: 'sedan' | 'suv' | 'truck' | 'motorcycle' | 'electric';
}

interface Payment {
  id: string;
  bookingId: string;
  amount: number;
  date: Date;
  method: string;
  status: 'completed' | 'pending' | 'failed' | 'refunded';
  spotName: string;
}

const UserDashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState(0);
  const [selectedBooking, setSelectedBooking] = useState<Booking | null>(null);
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false);

  // Mock data
  const user = {
    name: 'John Doe',
    email: 'john.doe@example.com',
    avatar: '/api/placeholder/100/100',
    memberSince: new Date('2023-01-15'),
    totalBookings: 45,
    totalSpent: 892.50,
  };

  const mockBookings: Booking[] = [
    {
      id: '1',
      spotName: 'Downtown Plaza Parking',
      spotAddress: '123 Main St, Downtown',
      startTime: new Date(Date.now() + 86400000), // Tomorrow
      endTime: new Date(Date.now() + 86400000 + 7200000), // Tomorrow + 2 hours
      duration: 2,
      totalCost: 16.50,
      status: 'upcoming',
      vehicleType: 'sedan',
      licensePlate: 'ABC-123',
      paymentMethod: 'Credit Card',
      bookingDate: new Date(),
    },
    {
      id: '2',
      spotName: 'City Center Garage',
      spotAddress: '456 Business Ave, City Center',
      startTime: new Date(Date.now() - 7200000), // 2 hours ago
      endTime: new Date(Date.now() + 1800000), // 30 minutes from now
      duration: 3,
      totalCost: 36.00,
      status: 'active',
      vehicleType: 'suv',
      licensePlate: 'XYZ-789',
      paymentMethod: 'Credit Card',
      bookingDate: new Date(Date.now() - 7200000),
    },
    {
      id: '3',
      spotName: 'Metro Station Parking',
      spotAddress: '789 Transit Blvd, Metro District',
      startTime: new Date(Date.now() - 172800000), // 2 days ago
      endTime: new Date(Date.now() - 165600000), // 2 days ago + 2 hours
      duration: 2,
      totalCost: 13.50,
      status: 'completed',
      vehicleType: 'sedan',
      licensePlate: 'ABC-123',
      paymentMethod: 'PayPal',
      bookingDate: new Date(Date.now() - 172800000),
    },
  ];

  const mockVehicles: Vehicle[] = [
    {
      id: '1',
      licensePlate: 'ABC-123',
      make: 'Toyota',
      model: 'Camry',
      color: 'Blue',
      type: 'sedan',
    },
    {
      id: '2',
      licensePlate: 'XYZ-789',
      make: 'Honda',
      model: 'CR-V',
      color: 'Black',
      type: 'suv',
    },
  ];

  const mockPayments: Payment[] = [
    {
      id: '1',
      bookingId: '2',
      amount: 36.00,
      date: new Date(Date.now() - 7200000),
      method: 'Credit Card',
      status: 'completed',
      spotName: 'City Center Garage',
    },
    {
      id: '2',
      bookingId: '3',
      amount: 13.50,
      date: new Date(Date.now() - 172800000),
      method: 'PayPal',
      status: 'completed',
      spotName: 'Metro Station Parking',
    },
  ];

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'success';
      case 'upcoming':
        return 'warning';
      case 'completed':
        return 'info';
      case 'cancelled':
        return 'error';
      default:
        return 'default';
    }
  };

  const handleCancelBooking = (booking: Booking) => {
    setSelectedBooking(booking);
    setCancelDialogOpen(true);
  };

  const confirmCancelBooking = () => {
    // Handle booking cancellation
    console.log('Cancelling booking:', selectedBooking?.id);
    setCancelDialogOpen(false);
    setSelectedBooking(null);
  };

  const BookingCard = ({ booking }: { booking: Booking }) => (
    <Card sx={{ mb: 2 }}>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
          <Box>
            <Typography variant="h6" gutterBottom>
              {booking.spotName}
            </Typography>
            <Typography color="text.secondary" variant="body2">
              {booking.spotAddress}
            </Typography>
          </Box>
          <Chip
            label={booking.status.toUpperCase()}
            color={getStatusColor(booking.status) as any}
            size="small"
          />
        </Box>
        
        <Stack spacing={1} sx={{ mb: 2 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
            <Typography variant="body2">Start:</Typography>
            <Typography variant="body2">{booking.startTime.toLocaleString()}</Typography>
          </Box>
          <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
            <Typography variant="body2">End:</Typography>
            <Typography variant="body2">{booking.endTime.toLocaleString()}</Typography>
          </Box>
          <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
            <Typography variant="body2">Duration:</Typography>
            <Typography variant="body2">{booking.duration} hours</Typography>
          </Box>
          <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
            <Typography variant="body2">Vehicle:</Typography>
            <Typography variant="body2">{booking.vehicleType} - {booking.licensePlate}</Typography>
          </Box>
          <Divider />
          <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
            <Typography variant="body2" fontWeight="bold">Total:</Typography>
            <Typography variant="body2" fontWeight="bold">${booking.totalCost.toFixed(2)}</Typography>
          </Box>
        </Stack>
      </CardContent>
      
      <CardActions>
        <Button size="small" startIcon={<ReceiptIcon />}>
          Receipt
        </Button>
        {booking.status === 'active' && (
          <Button size="small" startIcon={<QrCodeIcon />}>
            QR Code
          </Button>
        )}
        {(booking.status === 'upcoming' || booking.status === 'active') && (
          <Button
            size="small"
            color="error"
            startIcon={<CancelIcon />}
            onClick={() => handleCancelBooking(booking)}
          >
            Cancel
          </Button>
        )}
      </CardActions>
    </Card>
  );

  return (
    <Container maxWidth="lg">
      <Box sx={{ py: 4 }}>
        {/* Header */}
        <Paper sx={{ p: 3, mb: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Avatar sx={{ width: 64, height: 64 }} src={user.avatar}>
              <PersonIcon />
            </Avatar>
            <Box>
              <Typography variant="h4">{user.name}</Typography>
              <Typography color="text.secondary">{user.email}</Typography>
              <Typography variant="body2" color="text.secondary">
                Member since {user.memberSince.toLocaleDateString()}
              </Typography>
            </Box>
          </Box>
        </Paper>

        {/* Stats Cards */}
        <Box
          sx={{
            display: 'grid',
            gridTemplateColumns: { xs: '1fr', sm: 'repeat(3, 1fr)' },
            gap: 3,
            mb: 3,
          }}
        >
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <HistoryIcon sx={{ fontSize: 40, color: 'primary.main', mb: 1 }} />
              <Typography variant="h4">{user.totalBookings}</Typography>
              <Typography color="text.secondary">Total Bookings</Typography>
            </CardContent>
          </Card>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <PaymentIcon sx={{ fontSize: 40, color: 'success.main', mb: 1 }} />
              <Typography variant="h4">${user.totalSpent}</Typography>
              <Typography color="text.secondary">Total Spent</Typography>
            </CardContent>
          </Card>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <CarIcon sx={{ fontSize: 40, color: 'info.main', mb: 1 }} />
              <Typography variant="h4">{mockVehicles.length}</Typography>
              <Typography color="text.secondary">Vehicles</Typography>
            </CardContent>
          </Card>
        </Box>

        {/* Tabs */}
        <Paper sx={{ mb: 3 }}>
          <Tabs
            value={activeTab}
            onChange={(_, newValue) => setActiveTab(newValue)}
            variant="fullWidth"
          >
            <Tab label="Current Bookings" />
            <Tab label="Booking History" />
            <Tab label="Vehicles" />
            <Tab label="Payment History" />
          </Tabs>
        </Paper>

        {/* Tab Content */}
        {activeTab === 0 && (
          <Box>
            <Typography variant="h6" gutterBottom>
              Current & Upcoming Bookings
            </Typography>
            {mockBookings
              .filter(b => b.status === 'active' || b.status === 'upcoming')
              .map(booking => (
                <BookingCard key={booking.id} booking={booking} />
              ))
            }
            {mockBookings.filter(b => b.status === 'active' || b.status === 'upcoming').length === 0 && (
              <Alert severity="info">No current or upcoming bookings</Alert>
            )}
          </Box>
        )}

        {activeTab === 1 && (
          <Box>
            <Typography variant="h6" gutterBottom>
              Booking History
            </Typography>
            {mockBookings
              .filter(b => b.status === 'completed' || b.status === 'cancelled')
              .map(booking => (
                <BookingCard key={booking.id} booking={booking} />
              ))
            }
          </Box>
        )}

        {activeTab === 2 && (
          <Box>
            <Typography variant="h6" gutterBottom>
              My Vehicles
            </Typography>
            <Box
              sx={{
                display: 'grid',
                gridTemplateColumns: { xs: '1fr', md: 'repeat(2, 1fr)' },
                gap: 2,
              }}
            >
              {mockVehicles.map(vehicle => (
                <Card key={vehicle.id}>
                  <CardContent>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <Box>
                        <Typography variant="h6">
                          {vehicle.make} {vehicle.model}
                        </Typography>
                        <Typography color="text.secondary">
                          License: {vehicle.licensePlate}
                        </Typography>
                        <Typography color="text.secondary">
                          Color: {vehicle.color}
                        </Typography>
                        <Chip label={vehicle.type} size="small" sx={{ mt: 1 }} />
                      </Box>
                      <IconButton>
                        <EditIcon />
                      </IconButton>
                    </Box>
                  </CardContent>
                </Card>
              ))}
            </Box>
          </Box>
        )}

        {activeTab === 3 && (
          <Box>
            <Typography variant="h6" gutterBottom>
              Payment History
            </Typography>
            <TableContainer component={Paper}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Date</TableCell>
                    <TableCell>Parking Spot</TableCell>
                    <TableCell>Amount</TableCell>
                    <TableCell>Method</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {mockPayments.map(payment => (
                    <TableRow key={payment.id}>
                      <TableCell>{payment.date.toLocaleDateString()}</TableCell>
                      <TableCell>{payment.spotName}</TableCell>
                      <TableCell>${payment.amount.toFixed(2)}</TableCell>
                      <TableCell>{payment.method}</TableCell>
                      <TableCell>
                        <Chip
                          label={payment.status}
                          color={payment.status === 'completed' ? 'success' : 'default'}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>
                        <IconButton size="small">
                          <ReceiptIcon />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Box>
        )}

        {/* Cancel Booking Dialog */}
        <Dialog open={cancelDialogOpen} onClose={() => setCancelDialogOpen(false)}>
          <DialogTitle>Cancel Booking</DialogTitle>
          <DialogContent>
            <Typography>
              Are you sure you want to cancel your booking for {selectedBooking?.spotName}?
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              Cancellation fees may apply depending on the timing.
            </Typography>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setCancelDialogOpen(false)}>
              Keep Booking
            </Button>
            <Button onClick={confirmCancelBooking} color="error" variant="contained">
              Cancel Booking
            </Button>
          </DialogActions>
        </Dialog>
      </Box>
    </Container>
  );
};

export default UserDashboard;
