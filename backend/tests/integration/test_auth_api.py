"""
Integration Tests for Authentication API Endpoints
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.core.security import get_password_hash
from tests.conftest import UserFactory


@pytest.mark.integration
class TestAuthenticationAPI:
    """Test authentication API endpoints."""
    
    async def test_user_registration_success(self, client: AsyncClient):
        """Test successful user registration."""
        user_data = {
            "email": "newuser@example.com",
            "password": "SecurePass123!",
            "first_name": "New",
            "last_name": "User",
            "phone": "1234567890"
        }
        
        response = await client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["first_name"] == user_data["first_name"]
        assert data["last_name"] == user_data["last_name"]
        assert "password" not in data
        assert "hashed_password" not in data
    
    async def test_user_registration_duplicate_email(self, client: AsyncClient, test_user: User):
        """Test registration with duplicate email."""
        user_data = {
            "email": test_user.email,  # Already exists
            "password": "SecurePass123!",
            "first_name": "Duplicate",
            "last_name": "User",
            "phone": "9876543210"
        }
        
        response = await client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 400
        data = response.json()
        assert "email already registered" in data["detail"].lower()
    
    async def test_user_registration_invalid_email(self, client: AsyncClient):
        """Test registration with invalid email."""
        user_data = {
            "email": "invalid-email",
            "password": "SecurePass123!",
            "first_name": "Invalid",
            "last_name": "Email",
            "phone": "1234567890"
        }
        
        response = await client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    async def test_user_registration_weak_password(self, client: AsyncClient):
        """Test registration with weak password."""
        user_data = {
            "email": "test@example.com",
            "password": "123",  # Too weak
            "first_name": "Weak",
            "last_name": "Password",
            "phone": "1234567890"
        }
        
        response = await client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 422
    
    async def test_user_login_success(self, client: AsyncClient, test_user: User):
        """Test successful user login."""
        login_data = {
            "username": test_user.email,
            "password": "secret"  # From test fixture
        }
        
        response = await client.post("/api/v1/auth/login", data=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == test_user.email
    
    async def test_user_login_wrong_password(self, client: AsyncClient, test_user: User):
        """Test login with wrong password."""
        login_data = {
            "username": test_user.email,
            "password": "wrongpassword"
        }
        
        response = await client.post("/api/v1/auth/login", data=login_data)
        
        assert response.status_code == 401
        data = response.json()
        assert "incorrect" in data["detail"].lower()
    
    async def test_user_login_nonexistent_user(self, client: AsyncClient):
        """Test login with nonexistent user."""
        login_data = {
            "username": "nonexistent@example.com",
            "password": "password"
        }
        
        response = await client.post("/api/v1/auth/login", data=login_data)
        
        assert response.status_code == 401
        data = response.json()
        assert "incorrect" in data["detail"].lower()
    
    async def test_token_refresh(self, client: AsyncClient, test_user: User):
        """Test token refresh."""
        # First login to get tokens
        login_data = {
            "username": test_user.email,
            "password": "secret"
        }
        
        login_response = await client.post("/api/v1/auth/login", data=login_data)
        tokens = login_response.json()
        
        # Use refresh token to get new access token
        refresh_data = {
            "refresh_token": tokens["refresh_token"]
        }
        
        response = await client.post("/api/v1/auth/refresh", json=refresh_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
    
    async def test_token_refresh_invalid_token(self, client: AsyncClient):
        """Test token refresh with invalid token."""
        refresh_data = {
            "refresh_token": "invalid_token"
        }
        
        response = await client.post("/api/v1/auth/refresh", json=refresh_data)
        
        assert response.status_code == 401
    
    async def test_get_current_user(self, client: AsyncClient, test_user: User, auth_headers: dict):
        """Test getting current user information."""
        response = await client.get("/api/v1/auth/me", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["first_name"] == test_user.first_name
        assert data["last_name"] == test_user.last_name
        assert "password" not in data
        assert "hashed_password" not in data
    
    async def test_get_current_user_unauthorized(self, client: AsyncClient):
        """Test getting current user without authentication."""
        response = await client.get("/api/v1/auth/me")
        
        assert response.status_code == 401
    
    async def test_get_current_user_invalid_token(self, client: AsyncClient):
        """Test getting current user with invalid token."""
        headers = {"Authorization": "Bearer invalid_token"}
        response = await client.get("/api/v1/auth/me", headers=headers)
        
        assert response.status_code == 401
    
    async def test_logout(self, client: AsyncClient, test_user: User, auth_headers: dict):
        """Test user logout."""
        response = await client.post("/api/v1/auth/logout", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Successfully logged out"
    
    async def test_change_password(self, client: AsyncClient, test_user: User, auth_headers: dict):
        """Test password change."""
        password_data = {
            "current_password": "secret",
            "new_password": "NewSecurePass123!"
        }
        
        response = await client.post("/api/v1/auth/change-password", json=password_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Password updated successfully"
    
    async def test_change_password_wrong_current(self, client: AsyncClient, test_user: User, auth_headers: dict):
        """Test password change with wrong current password."""
        password_data = {
            "current_password": "wrong_password",
            "new_password": "NewSecurePass123!"
        }
        
        response = await client.post("/api/v1/auth/change-password", json=password_data, headers=auth_headers)
        
        assert response.status_code == 400
        data = response.json()
        assert "current password" in data["detail"].lower()
    
    async def test_forgot_password(self, client: AsyncClient, test_user: User):
        """Test forgot password functionality."""
        forgot_data = {
            "email": test_user.email
        }
        
        response = await client.post("/api/v1/auth/forgot-password", json=forgot_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "reset link" in data["message"].lower()
    
    async def test_forgot_password_nonexistent_user(self, client: AsyncClient):
        """Test forgot password for nonexistent user."""
        forgot_data = {
            "email": "nonexistent@example.com"
        }
        
        response = await client.post("/api/v1/auth/forgot-password", json=forgot_data)
        
        # Should still return 200 for security reasons
        assert response.status_code == 200
        data = response.json()
        assert "reset link" in data["message"].lower()
    
    async def test_update_profile(self, client: AsyncClient, test_user: User, auth_headers: dict):
        """Test profile update."""
        update_data = {
            "first_name": "Updated",
            "last_name": "Name",
            "phone": "9876543210"
        }
        
        response = await client.put("/api/v1/auth/profile", json=update_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Updated"
        assert data["last_name"] == "Name"
        assert data["phone"] == "9876543210"
    
    async def test_update_profile_unauthorized(self, client: AsyncClient):
        """Test profile update without authentication."""
        update_data = {
            "first_name": "Updated",
            "last_name": "Name"
        }
        
        response = await client.put("/api/v1/auth/profile", json=update_data)
        
        assert response.status_code == 401


@pytest.mark.integration
class TestUserManagementAPI:
    """Test user management API endpoints (admin only)."""
    
    async def test_get_all_users_admin(self, client: AsyncClient, test_admin_user: User, admin_auth_headers: dict):
        """Test getting all users as admin."""
        response = await client.get("/api/v1/users/", headers=admin_auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1  # At least the admin user
    
    async def test_get_all_users_non_admin(self, client: AsyncClient, test_user: User, auth_headers: dict):
        """Test getting all users as non-admin (should fail)."""
        response = await client.get("/api/v1/users/", headers=auth_headers)
        
        assert response.status_code == 403
    
    async def test_get_user_by_id_admin(self, client: AsyncClient, test_user: User, test_admin_user: User, admin_auth_headers: dict):
        """Test getting user by ID as admin."""
        response = await client.get(f"/api/v1/users/{test_user.id}", headers=admin_auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
    
    async def test_get_user_by_id_not_found(self, client: AsyncClient, test_admin_user: User, admin_auth_headers: dict):
        """Test getting nonexistent user by ID."""
        response = await client.get("/api/v1/users/nonexistent-id", headers=admin_auth_headers)
        
        assert response.status_code == 404
    
    async def test_deactivate_user_admin(self, client: AsyncClient, test_user: User, test_admin_user: User, admin_auth_headers: dict):
        """Test deactivating user as admin."""
        response = await client.patch(f"/api/v1/users/{test_user.id}/deactivate", headers=admin_auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False
    
    async def test_activate_user_admin(self, client: AsyncClient, test_user: User, test_admin_user: User, admin_auth_headers: dict):
        """Test activating user as admin."""
        # First deactivate
        await client.patch(f"/api/v1/users/{test_user.id}/deactivate", headers=admin_auth_headers)
        
        # Then reactivate
        response = await client.patch(f"/api/v1/users/{test_user.id}/activate", headers=admin_auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is True
