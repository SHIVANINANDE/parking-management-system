# System Design Document

## Overview

The Parking Management System is designed as a scalable, real-time platform that handles parking lot discovery, reservation management, payment processing, and analytics. The system supports multiple user types (customers, operators, administrators) with different access levels and capabilities.

## High-Level Architecture

### System Context Diagram

```
                    ┌─────────────────────┐
                    │      Internet       │
                    └─────────────────────┘
                              │
                    ┌─────────────────────┐
                    │    Load Balancer    │
                    │     (Nginx/ALB)     │
                    └─────────────────────┘
                              │
        ┌────────────────────────────────────────────────────┐
        │                API Gateway                         │
        │            (FastAPI Application)                   │
        │                                                    │
        │ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐│
        │ │ Auth Service │ │Parking Service│ │Payment Service││
        │ └──────────────┘ └──────────────┘ └──────────────┘│
        │ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐│
        │ │Notification  │ │Analytics     │ │ Spatial      ││
        │ │   Service    │ │   Service    │ │  Service     ││
        │ └──────────────┘ └──────────────┘ └──────────────┘│
        └────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────────────────────────────────────┐
        │                Event Bus (Kafka)                    │
        └─────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────────────────────────────────────┐
        │                 Data Layer                          │
        │                                                     │
        │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐    │
        │ │ PostgreSQL  │ │    Redis    │ │Elasticsearch│    │
        │ │  + PostGIS  │ │   Cache     │ │  Analytics  │    │
        │ └─────────────┘ └─────────────┘ └─────────────┘    │
        └─────────────────────────────────────────────────────┘
```

### Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend Layer                           │
│                                                                 │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐│
│ │   Web App   │ │Mobile PWA   │ │  Admin      │ │  Operator   ││
│ │ (React SPA) │ │(React PWA)  │ │ Dashboard   │ │ Dashboard   ││
│ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘│
└─────────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────────┐
│                      API Gateway Layer                          │
│                                                                 │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐│
│ │Rate Limiting│ │Authentication│ │ Request     │ │  Response   ││
│ │& Throttling │ │Authorization │ │Validation   │ │Formatting   ││
│ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘│
└─────────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────────┐
│                     Business Logic Layer                        │
│                                                                 │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐            │
│ │ User Service │ │Parking Service│ │Reservation   │            │
│ │              │ │              │ │  Service     │            │
│ └──────────────┘ └──────────────┘ └──────────────┘            │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐            │
│ │Payment       │ │Notification  │ │Analytics     │            │
│ │  Service     │ │  Service     │ │  Service     │            │
│ └──────────────┘ └──────────────┘ └──────────────┘            │
└─────────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────────┐
│                      Data Access Layer                          │
│                                                                 │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐            │
│ │  Repository  │ │    Cache     │ │   Search     │            │
│ │   Pattern    │ │   Manager    │ │   Manager    │            │
│ └──────────────┘ └──────────────┘ └──────────────┘            │
└─────────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────────┐
│                      Infrastructure Layer                       │
│                                                                 │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐            │
│ │  PostgreSQL  │ │    Redis     │ │Elasticsearch │            │
│ │   + PostGIS  │ │              │ │              │            │
│ └──────────────┘ └──────────────┘ └──────────────┘            │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐            │
│ │    Kafka     │ │   Monitoring │ │  External    │            │
│ │              │ │   Stack      │ │   APIs       │            │
│ └──────────────┘ └──────────────┘ └──────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

## Core Services

### 1. Authentication Service

**Responsibilities:**
- User registration and authentication
- JWT token management and refresh
- Role-based access control
- Session management

**Key Components:**
```python
class AuthService:
    - register_user()
    - authenticate_user()
    - create_tokens()
    - refresh_token()
    - validate_token()
    - revoke_token()

class RoleManager:
    - assign_role()
    - check_permission()
    - get_user_roles()
```

**Database Schema:**
```sql
-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    phone_number VARCHAR(20),
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Roles and permissions
CREATE TABLE roles (
    id UUID PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT
);

CREATE TABLE user_roles (
    user_id UUID REFERENCES users(id),
    role_id UUID REFERENCES roles(id),
    PRIMARY KEY (user_id, role_id)
);
```

### 2. Parking Service

**Responsibilities:**
- Parking lot management
- Spot availability tracking
- Location-based search
- Real-time updates

**Key Components:**
```python
class ParkingService:
    - search_parking_lots()
    - get_lot_details()
    - update_spot_availability()
    - calculate_distance()

class SpatialService:
    - find_nearby_lots()
    - calculate_route()
    - validate_coordinates()
```

