import React, { useState } from 'react';
import {
  Box,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  IconButton,
  Card,
  CardContent,
  Tabs,
  Tab,
  Chip,
  Tooltip,
  Stack,
} from '@mui/material';
import {
  DateRange,
  Download,
  Refresh,
  TrendingUp,
  PieChart,
  BarChart,
  Timeline,
  Insights,
  Settings,
} from '@mui/icons-material';
import AnalyticsChart from '../components/AnalyticsChart';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`analytics-tabpanel-${index}`}
      aria-labelledby={`analytics-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ py: 3 }}>
          {children}
        </Box>
      )}
    </div>
  );
}

function a11yProps(index: number) {
  return {
    id: `analytics-tab-${index}`,
    'aria-controls': `analytics-tabpanel-${index}`,
  };
}

const AnalyticsDashboard: React.FC = () => {
  const [timeRange, setTimeRange] = useState('today');
  const [currentTab, setCurrentTab] = useState(0);
  const [refreshing, setRefreshing] = useState(false);

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setCurrentTab(newValue);
  };

  const handleRefresh = () => {
    setRefreshing(true);
    // Simulate data refresh
    setTimeout(() => setRefreshing(false), 2000);
  };

  const handleExport = () => {
    console.log('Exporting analytics data...');
  };

  const handleDateRangeChange = (range: string) => {
    setTimeRange(range);
    // Here you would typically fetch new data based on the range
  };

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" component="h1" gutterBottom>
            Analytics Dashboard
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Comprehensive parking analytics and insights
          </Typography>
        </Box>
        
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
          <FormControl size="small" sx={{ minWidth: 140 }}>
            <InputLabel>Time Range</InputLabel>
            <Select
              value={timeRange}
              label="Time Range"
              onChange={(e) => handleDateRangeChange(e.target.value)}
              startAdornment={<DateRange sx={{ mr: 1, color: 'action.active' }} />}
            >
              <MenuItem value="today">Today</MenuItem>
              <MenuItem value="yesterday">Yesterday</MenuItem>
              <MenuItem value="week">This Week</MenuItem>
              <MenuItem value="month">This Month</MenuItem>
              <MenuItem value="quarter">This Quarter</MenuItem>
              <MenuItem value="year">This Year</MenuItem>
              <MenuItem value="custom">Custom Range</MenuItem>
            </Select>
          </FormControl>
          
          <Tooltip title="Refresh Data">
            <IconButton onClick={handleRefresh} disabled={refreshing}>
              <Refresh />
            </IconButton>
          </Tooltip>
          
          <Tooltip title="Export Data">
            <Button
              variant="outlined"
              startIcon={<Download />}
              onClick={handleExport}
              size="small"
            >
              Export
            </Button>
          </Tooltip>
          
          <Tooltip title="Settings">
            <IconButton>
              <Settings />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* Quick Stats */}
      <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
        <Card sx={{ flex: '1 1 200px', minWidth: 200 }}>
          <CardContent sx={{ textAlign: 'center' }}>
            <TrendingUp sx={{ fontSize: 40, color: 'primary.main', mb: 1 }} />
            <Typography variant="h6">Peak Hour</Typography>
            <Typography variant="h4" color="primary">6 PM</Typography>
            <Typography variant="body2" color="text.secondary">
              Highest occupancy time
            </Typography>
          </CardContent>
        </Card>
        
        <Card sx={{ flex: '1 1 200px', minWidth: 200 }}>
          <CardContent sx={{ textAlign: 'center' }}>
            <PieChart sx={{ fontSize: 40, color: 'success.main', mb: 1 }} />
            <Typography variant="h6">Avg Occupancy</Typography>
            <Typography variant="h4" color="success.main">78%</Typography>
            <Typography variant="body2" color="text.secondary">
              Overall utilization rate
            </Typography>
          </CardContent>
        </Card>
        
        <Card sx={{ flex: '1 1 200px', minWidth: 200 }}>
          <CardContent sx={{ textAlign: 'center' }}>
            <BarChart sx={{ fontSize: 40, color: 'warning.main', mb: 1 }} />
            <Typography variant="h6">Revenue</Typography>
            <Typography variant="h4" color="warning.main">$12.5K</Typography>
            <Typography variant="body2" color="text.secondary">
              Today's earnings
            </Typography>
          </CardContent>
        </Card>
        
        <Card sx={{ flex: '1 1 200px', minWidth: 200 }}>
          <CardContent sx={{ textAlign: 'center' }}>
            <Timeline sx={{ fontSize: 40, color: 'info.main', mb: 1 }} />
            <Typography variant="h6">Avg Duration</Typography>
            <Typography variant="h4" color="info.main">2.3h</Typography>
            <Typography variant="body2" color="text.secondary">
              Average parking time
            </Typography>
          </CardContent>
        </Card>
      </Box>

      {/* Tabs */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
        <Tabs 
          value={currentTab} 
          onChange={handleTabChange} 
          aria-label="analytics tabs"
          variant="scrollable"
          scrollButtons="auto"
        >
          <Tab 
            label={
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <TrendingUp fontSize="small" />
                <span>Occupancy Trends</span>
              </Box>
            } 
            {...a11yProps(0)} 
          />
          <Tab 
            label={
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <BarChart fontSize="small" />
                <span>Revenue Analytics</span>
              </Box>
            } 
            {...a11yProps(1)} 
          />
          <Tab 
            label={
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <PieChart fontSize="small" />
                <span>Distribution</span>
              </Box>
            } 
            {...a11yProps(2)} 
          />
          <Tab 
            label={
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Insights fontSize="small" />
                <span>Insights</span>
              </Box>
            } 
            {...a11yProps(3)} 
          />
        </Tabs>
      </Box>

      {/* Tab Panels */}
      <TabPanel value={currentTab} index={0}>
        <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
          <Box sx={{ flex: '2 1 600px', minWidth: 600 }}>
            <AnalyticsChart
              title="Hourly Occupancy Trends"
              chartType="line"
              dataType="occupancy"
              height={400}
              showControls={true}
            />
          </Box>
          <Box sx={{ flex: '1 1 400px', minWidth: 400 }}>
            <AnalyticsChart
              title="Occupancy vs Availability"
              chartType="area"
              dataType="occupancy"
              height={400}
              showControls={false}
            />
          </Box>
        </Box>
        
        <Box sx={{ mt: 3 }}>
          <AnalyticsChart
            title="Daily Occupancy Overview"
            chartType="bar"
            dataType="occupancy"
            height={300}
            showControls={true}
            fullWidth={true}
          />
        </Box>
      </TabPanel>

      <TabPanel value={currentTab} index={1}>
        <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
          <Box sx={{ flex: '1 1 500px', minWidth: 500 }}>
            <AnalyticsChart
              title="Monthly Revenue Trends"
              chartType="line"
              dataType="revenue"
              height={400}
              showControls={true}
            />
          </Box>
          <Box sx={{ flex: '1 1 500px', minWidth: 500 }}>
            <AnalyticsChart
              title="Revenue vs Reservations"
              chartType="bar"
              dataType="revenue"
              height={400}
              showControls={true}
            />
          </Box>
        </Box>
        
        <Box sx={{ mt: 3 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Revenue Insights
              </Typography>
              <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
                <Chip label="Peak Revenue: June" color="success" />
                <Chip label="Growth Rate: +15.3%" color="info" />
                <Chip label="Avg/Month: $18.7K" color="primary" />
              </Stack>
              <Typography variant="body2" color="text.secondary">
                Revenue has shown consistent growth over the past 6 months, with June being the highest performing month. 
                The correlation between reservations and revenue indicates efficient utilization of parking resources.
              </Typography>
            </CardContent>
          </Card>
        </Box>
      </TabPanel>

      <TabPanel value={currentTab} index={2}>
        <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
          <Box sx={{ flex: '1 1 500px', minWidth: 500 }}>
            <AnalyticsChart
              title="Parking Lot Distribution"
              chartType="pie"
              dataType="distribution"
              height={400}
              showControls={true}
            />
          </Box>
          <Box sx={{ flex: '1 1 500px', minWidth: 500 }}>
            <Card sx={{ height: 400 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Lot Performance Summary
                </Typography>
                
                <Box sx={{ mt: 2 }}>
                  {[
                    { name: 'Lot A - Downtown', occupancy: 80, spots: 35, color: '#8884d8' },
                    { name: 'Lot B - Mall', occupancy: 84, spots: 45, color: '#82ca9d' },
                    { name: 'Lot C - Airport', occupancy: 87, spots: 60, color: '#ffc658' },
                    { name: 'Lot D - Hospital', occupancy: 80, spots: 25, color: '#ff7300' },
                    { name: 'Lot E - University', occupancy: 43, spots: 35, color: '#0088fe' },
                  ].map((lot, index) => (
                    <Box key={index} sx={{ mb: 2, p: 2, border: 1, borderColor: 'divider', borderRadius: 1 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                        <Typography variant="subtitle1">{lot.name}</Typography>
                        <Chip 
                          label={`${lot.occupancy}%`} 
                          color={lot.occupancy > 85 ? 'error' : lot.occupancy > 70 ? 'warning' : 'success'}
                          size="small"
                        />
                      </Box>
                      <Typography variant="body2" color="text.secondary">
                        {Math.round((lot.occupancy / 100) * lot.spots)} / {lot.spots} spots occupied
                      </Typography>
                      <Box 
                        sx={{ 
                          height: 8, 
                          backgroundColor: 'grey.200', 
                          borderRadius: 4, 
                          mt: 1,
                          position: 'relative',
                          overflow: 'hidden'
                        }}
                      >
                        <Box 
                          sx={{ 
                            height: '100%', 
                            backgroundColor: lot.color,
                            width: `${lot.occupancy}%`,
                            borderRadius: 4,
                          }}
                        />
                      </Box>
                    </Box>
                  ))}
                </Box>
              </CardContent>
            </Card>
          </Box>
        </Box>
      </TabPanel>

      <TabPanel value={currentTab} index={3}>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Insights />
                AI-Powered Insights
              </Typography>
              
              <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', mb: 2 }}>
                <Chip label="High Demand Alert" color="warning" />
                <Chip label="Revenue Optimization" color="info" />
                <Chip label="Capacity Planning" color="primary" />
              </Box>
              
              <Typography variant="body1" paragraph>
                <strong>Peak Hour Analysis:</strong> Parking demand reaches its highest at 6 PM, with 95% occupancy. 
                Consider implementing dynamic pricing during peak hours to optimize revenue.
              </Typography>
              
              <Typography variant="body1" paragraph>
                <strong>Underutilized Resources:</strong> Lot E (University) shows only 43% average occupancy. 
                Explore partnerships with nearby businesses or events to increase utilization.
              </Typography>
              
              <Typography variant="body1" paragraph>
                <strong>Revenue Growth Opportunity:</strong> Airport lot (Lot C) has the highest occupancy but 
                lower-than-optimal pricing. Consider gradual price adjustments to maximize revenue without 
                significantly impacting demand.
              </Typography>
            </CardContent>
          </Card>
          
          <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
            <Card sx={{ flex: '1 1 300px', minWidth: 300 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>Recommendations</Typography>
                <Box component="ul" sx={{ pl: 2 }}>
                  <Typography component="li" variant="body2" paragraph>
                    Implement dynamic pricing for peak hours (5-7 PM)
                  </Typography>
                  <Typography component="li" variant="body2" paragraph>
                    Add 15 more spots to Airport lot to meet demand
                  </Typography>
                  <Typography component="li" variant="body2" paragraph>
                    Promote University lot for nearby events
                  </Typography>
                  <Typography component="li" variant="body2" paragraph>
                    Consider adding EV charging stations in high-demand lots
                  </Typography>
                </Box>
              </CardContent>
            </Card>
            
            <Card sx={{ flex: '1 1 300px', minWidth: 300 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>Forecasting</Typography>
                <Typography variant="body2" paragraph>
                  <strong>Next Week:</strong> Expected 12% increase in demand due to local events
                </Typography>
                <Typography variant="body2" paragraph>
                  <strong>Next Month:</strong> University lot utilization expected to increase by 25% 
                  when semester starts
                </Typography>
                <Typography variant="body2" paragraph>
                  <strong>Holiday Season:</strong> Mall lot demand projected to increase by 40% 
                  during shopping season
                </Typography>
              </CardContent>
            </Card>
          </Box>
        </Box>
      </TabPanel>
    </Box>
  );
};

export default AnalyticsDashboard;
