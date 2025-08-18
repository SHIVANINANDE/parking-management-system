import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  Button,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Switch,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import {
  TrendingUp,
  TrendingDown,
  People,
  LocalParking,
  AttachMoney,
  Refresh,
  Settings,
  Notifications,
  Download,
} from '@mui/icons-material';
import MapComponent from './MapComponent';

// Mock data for demonstration
const mockMetrics = {
  totalRevenue: 125480,
  revenueChange: 12.5,
  activeUsers: 1247,
  usersChange: -3.2,
  occupiedSpots: 342,
  totalSpots: 450,
  occupancyChange: 8.7,
  totalReservations: 89,
  reservationsChange: 15.3,
};

const mockActivity = [
  {
    id: '1',
    description: 'New reservation made for Spot A-15',
    timestamp: new Date().toISOString(),
    type: 'reservation',
  },
  {
    id: '2',
    description: 'Payment completed - $25.00',
    timestamp: new Date(Date.now() - 1000 * 60 * 15).toISOString(),
    type: 'payment',
  },
  {
    id: '3',
    description: 'Parking lot B reached 90% capacity',
    timestamp: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
    type: 'alert',
  },
  {
    id: '4',
    description: 'User checked out from Spot C-7',
    timestamp: new Date(Date.now() - 1000 * 60 * 45).toISOString(),
    type: 'checkout',
  },
];

// Stats Card Component
interface StatsCardProps {
  title: string;
  value: string | number;
  change: number;
  icon: React.ReactNode;
  color: 'primary' | 'secondary' | 'success' | 'error' | 'warning' | 'info';
}

const StatsCard: React.FC<StatsCardProps> = ({ title, value, change, icon, color }) => {
  const isPositive = change >= 0;
  
  return (
    <Card sx={{ height: '100%' }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <Box
            sx={{
              p: 1,
              borderRadius: 1,
              backgroundColor: `${color}.light`,
              color: `${color}.contrastText`,
              mr: 2,
            }}
          >
            {icon}
          </Box>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            {title}
          </Typography>
        </Box>
        
        <Typography variant="h4" component="div" gutterBottom>
          {value}
        </Typography>
        
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          {isPositive ? (
            <TrendingUp sx={{ color: 'success.main', mr: 0.5 }} />
          ) : (
            <TrendingDown sx={{ color: 'error.main', mr: 0.5 }} />
          )}
          <Typography
            variant="body2"
            sx={{
              color: isPositive ? 'success.main' : 'error.main',
              fontWeight: 'medium',
            }}
          >
            {isPositive ? '+' : ''}{change.toFixed(1)}%
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ ml: 1 }}>
            from last month
          </Typography>
        </Box>
      </CardContent>
    </Card>
  );
};