**Database Schema:**
```sql
-- Parking lots with spatial data
CREATE TABLE parking_lots (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    location GEOMETRY(POINT, 4326) NOT NULL,
    address TEXT NOT NULL,
    total_spots INTEGER NOT NULL,
    available_spots INTEGER NOT NULL,
    hourly_rate DECIMAL(10,2) NOT NULL,
    daily_rate DECIMAL(10,2),
    amenities JSONB,
    operating_hours JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Spatial index for efficient location queries
CREATE INDEX idx_parking_lots_location 
ON parking_lots USING GIST (location);

-- Parking spots
CREATE TABLE parking_spots (
    id UUID PRIMARY KEY,
    parking_lot_id UUID REFERENCES parking_lots(id),
    spot_number VARCHAR(20) NOT NULL,
    spot_type VARCHAR(20) NOT NULL, -- standard, compact, accessible, ev_charging
    is_available BOOLEAN DEFAULT TRUE,
    width DECIMAL(5,2),
    length DECIMAL(5,2),
    location_coordinates JSONB -- x, y coordinates within lot
);
```

### 3. Reservation Service

**Responsibilities:**
- Reservation creation and management
- Conflict detection and resolution
- Time slot optimization
- QR code generation

**Key Components:**
```python
class ReservationService:
    - create_reservation()
    - check_availability()
    - update_reservation()
    - cancel_reservation()
    - generate_qr_code()

class ConflictResolver:
    - detect_conflicts()
    - suggest_alternatives()
    - auto_extend_reservation()
```

**Business Logic:**
```python
async def create_reservation(self, data: ReservationCreate) -> Reservation:
    # 1. Validate time slot
    if data.start_time >= data.end_time:
        raise ValidationError("Invalid time range")
    
    # 2. Check spot availability
    is_available = await self.check_spot_availability(
        data.spot_id, data.start_time, data.end_time
    )
    if not is_available:
        alternatives = await self.suggest_alternatives(data)
        raise SpotUnavailableError(alternatives=alternatives)
    
    # 3. Calculate pricing
    pricing = await self.calculate_pricing(
        data.parking_lot_id, data.start_time, data.end_time
    )
    
    # 4. Create reservation
    reservation = Reservation(
        user_id=data.user_id,
        spot_id=data.spot_id,
        start_time=data.start_time,
        end_time=data.end_time,
        total_cost=pricing.total_cost,
        status=ReservationStatus.PENDING
    )
    
    # 5. Reserve the spot
    await self.repository.save(reservation)
    await self.update_spot_availability(data.spot_id, False)
    
    # 6. Publish event
    await self.event_bus.publish(
        ReservationCreatedEvent(reservation_id=reservation.id)
    )
    
    return reservation
```

### 4. Payment Service

**Responsibilities:**
- Payment processing via Stripe
- Invoice generation
- Refund management
- Payment history tracking

**Key Components:**
```python
class PaymentService:
    - create_payment_intent()
    - process_payment()
    - handle_webhook()
    - issue_refund()

class InvoiceService:
    - generate_invoice()
    - send_invoice_email()
    - track_payment_status()
```

**Payment Flow:**
```
1. User initiates payment
2. Create Stripe PaymentIntent
3. Frontend handles 3D Secure if needed
4. Stripe webhook confirms payment
5. Update reservation status
6. Send confirmation email
7. Generate invoice
```

### 5. Notification Service

**Responsibilities:**
- Real-time WebSocket notifications
- Email notifications
- SMS alerts (optional)
- Push notifications (future)

**Key Components:**
```python
class NotificationService:
    - send_websocket_notification()
    - send_email()
    - send_sms()
    - broadcast_update()

class WebSocketManager:
    - connect_user()
    - disconnect_user()
    - broadcast_to_subscribers()
    - handle_room_subscriptions()
```

**Notification Types:**
- Reservation confirmed
- Payment processed
- Spot availability updates
- Reservation reminders
- System maintenance alerts

### 6. Analytics Service

**Responsibilities:**
- Occupancy analytics
- Revenue reporting
- Usage pattern analysis
- Predictive analytics

**Key Components:**
```python
class AnalyticsService:
    - calculate_occupancy_rate()
    - generate_revenue_report()
    - analyze_usage_patterns()
    - predict_demand()

class ReportGenerator:
    - daily_summary()
    - monthly_report()
    - custom_date_range()
    - export_to_csv()
```

## Data Flow Patterns

### 1. Command Query Responsibility Segregation (CQRS)

**Write Side (Commands):**
```python
# Command Pattern
@dataclass
class CreateReservationCommand:
    user_id: UUID
    parking_lot_id: UUID
    spot_id: UUID
    start_time: datetime
    end_time: datetime

class ReservationCommandHandler:
    async def handle(self, command: CreateReservationCommand):
        # Validate business rules
        # Execute command
        # Publish domain events
        pass
```

