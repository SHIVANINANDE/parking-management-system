# Architectural Decision Records (ADR)

## ADR-001: Technology Stack Selection

**Date:** 2024-01-10  
**Status:** Accepted  
**Decision Makers:** Technical Team  

### Context
We need to select a technology stack for building a comprehensive parking management system that handles real-time data, spatial operations, payments, and high concurrency.

### Decision
We will use:
- **Backend**: FastAPI with Python 3.9+
- **Database**: PostgreSQL with PostGIS extension
- **Frontend**: React 18 with TypeScript
- **Caching**: Redis
- **Search**: Elasticsearch
- **Message Queue**: Apache Kafka
- **Containerization**: Docker

### Rationale
- **FastAPI**: Excellent async support, automatic API documentation, type hints
- **PostgreSQL + PostGIS**: Robust spatial data support, ACID compliance
- **React + TypeScript**: Component reusability, type safety, large ecosystem
- **Redis**: High-performance caching and session storage
- **Elasticsearch**: Full-text search and analytics capabilities
- **Kafka**: Reliable message streaming for real-time updates

### Consequences
- **Positive**: High performance, scalability, modern development experience
- **Negative**: Learning curve for team members, complex deployment setup

---

## ADR-002: Database Architecture - CQRS Pattern

**Date:** 2024-01-12  
**Status:** Accepted  
**Decision Makers:** Backend Team  

### Context
The system needs to handle both transactional operations (reservations, payments) and analytical queries (occupancy analytics, reporting) efficiently.

### Decision
Implement Command Query Responsibility Segregation (CQRS) pattern with event sourcing for critical operations.

### Architecture
```
Write Side (Commands):
├── FastAPI endpoints
├── Command handlers
├── Domain models
├── PostgreSQL (transactional)
└── Event publishing (Kafka)

Read Side (Queries):
├── Event handlers
├── Read models
├── Elasticsearch (analytics)
├── Redis (caching)
└── Materialized views
```

### Rationale
- **Separation of Concerns**: Different optimization strategies for reads vs writes
- **Scalability**: Independent scaling of read and write workloads
- **Performance**: Optimized read models for specific query patterns
- **Auditability**: Complete event history for compliance

### Implementation
```python
# Command Side
class CreateReservationCommand:
    parking_lot_id: UUID
    user_id: UUID
    start_time: datetime
    end_time: datetime

class ReservationCommandHandler:
    async def handle(self, command: CreateReservationCommand):
        # Business logic
        reservation = Reservation.create(...)
        await self.repository.save(reservation)
        
        # Publish event
        event = ReservationCreatedEvent(...)
        await self.event_bus.publish(event)

# Query Side
class ReservationProjection:
    async def on_reservation_created(self, event: ReservationCreatedEvent):
        # Update read model
        await self.elasticsearch.index(...)
        await self.cache.invalidate(...)
```

### Consequences
- **Positive**: Better performance, scalability, data consistency
- **Negative**: Increased complexity, eventual consistency challenges

---

## ADR-003: Real-time Communication Strategy

**Date:** 2024-01-15  
**Status:** Accepted  
**Decision Makers:** Full Stack Team  

### Context
The system requires real-time updates for parking availability, reservation status, and notifications.

### Decision
Use a hybrid approach:
1. **WebSockets** for real-time UI updates
2. **Server-Sent Events (SSE)** for notifications
3. **Kafka** for internal service communication

### Architecture
```
Client (React) 
    ↓ WebSocket
WebSocket Manager (FastAPI)
    ↓ Subscribe
Kafka Consumer
    ↓ Events
Redis Pub/Sub
    ↓ Broadcast
Multiple WebSocket connections
```

