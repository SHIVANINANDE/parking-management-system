"""
Unit Tests for Reservation Model and Services
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal

from app.models.reservation import Reservation
from app.models.payment import Payment
from app.services.reservation_service import ReservationService
from app.services.payment_service import PaymentService


@pytest.mark.unit
class TestReservationModel:
    """Test Reservation model functionality."""
    
    def test_reservation_creation(self):
        """Test reservation model creation."""
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(hours=2)
        
        reservation = Reservation(
            user_id="user-123",
            parking_spot_id="spot-456",
            vehicle_id="vehicle-789",
            start_time=start_time,
            end_time=end_time,
            status="confirmed",
            total_amount=10.0
        )
        
        assert reservation.user_id == "user-123"
        assert reservation.parking_spot_id == "spot-456"
        assert reservation.vehicle_id == "vehicle-789"
        assert reservation.start_time == start_time
        assert reservation.end_time == end_time
        assert reservation.status == "confirmed"
        assert reservation.total_amount == 10.0
    
    def test_reservation_duration_calculation(self):
        """Test reservation duration calculation."""
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(hours=3, minutes=30)
        
        reservation = Reservation(
            start_time=start_time,
            end_time=end_time
        )
        
        duration = reservation.duration_hours
        assert duration == 3.5
    
    def test_reservation_status_validation(self):
        """Test reservation status validation."""
        valid_statuses = ["pending", "confirmed", "active", "completed", "cancelled"]
        
        for status in valid_statuses:
            reservation = Reservation(
                user_id="user-123",
                status=status
            )
            assert reservation.status == status
    
    def test_reservation_overlap_detection(self):
        """Test reservation overlap detection."""
        base_start = datetime.utcnow()
        base_end = base_start + timedelta(hours=2)
        
        # Overlapping scenarios
        overlap_scenarios = [
            # Starts before, ends during
            (base_start - timedelta(minutes=30), base_start + timedelta(minutes=30)),
            # Starts during, ends after
            (base_start + timedelta(minutes=30), base_end + timedelta(minutes=30)),
            # Completely contains
            (base_start - timedelta(minutes=30), base_end + timedelta(minutes=30)),
            # Completely contained
            (base_start + timedelta(minutes=15), base_end - timedelta(minutes=15))
        ]
        
        base_reservation = Reservation(
            start_time=base_start,
            end_time=base_end
        )
        
        for start, end in overlap_scenarios:
            test_reservation = Reservation(
                start_time=start,
                end_time=end
            )
            
            assert base_reservation.overlaps_with(test_reservation)
    
    def test_reservation_no_overlap(self):
        """Test no overlap detection."""
        base_start = datetime.utcnow()
        base_end = base_start + timedelta(hours=2)
        
        # Non-overlapping scenarios
        non_overlap_scenarios = [
            # Before
            (base_start - timedelta(hours=3), base_start - timedelta(hours=1)),
            # After
            (base_end + timedelta(hours=1), base_end + timedelta(hours=3)),
            # Adjacent before
            (base_start - timedelta(hours=1), base_start),
            # Adjacent after
            (base_end, base_end + timedelta(hours=1))
        ]
        
        base_reservation = Reservation(
            start_time=base_start,
            end_time=base_end
        )
        
        for start, end in non_overlap_scenarios:
            test_reservation = Reservation(
                start_time=start,
                end_time=end
            )
            
            assert not base_reservation.overlaps_with(test_reservation)


@pytest.mark.unit
class TestReservationService:
    """Test ReservationService functionality."""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return Mock(spec=AsyncSession)
    
    @pytest.fixture
    def reservation_service(self, mock_db):
        """Create ReservationService instance with mock db."""
        return ReservationService(mock_db)
    
    async def test_create_reservation(self, reservation_service, mock_db):
        """Test reservation creation service."""
        reservation_data = {
            "user_id": "user-123",
            "parking_spot_id": "spot-456",
            "vehicle_id": "vehicle-789",
            "start_time": datetime.utcnow(),
            "end_time": datetime.utcnow() + timedelta(hours=2)
        }
        
        mock_reservation = Reservation(**reservation_data)
        mock_reservation.id = "reservation-123"
        
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()
        
        with patch('app.services.reservation_service.Reservation') as MockReservation:
            MockReservation.return_value = mock_reservation
            
            result = await reservation_service.create_reservation(reservation_data)
            
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once()
    
    async def test_check_spot_availability(self, reservation_service, mock_db):
        """Test spot availability checking."""
        spot_id = "spot-456"
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(hours=2)
        
        # No conflicting reservations
        mock_db.execute.return_value.scalars.return_value.all.return_value = []
        
        result = await reservation_service.check_spot_availability(
            spot_id, start_time, end_time
        )
        
        assert result is True
        mock_db.execute.assert_called_once()
    
    async def test_check_spot_unavailable(self, reservation_service, mock_db):
        """Test spot unavailability detection."""
        spot_id = "spot-456"
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(hours=2)
        
        # Conflicting reservation exists
        conflicting_reservation = Reservation(
            parking_spot_id=spot_id,
            start_time=start_time - timedelta(minutes=30),
            end_time=start_time + timedelta(minutes=30),
            status="confirmed"
        )
        
        mock_db.execute.return_value.scalars.return_value.all.return_value = [
            conflicting_reservation
        ]
        
        result = await reservation_service.check_spot_availability(
            spot_id, start_time, end_time
        )
        
        assert result is False
    
    async def test_cancel_reservation(self, reservation_service, mock_db):
        """Test reservation cancellation."""
        reservation_id = "reservation-123"
        
        mock_reservation = Reservation(
            id=reservation_id,
            status="confirmed",
            start_time=datetime.utcnow() + timedelta(hours=1)  # Future reservation
        )
        
        with patch.object(
            reservation_service, 
            'get_reservation_by_id', 
            return_value=mock_reservation
        ):
            mock_db.commit = Mock()
            
            result = await reservation_service.cancel_reservation(reservation_id)
            
            assert result.status == "cancelled"
            mock_db.commit.assert_called_once()
    
    async def test_extend_reservation(self, reservation_service, mock_db):
        """Test reservation extension."""
        reservation_id = "reservation-123"
        extension_hours = 1
        
        original_end = datetime.utcnow() + timedelta(hours=2)
        mock_reservation = Reservation(
            id=reservation_id,
            status="active",
            end_time=original_end
        )
        
        with patch.object(
            reservation_service, 
            'get_reservation_by_id', 
            return_value=mock_reservation
        ):
            with patch.object(
                reservation_service,
                'check_spot_availability',
                return_value=True
            ):
                mock_db.commit = Mock()
                
                result = await reservation_service.extend_reservation(
                    reservation_id, extension_hours
                )
                
                expected_end = original_end + timedelta(hours=extension_hours)
                assert result.end_time == expected_end
                mock_db.commit.assert_called_once()
    
    async def test_get_user_reservations(self, reservation_service, mock_db):
        """Test getting user reservations."""
        user_id = "user-123"
        
        mock_reservations = [
            Reservation(id="res-1", user_id=user_id, status="confirmed"),
            Reservation(id="res-2", user_id=user_id, status="active"),
            Reservation(id="res-3", user_id=user_id, status="completed")
        ]
        
        mock_db.execute.return_value.scalars.return_value.all.return_value = mock_reservations
        
        result = await reservation_service.get_user_reservations(user_id)
        
        assert len(result) == 3
        assert all(res.user_id == user_id for res in result)
        mock_db.execute.assert_called_once()
    
    async def test_reservation_auto_completion(self, reservation_service, mock_db):
        """Test automatic reservation completion."""
        cutoff_time = datetime.utcnow()
        
        mock_active_reservations = [
            Reservation(
                id="res-1", 
                status="active", 
                end_time=cutoff_time - timedelta(minutes=30)
            ),
            Reservation(
                id="res-2", 
                status="active", 
                end_time=cutoff_time - timedelta(hours=1)
            )
        ]
        
        mock_db.execute.return_value.scalars.return_value.all.return_value = mock_active_reservations
        mock_db.commit = Mock()
        
        result = await reservation_service.complete_expired_reservations()
        
        assert result == 2  # Two reservations completed
        for reservation in mock_active_reservations:
            assert reservation.status == "completed"
        mock_db.commit.assert_called_once()


@pytest.mark.unit
class TestPaymentModel:
    """Test Payment model functionality."""
    
    def test_payment_creation(self):
        """Test payment model creation."""
        payment = Payment(
            reservation_id="reservation-123",
            amount=Decimal("25.50"),
            payment_method="credit_card",
            status="completed",
            transaction_id="txn_abc123"
        )
        
        assert payment.reservation_id == "reservation-123"
        assert payment.amount == Decimal("25.50")
        assert payment.payment_method == "credit_card"
        assert payment.status == "completed"
        assert payment.transaction_id == "txn_abc123"
    
    def test_payment_status_validation(self):
        """Test payment status validation."""
        valid_statuses = ["pending", "processing", "completed", "failed", "refunded"]
        
        for status in valid_statuses:
            payment = Payment(
                reservation_id="reservation-123",
                amount=Decimal("10.00"),
                status=status
            )
            assert payment.status == status
    
    def test_payment_method_validation(self):
        """Test payment method validation."""
        valid_methods = ["credit_card", "debit_card", "paypal", "apple_pay", "google_pay"]
        
        for method in valid_methods:
            payment = Payment(
                reservation_id="reservation-123",
                amount=Decimal("10.00"),
                payment_method=method
            )
            assert payment.payment_method == method


@pytest.mark.unit
class TestPaymentService:
    """Test PaymentService functionality."""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return Mock(spec=AsyncSession)
    
    @pytest.fixture
    def payment_service(self, mock_db):
        """Create PaymentService instance with mock db."""
        return PaymentService(mock_db)
    
    async def test_process_payment(self, payment_service, mock_db):
        """Test payment processing."""
        payment_data = {
            "reservation_id": "reservation-123",
            "amount": Decimal("25.50"),
            "payment_method": "credit_card",
            "card_token": "tok_visa_1234"
        }
        
        mock_payment = Payment(**payment_data)
        mock_payment.id = "payment-456"
        
        with patch('app.services.payment_service.stripe.PaymentIntent.create') as mock_stripe:
            mock_stripe.return_value.id = "pi_test_123"
            mock_stripe.return_value.status = "succeeded"
            
            mock_db.add = Mock()
            mock_db.commit = Mock()
            mock_db.refresh = Mock()
            
            result = await payment_service.process_payment(payment_data)
            
            mock_stripe.assert_called_once()
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
    
    async def test_refund_payment(self, payment_service, mock_db):
        """Test payment refund."""
        payment_id = "payment-456"
        refund_amount = Decimal("15.00")
        
        mock_payment = Payment(
            id=payment_id,
            transaction_id="pi_test_123",
            amount=Decimal("25.50"),
            status="completed"
        )
        
        with patch.object(
            payment_service, 
            'get_payment_by_id', 
            return_value=mock_payment
        ):
            with patch('app.services.payment_service.stripe.Refund.create') as mock_refund:
                mock_refund.return_value.id = "re_test_123"
                mock_refund.return_value.status = "succeeded"
                
                mock_db.commit = Mock()
                
                result = await payment_service.refund_payment(payment_id, refund_amount)
                
                mock_refund.assert_called_once_with(
                    payment_intent=mock_payment.transaction_id,
                    amount=int(refund_amount * 100)  # Convert to cents
                )
                mock_db.commit.assert_called_once()
    
    async def test_payment_webhook_processing(self, payment_service, mock_db):
        """Test payment webhook processing."""
        webhook_data = {
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": "pi_test_123",
                    "status": "succeeded",
                    "amount": 2550,  # $25.50 in cents
                    "metadata": {
                        "reservation_id": "reservation-123"
                    }
                }
            }
        }
        
        mock_payment = Payment(
            reservation_id="reservation-123",
            transaction_id="pi_test_123",
            status="processing"
        )
        
        with patch.object(
            payment_service,
            'get_payment_by_transaction_id',
            return_value=mock_payment
        ):
            mock_db.commit = Mock()
            
            result = await payment_service.process_webhook(webhook_data)
            
            assert mock_payment.status == "completed"
            mock_db.commit.assert_called_once()
