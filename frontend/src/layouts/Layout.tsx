import { Outlet } from 'react-router-dom';
import { Box, AppBar, Toolbar, Typography, Drawer, List, ListItem, ListItemIcon, ListItemText } from '@mui/material';
import { Dashboard, LocalParking, BookOnline, Settings } from '@mui/icons-material';
import { useAppSelector, useAppDispatch } from '@/hooks';
import { toggleSidebar } from '@/store/slices/uiSlice';
import { Link, useLocation } from 'react-router-dom';
import styled from 'styled-components';

const drawerWidth = 240;

const StyledDrawer = styled(Drawer)`
  .MuiDrawer-paper {
    width: ${drawerWidth}px;
    box-sizing: border-box;
    background: ${({ theme }) => theme.palette.background.paper};
  }
`;

const StyledListItem = styled(ListItem)<{ $active?: boolean }>`
  background-color: ${({ $active, theme }) => 
    $active ? theme.palette.action.selected : 'transparent'};
  margin: 8px;
  border-radius: 8px;
  
  &:hover {
    background-color: ${({ theme }) => theme.palette.action.hover};
  }
`;

const menuItems = [
  { text: 'Dashboard', icon: <Dashboard />, path: '/' },
  { text: 'Parking Lots', icon: <LocalParking />, path: '/parking-lots' },
  { text: 'Reservations', icon: <BookOnline />, path: '/reservations' },
  { text: 'Settings', icon: <Settings />, path: '/settings' },
];

const Layout = () => {
  const { sidebarOpen } = useAppSelector(state => state.ui);
  const location = useLocation();

  return (
    <Box sx={{ display: 'flex' }}>
      <AppBar
        position="fixed"
        sx={{
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          ml: { sm: `${drawerWidth}px` },
        }}
      >
        <Toolbar>
          <Typography variant="h6" noWrap component="div">
            Smart Parking Management
          </Typography>
        </Toolbar>
      </AppBar>

      <Box
        component="nav"
        sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }}
      >
        <StyledDrawer
          variant="permanent"
          sx={{
            display: { xs: 'none', sm: 'block' },
          }}
          open
        >
          <Toolbar />
          <Box sx={{ overflow: 'auto' }}>
            <List>
              {menuItems.map((item) => (
                <StyledListItem
                  key={item.text}
                  component={Link}
                  to={item.path}
                  $active={location.pathname === item.path}
                >
                  <ListItemIcon>{item.icon}</ListItemIcon>
                  <ListItemText primary={item.text} />
                </StyledListItem>
              ))}
            </List>
          </Box>
        </StyledDrawer>
      </Box>

      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: { sm: `calc(100% - ${drawerWidth}px)` },
        }}
      >
        <Toolbar />
        <Outlet />
      </Box>
    </Box>
  );
};

export default Layout;