**Read Side (Queries):**
```python
# Query Pattern
@dataclass
class GetAvailableSpotsQuery:
    parking_lot_id: UUID
    start_time: datetime
    end_time: datetime

class ParkingQueryHandler:
    async def handle(self, query: GetAvailableSpotsQuery):
        # Optimized read from materialized views
        # Return projection data
        pass
```

### 2. Event-Driven Architecture

**Domain Events:**
```python
@dataclass
class ReservationCreatedEvent:
    reservation_id: UUID
    user_id: UUID
    parking_lot_id: UUID
    start_time: datetime
    total_cost: Decimal
    timestamp: datetime

class EventHandler:
    async def on_reservation_created(self, event: ReservationCreatedEvent):
        # Update read models
        # Send notifications
        # Update analytics
        # Trigger workflows
        pass
```

**Event Processing:**
```
1. Command executed → Event published to Kafka
2. Event handlers process asynchronously
3. Read models updated
4. Notifications sent
5. Analytics updated
```

## Scalability Design

### 1. Horizontal Scaling

**Stateless Design:**
- No server-side sessions
- JWT tokens for authentication
- Database connection pooling
- Shared Redis cache

**Load Balancing:**
```
Internet → Load Balancer → Multiple API Instances
                        ├─ Instance 1 (Auto-scaled)
                        ├─ Instance 2 (Auto-scaled)
                        └─ Instance N (Auto-scaled)
```

### 2. Database Scaling

**Read Replicas:**
```sql
-- Master (Write operations)
CREATE DATABASE parking_master;

-- Read Replica 1 (Analytics queries)
CREATE DATABASE parking_replica_analytics;

-- Read Replica 2 (Search queries)
CREATE DATABASE parking_replica_search;
```

**Partitioning Strategy:**
```sql
-- Partition reservations by date
CREATE TABLE reservations_2024_01 PARTITION OF reservations
FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE reservations_2024_02 PARTITION OF reservations
FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
```

### 3. Caching Strategy

**Multi-Level Caching:**
```python
# L1: Application Cache (in-memory)
@lru_cache(maxsize=1000)
def get_parking_lot_config(lot_id: UUID):
    pass

# L2: Redis Cache (distributed)
async def get_parking_lot(lot_id: UUID):
    cached = await redis.get(f"lot:{lot_id}")
    if cached:
        return json.loads(cached)
    
    lot = await db.get_parking_lot(lot_id)
    await redis.setex(f"lot:{lot_id}", 3600, json.dumps(lot))
    return lot

# L3: CDN (static content)
# Static assets, images, maps tiles
```

## Security Architecture

### 1. Authentication & Authorization

**JWT Token Structure:**
```json
{
  "header": {
    "alg": "HS256",
    "typ": "JWT"
  },
  "payload": {
    "sub": "user-uuid",
    "email": "user@example.com",
    "roles": ["user"],
    "permissions": ["read:parking", "write:reservation"],
    "exp": 1642248000,
    "iat": 1642244400
  }
}
```

**Role-Based Access Control:**
```python
PERMISSIONS = {
    "guest": ["read:parking"],
    "user": ["read:parking", "write:reservation", "read:own_data"],
    "operator": ["read:parking", "write:parking", "read:analytics"],
    "admin": ["*"]
}
```

### 2. Data Protection

**Encryption:**
- TLS 1.3 for data in transit
- AES-256 for sensitive data at rest
- Bcrypt for password hashing
- JWT signatures for token integrity

**Input Validation:**
```python
class ReservationCreateSchema(BaseModel):
    parking_lot_id: UUID
    start_time: datetime = Field(..., description="ISO 8601 format")
    end_time: datetime = Field(..., description="ISO 8601 format")
    
    @validator('end_time')
    def end_time_must_be_after_start(cls, v, values):
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError('end_time must be after start_time')
        return v
```

## Monitoring & Observability

### 1. Application Metrics

**Business Metrics:**
```python
# Prometheus metrics
RESERVATIONS_TOTAL = Counter('reservations_total', 'Total reservations')
REVENUE_TOTAL = Gauge('revenue_total', 'Total revenue in USD')
OCCUPANCY_RATE = Gauge('occupancy_rate', 'Current occupancy rate')
USER_SESSIONS = Gauge('active_user_sessions', 'Active user sessions')
```

