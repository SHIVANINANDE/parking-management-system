# Smart Parking Management System - Database Schema

## Overview

The Smart Parking Management System uses PostgreSQL with PostGIS extension for geospatial data handling. The database is designed to handle user management, vehicle registration, parking lot management, spot tracking, reservations, payments, and comprehensive analytics.

## Core Tables

### 1. Users Table
**Purpose**: Manages user authentication, profiles, and roles

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| email | VARCHAR(255) | Unique email address |
| username | VARCHAR(100) | Optional unique username |
| hashed_password | VARCHAR(255) | Bcrypt hashed password |
| salt | VARCHAR(100) | Password salt |
| first_name | VARCHAR(100) | User's first name |
| last_name | VARCHAR(100) | User's last name |
| phone_number | VARCHAR(20) | Contact phone number |
| date_of_birth | DATETIME | Date of birth |
| role | ENUM | user, admin, manager, operator |
| status | ENUM | active, inactive, suspended, pending_verification |
| is_email_verified | BOOLEAN | Email verification status |
| is_phone_verified | BOOLEAN | Phone verification status |
| failed_login_attempts | INTEGER | Failed login counter |
| last_login_at | DATETIME | Last login timestamp |
| password_reset_token | VARCHAR(255) | Password reset token |
| password_reset_expires | DATETIME | Token expiration |
| email_verification_token | VARCHAR(255) | Email verification token |
| profile_picture_url | VARCHAR(500) | Profile picture URL |
| timezone | VARCHAR(50) | User's timezone |
| language | VARCHAR(10) | Preferred language |
| notifications_enabled | BOOLEAN | Notification preferences |
| created_at | DATETIME | Account creation time |
| updated_at | DATETIME | Last update time |
| last_activity_at | DATETIME | Last activity time |

**Indexes**: email (unique), username (unique), id

---

### 2. Vehicles Table
**Purpose**: Stores vehicle information for users

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| owner_id | INTEGER | Foreign key to users.id |
| license_plate | VARCHAR(20) | Unique license plate number |
| vin | VARCHAR(17) | Vehicle Identification Number |
| make | VARCHAR(50) | Vehicle manufacturer |
| model | VARCHAR(100) | Vehicle model |
| year | INTEGER | Manufacturing year |
| color | VARCHAR(30) | Vehicle color |
| vehicle_type | ENUM | car, motorcycle, truck, van, electric_car, electric_motorcycle, bicycle, scooter |
| fuel_type | ENUM | gasoline, diesel, electric, hybrid, plug_in_hybrid, cng, lpg |
| length_cm | INTEGER | Vehicle length in centimeters |
| width_cm | INTEGER | Vehicle width in centimeters |
| height_cm | INTEGER | Vehicle height in centimeters |
| weight_kg | INTEGER | Vehicle weight in kilograms |
| battery_capacity_kwh | INTEGER | Battery capacity for electric vehicles |
| charging_port_type | VARCHAR(50) | Charging port type |
| registration_number | VARCHAR(50) | Registration number |
| registration_expiry | DATETIME | Registration expiry date |
| insurance_number | VARCHAR(100) | Insurance policy number |
| insurance_expiry | DATETIME | Insurance expiry date |
| is_active | BOOLEAN | Vehicle active status |
| is_verified | BOOLEAN | Verification status |
| nickname | VARCHAR(100) | User-defined nickname |
| notes | TEXT | Additional notes |
| created_at | DATETIME | Creation timestamp |
| updated_at | DATETIME | Last update timestamp |

**Indexes**: license_plate (unique), owner_id, id

---

