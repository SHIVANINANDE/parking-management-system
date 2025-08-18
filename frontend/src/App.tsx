import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { Provider } from 'react-redux';
import { ThemeProvider, CssBaseline, GlobalStyles } from '@mui/material';
import { store } from './store';
import { queryClient } from './services/queryClient';
import { initializeWebSockets } from './services/websocket';
import theme from './theme/theme';
import Layout from './layouts/Layout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import ParkingLots from './pages/ParkingLots';
import Reservations from './pages/Reservations';
import Analytics from './pages/Analytics';
import { useAppSelector } from './hooks/useAppSelector';
import './App.css';

// Global styles for Leaflet
const leafletStyles = {
  '@global': {
    '.leaflet-container': {
      height: '100%',
      width: '100%',
      background: 'transparent',
    },
    '.leaflet-tile-pane': {
      filter: 'brightness(0.95)',
    },
    '.leaflet-control-zoom': {
      border: 'none !important',
      borderRadius: '8px !important',
      boxShadow: '0 2px 8px rgba(0,0,0,0.15) !important',
    },
    '.leaflet-control-zoom a': {
      backgroundColor: '#fff !important',
      border: 'none !important',
      borderRadius: '0 !important',
      color: '#333 !important',
      fontSize: '16px !important',
      fontWeight: 'bold !important',
      '&:hover': {
        backgroundColor: '#f5f5f5 !important',
      },
    },
    '.leaflet-control-zoom a:first-of-type': {
      borderTopLeftRadius: '8px !important',
      borderTopRightRadius: '8px !important',
    },
    '.leaflet-control-zoom a:last-of-type': {
      borderBottomLeftRadius: '8px !important',
      borderBottomRightRadius: '8px !important',
    },
    '.leaflet-popup': {
      '& .leaflet-popup-content-wrapper': {
        borderRadius: '12px',
        boxShadow: '0 4px 20px rgba(0,0,0,0.15)',
        border: 'none',
      },
      '& .leaflet-popup-tip': {
        backgroundColor: '#fff',
        boxShadow: 'none',
      },
    },
    '.leaflet-marker-icon': {
      filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.2))',
    },
    '.custom-div-icon': {
      backgroundColor: 'transparent !important',
      border: 'none !important',
    },
    // Custom spot status colors
    '.spot-marker': {
      borderRadius: '50%',
      border: '2px solid #fff',
      boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
      '&.available': {
        backgroundColor: '#4caf50',
      },
      '&.occupied': {
        backgroundColor: '#f44336',
      },
      '&.reserved': {
        backgroundColor: '#ff9800',
      },
      '&.maintenance': {
        backgroundColor: '#9e9e9e',
      },
    },
    // Custom cluster styles
    '.marker-cluster': {
      backgroundColor: 'rgba(33, 150, 243, 0.6) !important',
      border: '2px solid #fff !important',
      borderRadius: '50% !important',
      color: '#fff !important',
      fontWeight: 'bold !important',
      textAlign: 'center !important',
      fontSize: '12px !important',
      '&.marker-cluster-small': {
        backgroundColor: 'rgba(33, 150, 243, 0.6) !important',
      },
      '&.marker-cluster-medium': {
        backgroundColor: 'rgba(33, 150, 243, 0.7) !important',
      },
      '&.marker-cluster-large': {
        backgroundColor: 'rgba(33, 150, 243, 0.8) !important',
      },
    },
  },
};

// Protected Route Component
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const isAuthenticated = useAppSelector((state) => state.auth.isAuthenticated);
  
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />;
};

// Main App Component
const AppContent: React.FC = () => {
  const isAuthenticated = useAppSelector((state) => state.auth.isAuthenticated);

  useEffect(() => {
    // Initialize WebSocket connections when app starts
    if (isAuthenticated) {
      initializeWebSockets();
    }
  }, [isAuthenticated]);

  return (
    <Router>
      <Routes>
        <Route 
          path="/login" 
          element={
            isAuthenticated ? <Navigate to="/dashboard" replace /> : <Login />
          } 
        />
        <Route 
          path="/" 
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="parking-lots" element={<ParkingLots />} />
          <Route path="reservations" element={<Reservations />} />
          <Route path="analytics" element={<Analytics />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
};

// Root App Component with Providers
const App: React.FC = () => {
  return (
    <Provider store={store}>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider theme={theme}>
          <CssBaseline />
          <GlobalStyles styles={leafletStyles} />
          <AppContent />
          {/* React Query Devtools - only in development */}
          {import.meta.env.DEV && <ReactQueryDevtools initialIsOpen={false} />}
        </ThemeProvider>
      </QueryClientProvider>
    </Provider>
  );
};

export default App;
