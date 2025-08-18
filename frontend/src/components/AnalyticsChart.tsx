import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  IconButton,
  Tooltip,
  CircularProgress,
} from '@mui/material';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import {
  ShowChart,
  BarChart as BarChartIcon,
  PieChart as PieChartIcon,
  TrendingUp,
  Download,
  Refresh,
  Fullscreen,
} from '@mui/icons-material';

// Sample data for demonstration
const mockOccupancyData = [
  { time: '06:00', occupied: 45, available: 155, total: 200 },
  { time: '08:00', occupied: 120, available: 80, total: 200 },
  { time: '10:00', occupied: 95, available: 105, total: 200 },
  { time: '12:00', occupied: 140, available: 60, total: 200 },
  { time: '14:00', occupied: 110, available: 90, total: 200 },
  { time: '16:00', occupied: 165, available: 35, total: 200 },
  { time: '18:00', occupied: 185, available: 15, total: 200 },
  { time: '20:00', occupied: 135, available: 65, total: 200 },
  { time: '22:00', occupied: 75, available: 125, total: 200 },
];

const mockRevenueData = [
  { month: 'Jan', revenue: 12500, reservations: 450 },
  { month: 'Feb', revenue: 15200, reservations: 520 },
  { month: 'Mar', revenue: 18900, reservations: 680 },
  { month: 'Apr', revenue: 22100, reservations: 750 },
  { month: 'May', revenue: 19800, reservations: 690 },
  { month: 'Jun', revenue: 25600, reservations: 890 },
];

const mockLotDistribution = [
  { name: 'Lot A - Downtown', value: 35, occupied: 28, color: '#8884d8' },
  { name: 'Lot B - Mall', value: 45, occupied: 38, color: '#82ca9d' },
  { name: 'Lot C - Airport', value: 60, occupied: 52, color: '#ffc658' },
  { name: 'Lot D - Hospital', value: 25, occupied: 20, color: '#ff7300' },
  { name: 'Lot E - University', value: 35, occupied: 15, color: '#0088fe' },
];

interface AnalyticsChartProps {
  title: string;
  chartType?: 'line' | 'bar' | 'area' | 'pie';
  dataType: 'occupancy' | 'revenue' | 'distribution';
  height?: number;
  showControls?: boolean;
  fullWidth?: boolean;
}