### 3. Parking_Lots Table
**Purpose**: Manages parking lot information and location data

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| name | VARCHAR(200) | Parking lot name |
| code | VARCHAR(20) | Unique short code |
| description | TEXT | Detailed description |
| address | VARCHAR(500) | Street address |
| city | VARCHAR(100) | City name |
| state | VARCHAR(100) | State/province |
| country | VARCHAR(100) | Country |
| postal_code | VARCHAR(20) | Postal/ZIP code |
| location | GEOMETRY(POINT) | PostGIS point geometry (WGS84) |
| boundary | GEOMETRY(POLYGON) | Lot boundary polygon |
| latitude | NUMERIC(10,8) | Latitude coordinate |
| longitude | NUMERIC(11,8) | Longitude coordinate |
| total_spots | INTEGER | Total parking spots |
| available_spots | INTEGER | Currently available spots |
| reserved_spots | INTEGER | Reserved spots |
| disabled_spots | INTEGER | Handicapped accessible spots |
| electric_spots | INTEGER | Electric vehicle spots |
| motorcycle_spots | INTEGER | Motorcycle spots |
| parking_lot_type | ENUM | outdoor, indoor, underground, multi_level, street_parking |
| access_type | ENUM | public, private, restricted, residential, commercial |
| total_floors | INTEGER | Number of floors |
| max_vehicle_height_cm | INTEGER | Height restriction |
| max_vehicle_weight_kg | INTEGER | Weight restriction |
| base_hourly_rate | NUMERIC(10,2) | Base hourly parking rate |
| daily_rate | NUMERIC(10,2) | Daily parking rate |
| monthly_rate | NUMERIC(10,2) | Monthly parking rate |
| pricing_rules | JSON | Complex pricing rules |
| is_24_hours | BOOLEAN | 24/7 operation |
| opening_time | TIME | Opening time |
| closing_time | TIME | Closing time |
| operating_days | JSON | Days of operation |
| has_security | BOOLEAN | Security presence |
| has_covered_parking | BOOLEAN | Covered parking available |
| has_ev_charging | BOOLEAN | EV charging available |
| has_valet_service | BOOLEAN | Valet service available |
| has_car_wash | BOOLEAN | Car wash service |
| has_restrooms | BOOLEAN | Restroom facilities |
| has_elevators | BOOLEAN | Elevator access |
| has_wheelchair_access | BOOLEAN | Wheelchair accessibility |
| accepts_cash | BOOLEAN | Cash payment accepted |
| accepts_card | BOOLEAN | Card payment accepted |
| accepts_mobile_payment | BOOLEAN | Mobile payment accepted |
| requires_permit | BOOLEAN | Permit required |
| contact_phone | VARCHAR(20) | Contact phone |
| contact_email | VARCHAR(255) | Contact email |
| manager_name | VARCHAR(200) | Manager name |
| operator_company | VARCHAR(200) | Operating company |
| status | ENUM | active, inactive, maintenance, temporarily_closed |
| is_reservation_enabled | BOOLEAN | Reservations allowed |
| is_real_time_updates | BOOLEAN | Real-time data updates |
| last_occupancy_update | DATETIME | Last occupancy update |
| website_url | VARCHAR(500) | Website URL |
| image_urls | JSON | Array of image URLs |
| amenities | JSON | Additional amenities |
| restrictions | JSON | Parking restrictions |
| special_instructions | TEXT | Special instructions |
| created_at | DATETIME | Creation timestamp |
| updated_at | DATETIME | Last update timestamp |

**Indexes**: name, city, code (unique), location (spatial), latitude, longitude

---

