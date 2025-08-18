"""
Test configuration and fixtures
"""
import pytest
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.database import Base, get_async_session
from app.core.config import settings

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def async_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with TestingSessionLocal() as session:
        yield session
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

import pytest
import asyncio
from typing import AsyncGenerator, Generator
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.database import Base, get_db
from app.core.config import settings
from app.models.user import User
from app.models.parking_lot import ParkingLot
from app.models.parking_spot import ParkingSpot
from app.models.vehicle import Vehicle
from app.models.reservation import Reservation

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False}
)

# Create test session factory
TestSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async with TestSessionLocal() as session:
        yield session
        
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create a test client."""
    def override_get_db():
        return db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture
async def async_client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        id="test-user-id",
        email="test@example.com",
        hashed_password="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "secret"
        first_name="Test",
        last_name="User",
        phone="1234567890",
        is_active=True,
        is_verified=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_admin_user(db_session: AsyncSession) -> User:
    """Create a test admin user."""
    user = User(
        id="test-admin-id",
        email="admin@example.com",
        hashed_password="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "secret"
        first_name="Admin",
        last_name="User",
        phone="9876543210",
        is_active=True,
        is_verified=True,
        role="admin"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_parking_lot(db_session: AsyncSession) -> ParkingLot:
    """Create a test parking lot."""
    parking_lot = ParkingLot(
        id="test-lot-id",
        name="Test Parking Lot",
        address="123 Test Street",
        latitude=37.7749,
        longitude=-122.4194,
        total_spots=100,
        available_spots=100,
        hourly_rate=5.0,
        is_active=True
    )
    db_session.add(parking_lot)
    await db_session.commit()
    await db_session.refresh(parking_lot)
    return parking_lot


@pytest.fixture
async def test_parking_spot(db_session: AsyncSession, test_parking_lot: ParkingLot) -> ParkingSpot:
    """Create a test parking spot."""
    spot = ParkingSpot(
        id="test-spot-id",
        parking_lot_id=test_parking_lot.id,
        spot_number="A01",
        spot_type="regular",
        is_available=True,
        is_active=True
    )
    db_session.add(spot)
    await db_session.commit()
    await db_session.refresh(spot)
    return spot


@pytest.fixture
async def test_vehicle(db_session: AsyncSession, test_user: User) -> Vehicle:
    """Create a test vehicle."""
    vehicle = Vehicle(
        id="test-vehicle-id",
        user_id=test_user.id,
        license_plate="TEST123",
        make="Toyota",
        model="Camry",
        color="Blue",
        vehicle_type="sedan"
    )
    db_session.add(vehicle)
    await db_session.commit()
    await db_session.refresh(vehicle)
    return vehicle


@pytest.fixture
async def test_reservation(
    db_session: AsyncSession,
    test_user: User,
    test_parking_spot: ParkingSpot,
    test_vehicle: Vehicle
) -> Reservation:
    """Create a test reservation."""
    from datetime import datetime, timedelta
    
    reservation = Reservation(
        id="test-reservation-id",
        user_id=test_user.id,
        parking_spot_id=test_parking_spot.id,
        vehicle_id=test_vehicle.id,
        start_time=datetime.utcnow(),
        end_time=datetime.utcnow() + timedelta(hours=2),
        status="confirmed",
        total_amount=10.0
    )
    db_session.add(reservation)
    await db_session.commit()
    await db_session.refresh(reservation)
    return reservation


@pytest.fixture
def auth_headers(test_user: User) -> dict:
    """Create authorization headers for testing."""
    from app.core.auth import create_access_token
    token = create_access_token(data={"sub": test_user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers(test_admin_user: User) -> dict:
    """Create admin authorization headers for testing."""
    from app.core.auth import create_access_token
    token = create_access_token(data={"sub": test_admin_user.email})
    return {"Authorization": f"Bearer {token}"}


# Test data factories
class UserFactory:
    @staticmethod
    def build(**kwargs):
        from faker import Faker
        fake = Faker()
        
        defaults = {
            "email": fake.email(),
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "phone": fake.phone_number()[:15],
            "is_active": True,
            "is_verified": True
        }
        defaults.update(kwargs)
        return defaults


class ParkingLotFactory:
    @staticmethod
    def build(**kwargs):
        from faker import Faker
        fake = Faker()
        
        defaults = {
            "name": fake.company(),
            "address": fake.address(),
            "latitude": float(fake.latitude()),
            "longitude": float(fake.longitude()),
            "total_spots": fake.random_int(min=50, max=500),
            "hourly_rate": fake.random.uniform(2.0, 15.0),
            "is_active": True
        }
        defaults.update(kwargs)
        return defaults


class VehicleFactory:
    @staticmethod
    def build(**kwargs):
        from faker import Faker
        fake = Faker()
        
        makes = ["Toyota", "Honda", "Ford", "BMW", "Mercedes", "Audi"]
        colors = ["Black", "White", "Silver", "Blue", "Red", "Gray"]
        types = ["sedan", "suv", "hatchback", "truck", "convertible"]
        
        defaults = {
            "license_plate": fake.license_plate(),
            "make": fake.random_element(makes),
            "model": fake.word().title(),
            "color": fake.random_element(colors),
            "vehicle_type": fake.random_element(types)
        }
        defaults.update(kwargs)
        return defaults

@pytest.fixture
def client() -> TestClient:
    """Create a synchronous test client."""
    return TestClient(app)
