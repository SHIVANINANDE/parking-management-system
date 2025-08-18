import React, { useState } from 'react';
import {
  Elements,
  CardElement,
  useStripe,
  useElements,
} from '@stripe/react-stripe-js';
import { loadStripe } from '@stripe/stripe-js';
import {
  Box,
  Paper,
  Typography,
  Button,
  Alert,
  CircularProgress,
  Stack,
  Divider,
} from '@mui/material';
import {
  CreditCard as CreditCardIcon,
  Security as SecurityIcon,
} from '@mui/icons-material';

// Initialize Stripe (replace with your publishable key)
const stripePromise = loadStripe('pk_test_51234567890abcdef'); // Replace with actual key

interface PaymentFormProps {
  amount: number;
  onPaymentSuccess: (paymentIntent: any) => void;
  onPaymentError: (error: string) => void;
  bookingDetails: {
    spotName: string;
    duration: number;
    startTime: Date;
    endTime: Date;
  };
}

const PaymentForm: React.FC<PaymentFormProps> = ({
  amount,
  onPaymentSuccess,
  onPaymentError,
  bookingDetails,
}) => {
  const stripe = useStripe();
  const elements = useElements();
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();

    if (!stripe || !elements) {
      return;
    }

    setProcessing(true);
    setError(null);

    const cardElement = elements.getElement(CardElement);

    if (!cardElement) {
      setError('Card element not found');
      setProcessing(false);
      return;
    }

    try {
      // Create payment method
      const { error: createError, paymentMethod } = await stripe.createPaymentMethod({
        type: 'card',
        card: cardElement,
        billing_details: {
          name: 'Customer Name', // Replace with actual customer name
        },
      });

      if (createError) {
        setError(createError.message || 'Payment failed');
        setProcessing(false);
        return;
      }

      // Simulate payment intent creation (replace with actual backend call)
      const paymentIntent = {
        id: `pi_${Date.now()}`,
        amount: amount * 100, // Stripe uses cents
        currency: 'usd',
        status: 'succeeded',
        payment_method: paymentMethod?.id,
      };

      // Simulate processing delay
      await new Promise(resolve => setTimeout(resolve, 2000));

      onPaymentSuccess(paymentIntent);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Payment processing failed';
      setError(errorMessage);
      onPaymentError(errorMessage);
    } finally {
      setProcessing(false);
    }
  };

  const cardElementOptions = {
    style: {
      base: {
        fontSize: '16px',
        color: '#424770',
        '::placeholder': {
          color: '#aab7c4',
        },
      },
      invalid: {
        color: '#9e2146',
      },
    },
  };

  return (
    <Box component="form" onSubmit={handleSubmit}>
      <Stack spacing={3}>
        {/* Booking Summary */}
        <Paper sx={{ p: 2, bgcolor: 'grey.50' }}>
          <Typography variant="h6" gutterBottom>
            Payment Summary
          </Typography>
          <Stack spacing={1}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
              <Typography>Parking Spot:</Typography>
              <Typography>{bookingDetails.spotName}</Typography>
            </Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
              <Typography>Duration:</Typography>
              <Typography>{bookingDetails.duration.toFixed(1)} hours</Typography>
            </Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
              <Typography>Start Time:</Typography>
              <Typography>{bookingDetails.startTime.toLocaleString()}</Typography>
            </Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
              <Typography>End Time:</Typography>
              <Typography>{bookingDetails.endTime.toLocaleString()}</Typography>
            </Box>
            <Divider />
            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
              <Typography variant="h6">Total Amount:</Typography>
              <Typography variant="h6" color="primary">
                ${amount.toFixed(2)}
              </Typography>
            </Box>
          </Stack>
        </Paper>

        {/* Payment Method */}
        <Paper sx={{ p: 3 }}>
          <Stack spacing={2}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <CreditCardIcon />
              <Typography variant="h6">Payment Information</Typography>
            </Box>
            
            <Box sx={{ p: 2, border: 1, borderColor: 'grey.300', borderRadius: 1 }}>
              <CardElement options={cardElementOptions} />
            </Box>

            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, color: 'text.secondary' }}>
              <SecurityIcon fontSize="small" />
              <Typography variant="caption">
                Your payment information is secure and encrypted
              </Typography>
            </Box>
          </Stack>
        </Paper>

        {/* Error Display */}
        {error && (
          <Alert severity="error" onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* Payment Button */}
        <Button
          type="submit"
          variant="contained"
          size="large"
          fullWidth
          disabled={!stripe || processing}
          startIcon={processing ? <CircularProgress size={20} /> : <CreditCardIcon />}
        >
          {processing ? 'Processing Payment...' : `Pay $${amount.toFixed(2)}`}
        </Button>

        {/* Test Card Info */}
        <Alert severity="info">
          <Typography variant="body2" fontWeight="bold">
            Test Mode
          </Typography>
          <Typography variant="caption">
            Use test card: 4242 4242 4242 4242, any future expiry date, any CVC
          </Typography>
        </Alert>
      </Stack>
    </Box>
  );
};

interface StripePaymentProps {
  amount: number;
  onPaymentSuccess: (paymentIntent: any) => void;
  onPaymentError: (error: string) => void;
  bookingDetails: {
    spotName: string;
    duration: number;
    startTime: Date;
    endTime: Date;
  };
}

const StripePayment: React.FC<StripePaymentProps> = (props) => {
  return (
    <Elements stripe={stripePromise}>
      <PaymentForm {...props} />
    </Elements>
  );
};

export default StripePayment;
