# API Documentation

## Overview

The Parking Management System API is built using FastAPI and provides RESTful endpoints for managing parking lots, reservations, payments, and user authentication. The API follows OpenAPI 3.0 specifications and includes comprehensive validation, error handling, and rate limiting.

## Base URL

- **Development**: `http://localhost:8000`
- **Production**: `https://api.parkingmanagement.com`

## Authentication

The API uses JWT (JSON Web Tokens) for authentication. Include the token in the Authorization header:

```
Authorization: Bearer <jwt_token>
```

### Authentication Endpoints

#### POST /auth/register
Register a new user account.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "secure_password123",
  "full_name": "John Doe",
  "phone_number": "+1234567890"
}
```

**Response (201):**
```json
{
  "id": "uuid-string",
  "email": "user@example.com",
  "full_name": "John Doe",
  "is_verified": false,
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### POST /auth/login
Authenticate user and receive JWT token.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "secure_password123"
}
```

**Response (200):**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "uuid-string",
    "email": "user@example.com",
    "full_name": "John Doe"
  }
}
```

#### POST /auth/refresh
Refresh access token using refresh token.

**Request Body:**
```json
{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

#### GET /auth/me
Get current authenticated user information.

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "id": "uuid-string",
  "email": "user@example.com",
  "full_name": "John Doe",
  "phone_number": "+1234567890",
  "is_verified": true,
  "created_at": "2024-01-01T00:00:00Z"
}
```

### Parking Lot Management

#### GET /parking-lots
List all parking lots with optional filtering.

**Query Parameters:**
- `lat` (float): Latitude for location-based search
- `lng` (float): Longitude for location-based search
- `radius` (float): Search radius in kilometers (default: 5)
- `amenities` (list): Filter by amenities (e.g., covered, security, ev_charging)
- `min_price` (float): Minimum hourly rate
- `max_price` (float): Maximum hourly rate
- `available_spots` (int): Minimum available spots
- `limit` (int): Results per page (default: 20, max: 100)
- `offset` (int): Pagination offset

**Response (200):**
```json
{
  "items": [
    {
      "id": "uuid-string",
      "name": "Downtown Parking Garage",
      "description": "Secure covered parking in city center",
      "location": {
        "type": "Point",
        "coordinates": [-122.4194, 37.7749]
      },
      "address": "123 Main St, San Francisco, CA 94111",
      "total_spots": 500,
      "available_spots": 45,
      "hourly_rate": 12.50,
      "daily_rate": 85.00,
      "amenities": ["covered", "security", "ev_charging"],
      "operating_hours": {
        "monday": {"open": "00:00", "close": "24:00"},
        "tuesday": {"open": "00:00", "close": "24:00"}
      },
      "images": ["https://example.com/image1.jpg"],
      "rating": 4.5,
      "reviews_count": 125
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

#### GET /parking-lots/{lot_id}
Get detailed information about a specific parking lot.

**Response (200):** Single parking lot object with additional details including real-time availability and recent reviews.

#### POST /parking-lots
Create a new parking lot (Admin only).

**Headers:** `Authorization: Bearer <admin_token>`

**Request Body:**
```json
{
  "name": "New Parking Garage",
  "description": "Modern parking facility",
  "latitude": 37.7749,
  "longitude": -122.4194,
  "address": "456 Oak St, San Francisco, CA 94102",
  "total_spots": 200,
  "hourly_rate": 15.00,
  "daily_rate": 100.00,
  "amenities": ["covered", "security"],
  "operating_hours": {
    "monday": {"open": "06:00", "close": "22:00"}
  }
}
```

### Parking Spots

#### GET /parking-lots/{lot_id}/spots
List available parking spots in a specific lot.

**Query Parameters:**
- `spot_type` (string): Filter by spot type (standard, compact, accessible, ev_charging)
- `available_only` (bool): Show only available spots (default: true)

**Response (200):**
```json
{
  "spots": [
    {
      "id": "uuid-string",
      "spot_number": "A-101",
      "spot_type": "standard",
      "is_available": true,
      "width": 2.5,
      "length": 5.0,
      "location_coordinates": {
        "x": 10.5,
        "y": 25.3
      }
    }
  ]
}
```

### Reservations

#### POST /reservations
Create a new parking reservation.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "parking_lot_id": "uuid-string",
  "spot_id": "uuid-string",
  "vehicle_id": "uuid-string",
  "start_time": "2024-01-15T10:00:00Z",
  "end_time": "2024-01-15T14:00:00Z",
  "payment_method": "stripe"
}
```