const AnalyticsChart: React.FC<AnalyticsChartProps> = ({
  title,
  chartType = 'line',
  dataType,
  height = 400,
  showControls = true,
  fullWidth = false,
}) => {
  const [currentChartType, setCurrentChartType] = useState(chartType);
  const [aggregation, setAggregation] = useState<'hourly' | 'daily' | 'weekly' | 'monthly'>('hourly');
  const [loading, setLoading] = useState(false);

  // Get data based on type
  const getData = () => {
    switch (dataType) {
      case 'occupancy':
        return mockOccupancyData;
      case 'revenue':
        return mockRevenueData;
      case 'distribution':
        return mockLotDistribution;
      default:
        return [];
    }
  };

  const data = getData();

  const handleChartTypeChange = (newType: typeof currentChartType) => {
    setCurrentChartType(newType);
  };

  const handleAggregationChange = (newAggregation: typeof aggregation) => {
    setAggregation(newAggregation);
  };

  const handleRefresh = () => {
    setLoading(true);
    // Simulate data refresh
    setTimeout(() => setLoading(false), 1000);
  };

  const handleExport = () => {
    // Implement export functionality
    console.log(`Exporting ${title} chart data...`);
  };

  const renderChart = () => {
    if (loading) {
      return (
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: height - 100 }}>
          <CircularProgress />
        </Box>
      );
    }

    const chartProps = {
      width: '100%',
      height: height - 100,
      data,
      margin: { top: 20, right: 30, left: 20, bottom: 5 },
    };

    switch (currentChartType) {
      case 'bar':
        return (
          <ResponsiveContainer {...chartProps}>
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey={dataType === 'occupancy' ? 'time' : dataType === 'revenue' ? 'month' : 'name'} 
              />
              <YAxis />
              <RechartsTooltip />
              <Legend />
              {dataType === 'occupancy' && (
                <>
                  <Bar dataKey="occupied" stackId="a" fill="#f44336" name="Occupied" />
                  <Bar dataKey="available" stackId="a" fill="#4caf50" name="Available" />
                </>
              )}
              {dataType === 'revenue' && (
                <>
                  <Bar dataKey="revenue" fill="#2196f3" name="Revenue ($)" />
                  <Bar dataKey="reservations" fill="#ff9800" name="Reservations" />
                </>
              )}
            </BarChart>
          </ResponsiveContainer>
        );

      case 'area':
        return (
          <ResponsiveContainer {...chartProps}>
            <AreaChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey={dataType === 'occupancy' ? 'time' : dataType === 'revenue' ? 'month' : 'name'} 
              />
              <YAxis />
              <RechartsTooltip />
              <Legend />
              {dataType === 'occupancy' && (
                <>
                  <Area 
                    type="monotone" 
                    dataKey="occupied" 
                    stackId="1" 
                    stroke="#f44336" 
                    fill="#f44336" 
                    name="Occupied"
                  />
                  <Area 
                    type="monotone" 
                    dataKey="available" 
                    stackId="1" 
                    stroke="#4caf50" 
                    fill="#4caf50" 
                    name="Available"
                  />
                </>
              )}
              {dataType === 'revenue' && (
                <Area 
                  type="monotone" 
                  dataKey="revenue" 
                  stroke="#2196f3" 
                  fill="#2196f3" 
                  name="Revenue ($)"
                />
              )}
            </AreaChart>
          </ResponsiveContainer>
        );

      case 'pie':
        if (dataType === 'distribution') {
          return (
            <ResponsiveContainer {...chartProps}>
              <PieChart>
                <Pie
                  data={mockLotDistribution}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }: any) => `${name} ${((percent || 0) * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="occupied"
                >
                  {mockLotDistribution.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <RechartsTooltip />
              </PieChart>
            </ResponsiveContainer>
          );
        }
        return null;

      case 'line':
      default:
        return (
          <ResponsiveContainer {...chartProps}>
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey={dataType === 'occupancy' ? 'time' : dataType === 'revenue' ? 'month' : 'name'} 
              />
              <YAxis />
              <RechartsTooltip />
              <Legend />
              {dataType === 'occupancy' && (
                <>
                  <Line 
                    type="monotone" 
                    dataKey="occupied" 
                    stroke="#f44336" 
                    strokeWidth={2}
                    name="Occupied"
                  />
                  <Line 
                    type="monotone" 
                    dataKey="available" 
                    stroke="#4caf50" 
                    strokeWidth={2}
                    name="Available"
                  />
                </>
              )}
              {dataType === 'revenue' && (
                <>
                  <Line 
                    type="monotone" 
                    dataKey="revenue" 
                    stroke="#2196f3" 
                    strokeWidth={2}
                    name="Revenue ($)"
                  />
                  <Line 
                    type="monotone" 
                    dataKey="reservations" 
                    stroke="#ff9800" 
                    strokeWidth={2}
                    name="Reservations"
                  />
                </>
              )}
            </LineChart>
          </ResponsiveContainer>
        );
    }
  };

  return (
    <Card sx={{ height: fullWidth ? '100%' : height, width: '100%' }}>
      <CardContent sx={{ p: 2, height: '100%' }}>
        {/* Header */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6" component="h2">
            {title}
          </Typography>
          
          {showControls && (
            <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
              {/* Chart Type Controls */}
              <Box sx={{ display: 'flex', gap: 0.5 }}>
                <Tooltip title="Line Chart">
                  <IconButton
                    size="small"
                    onClick={() => handleChartTypeChange('line')}
                    color={currentChartType === 'line' ? 'primary' : 'default'}
                  >
                    <ShowChart />
                  </IconButton>
                </Tooltip>
                
                <Tooltip title="Bar Chart">
                  <IconButton
                    size="small"
                    onClick={() => handleChartTypeChange('bar')}
                    color={currentChartType === 'bar' ? 'primary' : 'default'}
                  >
                    <BarChartIcon />
                  </IconButton>
                </Tooltip>
                
                <Tooltip title="Area Chart">
                  <IconButton
                    size="small"
                    onClick={() => handleChartTypeChange('area')}
                    color={currentChartType === 'area' ? 'primary' : 'default'}
                  >
                    <TrendingUp />
                  </IconButton>
                </Tooltip>
                
                {dataType === 'distribution' && (
                  <Tooltip title="Pie Chart">
                    <IconButton
                      size="small"
                      onClick={() => handleChartTypeChange('pie')}
                      color={currentChartType === 'pie' ? 'primary' : 'default'}
                    >
                      <PieChartIcon />
                    </IconButton>
                  </Tooltip>
                )}
              </Box>

              {/* Time Aggregation */}
              {dataType !== 'distribution' && (
                <FormControl size="small" sx={{ minWidth: 80 }}>
                  <InputLabel>Period</InputLabel>
                  <Select
                    value={aggregation}
                    label="Period"
                    onChange={(e) => handleAggregationChange(e.target.value as typeof aggregation)}
                  >
                    <MenuItem value="hourly">Hourly</MenuItem>
                    <MenuItem value="daily">Daily</MenuItem>
                    <MenuItem value="weekly">Weekly</MenuItem>
                    <MenuItem value="monthly">Monthly</MenuItem>
                  </Select>
                </FormControl>
              )}

              {/* Action Buttons */}
              <Tooltip title="Refresh">
                <IconButton size="small" onClick={handleRefresh} disabled={loading}>
                  <Refresh />
                </IconButton>
              </Tooltip>
              
              <Tooltip title="Export">
                <IconButton size="small" onClick={handleExport}>
                  <Download />
                </IconButton>
              </Tooltip>
              
              <Tooltip title="Fullscreen">
                <IconButton size="small">
                  <Fullscreen />
                </IconButton>
              </Tooltip>
            </Box>
          )}
        </Box>

        {/* Data Info */}
        <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
          <Chip label={`${data.length} data points`} size="small" variant="outlined" />
          <Chip label={aggregation} size="small" color="primary" />
          <Chip label={currentChartType} size="small" color="secondary" />
        </Box>

        {/* Chart */}
        <Box sx={{ height: height - 120 }}>
          {renderChart()}
        </Box>
      </CardContent>
    </Card>
  );
};

export default AnalyticsChart;