### 4. Parking_Spots Table
**Purpose**: Individual parking spot management with geospatial data

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| parking_lot_id | INTEGER | Foreign key to parking_lots.id |
| spot_number | VARCHAR(20) | Spot number/identifier |
| spot_code | VARCHAR(50) | QR code or unique identifier |
| floor | INTEGER | Floor level |
| section | VARCHAR(10) | Section identifier (A, B, C, etc.) |
| row | VARCHAR(10) | Row identifier |
| zone | VARCHAR(50) | Special zone designation |
| location | GEOMETRY(POINT) | Precise spot location |
| spot_boundary | GEOMETRY(POLYGON) | Exact spot boundaries |
| latitude | NUMERIC(10,8) | Latitude coordinate |
| longitude | NUMERIC(11,8) | Longitude coordinate |
| spot_type | ENUM | regular, compact, handicapped, electric, motorcycle, loading_zone, vip, family |
| status | ENUM | available, occupied, reserved, out_of_order, maintenance |
| length_cm | INTEGER | Spot length in centimeters |
| width_cm | INTEGER | Spot width in centimeters |
| height_cm | INTEGER | Height clearance |
| max_vehicle_length_cm | INTEGER | Maximum vehicle length |
| max_vehicle_width_cm | INTEGER | Maximum vehicle width |
| max_vehicle_height_cm | INTEGER | Maximum vehicle height |
| max_vehicle_weight_kg | INTEGER | Maximum vehicle weight |
| has_ev_charging | BOOLEAN | EV charging available |
| charging_type | ENUM | none, type_1, type_2, ccs, chademo, tesla, universal |
| charging_power_kw | NUMERIC(5,2) | Charging power in kW |
| charging_network | VARCHAR(100) | Charging network provider |
| charging_station_id | VARCHAR(100) | Charging station ID |
| is_handicapped_accessible | BOOLEAN | Handicapped accessibility |
| has_wider_access | BOOLEAN | Wider access for accessibility |
| is_covered | BOOLEAN | Covered parking |
| has_custom_pricing | BOOLEAN | Custom pricing enabled |
| hourly_rate | NUMERIC(10,2) | Custom hourly rate |
| daily_rate | NUMERIC(10,2) | Custom daily rate |
| pricing_multiplier | NUMERIC(3,2) | Pricing multiplier |
| sensor_id | VARCHAR(100) | IoT sensor identifier |
| has_sensor | BOOLEAN | Sensor installed |
| last_sensor_update | DATETIME | Last sensor reading |
| sensor_battery_level | INTEGER | Sensor battery percentage |
| is_active | BOOLEAN | Spot active status |
| is_reservable | BOOLEAN | Available for reservation |
| current_vehicle_id | INTEGER | Currently parked vehicle |
| occupied_since | DATETIME | Occupation start time |
| last_occupied_at | DATETIME | Last occupation time |
| total_occupancy_time | INTEGER | Total occupied minutes |
| maintenance_notes | TEXT | Maintenance notes |
| last_maintenance_date | DATETIME | Last maintenance date |
| issue_reported | BOOLEAN | Issue reported flag |
| issue_description | TEXT | Issue description |
| issue_reported_at | DATETIME | Issue report time |
| features | JSON | Additional features |
| special_instructions | TEXT | Special instructions |
| created_at | DATETIME | Creation timestamp |
| updated_at | DATETIME | Last update timestamp |
| status_changed_at | DATETIME | Status change timestamp |

**Indexes**: parking_lot_id, spot_number, status, location (spatial), sensor_id (unique)

---

### 5. Reservations Table
**Purpose**: Manages parking reservations with time constraints

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| user_id | INTEGER | Foreign key to users.id |
| vehicle_id | INTEGER | Foreign key to vehicles.id |
| parking_lot_id | INTEGER | Foreign key to parking_lots.id |
| parking_spot_id | INTEGER | Foreign key to parking_spots.id |
| reservation_number | VARCHAR(50) | Unique reservation number |
| confirmation_code | VARCHAR(20) | Confirmation code |
| reservation_type | ENUM | immediate, scheduled, recurring |
| start_time | DATETIME | Reservation start time |
| end_time | DATETIME | Reservation end time |
| actual_arrival_time | DATETIME | Actual arrival time |
| actual_departure_time | DATETIME | Actual departure time |
| grace_period_minutes | INTEGER | Late arrival tolerance |
| max_extension_hours | INTEGER | Maximum extension allowed |
| extended_until | DATETIME | Extension end time |
| extension_count | INTEGER | Number of extensions |
| status | ENUM | pending, confirmed, active, completed, cancelled, expired, no_show, overstayed |
| is_recurring | BOOLEAN | Recurring reservation flag |
| parent_reservation_id | INTEGER | Parent reservation for recurring |
| base_cost | NUMERIC(10,2) | Base cost |
| total_cost | NUMERIC(10,2) | Total cost including fees |
| tax_amount | NUMERIC(10,2) | Tax amount |
| discount_amount | NUMERIC(10,2) | Discount applied |
| extension_cost | NUMERIC(10,2) | Extension fees |
| penalty_cost | NUMERIC(10,2) | Penalty fees |
| is_paid | BOOLEAN | Payment status |
| payment_due_at | DATETIME | Payment due time |
| refund_amount | NUMERIC(10,2) | Refund amount |
| requires_ev_charging | BOOLEAN | EV charging required |
| requires_handicapped_access | BOOLEAN | Handicapped access required |
| preferred_spot_type | VARCHAR(50) | Preferred spot type |
| special_requests | TEXT | Special requests |
| cancelled_at | DATETIME | Cancellation time |
| cancellation_reason | VARCHAR(200) | Cancellation reason |
| is_refundable | BOOLEAN | Refund eligibility |
| cancellation_fee | NUMERIC(10,2) | Cancellation fee |
| recurrence_pattern | JSON | Recurring pattern rules |
| recurrence_end_date | DATETIME | Recurrence end date |
| next_occurrence_date | DATETIME | Next occurrence |
| reminder_sent | BOOLEAN | Reminder notification sent |
| arrival_notification_sent | BOOLEAN | Arrival notification sent |
| departure_reminder_sent | BOOLEAN | Departure reminder sent |
| qr_code | VARCHAR(200) | QR code for check-in |
| check_in_method | VARCHAR(50) | Check-in method used |
| check_out_method | VARCHAR(50) | Check-out method used |
| license_plate_verified | BOOLEAN | License plate verified |
| spot_verified | BOOLEAN | Spot verified |
| notes | TEXT | User notes |
| internal_notes | TEXT | Staff notes |
| created_at | DATETIME | Creation timestamp |
| updated_at | DATETIME | Last update timestamp |
| confirmed_at | DATETIME | Confirmation timestamp |

