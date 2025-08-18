import React, { useState } from 'react';
import {
  Box,
  Container,
  Typography,
  Tabs,
  Tab,
  Paper,
} from '@mui/material';
import {
  Search as SearchIcon,
  Dashboard as DashboardIcon,
  Person as PersonIcon,
  AdminPanelSettings as AdminIcon,
} from '@mui/icons-material';
import ParkingSpotSearch from '../components/ParkingSpotSearch';
import UserDashboard from '../components/UserDashboard';
import AdminDashboard from '../components/AdminDashboard';

const DashboardPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState(0);

  const tabs = [
    {
      label: 'Search Parking',
      icon: SearchIcon,
      component: <ParkingSpotSearch />,
    },
    {
      label: 'My Dashboard',
      icon: PersonIcon,
      component: <UserDashboard />,
    },
    {
      label: 'Admin Panel',
      icon: AdminIcon,
      component: <AdminDashboard />,
    },
  ];

  return (
    <Container maxWidth="xl">
      <Box sx={{ py: 4 }}>
        {/* Header */}
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 4 }}>
          <DashboardIcon sx={{ fontSize: 40, mr: 2, color: 'primary.main' }} />
          <Typography variant="h4" component="h1">
            Parking Management System
          </Typography>
        </Box>

        {/* Navigation Tabs */}
        <Paper sx={{ mb: 3 }}>
          <Tabs
            value={activeTab}
            onChange={(_, newValue) => setActiveTab(newValue)}
            variant="fullWidth"
          >
            {tabs.map((tab, index) => (
              <Tab
                key={index}
                label={tab.label}
                icon={<tab.icon />}
                iconPosition="start"
              />
            ))}
          </Tabs>
        </Paper>

        {/* Tab Content */}
        <Box>
          {tabs[activeTab].component}
        </Box>
      </Box>
    </Container>
  );
};

export default DashboardPage;