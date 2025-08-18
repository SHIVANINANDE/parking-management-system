"""
Unit Tests for User Model and Services
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.user_service import UserService
from app.core.security import verify_password, get_password_hash
from tests.conftest import UserFactory


@pytest.mark.unit
class TestUserModel:
    """Test User model functionality."""
    
    def test_user_creation(self):
        """Test user model creation."""
        user_data = UserFactory.build()
        user = User(**user_data)
        
        assert user.email == user_data["email"]
        assert user.first_name == user_data["first_name"]
        assert user.last_name == user_data["last_name"]
        assert user.is_active == user_data["is_active"]
        assert user.is_verified == user_data["is_verified"]
    
    def test_user_full_name(self):
        """Test user full name property."""
        user = User(first_name="John", last_name="Doe")
        assert user.full_name == "John Doe"
    
    def test_user_password_hashing(self):
        """Test password hashing and verification."""
        password = "test_password_123"
        hashed = get_password_hash(password)
        
        user = User(
            email="test@example.com",
            hashed_password=hashed
        )
        
        assert verify_password(password, user.hashed_password)
        assert not verify_password("wrong_password", user.hashed_password)
    
    def test_user_dict_conversion(self):
        """Test user to dict conversion."""
        user_data = UserFactory.build()
        user = User(**user_data)
        user.id = "test-id"
        user.created_at = datetime.utcnow()
        
        user_dict = user.to_dict()
        
        assert user_dict["id"] == user.id
        assert user_dict["email"] == user.email
        assert user_dict["first_name"] == user.first_name
        assert "hashed_password" not in user_dict  # Should be excluded


@pytest.mark.unit
class TestUserService:
    """Test UserService functionality."""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return Mock(spec=AsyncSession)
    
    @pytest.fixture
    def user_service(self, mock_db):
        """Create UserService instance with mock db."""
        return UserService(mock_db)
    
    async def test_create_user(self, user_service, mock_db):
        """Test user creation service."""
        user_data = UserFactory.build()
        mock_user = User(**user_data)
        mock_user.id = "test-id"
        
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()
        
        with patch('app.services.user_service.get_password_hash') as mock_hash:
            mock_hash.return_value = "hashed_password"
            
            result = await user_service.create_user(user_data)
            
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once()
    
    async def test_get_user_by_email(self, user_service, mock_db):
        """Test get user by email service."""
        email = "test@example.com"
        mock_user = User(email=email)
        
        with patch('app.services.user_service.select') as mock_select:
            mock_stmt = Mock()
            mock_select.return_value = mock_stmt
            mock_db.execute.return_value.scalar_one_or_none.return_value = mock_user
            
            result = await user_service.get_user_by_email(email)
            
            assert result == mock_user
            mock_db.execute.assert_called_once()
    
    async def test_authenticate_user_success(self, user_service):
        """Test successful user authentication."""
        email = "test@example.com"
        password = "test_password"
        hashed_password = get_password_hash(password)
        
        mock_user = User(email=email, hashed_password=hashed_password)
        
        with patch.object(user_service, 'get_user_by_email', return_value=mock_user):
            result = await user_service.authenticate_user(email, password)
            
            assert result == mock_user
    
    async def test_authenticate_user_wrong_password(self, user_service):
        """Test user authentication with wrong password."""
        email = "test@example.com"
        password = "wrong_password"
        hashed_password = get_password_hash("correct_password")
        
        mock_user = User(email=email, hashed_password=hashed_password)
        
        with patch.object(user_service, 'get_user_by_email', return_value=mock_user):
            result = await user_service.authenticate_user(email, password)
            
            assert result is None
    
    async def test_authenticate_user_not_found(self, user_service):
        """Test user authentication when user not found."""
        email = "nonexistent@example.com"
        password = "password"
        
        with patch.object(user_service, 'get_user_by_email', return_value=None):
            result = await user_service.authenticate_user(email, password)
            
            assert result is None
    
    async def test_update_user_profile(self, user_service, mock_db):
        """Test user profile update."""
        user_id = "test-id"
        update_data = {"first_name": "Updated", "last_name": "Name"}
        
        mock_user = User(id=user_id, first_name="Old", last_name="Name")
        
        with patch.object(user_service, 'get_user_by_id', return_value=mock_user):
            mock_db.commit = Mock()
            mock_db.refresh = Mock()
            
            result = await user_service.update_user_profile(user_id, update_data)
            
            assert result.first_name == "Updated"
            assert result.last_name == "Name"
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once()


@pytest.mark.unit
class TestUserValidation:
    """Test user data validation."""
    
    def test_valid_email_format(self):
        """Test valid email format validation."""
        from app.schemas.user import UserCreate
        from pydantic import ValidationError
        
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "test+label@domain.org"
        ]
        
        for email in valid_emails:
            user_data = {
                "email": email,
                "password": "password123",
                "first_name": "Test",
                "last_name": "User",
                "phone": "1234567890"
            }
            user = UserCreate(**user_data)
            assert user.email == email
    
    def test_invalid_email_format(self):
        """Test invalid email format validation."""
        from app.schemas.user import UserCreate
        from pydantic import ValidationError
        
        invalid_emails = [
            "invalid-email",
            "@domain.com",
            "test@",
            "test..test@domain.com"
        ]
        
        for email in invalid_emails:
            with pytest.raises(ValidationError):
                UserCreate(
                    email=email,
                    password="password123",
                    first_name="Test",
                    last_name="User",
                    phone="1234567890"
                )
    
    def test_password_strength_validation(self):
        """Test password strength validation."""
        from app.schemas.user import UserCreate
        from pydantic import ValidationError
        
        # Valid passwords
        valid_passwords = [
            "StrongPass123!",
            "MySecure@Pass1",
            "Complex#Password99"
        ]
        
        for password in valid_passwords:
            user = UserCreate(
                email="test@example.com",
                password=password,
                first_name="Test",
                last_name="User",
                phone="1234567890"
            )
            assert user.password == password
        
        # Invalid passwords (too short)
        with pytest.raises(ValidationError):
            UserCreate(
                email="test@example.com",
                password="123",
                first_name="Test",
                last_name="User",
                phone="1234567890"
            )
    
    def test_phone_number_validation(self):
        """Test phone number validation."""
        from app.schemas.user import UserCreate
        
        valid_phones = [
            "1234567890",
            "+1-234-567-8900",
            "(555) 123-4567"
        ]
        
        for phone in valid_phones:
            user = UserCreate(
                email="test@example.com",
                password="password123",
                first_name="Test",
                last_name="User",
                phone=phone
            )
            assert user.phone == phone