**Indexes**: user_id, vehicle_id, parking_lot_id, parking_spot_id, reservation_number (unique), confirmation_code (unique), start_time, end_time, status

---

### 6. Payments Table
**Purpose**: Transaction records and payment processing

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| user_id | INTEGER | Foreign key to users.id |
| reservation_id | INTEGER | Foreign key to reservations.id |
| payment_number | VARCHAR(50) | Unique payment number |
| external_transaction_id | VARCHAR(100) | External processor ID |
| receipt_number | VARCHAR(50) | Receipt number |
| payment_type | ENUM | reservation, extension, penalty, cancellation, subscription, refund, deposit, top_up |
| payment_method | ENUM | credit_card, debit_card, digital_wallet, bank_transfer, cash, mobile_payment, cryptocurrency, account_credit, gift_card, subscription |
| status | ENUM | pending, processing, completed, failed, cancelled, refunded, partially_refunded, disputed, chargeback |
| amount | NUMERIC(10,2) | Payment amount |
| currency | ENUM | USD, EUR, GBP, CAD, AUD, JPY, CNY, INR |
| tax_amount | NUMERIC(10,2) | Tax amount |
| fee_amount | NUMERIC(10,2) | Processing fees |
| net_amount | NUMERIC(10,2) | Net amount after fees |
| discount_amount | NUMERIC(10,2) | Discount applied |
| promotion_code | VARCHAR(50) | Promotion code used |
| promotion_discount | NUMERIC(10,2) | Promotion discount |
| payment_processor | VARCHAR(50) | Payment processor |
| processor_fee | NUMERIC(10,2) | Processor fee |
| processor_transaction_id | VARCHAR(100) | Processor transaction ID |
| processor_response | JSON | Full processor response |
| masked_card_number | VARCHAR(20) | Masked card number |
| card_brand | VARCHAR(20) | Card brand |
| card_expiry_month | INTEGER | Card expiry month |
| card_expiry_year | INTEGER | Card expiry year |
| billing_address | JSON | Billing address |
| wallet_type | VARCHAR(50) | Digital wallet type |
| wallet_transaction_id | VARCHAR(100) | Wallet transaction ID |
| bank_account_last4 | VARCHAR(4) | Last 4 digits of account |
| bank_routing_number | VARCHAR(20) | Bank routing number |
| bank_name | VARCHAR(100) | Bank name |
| risk_score | NUMERIC(5,2) | Fraud risk score |
| is_flagged | BOOLEAN | Fraud flag |
| fraud_check_result | VARCHAR(50) | Fraud check result |
| avs_result | VARCHAR(10) | Address verification result |
| cvv_result | VARCHAR(10) | CVV verification result |
| ip_address | VARCHAR(45) | Client IP address |
| user_agent | TEXT | Client user agent |
| device_fingerprint | VARCHAR(100) | Device fingerprint |
| refund_amount | NUMERIC(10,2) | Refunded amount |
| refund_reason | VARCHAR(200) | Refund reason |
| refunded_at | DATETIME | Refund timestamp |
| refund_transaction_id | VARCHAR(100) | Refund transaction ID |
| created_at | DATETIME | Creation timestamp |
| updated_at | DATETIME | Last update timestamp |
| processed_at | DATETIME | Processing timestamp |
| failed_at | DATETIME | Failure timestamp |
| retry_count | INTEGER | Retry attempts |
| last_retry_at | DATETIME | Last retry time |
| failure_reason | TEXT | Failure reason |
| failure_code | VARCHAR(50) | Failure code |
| dispute_initiated_at | DATETIME | Dispute initiation time |
| dispute_amount | NUMERIC(10,2) | Disputed amount |
| dispute_reason | VARCHAR(200) | Dispute reason |
| dispute_evidence_due_date | DATETIME | Evidence due date |
| chargeback_id | VARCHAR(100) | Chargeback ID |
| subscription_id | VARCHAR(100) | Subscription ID |
| billing_period_start | DATETIME | Billing period start |
| billing_period_end | DATETIME | Billing period end |
| description | TEXT | Payment description |
| internal_notes | TEXT | Internal notes |
| metadata | JSON | Additional metadata |

