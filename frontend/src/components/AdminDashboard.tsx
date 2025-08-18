import React, { useState } from 'react';
import {
  Box,
  Container,
  Typography,
  Card,
  CardContent,
  Paper,
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  IconButton,
  Button,
  Stack,
  Alert,
  useTheme,
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  TrendingUp as TrendingUpIcon,
  People as PeopleIcon,
  DirectionsCar as CarIcon,
  AttachMoney as MoneyIcon,
  Analytics as AnalyticsIcon,
  Visibility as ViewIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Add as AddIcon,
} from '@mui/icons-material';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
} from 'chart.js';
import { Line, Bar, Doughnut } from 'react-chartjs-2';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement
);

interface ParkingLot {
  id: string;
  name: string;
  address: string;
  totalSpots: number;
  occupiedSpots: number;
  revenue: number;
  status: 'active' | 'maintenance' | 'closed';
}

interface DashboardStats {
  totalRevenue: number;
  totalBookings: number;
  activeUsers: number;
  occupancyRate: number;
  revenueGrowth: number;
  bookingGrowth: number;
}

const AdminDashboard: React.FC = () => {
  const theme = useTheme();
  const [activeTab, setActiveTab] = useState(0);

  // Mock data
  const dashboardStats: DashboardStats = {
    totalRevenue: 45789.50,
    totalBookings: 1234,
    activeUsers: 456,
    occupancyRate: 78.5,
    revenueGrowth: 12.5,
    bookingGrowth: 8.3,
  };

  const mockParkingLots: ParkingLot[] = [
    {
      id: '1',
      name: 'Downtown Plaza Parking',
      address: '123 Main St, Downtown',
      totalSpots: 150,
      occupiedSpots: 118,
      revenue: 12450.75,
      status: 'active',
    },
    {
      id: '2',
      name: 'City Center Garage',
      address: '456 Business Ave, City Center',
      totalSpots: 200,
      occupiedSpots: 156,
      revenue: 18920.30,
      status: 'active',
    },
    {
      id: '3',
      name: 'Metro Station Parking',
      address: '789 Transit Blvd, Metro District',
      totalSpots: 100,
      occupiedSpots: 45,
      revenue: 8765.25,
      status: 'maintenance',
    },
  ];

  // Chart data
  const revenueChartData = {
    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
    datasets: [
      {
        label: 'Revenue ($)',
        data: [12000, 19000, 15000, 25000, 22000, 30000],
        borderColor: theme.palette.primary.main,
        backgroundColor: theme.palette.primary.light + '20',
        tension: 0.4,
      },
    ],
  };

  const occupancyChartData = {
    labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
    datasets: [
      {
        label: 'Occupancy Rate (%)',
        data: [65, 78, 82, 85, 90, 88, 70],
        backgroundColor: theme.palette.success.main,
      },
    ],
  };

  const parkingTypeData = {
    labels: ['Regular', 'Electric', 'Handicapped', 'Motorcycle'],
    datasets: [
      {
        data: [60, 20, 10, 10],
        backgroundColor: [
          theme.palette.primary.main,
          theme.palette.success.main,
          theme.palette.warning.main,
          theme.palette.info.main,
        ],
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    plugins: {
      legend: {
        position: 'top' as const,
      },
    },
  };

  const StatCard = ({ 
    title, 
    value, 
    growth, 
    icon: Icon, 
    color 
  }: { 
    title: string; 
    value: string | number; 
    growth?: number; 
    icon: any; 
    color: string;
  }) => (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box>
            <Typography color="text.secondary" gutterBottom>
              {title}
            </Typography>
            <Typography variant="h4" component="div">
              {value}
            </Typography>
            {growth !== undefined && (
              <Typography
                variant="body2"
                color={growth > 0 ? 'success.main' : 'error.main'}
                sx={{ display: 'flex', alignItems: 'center', mt: 1 }}
              >
                <TrendingUpIcon fontSize="small" sx={{ mr: 0.5 }} />
                {growth > 0 ? '+' : ''}{growth}%
              </Typography>
            )}
          </Box>
          <Icon sx={{ fontSize: 40, color }} />
        </Box>
      </CardContent>
    </Card>
  );

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'success';
      case 'maintenance':
        return 'warning';
      case 'closed':
        return 'error';
      default:
        return 'default';
    }
  };

  const getOccupancyColor = (rate: number) => {
    if (rate >= 80) return 'error.main';
    if (rate >= 60) return 'warning.main';
    return 'success.main';
  };

  return (
    <Container maxWidth="xl">
      <Box sx={{ py: 4 }}>
        {/* Header */}
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 4 }}>
          <DashboardIcon sx={{ fontSize: 40, mr: 2, color: 'primary.main' }} />
          <Typography variant="h4" component="h1">
            Admin Dashboard
          </Typography>
        </Box>

        {/* Stats Overview */}
        <Box
          sx={{
            display: 'grid',
            gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', lg: 'repeat(4, 1fr)' },
            gap: 3,
            mb: 4,
          }}
        >
          <StatCard
            title="Total Revenue"
            value={`$${dashboardStats.totalRevenue.toLocaleString()}`}
            growth={dashboardStats.revenueGrowth}
            icon={MoneyIcon}
            color={theme.palette.success.main}
          />
          <StatCard
            title="Total Bookings"
            value={dashboardStats.totalBookings}
            growth={dashboardStats.bookingGrowth}
            icon={CarIcon}
            color={theme.palette.primary.main}
          />
          <StatCard
            title="Active Users"
            value={dashboardStats.activeUsers}
            icon={PeopleIcon}
            color={theme.palette.info.main}
          />
          <StatCard
            title="Occupancy Rate"
            value={`${dashboardStats.occupancyRate}%`}
            icon={AnalyticsIcon}
            color={theme.palette.warning.main}
          />
        </Box>

        {/* Tabs */}
        <Paper sx={{ mb: 3 }}>
          <Tabs
            value={activeTab}
            onChange={(_, newValue) => setActiveTab(newValue)}
            variant="fullWidth"
          >
            <Tab label="Analytics" />
            <Tab label="Parking Lots" />
            <Tab label="Real-time Monitoring" />
            <Tab label="Reports" />
          </Tabs>
        </Paper>

        {/* Tab Content */}
        {activeTab === 0 && (
          <Box>
            <Typography variant="h6" gutterBottom>
              Analytics Dashboard
            </Typography>
            <Box
              sx={{
                display: 'grid',
                gridTemplateColumns: { xs: '1fr', lg: 'repeat(2, 1fr)' },
                gap: 3,
                mb: 3,
              }}
            >
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Revenue Trend
                  </Typography>
                  <Line data={revenueChartData} options={chartOptions} />
                </CardContent>
              </Card>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Weekly Occupancy
                  </Typography>
                  <Bar data={occupancyChartData} options={chartOptions} />
                </CardContent>
              </Card>
            </Box>
            <Box
              sx={{
                display: 'grid',
                gridTemplateColumns: { xs: '1fr', lg: 'repeat(2, 1fr)' },
                gap: 3,
              }}
            >
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Parking Spot Types
                  </Typography>
                  <Box sx={{ maxWidth: 400, mx: 'auto' }}>
                    <Doughnut data={parkingTypeData} options={chartOptions} />
                  </Box>
                </CardContent>
              </Card>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Key Metrics
                  </Typography>
                  <Stack spacing={2}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography>Average Session Duration:</Typography>
                      <Typography fontWeight="bold">2.4 hours</Typography>
                    </Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography>Peak Hours:</Typography>
                      <Typography fontWeight="bold">9 AM - 11 AM</Typography>
                    </Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography>Most Popular Spot Type:</Typography>
                      <Typography fontWeight="bold">Regular</Typography>
                    </Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography>Customer Satisfaction:</Typography>
                      <Typography fontWeight="bold">4.8/5</Typography>
                    </Box>
                  </Stack>
                </CardContent>
              </Card>
            </Box>
          </Box>
        )}

        {activeTab === 1 && (
          <Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
              <Typography variant="h6">
                Parking Lot Management
              </Typography>
              <Button variant="contained" startIcon={<AddIcon />}>
                Add New Lot
              </Button>
            </Box>
            <TableContainer component={Paper}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Name</TableCell>
                    <TableCell>Address</TableCell>
                    <TableCell>Occupancy</TableCell>
                    <TableCell>Revenue</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {mockParkingLots.map((lot) => (
                    <TableRow key={lot.id}>
                      <TableCell>{lot.name}</TableCell>
                      <TableCell>{lot.address}</TableCell>
                      <TableCell>
                        <Box>
                          <Typography variant="body2">
                            {lot.occupiedSpots}/{lot.totalSpots}
                          </Typography>
                          <Typography
                            variant="caption"
                            sx={{ color: getOccupancyColor((lot.occupiedSpots / lot.totalSpots) * 100) }}
                          >
                            {((lot.occupiedSpots / lot.totalSpots) * 100).toFixed(1)}%
                          </Typography>
                        </Box>
                      </TableCell>
                      <TableCell>${lot.revenue.toLocaleString()}</TableCell>
                      <TableCell>
                        <Chip
                          label={lot.status}
                          color={getStatusColor(lot.status) as any}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>
                        <IconButton size="small" sx={{ mr: 1 }}>
                          <ViewIcon />
                        </IconButton>
                        <IconButton size="small" sx={{ mr: 1 }}>
                          <EditIcon />
                        </IconButton>
                        <IconButton size="small" color="error">
                          <DeleteIcon />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Box>
        )}

        {activeTab === 2 && (
          <Box>
            <Typography variant="h6" gutterBottom>
              Real-time Monitoring
            </Typography>
            <Alert severity="info" sx={{ mb: 3 }}>
              Real-time data updates every 30 seconds
            </Alert>
            <Box
              sx={{
                display: 'grid',
                gridTemplateColumns: { xs: '1fr', md: 'repeat(3, 1fr)' },
                gap: 3,
              }}
            >
              {mockParkingLots.map((lot) => (
                <Card key={lot.id}>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      {lot.name}
                    </Typography>
                    <Stack spacing={2}>
                      <Box>
                        <Typography variant="body2" color="text.secondary">
                          Occupancy
                        </Typography>
                        <Typography variant="h4">
                          {lot.occupiedSpots}/{lot.totalSpots}
                        </Typography>
                        <Typography
                          variant="body2"
                          sx={{ color: getOccupancyColor((lot.occupiedSpots / lot.totalSpots) * 100) }}
                        >
                          {((lot.occupiedSpots / lot.totalSpots) * 100).toFixed(1)}% Full
                        </Typography>
                      </Box>
                      <Box>
                        <Typography variant="body2" color="text.secondary">
                          Status
                        </Typography>
                        <Chip
                          label={lot.status}
                          color={getStatusColor(lot.status) as any}
                          size="small"
                        />
                      </Box>
                      <Box>
                        <Typography variant="body2" color="text.secondary">
                          Today's Revenue
                        </Typography>
                        <Typography variant="h6">
                          ${(lot.revenue * 0.15).toFixed(2)}
                        </Typography>
                      </Box>
                    </Stack>
                  </CardContent>
                </Card>
              ))}
            </Box>
          </Box>
        )}

        {activeTab === 3 && (
          <Box>
            <Typography variant="h6" gutterBottom>
              Reports & Analytics
            </Typography>
            <Box
              sx={{
                display: 'grid',
                gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', lg: 'repeat(3, 1fr)' },
                gap: 3,
              }}
            >
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Revenue Report
                  </Typography>
                  <Typography variant="body2" color="text.secondary" paragraph>
                    Monthly revenue breakdown and trends
                  </Typography>
                  <Button variant="outlined" fullWidth>
                    Generate Report
                  </Button>
                </CardContent>
              </Card>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Occupancy Report
                  </Typography>
                  <Typography variant="body2" color="text.secondary" paragraph>
                    Detailed occupancy patterns and insights
                  </Typography>
                  <Button variant="outlined" fullWidth>
                    Generate Report
                  </Button>
                </CardContent>
              </Card>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Customer Report
                  </Typography>
                  <Typography variant="body2" color="text.secondary" paragraph>
                    User behavior and satisfaction metrics
                  </Typography>
                  <Button variant="outlined" fullWidth>
                    Generate Report
                  </Button>
                </CardContent>
              </Card>
            </Box>
          </Box>
        )}
      </Box>
    </Container>
  );
};

export default AdminDashboard;
