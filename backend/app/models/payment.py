from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, Numeric, ForeignKey, Text, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base
import enum
from datetime import datetime

class PaymentStatus(enum.Enum):
    PENDING = "pending"           # Payment initiated but not processed
    PROCESSING = "processing"     # Payment being processed
    COMPLETED = "completed"       # Payment successful
    FAILED = "failed"            # Payment failed
    CANCELLED = "cancelled"       # Payment cancelled
    REFUNDED = "refunded"        # Payment refunded
    PARTIALLY_REFUNDED = "partially_refunded"  # Partial refund issued
    DISPUTED = "disputed"        # Payment disputed by customer
    CHARGEBACK = "chargeback"    # Chargeback initiated

class PaymentMethod(enum.Enum):
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    DIGITAL_WALLET = "digital_wallet"  # Apple Pay, Google Pay, etc.
    BANK_TRANSFER = "bank_transfer"
    CASH = "cash"
    MOBILE_PAYMENT = "mobile_payment"  # Venmo, PayPal, etc.
    CRYPTOCURRENCY = "cryptocurrency"
    ACCOUNT_CREDIT = "account_credit"  # Prepaid account balance
    GIFT_CARD = "gift_card"
    SUBSCRIPTION = "subscription"      # Monthly/yearly subscription

class PaymentType(enum.Enum):
    RESERVATION = "reservation"       # Payment for reservation
    EXTENSION = "extension"          # Payment for extending stay
    PENALTY = "penalty"             # Penalty fees
    CANCELLATION = "cancellation"   # Cancellation fees
    SUBSCRIPTION = "subscription"   # Subscription payments
    REFUND = "refund"              # Refund transaction
    DEPOSIT = "deposit"            # Security deposit
    TOP_UP = "top_up"             # Account balance top-up

