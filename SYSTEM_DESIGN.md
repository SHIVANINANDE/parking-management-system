# 🏗️ Parking Management System - System Design Document

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture Design](#architecture-design)
3. [Database Design](#database-design)
4. [API Design](#api-design)
5. [Real-time System](#real-time-system)
6. [Scalability & Performance](#scalability--performance)
7. [Security Design](#security-design)
8. [Deployment Architecture](#deployment-architecture)
9. [Monitoring & Observability](#monitoring--observability)
10. [Trade-offs & Decisions](#trade-offs--decisions)

## System Overview

### Business Requirements
The Parking Management System is designed to solve urban parking challenges by providing:
- **Real-time parking availability** for users
- **Intelligent reservation system** with conflict detection
- **Dynamic pricing** based on demand and location
- **Analytics and insights** for parking operators
- **Scalable multi-tenant architecture** supporting multiple cities

### High-Level Goals
- **Performance**: Handle 10,000+ concurrent users with sub-second response times
- **Availability**: 99.9% uptime with graceful degradation
- **Scalability**: Horizontal scaling to support multiple cities
- **Consistency**: Strong consistency for reservations, eventual consistency for analytics
- **Security**: PCI DSS compliant payment processing

## Architecture Design

### Overall Architecture Pattern
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Load Balancer (NGINX)                          │
└─────────────────────────┬───────────────────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────────────────┐
│                           API Gateway                                       │
│                     (Rate Limiting, Auth)                                   │
└─────────────┬─────────────────────────────┬─────────────────────────────────┘
              │                             │
┌─────────────▼──────────────┐   ┌─────────▼──────────────┐
│      Microservice 1        │   │    Microservice N      │
│    (Parking Service)       │   │   (Analytics Service)  │
└─────────────┬──────────────┘   └─────────┬──────────────┘
              │                             │
┌─────────────▼─────────────────────────────▼──────────────────────────────────┐
│                          Event Bus (Kafka)                                   │
└─────────────┬─────────────────────────────┬──────────────────────────────────┘
              │                             │
┌─────────────▼──────────────┐   ┌─────────▼──────────────┐
│      Primary Database      │   │     Cache Layer        │
│    (PostgreSQL+PostGIS)    │   │      (Redis)           │
└────────────────────────────┘   └────────────────────────┘
```

### Microservices Architecture

#### 1. User Service
- **Responsibilities**: Authentication, user management, profiles
- **Technology**: FastAPI + PostgreSQL
- **Scaling**: Stateless, horizontally scalable
- **Data**: User accounts, preferences, authentication tokens

#### 2. Parking Service
- **Responsibilities**: Parking lot management, spot availability, spatial queries
- **Technology**: FastAPI + PostgreSQL + PostGIS
- **Scaling**: Read replicas for spatial queries
- **Data**: Parking lots, spots, real-time availability

#### 3. Reservation Service
- **Responsibilities**: Booking logic, conflict detection, reservation lifecycle
- **Technology**: FastAPI + PostgreSQL with ACID transactions
- **Scaling**: Database sharding by geographical region
- **Data**: Reservations, booking history, conflicts

#### 4. Payment Service
- **Responsibilities**: Payment processing, billing, refunds
- **Technology**: FastAPI + Stripe API + PostgreSQL
- **Scaling**: PCI DSS compliant isolated service
- **Data**: Payment records, billing information

#### 5. Analytics Service
- **Responsibilities**: Usage analytics, reporting, business intelligence
- **Technology**: FastAPI + Elasticsearch + Redis
- **Scaling**: Time-series data partitioning
- **Data**: Usage metrics, occupancy patterns, revenue analytics

#### 6. Notification Service
- **Responsibilities**: Real-time notifications, WebSocket connections
- **Technology**: FastAPI + WebSockets + Redis Pub/Sub
- **Scaling**: Sticky sessions with Redis for WebSocket state
- **Data**: User notifications, real-time updates

### Event-Driven Architecture (CQRS)

```
┌─────────────┐    Command    ┌─────────────┐    Event     ┌─────────────┐
│   Frontend  │──────────────►│   Service   │─────────────►│ Event Store │
└─────────────┘               └─────────────┘              └─────────────┘
                                     │                            │
                                     │                            │
                              ┌─────────────┐              ┌─────────────┐
                              │  Write DB   │              │ Event Bus   │
                              │(PostgreSQL) │              │  (Kafka)    │
                              └─────────────┘              └─────────────┘
                                                                   │
                                                            ┌─────────────┐
                                                            │   Read DB   │
                                                            │(Elasticsearch)│
                                                            └─────────────┘
```

**Key Events:**
- `ParkingSpotBooked`
- `ParkingSpotReleased`
- `PaymentProcessed`
- `UserRegistered`
- `ReservationCancelled`

## Database Design

### PostgreSQL Schema Design

#### Core Tables

```sql
-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Parking lots with spatial data
CREATE TABLE parking_lots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    address TEXT NOT NULL,
    location GEOGRAPHY(POINT, 4326) NOT NULL, -- PostGIS spatial column
    total_spots INTEGER NOT NULL,
    hourly_rate DECIMAL(10,2) NOT NULL,
    operator_id UUID REFERENCES users(id),
    amenities JSONB DEFAULT '{}',
    operating_hours JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Individual parking spots
CREATE TABLE parking_spots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parking_lot_id UUID REFERENCES parking_lots(id) ON DELETE CASCADE,
    spot_number VARCHAR(10) NOT NULL,
    spot_type VARCHAR(20) DEFAULT 'regular', -- regular, disabled, ev, compact
    is_available BOOLEAN DEFAULT true,
    sensors JSONB DEFAULT '{}', -- IoT sensor data
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(parking_lot_id, spot_number)
);

-- Reservations with conflict prevention
CREATE TABLE reservations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) NOT NULL,
    parking_spot_id UUID REFERENCES parking_spots(id) NOT NULL,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(20) DEFAULT 'active', -- active, completed, cancelled
    total_cost DECIMAL(10,2) NOT NULL,
    payment_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    -- Prevent overlapping reservations
    EXCLUDE USING gist (
        parking_spot_id WITH =,
        tstzrange(start_time, end_time) WITH &&
    ) WHERE (status = 'active')
);

-- Payment records
CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reservation_id UUID REFERENCES reservations(id),
    user_id UUID REFERENCES users(id) NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    stripe_payment_intent_id VARCHAR(255),
    status VARCHAR(20) DEFAULT 'pending', -- pending, completed, failed, refunded
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### Indexing Strategy

```sql
-- Spatial index for location-based queries
CREATE INDEX idx_parking_lots_location ON parking_lots USING GIST (location);

-- Performance indexes
CREATE INDEX idx_reservations_user_id ON reservations(user_id);
CREATE INDEX idx_reservations_spot_time ON reservations(parking_spot_id, start_time, end_time);
CREATE INDEX idx_parking_spots_lot_available ON parking_spots(parking_lot_id, is_available);
CREATE INDEX idx_payments_user_status ON payments(user_id, status);

-- Composite indexes for common queries
CREATE INDEX idx_reservations_active_time ON reservations(status, start_time) WHERE status = 'active';
```

### Data Partitioning Strategy

#### Time-based Partitioning (Reservations)
```sql
-- Partition reservations by month for performance
CREATE TABLE reservations_2025_01 PARTITION OF reservations
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

CREATE TABLE reservations_2025_02 PARTITION OF reservations
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');
```

#### Geographic Partitioning (Parking Lots)
```sql
-- Partition by city/region for global scaling
CREATE TABLE parking_lots_sf PARTITION OF parking_lots
    FOR VALUES WITH (city = 'San Francisco');

CREATE TABLE parking_lots_ny PARTITION OF parking_lots
    FOR VALUES WITH (city = 'New York');
```

## API Design

### RESTful API Endpoints

#### Authentication Endpoints
```yaml
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/refresh
POST /api/v1/auth/logout
```

#### Parking Management
```yaml
GET /api/v1/parking-lots?lat={lat}&lng={lng}&radius={radius}
GET /api/v1/parking-lots/{id}
GET /api/v1/parking-lots/{id}/spots
POST /api/v1/parking-lots/{id}/spots/{spot_id}/reserve
```

#### Reservation Management
```yaml
GET /api/v1/reservations
POST /api/v1/reservations
GET /api/v1/reservations/{id}
PUT /api/v1/reservations/{id}
DELETE /api/v1/reservations/{id}
```

### GraphQL Schema (Future Enhancement)

```graphql
type ParkingLot {
  id: ID!
  name: String!
  location: Location!
  spots: [ParkingSpot!]!
  hourlyRate: Float!
  availability: Int!
  distance: Float # Calculated field
}

type Query {
  nearbyParkingLots(
    location: LocationInput!
    radius: Float = 1000
    filters: ParkingFilters
  ): [ParkingLot!]!
  
  myReservations(
    status: ReservationStatus
    limit: Int = 20
    offset: Int = 0
  ): [Reservation!]!
}

type Mutation {
  createReservation(input: CreateReservationInput!): Reservation!
  cancelReservation(id: ID!): Reservation!
}
```

### API Performance Optimizations

#### Caching Strategy
```python
# Redis caching for frequently accessed data
@cache(expire=300)  # 5 minutes
async def get_parking_lot_availability(lot_id: str):
    return await db.execute(availability_query)

# Cache invalidation on updates
async def update_spot_availability(spot_id: str, available: bool):
    await db.execute(update_query)
    await cache.delete(f"lot_availability:{lot_id}")
```

#### Response Optimization
```python
# Pagination for large datasets
class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool

# Efficient spatial queries with PostGIS
SELECT pl.*, ST_Distance(pl.location, ST_Point(lng, lat)) as distance
FROM parking_lots pl
WHERE ST_DWithin(pl.location, ST_Point(lng, lat), radius)
ORDER BY distance
LIMIT 20;
```

## Real-time System

### WebSocket Architecture

```python
# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_locations: Dict[str, tuple] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
    
    async def send_location_updates(self, location: tuple, radius: float):
        # Send updates to users in proximity
        nearby_users = self.get_nearby_users(location, radius)
        for user_id in nearby_users:
            await self.send_personal_message(
                {"type": "availability_update", "data": updates},
                user_id
            )
```

### Event Streaming with Kafka

```python
# Event producer
class EventProducer:
    async def publish_spot_update(self, spot_id: str, available: bool):
        event = {
            "event_type": "spot_availability_changed",
            "spot_id": spot_id,
            "available": available,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.kafka_producer.send("parking_events", event)

# Event consumer
class AvailabilityConsumer:
    async def handle_spot_update(self, event: dict):
        # Update cache
        await redis.set(f"spot:{event['spot_id']}", event['available'])
        
        # Notify connected users
        await connection_manager.broadcast_availability_update(event)
```

## Scalability & Performance

### Horizontal Scaling Strategy

#### Database Scaling
```yaml
# Read Replicas Configuration
Primary Database:
  - Write operations
  - Critical reads (reservations, payments)
  
Read Replicas (3):
  - Parking lot searches
  - Analytics queries
  - User profile reads

# Connection Pooling
Database Pool Configuration:
  min_connections: 10
  max_connections: 100
  pool_recycle: 3600
  pool_pre_ping: true
```

#### Application Scaling
```yaml
# Kubernetes Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: parking-service
spec:
  replicas: 5
  template:
    spec:
      containers:
      - name: parking-service
        image: parking-service:latest
        resources:
          requests:
            memory: "256Mi"
            cpu: "200m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
```

### Caching Strategy

#### Multi-Level Caching
```python
# L1 Cache: Application Memory (In-Process)
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_parking_lot_static_data(lot_id: str):
    return parking_lot_data

# L2 Cache: Redis (Distributed)
class CacheService:
    async def get_availability(self, lot_id: str):
        # Try L2 cache first
        cached = await self.redis.get(f"availability:{lot_id}")
        if cached:
            return json.loads(cached)
        
        # Fall back to database
        data = await self.db.get_availability(lot_id)
        await self.redis.setex(f"availability:{lot_id}", 300, json.dumps(data))
        return data

# L3 Cache: CDN (Static Assets)
# Serve static maps, images via CloudFront
```

### Performance Optimizations

#### Database Query Optimization
```sql
-- Optimized availability query with spatial index
EXPLAIN ANALYZE
SELECT 
    pl.id,
    pl.name,
    COUNT(ps.id) as total_spots,
    COUNT(ps.id) FILTER (WHERE ps.is_available = true) as available_spots,
    ST_Distance(pl.location, ST_Point($1, $2)) as distance
FROM parking_lots pl
JOIN parking_spots ps ON pl.id = ps.parking_lot_id
WHERE ST_DWithin(pl.location, ST_Point($1, $2), $3)
GROUP BY pl.id, pl.location
ORDER BY distance
LIMIT 20;

-- Result: Index Scan using idx_parking_lots_location (cost=0.41..8.43)
```

#### Connection Management
```python
# Async connection pooling
class DatabaseManager:
    def __init__(self):
        self.pool = None
    
    async def init_pool(self):
        self.pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=10,
            max_size=100,
            command_timeout=60,
            server_settings={
                'jit': 'off',  # Disable JIT for faster connection
                'statement_timeout': '30s'
            }
        )
    
    async def execute_query(self, query: str, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)
```

## Security Design

### Authentication & Authorization

#### JWT Token Strategy
```python
# Token structure
{
  "sub": "user_id",
  "email": "user@example.com",
  "roles": ["user"],
  "exp": 1640995200,
  "iat": 1640908800,
  "jti": "unique_token_id"
}

# Token rotation
class TokenService:
    async def refresh_token(self, refresh_token: str):
        # Validate refresh token
        payload = self.verify_token(refresh_token)
        
        # Issue new access token
        new_access_token = self.create_access_token(payload['sub'])
        
        # Rotate refresh token
        new_refresh_token = self.create_refresh_token(payload['sub'])
        
        # Blacklist old refresh token
        await self.blacklist_token(refresh_token)
        
        return new_access_token, new_refresh_token
```

#### Role-Based Access Control
```python
class RoleChecker:
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles
    
    def __call__(self, current_user: User = Depends(get_current_user)):
        if not any(role in current_user.roles for role in self.allowed_roles):
            raise HTTPException(
                status_code=403,
                detail="Operation not permitted"
            )
        return current_user

# Usage
@app.post("/admin/parking-lots")
async def create_parking_lot(
    lot_data: ParkingLotCreate,
    current_user: User = Depends(RoleChecker(["admin", "operator"]))
):
    return await parking_service.create_lot(lot_data)
```

### Data Security

#### Encryption Strategy
```python
# Field-level encryption for sensitive data
class EncryptedField:
    def __init__(self, field_name: str):
        self.field_name = field_name
        self.cipher = Fernet(settings.ENCRYPTION_KEY)
    
    def encrypt(self, value: str) -> str:
        return self.cipher.encrypt(value.encode()).decode()
    
    def decrypt(self, encrypted_value: str) -> str:
        return self.cipher.decrypt(encrypted_value.encode()).decode()

# Database encryption at rest
# PostgreSQL with transparent data encryption (TDE)
```

#### PCI DSS Compliance
```python
# Payment data handling
class PaymentProcessor:
    def __init__(self):
        self.stripe = stripe.PaymentIntent
    
    async def process_payment(self, amount: int, payment_method: str):
        # Never store credit card data
        # Use Stripe's secure vault
        intent = await self.stripe.create(
            amount=amount,
            currency='usd',
            payment_method=payment_method,
            confirmation_method='manual',
            confirm=True
        )
        
        # Store only payment intent ID
        return intent.id
```

### Network Security

#### API Rate Limiting
```python
# Redis-based rate limiting
class RateLimiter:
    def __init__(self, requests: int, window: int):
        self.requests = requests
        self.window = window
    
    async def check_rate_limit(self, key: str) -> bool:
        current = await redis.get(key)
        if current is None:
            await redis.setex(key, self.window, 1)
            return True
        
        if int(current) >= self.requests:
            return False
        
        await redis.incr(key)
        return True

# Usage
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host
    if not await rate_limiter.check_rate_limit(f"rate_limit:{client_ip}"):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    return await call_next(request)
```

## Deployment Architecture

### Containerization Strategy

#### Docker Configuration
```dockerfile
# Multi-stage build for optimization
FROM python:3.11-slim as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-slim

# Security: Non-root user
RUN adduser --disabled-password --gecos '' appuser

WORKDIR /app
COPY --from=builder /root/.local /home/appuser/.local
COPY . .

USER appuser
ENV PATH=/home/appuser/.local/bin:$PATH

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Docker Compose for Development
```yaml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/parking
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis
      - kafka

  db:
    image: postgis/postgis:13-3.1
    environment:
      POSTGRES_DB: parking
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  kafka:
    image: confluentinc/cp-kafka:latest
    environment:
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
    ports:
      - "9092:9092"
```

### Kubernetes Deployment

#### Production Deployment
```yaml
# Namespace
apiVersion: v1
kind: Namespace
metadata:
  name: parking-system

---
# ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: parking-config
  namespace: parking-system
data:
  ENVIRONMENT: "production"
  LOG_LEVEL: "INFO"

---
# Secret
apiVersion: v1
kind: Secret
metadata:
  name: parking-secrets
  namespace: parking-system
type: Opaque
data:
  DATABASE_URL: <base64-encoded-url>
  REDIS_URL: <base64-encoded-url>
  JWT_SECRET: <base64-encoded-secret>

---
# Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: parking-api
  namespace: parking-system
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
      - name: parking-api
        image: parking-api:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: parking-config
        - secretRef:
            name: parking-secrets
        resources:
          requests:
            memory: "256Mi"
            cpu: "200m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5

---
# Service
apiVersion: v1
kind: Service
metadata:
  name: parking-api-service
  namespace: parking-system
spec:
  selector:
    app: parking-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: ClusterIP

---
# Ingress
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: parking-ingress
  namespace: parking-system
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - api.parkingsystem.com
    secretName: parking-tls
  rules:
  - host: api.parkingsystem.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: parking-api-service
            port:
              number: 80
```

## Monitoring & Observability

### Metrics Collection

#### Prometheus Configuration
```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'parking-api'
    static_configs:
      - targets: ['parking-api:8000']
    metrics_path: '/metrics'
    scrape_interval: 5s

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
```

#### Application Metrics
```python
from prometheus_client import Counter, Histogram, Gauge

# Custom metrics
REQUEST_COUNT = Counter(
    'parking_api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'parking_api_request_duration_seconds',
    'Request duration',
    ['method', 'endpoint']
)

ACTIVE_RESERVATIONS = Gauge(
    'parking_active_reservations',
    'Currently active reservations'
)

# Middleware for automatic metrics
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    REQUEST_DURATION.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(time.time() - start_time)
    
    return response
```

### Logging Strategy

#### Structured Logging
```python
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Usage
async def create_reservation(reservation_data: ReservationCreate):
    logger.info(
        "Creating reservation",
        user_id=reservation_data.user_id,
        parking_spot_id=reservation_data.parking_spot_id,
        start_time=reservation_data.start_time
    )
    
    try:
        reservation = await reservation_service.create(reservation_data)
        logger.info(
            "Reservation created successfully",
            reservation_id=reservation.id,
            user_id=reservation_data.user_id
        )
        return reservation
    except Exception as e:
        logger.error(
            "Failed to create reservation",
            error=str(e),
            user_id=reservation_data.user_id,
            exc_info=True
        )
        raise
```

### Alerting Configuration

#### Grafana Alerts
```yaml
# Alert Rules
groups:
  - name: parking-api-alerts
    rules:
      - alert: HighErrorRate
        expr: rate(parking_api_requests_total{status=~"5.."}[5m]) > 0.1
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} per second"

      - alert: HighResponseTime
        expr: histogram_quantile(0.95, rate(parking_api_request_duration_seconds_bucket[5m])) > 0.5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High response time detected"
          description: "95th percentile response time is {{ $value }}s"

      - alert: DatabaseConnectionFailure
        expr: up{job="postgres"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Database connection failure"
          description: "PostgreSQL database is down"
```

## Trade-offs & Decisions

### Architectural Decisions

#### 1. PostgreSQL vs NoSQL
**Decision**: PostgreSQL with PostGIS
**Reasoning**:
- ✅ ACID compliance for financial transactions
- ✅ Excellent spatial query support with PostGIS
- ✅ Strong consistency for reservation conflicts
- ✅ Rich query capabilities for analytics
- ❌ Horizontal scaling complexity

#### 2. Microservices vs Monolith
**Decision**: Microservices architecture
**Reasoning**:
- ✅ Independent scaling of services
- ✅ Technology diversity (different languages per service)
- ✅ Team autonomy and parallel development
- ✅ Fault isolation
- ❌ Network latency between services
- ❌ Distributed system complexity

#### 3. Event Sourcing vs Traditional CRUD
**Decision**: Hybrid approach (CQRS with traditional state)
**Reasoning**:
- ✅ Event-driven real-time updates
- ✅ Audit trail for business events
- ✅ Eventual consistency where appropriate
- ✅ Simpler implementation than full event sourcing
- ❌ Additional complexity over pure CRUD

#### 4. Synchronous vs Asynchronous Processing
**Decision**: Async where possible, sync for critical paths
**Reasoning**:
- ✅ Higher throughput with async I/O
- ✅ Better resource utilization
- ✅ Non-blocking operations
- ❌ More complex error handling
- ❌ Debugging complexity

### Performance Trade-offs

#### 1. Consistency vs Availability
- **Strong consistency**: Reservation conflicts, payments
- **Eventual consistency**: Analytics, availability updates
- **Reasoning**: CAP theorem - chose consistency for critical operations

#### 2. Normalization vs Denormalization
- **Normalized**: Transactional data (reservations, payments)
- **Denormalized**: Read-heavy data (parking lot search results)
- **Reasoning**: Balance between data integrity and query performance

#### 3. Real-time vs Batch Processing
- **Real-time**: Availability updates, notifications
- **Batch**: Analytics aggregation, reporting
- **Reasoning**: User experience vs resource efficiency

### Security Trade-offs

#### 1. JWT vs Session-based Authentication
**Decision**: JWT with refresh tokens
**Reasoning**:
- ✅ Stateless authentication (scales better)
- ✅ Cross-service authentication
- ✅ Mobile app friendly
- ❌ Token revocation complexity
- ❌ Payload size limitations

#### 2. Field-level vs Database-level Encryption
**Decision**: Hybrid approach
**Reasoning**:
- **Field-level**: Sensitive PII data
- **Database-level**: General data protection
- **Balance**: Security vs performance impact

### Scalability Trade-offs

#### 1. Vertical vs Horizontal Scaling
**Decision**: Horizontal scaling with stateless services
**Reasoning**:
- ✅ Cost-effective scaling
- ✅ Better fault tolerance
- ✅ Auto-scaling capabilities
- ❌ Session management complexity

#### 2. Read Replicas vs Caching
**Decision**: Both strategies combined
**Reasoning**:
- **Read replicas**: Complex analytical queries
- **Caching**: Frequently accessed simple data
- **Result**: Optimal performance for different use cases

## Future Enhancements

### Phase 2 Features
1. **Machine Learning Integration**
   - Demand prediction algorithms
   - Dynamic pricing optimization
   - Route optimization for users

2. **IoT Integration**
   - Smart sensor data processing
   - Automatic spot detection
   - Environmental monitoring

3. **Mobile Applications**
   - Native iOS/Android apps
   - Offline capabilities
   - Push notifications

4. **Advanced Analytics**
   - Real-time dashboards
   - Predictive analytics
   - Business intelligence reports

### Scaling Considerations
1. **Multi-region Deployment**
   - Geographic data distribution
   - Cross-region replication
   - Latency optimization

2. **Service Mesh Implementation**
   - Istio for service communication
   - Advanced traffic management
   - Enhanced security policies

3. **Event Streaming Enhancement**
   - Kafka Streams for complex event processing
   - Real-time analytics pipelines
   - Event replay capabilities

---

This system design document provides a comprehensive overview of the Parking Management System architecture, covering all major components, design decisions, and trade-offs. The design prioritizes performance, scalability, and maintainability while ensuring strong consistency for critical operations and high availability for user-facing features.