**Indexes**: user_id, reservation_id, payment_number (unique), external_transaction_id, payment_type, status, promotion_code

---

## Analytics Tables

### 7. Occupancy_Analytics Table
**Purpose**: Track parking spot occupancy metrics over time

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| parking_lot_id | INTEGER | Foreign key to parking_lots.id |
| parking_spot_id | INTEGER | Foreign key to parking_spots.id (null for lot-wide) |
| period_type | ENUM | hourly, daily, weekly, monthly, quarterly, yearly |
| period_start | DATETIME | Analysis period start |
| period_end | DATETIME | Analysis period end |
| analysis_date | DATE | Date for easier querying |
| total_spots | INTEGER | Total spots analyzed |
| total_minutes_available | INTEGER | Total available minutes |
| total_minutes_occupied | INTEGER | Total occupied minutes |
| total_minutes_reserved | INTEGER | Total reserved minutes |
| occupancy_rate | NUMERIC(5,2) | Occupancy percentage |
| utilization_rate | NUMERIC(5,2) | Utilization percentage |
| availability_rate | NUMERIC(5,2) | Availability percentage |
| peak_occupancy | INTEGER | Peak spots occupied |
| peak_occupancy_time | DATETIME | Peak time |
| average_occupancy | NUMERIC(8,2) | Average occupancy |
| total_arrivals | INTEGER | Vehicle arrivals |
| total_departures | INTEGER | Vehicle departures |
| total_reservations | INTEGER | Reservations made |
| no_show_count | INTEGER | No-show reservations |
| avg_parking_duration | NUMERIC(8,2) | Average parking duration |
| min_parking_duration | INTEGER | Shortest duration |
| max_parking_duration | INTEGER | Longest duration |
| median_parking_duration | NUMERIC(8,2) | Median duration |
| turnover_rate | NUMERIC(5,2) | Turnover rate |
| avg_vacancy_duration | NUMERIC(8,2) | Average vacancy time |
| regular_spot_occupancy | NUMERIC(5,2) | Regular spot occupancy |
| handicapped_spot_occupancy | NUMERIC(5,2) | Handicapped spot occupancy |
| electric_spot_occupancy | NUMERIC(5,2) | Electric spot occupancy |
| motorcycle_spot_occupancy | NUMERIC(5,2) | Motorcycle spot occupancy |
| morning_peak_occupancy | NUMERIC(5,2) | Morning peak (6-10 AM) |
| midday_occupancy | NUMERIC(5,2) | Midday (10 AM-2 PM) |
| afternoon_peak_occupancy | NUMERIC(5,2) | Afternoon peak (2-6 PM) |
| evening_occupancy | NUMERIC(5,2) | Evening (6-10 PM) |
| overnight_occupancy | NUMERIC(5,2) | Overnight (10 PM-6 AM) |
| weekday_avg_occupancy | NUMERIC(5,2) | Weekday average |
| weekend_avg_occupancy | NUMERIC(5,2) | Weekend average |
| weather_condition | VARCHAR(50) | Weather condition |
| temperature_avg | NUMERIC(5,2) | Average temperature |
| data_completeness | NUMERIC(5,2) | Data completeness percentage |
| sensor_uptime | NUMERIC(5,2) | Sensor uptime percentage |
| created_at | DATETIME | Creation timestamp |
| updated_at | DATETIME | Last update timestamp |