### Implementation
```python
# WebSocket Manager
class ParkingWebSocketManager:
    def __init__(self):
        self.connections: Dict[str, WebSocket] = {}
        self.subscriptions: Dict[str, Set[str]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.connections[user_id] = websocket
    
    async def broadcast_parking_update(self, lot_id: str, data: dict):
        interested_users = self.get_subscribers(lot_id)
        for user_id in interested_users:
            if user_id in self.connections:
                await self.connections[user_id].send_json(data)

# Kafka Event Handler
class ParkingEventHandler:
    async def on_spot_status_changed(self, event: SpotStatusChangedEvent):
        await self.websocket_manager.broadcast_parking_update(
            event.parking_lot_id,
            {
                "type": "spot_availability",
                "data": event.to_dict()
            }
        )
```

### Rationale
- **WebSockets**: Bi-directional, low latency for interactive features
- **SSE**: Simple, unidirectional for notifications
- **Kafka**: Reliable, scalable for service-to-service communication

### Consequences
- **Positive**: Excellent user experience, scalable real-time features
- **Negative**: Complex connection management, testing challenges

---

## ADR-004: Spatial Data Processing

**Date:** 2024-01-18  
**Status:** Accepted  
**Decision Makers:** Backend Team  

### Context
The system needs efficient spatial operations for location-based search, route optimization, and geofencing.

### Decision
Use PostgreSQL with PostGIS extension as the primary spatial database, complemented by specialized libraries for advanced operations.

### Architecture
```
Spatial Stack:
├── PostGIS (primary spatial database)
├── Shapely (geometric operations)
├── GeoPy (geocoding/reverse geocoding)
├── H3 (hexagonal spatial indexing)
├── NetworkX (route optimization)
└── Folium (map visualization)
```

### Implementation
```python
# Spatial Service
class SpatialService:
    async def find_nearby_parking_lots(
        self, 
        lat: float, 
        lng: float, 
        radius_km: float = 5.0
    ) -> List[ParkingLot]:
        query = """
        SELECT p.*, 
               ST_Distance(
                   ST_GeomFromText('POINT(%s %s)', 4326),
                   p.location
               ) as distance
        FROM parking_lots p
        WHERE ST_DWithin(
            ST_GeomFromText('POINT(%s %s)', 4326),
            p.location,
            %s
        )
        ORDER BY distance
        """
        
        return await self.db.fetch_all(
            query, lng, lat, lng, lat, radius_km * 1000
        )
    
    def create_geofence(self, center: Point, radius_m: float) -> Polygon:
        """Create circular geofence using H3 for efficient checking"""
        h3_index = h3.geo_to_h3(center.lat, center.lng, resolution=9)
        return h3.h3_to_geo_boundary(h3_index)
```

### Rationale
- **PostGIS**: Industry standard, excellent performance, SQL integration
- **H3**: Efficient spatial indexing for large-scale operations
- **Shapely**: Pythonic geometric operations
- **Multiple libraries**: Specialized tools for specific use cases

### Consequences
- **Positive**: High performance spatial operations, standard compliance
- **Negative**: Complex setup, requires spatial expertise

---

## ADR-005: Authentication and Authorization

**Date:** 2024-01-20  
**Status:** Accepted  
**Decision Makers:** Security Team  

### Context
The system needs secure authentication with role-based access control for users, parking lot operators, and administrators.

### Decision
Implement JWT-based authentication with refresh tokens and role-based authorization.

### Architecture
```
Authentication Flow:
├── User credentials → Login endpoint
├── JWT access token (15 min expiry)
├── JWT refresh token (7 days expiry)
├── Role-based permissions
└── Token refresh mechanism

Authorization Levels:
├── Guest: View parking lots, pricing
├── User: Make reservations, manage profile
├── Operator: Manage specific parking lots
└── Admin: System administration
```