class Currency(enum.Enum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    CAD = "CAD"
    AUD = "AUD"
    JPY = "JPY"
    CNY = "CNY"
    INR = "INR"

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    reservation_id = Column(Integer, ForeignKey("reservations.id"), nullable=True, index=True)
    
    # Payment Identification
    payment_number = Column(String(50), unique=True, index=True, nullable=False)
    external_transaction_id = Column(String(100), nullable=True, index=True)  # From payment processor
    receipt_number = Column(String(50), unique=True, nullable=True)
    
    # Payment Details
    payment_type = Column(Enum(PaymentType), nullable=False, index=True)
    payment_method = Column(Enum(PaymentMethod), nullable=False)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False, index=True)
    
    # Amount Information
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(Enum(Currency), default=Currency.USD, nullable=False)
    tax_amount = Column(Numeric(10, 2), nullable=False, default=0.00)
    fee_amount = Column(Numeric(10, 2), nullable=False, default=0.00)  # Processing fees
    net_amount = Column(Numeric(10, 2), nullable=False)  # Amount after fees
    
    # Discounts and Promotions
    discount_amount = Column(Numeric(10, 2), nullable=False, default=0.00)
    promotion_code = Column(String(50), nullable=True, index=True)
    promotion_discount = Column(Numeric(10, 2), nullable=False, default=0.00)
    
    # Payment Processor Information
    payment_processor = Column(String(50), nullable=True)  # Stripe, PayPal, Square, etc.
    processor_fee = Column(Numeric(10, 2), nullable=False, default=0.00)
    processor_transaction_id = Column(String(100), nullable=True)
    processor_response = Column(JSON, nullable=True)  # Full response from processor
    
    # Card/Account Information (tokenized/masked)
    masked_card_number = Column(String(20), nullable=True)  # Last 4 digits only
    card_brand = Column(String(20), nullable=True)  # Visa, Mastercard, etc.
    card_expiry_month = Column(Integer, nullable=True)
    card_expiry_year = Column(Integer, nullable=True)
    billing_address = Column(JSON, nullable=True)
    
    # Digital Wallet Information
    wallet_type = Column(String(50), nullable=True)  # Apple Pay, Google Pay, etc.
    wallet_transaction_id = Column(String(100), nullable=True)
    
    # Bank Transfer Information
    bank_account_last4 = Column(String(4), nullable=True)
    bank_routing_number = Column(String(20), nullable=True)
    bank_name = Column(String(100), nullable=True)
    
    # Security and Fraud Prevention
    risk_score = Column(Numeric(5, 2), nullable=True)  # Fraud risk score 0-100
    is_flagged = Column(Boolean, default=False, nullable=False)
    fraud_check_result = Column(String(50), nullable=True)  # approved, declined, review
    avs_result = Column(String(10), nullable=True)  # Address Verification System
    cvv_result = Column(String(10), nullable=True)  # CVV verification result
    
    # IP and Device Information
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(Text, nullable=True)
    device_fingerprint = Column(String(100), nullable=True)
    
    # Refund Information
    refund_amount = Column(Numeric(10, 2), nullable=False, default=0.00)
    refund_reason = Column(String(200), nullable=True)
    refunded_at = Column(DateTime(timezone=True), nullable=True)
    refund_transaction_id = Column(String(100), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Retry and Failure Handling
    retry_count = Column(Integer, default=0, nullable=False)
    last_retry_at = Column(DateTime(timezone=True), nullable=True)
    failure_reason = Column(Text, nullable=True)
    failure_code = Column(String(50), nullable=True)
    
    # Dispute and Chargeback
    dispute_initiated_at = Column(DateTime(timezone=True), nullable=True)
    dispute_amount = Column(Numeric(10, 2), nullable=True)
    dispute_reason = Column(String(200), nullable=True)
    dispute_evidence_due_date = Column(DateTime(timezone=True), nullable=True)
    chargeback_id = Column(String(100), nullable=True)
    
    # Subscription Information (if applicable)
    subscription_id = Column(String(100), nullable=True)
    billing_period_start = Column(DateTime(timezone=True), nullable=True)
    billing_period_end = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata and Additional Information
    description = Column(Text, nullable=True)
    internal_notes = Column(Text, nullable=True)
    metadata = Column(JSON, nullable=True)  # Additional custom data
    
    # Relationships
    user = relationship("User", back_populates="payments")
    reservation = relationship("Reservation", back_populates="payments")
    
    def __repr__(self):
        return f"<Payment(id={self.id}, number='{self.payment_number}', amount={self.amount}, status='{self.status.value}')>"
    
    @property
    def is_successful(self):
        """Check if payment was successful"""
        return self.status == PaymentStatus.COMPLETED
    
    @property
    def is_refundable(self):
        """Check if payment can be refunded"""
        if self.status != PaymentStatus.COMPLETED:
            return False
        
        if self.refund_amount >= self.amount:
            return False  # Already fully refunded
        
        return True
    
    @property
    def remaining_refundable_amount(self):
        """Calculate remaining amount that can be refunded"""
        if not self.is_refundable:
            return 0.00
        
        return self.amount - self.refund_amount
    
    @property
    def total_amount(self):
        """Total amount including tax and fees"""
        return self.amount + self.tax_amount + self.fee_amount
    
    @property
    def is_disputed(self):
        """Check if payment is under dispute"""
        return self.status in [PaymentStatus.DISPUTED, PaymentStatus.CHARGEBACK]
    
    @property
    def payment_method_display(self):
        """Human-readable payment method display"""
        if self.payment_method == PaymentMethod.CREDIT_CARD and self.masked_card_number:
            return f"{self.card_brand} ****{self.masked_card_number}"
        elif self.payment_method == PaymentMethod.DIGITAL_WALLET and self.wallet_type:
            return self.wallet_type
        elif self.payment_method == PaymentMethod.BANK_TRANSFER and self.bank_account_last4:
            return f"Bank ****{self.bank_account_last4}"
        else:
            return self.payment_method.value.replace('_', ' ').title()
    
    def calculate_refund_amount(self, requested_amount=None):
        """Calculate actual refund amount considering fees and limits"""
        if not self.is_refundable:
            return 0.00
        
        max_refundable = self.remaining_refundable_amount
        
        if requested_amount is None:
            return max_refundable
        
        return min(requested_amount, max_refundable)
    
    def process_refund(self, amount, reason=None):
        """Process a refund for this payment"""
        refund_amount = self.calculate_refund_amount(amount)
        
        if refund_amount <= 0:
            raise ValueError("No refundable amount available")
        
        self.refund_amount += refund_amount
        self.refund_reason = reason
        self.refunded_at = datetime.utcnow()
        
        # Update status
        if self.refund_amount >= self.amount:
            self.status = PaymentStatus.REFUNDED
        else:
            self.status = PaymentStatus.PARTIALLY_REFUNDED
        
        return refund_amount