**Technical Metrics:**
```python
# Performance metrics
REQUEST_DURATION = Histogram('request_duration_seconds', 'Request duration')
DATABASE_CONNECTIONS = Gauge('database_connections', 'Active DB connections')
CACHE_HIT_RATE = Gauge('cache_hit_rate', 'Cache hit rate percentage')
ERROR_RATE = Counter('errors_total', 'Total errors by type')
```

### 2. Distributed Tracing

**OpenTelemetry Integration:**
```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

async def create_reservation(data: ReservationCreate):
    with tracer.start_as_current_span("create_reservation") as span:
        span.set_attribute("user_id", str(data.user_id))
        span.set_attribute("parking_lot_id", str(data.parking_lot_id))
        
        with tracer.start_as_current_span("validate_availability"):
            # Validation logic
            pass
        
        with tracer.start_as_current_span("process_payment"):
            # Payment logic
            pass
        
        with tracer.start_as_current_span("save_reservation"):
            # Database save
            pass
```

### 3. Structured Logging

**Log Format:**
```json
{
  "timestamp": "2024-01-15T10:30:00.000Z",
  "level": "INFO",
  "logger": "reservation_service",
  "message": "Reservation created successfully",
  "context": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "reservation_id": "660e8400-e29b-41d4-a716-446655440000",
    "parking_lot_id": "770e8400-e29b-41d4-a716-446655440000",
    "total_cost": 25.50,
    "duration_hours": 2.5
  },
  "trace_id": "0123456789abcdef",
  "span_id": "fedcba9876543210"
}
```

## Deployment Architecture

### 1. Container Orchestration

**Docker Compose (Development):**
```yaml
version: '3.8'
services:
  api:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/parking
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis
  
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - api
  
  postgres:
    image: postgis/postgis:15-3.3
    environment:
      - POSTGRES_DB=parking
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
```

**Kubernetes (Production):**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: parking-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: parking-api
  template:
    metadata:
      labels:
        app: parking-api
    spec:
      containers:
      - name: api
        image: parking-management/api:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

### 2. CI/CD Pipeline

**GitHub Actions Workflow:**
```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: |
          pip install -r backend/requirements.txt
      
      - name: Run tests
        run: |
          pytest backend/tests/ --cov=app --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
  
  deploy:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to production
        run: |
          # Deployment script
```

## Performance Considerations

### 1. Database Optimization

**Query Optimization:**
```sql
-- Efficient spatial queries with proper indexing
EXPLAIN ANALYZE
SELECT p.*, ST_Distance(p.location, ST_Point(-122.4194, 37.7749)) as distance
FROM parking_lots p
WHERE ST_DWithin(p.location, ST_Point(-122.4194, 37.7749), 5000)
ORDER BY distance
LIMIT 20;

-- Index usage
CREATE INDEX CONCURRENTLY idx_parking_lots_location_gist 
ON parking_lots USING GIST (location);

-- Partial indexes for common queries
CREATE INDEX CONCURRENTLY idx_reservations_active 
ON reservations (start_time, end_time) 
WHERE status = 'active';
```

**Connection Pooling:**
```python
# SQLAlchemy async engine with connection pooling
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600
)
```

### 2. Caching Strategy

**Cache Layers:**
```python
# Hot data (frequently accessed)
await redis.setex("hot:parking_lots", 300, data)  # 5 minutes

# Warm data (moderately accessed)
await redis.setex("warm:user_preferences", 1800, data)  # 30 minutes

# Cold data (rarely accessed)
await redis.setex("cold:historical_data", 86400, data)  # 24 hours
```

### 3. API Optimization

**Response Compression:**
```python
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(GZipMiddleware, minimum_size=1000)
```

**Pagination:**
```python
@router.get("/parking-lots")
async def list_parking_lots(
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    query = select(ParkingLot).offset(offset).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()
```

## Disaster Recovery

### 1. Backup Strategy

**Database Backups:**
```bash
# Daily full backup
pg_dump -h localhost -U user -d parking > backup_$(date +%Y%m%d).sql

# Point-in-time recovery setup
archive_mode = on
archive_command = 'cp %p /var/lib/postgresql/archive/%f'
```

**Application State:**
```bash
# Redis backup
redis-cli BGSAVE

# Configuration backup
kubectl get configmaps -o yaml > configmaps-backup.yaml
```

### 2. High Availability

**Database HA:**
```
Primary Database ──► Standby Database (Streaming Replication)
       │                      │
       └─► Standby Database 2 ─┘ (Cascading Replication)
```

**Application HA:**
```
Load Balancer ──► API Instance 1 (Active)
              ├─► API Instance 2 (Active)
              └─► API Instance 3 (Active)
```

This system design ensures scalability, reliability, and maintainability while providing excellent performance for all user types and use cases.
