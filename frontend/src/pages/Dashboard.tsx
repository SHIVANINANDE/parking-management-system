import { Paper, Typography, Box, Card, CardContent } from '@mui/material';
import { LocalParking, DirectionsCar, Schedule, TrendingUp } from '@mui/icons-material';
import styled from 'styled-components';

const StatsCard = styled(Card)`
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 16px;
`;

const IconWrapper = styled(Box)`
  display: flex;
  align-items: center;
  justify-content: center;
  width: 60px;
  height: 60px;
  border-radius: 50%;
  margin-bottom: 16px;
`;

const statsData = [
  {
    title: 'Total Spots',
    value: '500',
    icon: <LocalParking />,
    color: '#1976d2',
    bgColor: '#e3f2fd',
  },
  {
    title: 'Available',
    value: '234',
    icon: <DirectionsCar />,
    color: '#4caf50',
    bgColor: '#e8f5e8',
  },
  {
    title: 'Reserved',
    value: '45',
    icon: <Schedule />,
    color: '#ff9800',
    bgColor: '#fff3e0',
  },
  {
    title: 'Utilization',
    value: '68%',
    icon: <TrendingUp />,
    color: '#9c27b0',
    bgColor: '#f3e5f5',
  },
];

const Dashboard = () => {
  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Dashboard
      </Typography>
      
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
        <Box sx={{ 
          display: 'grid', 
          gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr', md: '1fr 1fr 1fr 1fr' },
          gap: 3 
        }}>
          {statsData.map((stat, index) => (
            <StatsCard key={index}>
              <CardContent>
                <IconWrapper sx={{ backgroundColor: stat.bgColor }}>
                  <Box sx={{ color: stat.color }}>
                    {stat.icon}
                  </Box>
                </IconWrapper>
                <Typography variant="h4" component="div" gutterBottom>
                  {stat.value}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {stat.title}
                </Typography>
              </CardContent>
            </StatsCard>
          ))}
        </Box>
        
        <Box sx={{ 
          display: 'grid', 
          gridTemplateColumns: { xs: '1fr', md: '2fr 1fr' },
          gap: 3 
        }}>
          <Paper sx={{ p: 2, height: 400 }}>
            <Typography variant="h6" gutterBottom>
              Parking Lot Occupancy
            </Typography>
            <Box 
              sx={{ 
                height: '100%', 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center',
                color: 'text.secondary' 
              }}
            >
              Chart will be implemented here
            </Box>
          </Paper>
          
          <Paper sx={{ p: 2, height: 400 }}>
            <Typography variant="h6" gutterBottom>
              Recent Activities
            </Typography>
            <Box 
              sx={{ 
                height: '100%', 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center',
                color: 'text.secondary' 
              }}
            >
              Activity feed will be implemented here
            </Box>
          </Paper>
        </Box>
      </Box>
    </Box>
  );
};

export default Dashboard;