// Recent Activity Component
const RecentActivity: React.FC = () => {
  return (
    <Card sx={{ height: 400 }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Recent Activity
        </Typography>
        
        <List sx={{ maxHeight: 300, overflow: 'auto' }}>
          {mockActivity.map((activity) => (
            <ListItem key={activity.id} divider>
              <ListItemText
                primary={activity.description}
                secondary={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography variant="body2" color="text.secondary">
                      {new Date(activity.timestamp).toLocaleString()}
                    </Typography>
                    <Chip
                      label={activity.type}
                      size="small"
                      color={
                        activity.type === 'reservation' ? 'primary' :
                        activity.type === 'payment' ? 'success' :
                        activity.type === 'alert' ? 'warning' : 'default'
                      }
                    />
                  </Box>
                }
              />
            </ListItem>
          ))}
        </List>
      </CardContent>
    </Card>
  );
};

// Settings Dialog Component
interface SettingsDialogProps {
  open: boolean;
  onClose: () => void;
}

const SettingsDialog: React.FC<SettingsDialogProps> = ({ open, onClose }) => {
  const [settings, setSettings] = useState({
    autoRefresh: true,
    refreshInterval: 30,
    notifications: true,
    emailAlerts: false,
    theme: 'light',
  });

  const handleSave = () => {
    // Here you would dispatch settings to the store
    console.log('Saving settings:', settings);
    onClose();
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Dashboard Settings</DialogTitle>
      <DialogContent>
        <Box sx={{ mt: 2 }}>
          <List>
            <ListItem>
              <ListItemText primary="Auto Refresh" secondary="Automatically refresh dashboard data" />
              <ListItemSecondaryAction>
                <Switch
                  checked={settings.autoRefresh}
                  onChange={(e) => setSettings({ ...settings, autoRefresh: e.target.checked })}
                />
              </ListItemSecondaryAction>
            </ListItem>
            
            <ListItem>
              <ListItemText primary="Notifications" secondary="Show system notifications" />
              <ListItemSecondaryAction>
                <Switch
                  checked={settings.notifications}
                  onChange={(e) => setSettings({ ...settings, notifications: e.target.checked })}
                />
              </ListItemSecondaryAction>
            </ListItem>
            
            <ListItem>
              <ListItemText primary="Email Alerts" secondary="Receive email notifications" />
              <ListItemSecondaryAction>
                <Switch
                  checked={settings.emailAlerts}
                  onChange={(e) => setSettings({ ...settings, emailAlerts: e.target.checked })}
                />
              </ListItemSecondaryAction>
            </ListItem>
          </List>
          
          <Box sx={{ mt: 3, display: 'flex', gap: 2 }}>
            <FormControl size="small" sx={{ minWidth: 160 }}>
              <InputLabel>Refresh Interval</InputLabel>
              <Select
                value={settings.refreshInterval}
                label="Refresh Interval"
                onChange={(e) => setSettings({ ...settings, refreshInterval: e.target.value as number })}
              >
                <MenuItem value={15}>15 seconds</MenuItem>
                <MenuItem value={30}>30 seconds</MenuItem>
                <MenuItem value={60}>1 minute</MenuItem>
                <MenuItem value={300}>5 minutes</MenuItem>
              </Select>
            </FormControl>
            
            <FormControl size="small" sx={{ minWidth: 120 }}>
              <InputLabel>Theme</InputLabel>
              <Select
                value={settings.theme}
                label="Theme"
                onChange={(e) => setSettings({ ...settings, theme: e.target.value })}
              >
                <MenuItem value="light">Light</MenuItem>
                <MenuItem value="dark">Dark</MenuItem>
                <MenuItem value="auto">Auto</MenuItem>
              </Select>
            </FormControl>
          </Box>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button onClick={handleSave} variant="contained">Save</Button>
      </DialogActions>
    </Dialog>
  );
};

// Main Dashboard Component
const Dashboard: React.FC = () => {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [filterDate, setFilterDate] = useState('today');

  const handleRefresh = () => {
    console.log('Refreshing dashboard data...');
  };

  const handleExport = () => {
    console.log('Exporting dashboard data...');
  };

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Dashboard
        </Typography>
        
        <Box sx={{ display: 'flex', gap: 1 }}>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Time Range</InputLabel>
            <Select
              value={filterDate}
              label="Time Range"
              onChange={(e) => setFilterDate(e.target.value)}
            >
              <MenuItem value="today">Today</MenuItem>
              <MenuItem value="week">This Week</MenuItem>
              <MenuItem value="month">This Month</MenuItem>
              <MenuItem value="year">This Year</MenuItem>
            </Select>
          </FormControl>
          
          <IconButton onClick={handleRefresh}>
            <Refresh />
          </IconButton>
          
          <IconButton onClick={handleExport}>
            <Download />
          </IconButton>
          
          <IconButton onClick={() => setSettingsOpen(true)}>
            <Settings />
          </IconButton>
        </Box>
      </Box>

      {/* Stats Cards */}
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 3, mb: 3 }}>
        <Box sx={{ flex: '1 1 300px', minWidth: 250 }}>
          <StatsCard
            title="Total Revenue"
            value={`$${mockMetrics.totalRevenue.toLocaleString()}`}
            change={mockMetrics.revenueChange}
            icon={<AttachMoney />}
            color="success"
          />
        </Box>
        
        <Box sx={{ flex: '1 1 300px', minWidth: 250 }}>
          <StatsCard
            title="Active Users"
            value={mockMetrics.activeUsers.toLocaleString()}
            change={mockMetrics.usersChange}
            icon={<People />}
            color="primary"
          />
        </Box>
        
        <Box sx={{ flex: '1 1 300px', minWidth: 250 }}>
          <StatsCard
            title="Occupied Spots"
            value={`${mockMetrics.occupiedSpots} / ${mockMetrics.totalSpots}`}
            change={mockMetrics.occupancyChange}
            icon={<LocalParking />}
            color="warning"
          />
        </Box>
        
        <Box sx={{ flex: '1 1 300px', minWidth: 250 }}>
          <StatsCard
            title="Reservations"
            value={mockMetrics.totalReservations.toLocaleString()}
            change={mockMetrics.reservationsChange}
            icon={<Notifications />}
            color="info"
          />
        </Box>
      </Box>

      {/* Main Content */}
      <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
        {/* Map */}
        <Box sx={{ flex: '2 1 600px', minWidth: 600 }}>
          <Card sx={{ height: 500 }}>
            <CardContent sx={{ p: 0, height: '100%' }}>
              <MapComponent height="100%" />
            </CardContent>
          </Card>
        </Box>
        
        {/* Recent Activity */}
        <Box sx={{ flex: '1 1 300px', minWidth: 300 }}>
          <RecentActivity />
        </Box>
      </Box>

      {/* Settings Dialog */}
      <SettingsDialog
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
      />
    </Box>
  );
};

export default Dashboard;