### Implementation
```python
# Authentication Service
class AuthService:
    def create_tokens(self, user: User) -> TokenPair:
        access_payload = {
            "sub": str(user.id),
            "email": user.email,
            "roles": [role.name for role in user.roles],
            "exp": datetime.utcnow() + timedelta(minutes=15)
        }
        
        refresh_payload = {
            "sub": str(user.id),
            "type": "refresh",
            "exp": datetime.utcnow() + timedelta(days=7)
        }
        
        return TokenPair(
            access_token=jwt.encode(access_payload, SECRET_KEY),
            refresh_token=jwt.encode(refresh_payload, SECRET_KEY)
        )

# Authorization Decorator
def require_role(required_role: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = get_current_user()
            if not current_user.has_role(required_role):
                raise HTTPException(403, "Insufficient permissions")
            return await func(*args, **kwargs)
        return wrapper
    return decorator

@require_role("admin")
async def delete_parking_lot(lot_id: UUID):
    pass
```

### Rationale
- **JWT**: Stateless, scalable, standard format
- **Refresh tokens**: Security without constant re-authentication
- **Role-based**: Flexible permission system
- **Short-lived access tokens**: Minimize security window

### Consequences
- **Positive**: Secure, scalable, industry standard
- **Negative**: Token management complexity, logout challenges

---

## ADR-006: Testing Strategy

**Date:** 2024-01-22  
**Status:** Accepted  
**Decision Makers:** QA Team  

### Context
Need comprehensive testing strategy to ensure system reliability and maintainability.

### Decision
Implement multi-layered testing approach with automated CI/CD integration.

### Testing Pyramid
```
├── Unit Tests (pytest) - 70%
│   ├── Business logic
│   ├── Data models
│   └── Utility functions
├── Integration Tests (pytest + httpx) - 20%
│   ├── API endpoints
│   ├── Database operations
│   └── External service mocks
├── E2E Tests (React Testing Library) - 8%
│   ├── User workflows
│   ├── Critical paths
│   └── Cross-browser testing
└── Load Tests (Locust) - 2%
    ├── Performance benchmarks
    ├── Stress testing
    └── Scalability validation
```

### Implementation
```python
# Unit Test Example
@pytest.mark.asyncio
async def test_reservation_creation():
    # Arrange
    user = UserFactory()
    parking_lot = ParkingLotFactory()
    spot = ParkingSpotFactory(parking_lot=parking_lot)
    
    # Act
    reservation = await ReservationService.create_reservation(
        user_id=user.id,
        spot_id=spot.id,
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(hours=2)
    )
    
    # Assert
    assert reservation.status == ReservationStatus.CONFIRMED
    assert reservation.total_cost == 25.0

# Integration Test Example
@pytest.mark.integration
async def test_parking_search_api(client: AsyncClient):
    response = await client.get(
        "/parking-lots",
        params={"lat": 37.7749, "lng": -122.4194, "radius": 5}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) > 0
```

### Testing Standards
- **Coverage Target**: 90%+ for business logic
- **Test Data**: Factory pattern with Faker
- **Isolation**: Clean database for each test
- **Mocking**: External services mocked
- **Performance**: Load tests in CI/CD

### Consequences
- **Positive**: High confidence, early bug detection, maintainable code
- **Negative**: Initial setup time, ongoing maintenance effort

---

## ADR-007: Error Handling and Monitoring

**Date:** 2024-01-25  
**Status:** Accepted  
**Decision Makers:** DevOps Team  

### Context
Need comprehensive error handling and monitoring for production reliability.

### Decision
Implement structured logging, error tracking, and observability stack.

### Architecture
```
Observability Stack:
├── Structured Logging (structlog)
├── Error Tracking (Sentry)
├── Metrics (Prometheus)
├── Tracing (OpenTelemetry)
└── Dashboards (Grafana)
```