**Indexes**: parking_lot_id, analysis_date, period_type, period_start

---

### 8. Revenue_Analytics Table
**Purpose**: Track revenue and financial metrics over time

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| parking_lot_id | INTEGER | Foreign key to parking_lots.id |
| period_type | ENUM | hourly, daily, weekly, monthly, quarterly, yearly |
| period_start | DATETIME | Analysis period start |
| period_end | DATETIME | Analysis period end |
| analysis_date | DATE | Date for easier querying |
| total_revenue | NUMERIC(12,2) | Total revenue |
| parking_revenue | NUMERIC(12,2) | Core parking revenue |
| penalty_revenue | NUMERIC(12,2) | Penalty fees |
| extension_revenue | NUMERIC(12,2) | Extension fees |
| cancellation_revenue | NUMERIC(12,2) | Cancellation fees |
| cash_revenue | NUMERIC(12,2) | Cash payments |
| card_revenue | NUMERIC(12,2) | Card payments |
| digital_wallet_revenue | NUMERIC(12,2) | Digital wallet payments |
| mobile_payment_revenue | NUMERIC(12,2) | Mobile payments |
| total_transactions | INTEGER | Total transactions |
| successful_transactions | INTEGER | Successful transactions |
| failed_transactions | INTEGER | Failed transactions |
| refunded_transactions | INTEGER | Refunded transactions |
| avg_transaction_value | NUMERIC(8,2) | Average transaction |
| min_transaction_value | NUMERIC(8,2) | Minimum transaction |
| max_transaction_value | NUMERIC(8,2) | Maximum transaction |
| median_transaction_value | NUMERIC(8,2) | Median transaction |
| processing_fees | NUMERIC(10,2) | Processing fees |
| operational_costs | NUMERIC(10,2) | Operational costs |
| net_revenue | NUMERIC(12,2) | Net revenue |
| avg_hourly_rate | NUMERIC(8,2) | Average hourly rate |
| avg_daily_rate | NUMERIC(8,2) | Average daily rate |
| discount_amount | NUMERIC(10,2) | Total discounts |
| promotion_usage | INTEGER | Promotions used |
| total_refunds | NUMERIC(10,2) | Total refunds |
| refund_rate | NUMERIC(5,2) | Refund rate percentage |
| avg_refund_amount | NUMERIC(8,2) | Average refund |
| unique_customers | INTEGER | Unique customers |
| repeat_customers | INTEGER | Returning customers |
| new_customers | INTEGER | New customers |
| revenue_per_spot | NUMERIC(8,2) | Revenue per spot |
| revenue_per_hour | NUMERIC(8,2) | Revenue per hour |
| revenue_per_customer | NUMERIC(8,2) | Revenue per customer |
| morning_revenue | NUMERIC(10,2) | Morning revenue |
| midday_revenue | NUMERIC(10,2) | Midday revenue |
| afternoon_revenue | NUMERIC(10,2) | Afternoon revenue |
| evening_revenue | NUMERIC(10,2) | Evening revenue |
| overnight_revenue | NUMERIC(10,2) | Overnight revenue |
| weekday_revenue | NUMERIC(10,2) | Weekday revenue |
| weekend_revenue | NUMERIC(10,2) | Weekend revenue |
| subscription_revenue | NUMERIC(10,2) | Subscription revenue |
| one_time_revenue | NUMERIC(10,2) | One-time revenue |
| predicted_revenue | NUMERIC(12,2) | AI predicted revenue |
| forecast_accuracy | NUMERIC(5,2) | Prediction accuracy |
| currency | VARCHAR(3) | Currency code |
| exchange_rate | NUMERIC(10,6) | Exchange rate |
| data_completeness | NUMERIC(5,2) | Data completeness |
| created_at | DATETIME | Creation timestamp |
| updated_at | DATETIME | Last update timestamp |

