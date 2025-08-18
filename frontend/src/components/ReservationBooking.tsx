import React, { useState } from 'react';
import {
  Box,
  Paper,
  Stepper,
  Step,
  StepLabel,
  Typography,
  Button,
  Card,
  CardContent,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Stack,
  Divider,
  Alert,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import {
  CheckCircle as CheckIcon,
  LocationOn as LocationIcon,
} from '@mui/icons-material';
import { DateTimePicker } from '@mui/x-date-pickers/DateTimePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { useForm, Controller } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';

interface BookingFormData {
  vehicleType: string;
  licensePlate: string;
  startTime: Date;
  endTime: Date;
  specialRequests?: string;
}

interface ParkingSpot {
  id: string;
  name: string;
  address: string;
  hourlyRate: number;
  amenities: string[];
}

interface ReservationBookingProps {
  spot: ParkingSpot;
  onClose: () => void;
  onBookingComplete: (booking: any) => void;
}

const steps = ['Vehicle Details', 'Date & Time', 'Payment', 'Confirmation'];

const bookingSchema = yup.object({
  vehicleType: yup.string().required('Vehicle type is required'),
  licensePlate: yup.string().required('License plate is required'),
  startTime: yup.date().required('Start time is required'),
  endTime: yup.date().required('End time is required'),
  specialRequests: yup.string().optional(),
});

const ReservationBooking: React.FC<ReservationBookingProps> = ({
  spot,
  onClose,
  onBookingComplete,
}) => {
  const [activeStep, setActiveStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [paymentMethod, setPaymentMethod] = useState('');
  const [bookingConfirmed, setBookingConfirmed] = useState(false);

  const {
    control,
    watch,
    formState: { errors },
  } = useForm<BookingFormData>({
    defaultValues: {
      vehicleType: '',
      licensePlate: '',
      startTime: new Date(),
      endTime: new Date(Date.now() + 3600000), // +1 hour
      specialRequests: '',
    },
    mode: 'onChange',
  });

  const formData = watch();

  const vehicleTypes = [
    { value: 'sedan', label: 'Sedan' },
    { value: 'suv', label: 'SUV' },
    { value: 'truck', label: 'Truck' },
    { value: 'motorcycle', label: 'Motorcycle' },
    { value: 'electric', label: 'Electric Vehicle' },
  ];

  const paymentMethods = [
    { value: 'credit_card', label: 'Credit Card' },
    { value: 'debit_card', label: 'Debit Card' },
    { value: 'paypal', label: 'PayPal' },
    { value: 'apple_pay', label: 'Apple Pay' },
  ];

  const calculateDuration = () => {
    if (formData.startTime && formData.endTime) {
      const diff = formData.endTime.getTime() - formData.startTime.getTime();
      return Math.max(0, diff / (1000 * 60 * 60)); // hours
    }
    return 0;
  };

  const calculateTotal = () => {
    const duration = calculateDuration();
    return duration * spot.hourlyRate;
  };

  const handleNext = () => {
    if (activeStep === steps.length - 1) {
      handleBookingSubmit();
    } else {
      setActiveStep((prevActiveStep) => prevActiveStep + 1);
    }
  };

  const handleBack = () => {
    setActiveStep((prevActiveStep) => prevActiveStep - 1);
  };

  const handleBookingSubmit = async () => {
    setLoading(true);
    try {
      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 2000));
      
      const booking = {
        id: Date.now().toString(),
        spotId: spot.id,
        spotName: spot.name,
        ...formData,
        paymentMethod,
        duration: calculateDuration(),
        totalCost: calculateTotal(),
        status: 'confirmed',
        bookingDate: new Date(),
      };

      setBookingConfirmed(true);
      onBookingComplete(booking);
    } catch (error) {
      console.error('Booking failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const renderStepContent = (step: number) => {
    switch (step) {
      case 0:
        return (
          <Stack spacing={3}>
            <Typography variant="h6">Vehicle Information</Typography>
            
            <Controller
              name="vehicleType"
              control={control}
              render={({ field }) => (
                <FormControl fullWidth error={!!errors.vehicleType}>
                  <InputLabel>Vehicle Type</InputLabel>
                  <Select {...field} label="Vehicle Type">
                    {vehicleTypes.map((type) => (
                      <MenuItem key={type.value} value={type.value}>
                        {type.label}
                      </MenuItem>
                    ))}
                  </Select>
                  {errors.vehicleType && (
                    <Typography variant="caption" color="error">
                      {errors.vehicleType.message}
                    </Typography>
                  )}
                </FormControl>
              )}
            />

            <Controller
              name="licensePlate"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  fullWidth
                  label="License Plate"
                  placeholder="ABC-123"
                  error={!!errors.licensePlate}
                  helperText={errors.licensePlate?.message}
                />
              )}
            />

            <Controller
              name="specialRequests"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  fullWidth
                  label="Special Requests (Optional)"
                  multiline
                  rows={3}
                  placeholder="Any special requirements or requests..."
                />
              )}
            />
          </Stack>
        );

      case 1:
        return (
          <Stack spacing={3}>
            <Typography variant="h6">Select Date & Time</Typography>
            
            <LocalizationProvider dateAdapter={AdapterDateFns}>
              <Stack spacing={2}>
                <Controller
                  name="startTime"
                  control={control}
                  render={({ field }) => (
                    <DateTimePicker
                      label="Start Date & Time"
                      value={field.value}
                      onChange={field.onChange}
                      slotProps={{
                        textField: {
                          fullWidth: true,
                          error: !!errors.startTime,
                          helperText: errors.startTime?.message,
                        },
                      }}
                    />
                  )}
                />

                <Controller
                  name="endTime"
                  control={control}
                  render={({ field }) => (
                    <DateTimePicker
                      label="End Date & Time"
                      value={field.value}
                      onChange={field.onChange}
                      slotProps={{
                        textField: {
                          fullWidth: true,
                          error: !!errors.endTime,
                          helperText: errors.endTime?.message,
                        },
                      }}
                    />
                  )}
                />
              </Stack>
            </LocalizationProvider>

            {formData.startTime && formData.endTime && (
              <Alert severity="info">
                Duration: {calculateDuration().toFixed(1)} hours
                <br />
                Estimated Cost: ${calculateTotal().toFixed(2)}
              </Alert>
            )}
          </Stack>
        );

      case 2:
        return (
          <Stack spacing={3}>
            <Typography variant="h6">Payment Information</Typography>
            
            <FormControl fullWidth>
              <InputLabel>Payment Method</InputLabel>
              <Select
                value={paymentMethod}
                label="Payment Method"
                onChange={(e) => setPaymentMethod(e.target.value)}
              >
                {paymentMethods.map((method) => (
                  <MenuItem key={method.value} value={method.value}>
                    {method.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <Paper sx={{ p: 2, bgcolor: 'grey.50' }}>
              <Typography variant="h6" gutterBottom>
                Booking Summary
              </Typography>
              <Stack spacing={1}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography>Parking Spot:</Typography>
                  <Typography>{spot.name}</Typography>
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography>Duration:</Typography>
                  <Typography>{calculateDuration().toFixed(1)} hours</Typography>
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography>Rate:</Typography>
                  <Typography>${spot.hourlyRate}/hour</Typography>
                </Box>
                <Divider />
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="h6">Total:</Typography>
                  <Typography variant="h6">${calculateTotal().toFixed(2)}</Typography>
                </Box>
              </Stack>
            </Paper>
          </Stack>
        );

      case 3:
        return (
          <Stack spacing={3} alignItems="center">
            {loading ? (
              <>
                <CircularProgress size={60} />
                <Typography>Processing your booking...</Typography>
              </>
            ) : bookingConfirmed ? (
              <>
                <CheckIcon color="success" sx={{ fontSize: 60 }} />
                <Typography variant="h6" color="success.main">
                  Booking Confirmed!
                </Typography>
                <Paper sx={{ p: 2, width: '100%' }}>
                  <Typography variant="h6" gutterBottom>
                    Booking Details
                  </Typography>
                  <Stack spacing={1}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography>Booking ID:</Typography>
                      <Typography>{Date.now()}</Typography>
                    </Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography>Parking Spot:</Typography>
                      <Typography>{spot.name}</Typography>
                    </Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography>Vehicle:</Typography>
                      <Typography>{formData.vehicleType} - {formData.licensePlate}</Typography>
                    </Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography>Duration:</Typography>
                      <Typography>{calculateDuration().toFixed(1)} hours</Typography>
                    </Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography>Total Paid:</Typography>
                      <Typography>${calculateTotal().toFixed(2)}</Typography>
                    </Box>
                  </Stack>
                </Paper>
              </>
            ) : null}
          </Stack>
        );

      default:
        return null;
    }
  };

  const isStepValid = (step: number) => {
    switch (step) {
      case 0:
        return formData.vehicleType && formData.licensePlate;
      case 1:
        return formData.startTime && formData.endTime && formData.endTime > formData.startTime;
      case 2:
        return paymentMethod;
      default:
        return true;
    }
  };

  return (
    <Dialog open onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Stack direction="row" alignItems="center" spacing={1}>
          <LocationIcon />
          <Typography variant="h6">Book Parking Spot</Typography>
        </Stack>
      </DialogTitle>
      
      <DialogContent>
        <Box sx={{ mt: 2 }}>
          {/* Parking Spot Info */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6">{spot.name}</Typography>
              <Typography color="text.secondary">{spot.address}</Typography>
              <Typography variant="h6" color="primary" sx={{ mt: 1 }}>
                ${spot.hourlyRate}/hour
              </Typography>
            </CardContent>
          </Card>

          {/* Stepper */}
          <Stepper activeStep={activeStep} sx={{ mb: 4 }}>
            {steps.map((label) => (
              <Step key={label}>
                <StepLabel>{label}</StepLabel>
              </Step>
            ))}
          </Stepper>

          {/* Step Content */}
          <Box sx={{ minHeight: 300 }}>
            {renderStepContent(activeStep)}
          </Box>
        </Box>
      </DialogContent>

      <DialogActions sx={{ p: 3 }}>
        <Button onClick={onClose} disabled={loading}>
          Cancel
        </Button>
        <Box sx={{ flex: 1 }} />
        <Button
          disabled={activeStep === 0 || loading}
          onClick={handleBack}
          sx={{ mr: 1 }}
        >
          Back
        </Button>
        <Button
          variant="contained"
          onClick={handleNext}
          disabled={!isStepValid(activeStep) || loading || bookingConfirmed}
        >
          {activeStep === steps.length - 1 ? 'Confirm Booking' : 'Next'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ReservationBooking;
