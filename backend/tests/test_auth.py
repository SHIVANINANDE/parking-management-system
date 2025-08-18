"""
Tests for authentication endpoints
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User, UserStatus
from app.services.auth_service import AuthService
from app.schemas.auth import UserCreate

class TestAuthentication:
    """Test authentication endpoints"""
    
    @pytest.mark.asyncio
    async def test_register_user(self, async_client: AsyncClient, async_session: AsyncSession):
        """Test user registration"""
        user_data = {
            "email": "test@example.com",
            "password": "TestPassword123!",
            "confirm_password": "TestPassword123!",
            "first_name": "Test",
            "last_name": "User"
        }
        
        response = await async_client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["first_name"] == user_data["first_name"]
        assert data["status"] == "pending_verification"
    
    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, async_client: AsyncClient, async_session: AsyncSession):
        """Test registration with duplicate email"""
        user_data = {
            "email": "test@example.com",
            "password": "TestPassword123!",
            "confirm_password": "TestPassword123!",
            "first_name": "Test",
            "last_name": "User"
        }
        
        # First registration
        await async_client.post("/api/v1/auth/register", json=user_data)
        
        # Second registration with same email
        response = await async_client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_register_weak_password(self, async_client: AsyncClient):
        """Test registration with weak password"""
        user_data = {
            "email": "test@example.com",
            "password": "weak",
            "confirm_password": "weak",
            "first_name": "Test",
            "last_name": "User"
        }
        
        response = await async_client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_login_success(self, async_client: AsyncClient, async_session: AsyncSession):
        """Test successful login"""
        # Create and verify user
        user_create = UserCreate(
            email="test@example.com",
            password="TestPassword123!",
            confirm_password="TestPassword123!",
            first_name="Test",
            last_name="User"
        )
        user = await AuthService.create_user(async_session, user_create)
        user.status = UserStatus.ACTIVE
        user.is_email_verified = True
        await async_session.commit()
        
        login_data = {
            "email": "test@example.com",
            "password": "TestPassword123!"
        }
        
        response = await async_client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
    
    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, async_client: AsyncClient):
        """Test login with invalid credentials"""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "WrongPassword123!"
        }
        
        response = await async_client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_login_unverified_email(self, async_client: AsyncClient, async_session: AsyncSession):
        """Test login with unverified email"""
        user_create = UserCreate(
            email="test@example.com",
            password="TestPassword123!",
            confirm_password="TestPassword123!",
            first_name="Test",
            last_name="User"
        )
        await AuthService.create_user(async_session, user_create)
        
        login_data = {
            "email": "test@example.com",
            "password": "TestPassword123!"
        }
        
        response = await async_client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 400
        assert "Email verification required" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_get_current_user(self, async_client: AsyncClient, async_session: AsyncSession):
        """Test getting current user info"""
        # Create and verify user
        user_create = UserCreate(
            email="test@example.com",
            password="TestPassword123!",
            confirm_password="TestPassword123!",
            first_name="Test",
            last_name="User"
        )
        user = await AuthService.create_user(async_session, user_create)
        user.status = UserStatus.ACTIVE
        user.is_email_verified = True
        await async_session.commit()
        
        # Login to get token
        login_data = {
            "email": "test@example.com",
            "password": "TestPassword123!"
        }
        login_response = await async_client.post("/api/v1/auth/login", json=login_data)
        token = login_response.json()["access_token"]
        
        # Get user info
        headers = {"Authorization": f"Bearer {token}"}
        response = await async_client.get("/api/v1/auth/me", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["first_name"] == "Test"
    
    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, async_client: AsyncClient):
        """Test getting current user with invalid token"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = await async_client.get("/api/v1/auth/me", headers=headers)
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_change_password(self, async_client: AsyncClient, async_session: AsyncSession):
        """Test password change"""
        # Create and verify user
        user_create = UserCreate(
            email="test@example.com",
            password="TestPassword123!",
            confirm_password="TestPassword123!",
            first_name="Test",
            last_name="User"
        )
        user = await AuthService.create_user(async_session, user_create)
        user.status = UserStatus.ACTIVE
        user.is_email_verified = True
        await async_session.commit()
        
        # Login to get token
        login_data = {
            "email": "test@example.com",
            "password": "TestPassword123!"
        }
        login_response = await async_client.post("/api/v1/auth/login", json=login_data)
        token = login_response.json()["access_token"]
        
        # Change password
        password_data = {
            "current_password": "TestPassword123!",
            "new_password": "NewPassword123!",
            "confirm_password": "NewPassword123!"
        }
        headers = {"Authorization": f"Bearer {token}"}
        response = await async_client.post("/api/v1/auth/change-password", json=password_data, headers=headers)
        
        assert response.status_code == 200
        assert "Password changed successfully" in response.json()["message"]
    
    @pytest.mark.asyncio
    async def test_refresh_token(self, async_client: AsyncClient, async_session: AsyncSession):
        """Test token refresh"""
        # Create and verify user
        user_create = UserCreate(
            email="test@example.com",
            password="TestPassword123!",
            confirm_password="TestPassword123!",
            first_name="Test",
            last_name="User"
        )
        user = await AuthService.create_user(async_session, user_create)
        user.status = UserStatus.ACTIVE
        user.is_email_verified = True
        await async_session.commit()
        
        # Login to get tokens
        login_data = {
            "email": "test@example.com",
            "password": "TestPassword123!"
        }
        login_response = await async_client.post("/api/v1/auth/login", json=login_data)
        refresh_token = login_response.json()["refresh_token"]
        
        # Refresh tokens
        refresh_data = {"refresh_token": refresh_token}
        response = await async_client.post("/api/v1/auth/refresh", json=refresh_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
    
    @pytest.mark.asyncio
    async def test_logout(self, async_client: AsyncClient, async_session: AsyncSession):
        """Test user logout"""
        # Create and verify user
        user_create = UserCreate(
            email="test@example.com",
            password="TestPassword123!",
            confirm_password="TestPassword123!",
            first_name="Test",
            last_name="User"
        )
        user = await AuthService.create_user(async_session, user_create)
        user.status = UserStatus.ACTIVE
        user.is_email_verified = True
        await async_session.commit()
        
        # Login to get token
        login_data = {
            "email": "test@example.com",
            "password": "TestPassword123!"
        }
        login_response = await async_client.post("/api/v1/auth/login", json=login_data)
        token = login_response.json()["access_token"]
        
        # Logout
        headers = {"Authorization": f"Bearer {token}"}
        response = await async_client.post("/api/v1/auth/logout", headers=headers)
        
        assert response.status_code == 200
        assert "Successfully logged out" in response.json()["message"]