### Implementation
```python
# Structured Logging
import structlog

logger = structlog.get_logger()

class ReservationService:
    async def create_reservation(self, data: ReservationCreate):
        logger.info(
            "Creating reservation",
            user_id=data.user_id,
            parking_lot_id=data.parking_lot_id,
            start_time=data.start_time
        )
        
        try:
            reservation = await self._process_reservation(data)
            logger.info(
                "Reservation created successfully",
                reservation_id=reservation.id,
                total_cost=reservation.total_cost
            )
            return reservation
            
        except InsufficientFundsError as e:
            logger.warning(
                "Reservation failed: insufficient funds",
                user_id=data.user_id,
                required_amount=e.required_amount,
                available_balance=e.available_balance
            )
            raise
        except Exception as e:
            logger.error(
                "Unexpected error in reservation creation",
                user_id=data.user_id,
                error=str(e),
                exc_info=True
            )
            raise

# Error Response Handler
@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid input data",
                "details": exc.errors()
            },
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url.path)
        }
    )
```

### Monitoring Metrics
- **Business Metrics**: Reservations/hour, revenue, conversion rate
- **Technical Metrics**: Response time, error rate, throughput
- **Infrastructure Metrics**: CPU, memory, disk, network

### Consequences
- **Positive**: Proactive issue detection, faster debugging
- **Negative**: Additional infrastructure, monitoring overhead

---

## ADR-008: Payment Processing Architecture

**Date:** 2024-01-28  
**Status:** Accepted  
**Decision Makers:** Finance & Tech Team  

### Context
Need secure, PCI-compliant payment processing with multiple payment methods support.

### Decision
Use Stripe as primary payment processor with tokenization for card storage.

### Architecture
```
Payment Flow:
├── Frontend: Stripe Elements (PCI compliance)
├── Backend: Stripe API integration
├── Webhook: Payment confirmation
├── Database: Payment metadata only
└── Audit: Complete payment trail
```

### Implementation
```python
# Payment Service
class PaymentService:
    def __init__(self):
        self.stripe = stripe
        self.stripe.api_key = settings.STRIPE_SECRET_KEY
    
    async def create_payment_intent(
        self, 
        amount: int, 
        currency: str = "usd",
        metadata: dict = None
    ) -> PaymentIntent:
        intent = await self.stripe.PaymentIntent.create_async(
            amount=amount,
            currency=currency,
            metadata=metadata,
            automatic_payment_methods={"enabled": True}
        )
        
        # Store payment record
        payment = PaymentRecord(
            stripe_payment_intent_id=intent.id,
            amount=amount,
            currency=currency,
            status=PaymentStatus.PENDING,
            metadata=metadata
        )
        await self.db.save(payment)
        
        return intent
    
    async def handle_webhook(self, payload: str, signature: str):
        event = stripe.Webhook.construct_event(
            payload, signature, settings.STRIPE_WEBHOOK_SECRET
        )
        
        if event.type == "payment_intent.succeeded":
            await self._handle_payment_success(event.data.object)
        elif event.type == "payment_intent.payment_failed":
            await self._handle_payment_failure(event.data.object)
```

### Security Measures
- **PCI Compliance**: No card data stored locally
- **Webhook Verification**: Signed webhook validation
- **Idempotency**: Prevent duplicate payments
- **Audit Trail**: Complete payment history

### Consequences
- **Positive**: PCI compliant, reliable, multiple payment methods
- **Negative**: Third-party dependency, transaction fees

---

## Decision Summary

| ADR | Decision | Status | Impact |
|-----|----------|--------|---------|
| 001 | Technology Stack | Accepted | High |
| 002 | CQRS Pattern | Accepted | High |
| 003 | Real-time Communication | Accepted | Medium |
| 004 | Spatial Data Processing | Accepted | High |
| 005 | Authentication/Authorization | Accepted | High |
| 006 | Testing Strategy | Accepted | Medium |
| 007 | Error Handling/Monitoring | Accepted | Medium |
| 008 | Payment Processing | Accepted | High |

## Future Decisions

Upcoming architectural decisions to be made:
- **Mobile App Architecture**: Native vs React Native vs Flutter
- **Microservices Migration**: Monolith to microservices transition plan
- **Multi-tenancy**: Supporting multiple parking operators
- **Machine Learning Integration**: Demand prediction and pricing optimization
