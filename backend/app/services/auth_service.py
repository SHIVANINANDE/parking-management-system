"""
Authentication service for user management
"""
from typing import Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from fastapi import HTTPException, status
from app.models.user import User, UserStatus, UserRole
from app.schemas.auth import UserCreate, UserLogin, PasswordChange, PasswordReset, PasswordResetConfirm
from app.core.security import (
    verify_password, 
    get_password_hash, 
    create_salt,
    create_access_token,
    create_refresh_token,
    generate_password_reset_token,
    generate_email_verification_token,
    verify_token
)
from app.core.config import settings
import redis

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

class AuthService:
    """Authentication service class"""
    
    @staticmethod
    async def create_user(db: AsyncSession, user_data: UserCreate) -> User:
        """Create a new user"""
        # Check if user already exists
        existing_user = await db.execute(
            select(User).where(User.email == user_data.email)
        )
        if existing_user.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Check username if provided
        if user_data.username:
            existing_username = await db.execute(
                select(User).where(User.username == user_data.username)
            )
            if existing_username.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )
        
        # Create user
        salt = create_salt()
        hashed_password = get_password_hash(user_data.password, salt)
        email_verification_token = generate_email_verification_token()
        
        user = User(
            email=user_data.email,
            username=user_data.username,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            phone_number=user_data.phone_number,
            hashed_password=hashed_password,
            salt=salt,
            email_verification_token=email_verification_token,
            role=UserRole.USER,
            status=UserStatus.PENDING_VERIFICATION
        )
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        # TODO: Send verification email
        # await EmailService.send_verification_email(user.email, email_verification_token)
        
        return user
    
    @staticmethod
    async def authenticate_user(db: AsyncSession, credentials: UserLogin) -> Optional[User]:
        """Authenticate user with email and password"""
        # Get user by email
        result = await db.execute(
            select(User).where(User.email == credentials.email)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        # Check if account is locked due to failed attempts
        if user.failed_login_attempts >= 5:
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account locked due to too many failed login attempts"
            )
        
        # Verify password
        if not verify_password(credentials.password, user.hashed_password, user.salt):
            # Increment failed login attempts
            user.failed_login_attempts += 1
            await db.commit()
            return None
        
        # Reset failed login attempts on successful login
        user.failed_login_attempts = 0
        user.last_login_at = datetime.utcnow()
        user.last_activity_at = datetime.utcnow()
        await db.commit()
        
        return user
    
    @staticmethod
    async def login_user(db: AsyncSession, credentials: UserLogin) -> Tuple[str, str, int]:
        """Login user and return tokens"""
        user = await AuthService.authenticate_user(db, credentials)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        if user.status != UserStatus.ACTIVE:
            if user.status == UserStatus.PENDING_VERIFICATION:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email verification required"
                )
            elif user.status == UserStatus.SUSPENDED:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Account suspended"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Account inactive"
                )
        
        # Create tokens
        access_token = create_access_token(
            subject=user.id,
            additional_claims={
                "email": user.email,
                "role": user.role.value,
                "verified": user.is_email_verified
            }
        )
        refresh_token = create_refresh_token(subject=user.id)
        
        # Store refresh token in Redis
        redis_client.setex(
            f"refresh_token:{user.id}",
            settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60,
            refresh_token
        )
        
        return access_token, refresh_token, settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    
    @staticmethod
    async def refresh_token(db: AsyncSession, refresh_token: str) -> Tuple[str, str, int]:
        """Refresh access token"""
        user_id = verify_token(refresh_token, "refresh")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Check if refresh token exists in Redis
        stored_token = redis_client.get(f"refresh_token:{user_id}")
        if not stored_token or stored_token != refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Get user
        result = await db.execute(select(User).where(User.id == int(user_id)))
        user = result.scalar_one_or_none()
        
        if not user or user.status != UserStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Create new tokens
        access_token = create_access_token(
            subject=user.id,
            additional_claims={
                "email": user.email,
                "role": user.role.value,
                "verified": user.is_email_verified
            }
        )
        new_refresh_token = create_refresh_token(subject=user.id)
        
        # Update refresh token in Redis
        redis_client.setex(
            f"refresh_token:{user.id}",
            settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60,
            new_refresh_token
        )
        
        return access_token, new_refresh_token, settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    
    @staticmethod
    async def logout_user(user_id: int, token: str):
        """Logout user and invalidate tokens"""
        # Remove refresh token from Redis
        redis_client.delete(f"refresh_token:{user_id}")
        
        # Add access token to blacklist
        redis_client.setex(
            f"blacklist:{token}",
            settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "1"
        )
    
    @staticmethod
    async def change_password(
        db: AsyncSession, 
        user: User, 
        password_data: PasswordChange
    ) -> bool:
        """Change user password"""
        # Verify current password
        if not verify_password(password_data.current_password, user.hashed_password, user.salt):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Create new salt and hash
        new_salt = create_salt()
        new_hashed_password = get_password_hash(password_data.new_password, new_salt)
        
        # Update user
        user.hashed_password = new_hashed_password
        user.salt = new_salt
        user.updated_at = datetime.utcnow()
        
        await db.commit()
        
        # Invalidate all existing tokens for this user
        redis_client.delete(f"refresh_token:{user.id}")
        
        return True
    
    @staticmethod
    async def request_password_reset(db: AsyncSession, email: str) -> bool:
        """Request password reset"""
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        
        if not user:
            # Don't reveal if email exists
            return True
        
        # Generate reset token
        reset_token = generate_password_reset_token()
        expires_at = datetime.utcnow() + timedelta(hours=1)  # 1 hour expiry
        
        # Update user
        user.password_reset_token = reset_token
        user.password_reset_expires = expires_at
        await db.commit()
        
        # TODO: Send password reset email
        # await EmailService.send_password_reset_email(user.email, reset_token)
        
        return True
    
    @staticmethod
    async def reset_password(
        db: AsyncSession, 
        reset_data: PasswordResetConfirm
    ) -> bool:
        """Reset password with token"""
        result = await db.execute(
            select(User).where(
                User.password_reset_token == reset_data.token,
                User.password_reset_expires > datetime.utcnow()
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
        
        # Create new salt and hash
        new_salt = create_salt()
        new_hashed_password = get_password_hash(reset_data.new_password, new_salt)
        
        # Update user
        user.hashed_password = new_hashed_password
        user.salt = new_salt
        user.password_reset_token = None
        user.password_reset_expires = None
        user.failed_login_attempts = 0
        user.updated_at = datetime.utcnow()
        
        await db.commit()
        
        # Invalidate all existing tokens for this user
        redis_client.delete(f"refresh_token:{user.id}")
        
        return True
    
    @staticmethod
    async def verify_email(db: AsyncSession, token: str) -> bool:
        """Verify email with token"""
        result = await db.execute(
            select(User).where(User.email_verification_token == token)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification token"
            )
        
        # Update user
        user.is_email_verified = True
        user.email_verification_token = None
        user.status = UserStatus.ACTIVE
        user.updated_at = datetime.utcnow()
        
        await db.commit()
        
        return True
    
    @staticmethod
    async def resend_verification_email(db: AsyncSession, email: str) -> bool:
        """Resend verification email"""
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        
        if not user:
            # Don't reveal if email exists
            return True
        
        if user.is_email_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already verified"
            )
        
        # Generate new verification token
        verification_token = generate_email_verification_token()
        user.email_verification_token = verification_token
        await db.commit()
        
        # TODO: Send verification email
        # await EmailService.send_verification_email(user.email, verification_token)
        
        return True