**Response (201):**
```json
{
  "id": "uuid-string",
  "reservation_number": "RES-2024-001234",
  "status": "confirmed",
  "parking_lot": {
    "id": "uuid-string",
    "name": "Downtown Parking Garage"
  },
  "spot": {
    "id": "uuid-string",
    "spot_number": "A-101"
  },
  "start_time": "2024-01-15T10:00:00Z",
  "end_time": "2024-01-15T14:00:00Z",
  "duration_hours": 4,
  "total_cost": 50.00,
  "payment_status": "pending",
  "qr_code": "data:image/png;base64,iVBORw0KGgoAAAANS..."
}
```

#### GET /reservations
List user's reservations.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `status` (string): Filter by status (pending, confirmed, active, completed, cancelled)
- `start_date` (date): Filter reservations from this date
- `end_date` (date): Filter reservations until this date
- `limit` (int): Results per page
- `offset` (int): Pagination offset

#### GET /reservations/{reservation_id}
Get detailed reservation information.

#### PUT /reservations/{reservation_id}
Update reservation (modify time, extend duration).

#### DELETE /reservations/{reservation_id}
Cancel reservation.

### Vehicles

#### GET /vehicles
List user's registered vehicles.

#### POST /vehicles
Register a new vehicle.

**Request Body:**
```json
{
  "license_plate": "ABC123",
  "make": "Toyota",
  "model": "Camry",
  "year": 2022,
  "color": "Blue",
  "vehicle_type": "sedan"
}
```

### Payments

#### POST /payments
Process payment for reservation.

**Request Body:**
```json
{
  "reservation_id": "uuid-string",
  "payment_method": "stripe",
  "stripe_payment_intent_id": "pi_1234567890"
}
```

#### GET /payments/history
Get payment history for user.

### Real-time Features

#### WebSocket /ws/parking-updates
Real-time parking availability updates.

**Connection:** `ws://localhost:8000/ws/parking-updates?token=<jwt_token>`

**Message Types:**
```json
{
  "type": "spot_availability",
  "data": {
    "parking_lot_id": "uuid-string",
    "available_spots": 42,
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

### Analytics Endpoints (Admin)

#### GET /analytics/occupancy
Get occupancy analytics for parking lots.

#### GET /analytics/revenue
Get revenue analytics.

#### GET /analytics/usage-patterns
Get usage pattern analytics.

## Error Handling

The API returns standard HTTP status codes with detailed error messages:

### Error Response Format
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": [
      {
        "field": "email",
        "message": "Invalid email format"
      }
    ]
  },
  "timestamp": "2024-01-15T10:30:00Z",
  "path": "/auth/register"
}
```

### Common Error Codes
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Missing or invalid authentication
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `409 Conflict`: Resource conflict (e.g., time slot already booked)
- `422 Unprocessable Entity`: Validation errors
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

## Rate Limiting

API endpoints are rate-limited based on user authentication:

- **Unauthenticated**: 100 requests per hour
- **Authenticated**: 1000 requests per hour
- **Admin**: 5000 requests per hour

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1642248000
```

## Pagination

List endpoints support cursor-based pagination:

**Query Parameters:**
- `limit`: Number of items per page (default: 20, max: 100)
- `offset`: Number of items to skip

**Response Headers:**
```
Link: <https://api.example.com/parking-lots?offset=20&limit=20>; rel="next"
X-Total-Count: 150
```

## Data Validation

All API endpoints include comprehensive data validation:

- **Email**: Valid email format required
- **Phone**: International phone number format
- **Coordinates**: Valid latitude/longitude ranges
- **Dates**: ISO 8601 format required
- **IDs**: Valid UUID format required

## OpenAPI Specification

The complete OpenAPI specification is available at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **JSON**: `http://localhost:8000/openapi.json`

## SDK Support

Official SDKs are available for:
- **JavaScript/TypeScript**: `npm install parking-management-sdk`
- **Python**: `pip install parking-management-sdk`
- **iOS**: Available via CocoaPods
- **Android**: Available via Maven

## Webhooks

The API supports webhooks for real-time notifications:

### Webhook Events
- `reservation.created`
- `reservation.confirmed`
- `reservation.cancelled`
- `payment.completed`
- `payment.failed`

### Webhook Payload Example
```json
{
  "event": "reservation.confirmed",
  "data": {
    "reservation_id": "uuid-string",
    "user_id": "uuid-string",
    "parking_lot_id": "uuid-string"
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Testing

Use the following test credentials for API testing:

**Test User:**
- Email: `test@example.com`
- Password: `testpassword123`

**Test Parking Lot ID:** `550e8400-e29b-41d4-a716-446655440000`

**Test Credit Card (Stripe):**
- Number: `4242424242424242`
- Expiry: `12/25`
- CVC: `123`