**Indexes**: parking_lot_id, analysis_date, period_type, period_start

## Relationships

### Foreign Key Relationships
- `vehicles.owner_id` → `users.id`
- `parking_spots.parking_lot_id` → `parking_lots.id`
- `parking_spots.current_vehicle_id` → `vehicles.id`
- `reservations.user_id` → `users.id`
- `reservations.vehicle_id` → `vehicles.id`
- `reservations.parking_lot_id` → `parking_lots.id`
- `reservations.parking_spot_id` → `parking_spots.id`
- `reservations.parent_reservation_id` → `reservations.id`
- `payments.user_id` → `users.id`
- `payments.reservation_id` → `reservations.id`
- `occupancy_analytics.parking_lot_id` → `parking_lots.id`
- `occupancy_analytics.parking_spot_id` → `parking_spots.id`
- `revenue_analytics.parking_lot_id` → `parking_lots.id`

## Geospatial Features

### PostGIS Integration
The system uses PostGIS for advanced geospatial operations:

1. **Point Geometries**: Store precise locations for parking lots and spots
2. **Polygon Geometries**: Store parking lot boundaries and spot boundaries
3. **Spatial Indexes**: GIST indexes for efficient spatial queries
4. **Coordinate System**: WGS84 (SRID 4326) for global compatibility

### Spatial Queries Supported
- Find parking lots within radius
- Calculate distances between locations
- Check if point is within parking lot boundary
- Find nearest available parking spots
- Geofencing for automated check-in/check-out

## Enum Types

All enum values are enforced at the database level for data integrity:

- **UserRole**: user, admin, manager, operator
- **UserStatus**: active, inactive, suspended, pending_verification
- **VehicleType**: car, motorcycle, truck, van, electric_car, electric_motorcycle, bicycle, scooter
- **FuelType**: gasoline, diesel, electric, hybrid, plug_in_hybrid, cng, lpg
- **ParkingLotType**: outdoor, indoor, underground, multi_level, street_parking
- **AccessType**: public, private, restricted, residential, commercial
- **ParkingLotStatus**: active, inactive, maintenance, temporarily_closed
- **SpotStatus**: available, occupied, reserved, out_of_order, maintenance
- **SpotType**: regular, compact, handicapped, electric, motorcycle, loading_zone, vip, family
- **ChargingType**: none, type_1, type_2, ccs, chademo, tesla, universal
- **ReservationStatus**: pending, confirmed, active, completed, cancelled, expired, no_show, overstayed
- **ReservationType**: immediate, scheduled, recurring
- **PaymentStatus**: pending, processing, completed, failed, cancelled, refunded, partially_refunded, disputed, chargeback
- **PaymentMethod**: credit_card, debit_card, digital_wallet, bank_transfer, cash, mobile_payment, cryptocurrency, account_credit, gift_card, subscription
- **PaymentType**: reservation, extension, penalty, cancellation, subscription, refund, deposit, top_up
- **Currency**: USD, EUR, GBP, CAD, AUD, JPY, CNY, INR
- **AnalyticsPeriod**: hourly, daily, weekly, monthly, quarterly, yearly

## Performance Considerations

### Indexing Strategy
- Primary keys on all tables
- Foreign key indexes for relationship queries
- Unique indexes on business-critical fields (email, license_plate, etc.)
- Composite indexes for common query patterns
- Spatial indexes (GIST) for geospatial queries
- Partial indexes for frequently filtered data

### Query Optimization
- Use of appropriate data types for storage efficiency
- JSON columns for flexible schema requirements
- Numeric precision for financial calculations
- Timezone-aware datetime storage
- Proper normalization to reduce redundancy

### Scalability Features
- Partitioning support for large analytics tables
- Archival strategy for historical data
- Efficient bulk operations for data loading
- Connection pooling and async operations
- Read replicas for reporting queries

## Security Features

### Data Protection
- Password hashing with bcrypt and salt
- Tokenized payment information storage
- PII encryption for sensitive data
- Audit trails through timestamps
- Role-based access control

### Compliance Considerations
- GDPR compliance for user data
- PCI DSS considerations for payment data
- Data retention policies
- Right to deletion support
- Data export capabilities