"""
Pydantic schemas for authentication
"""
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, validator
from datetime import datetime
from app.models.user import UserRole, UserStatus
from app.core.security import validate_password_strength

class UserBase(BaseModel):
    """Base user schema"""
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone_number: Optional[str] = Field(None, max_length=20)
    username: Optional[str] = Field(None, min_length=3, max_length=100)

class UserCreate(UserBase):
    """Schema for user creation"""
    password: str = Field(..., min_length=8)
    confirm_password: str
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        is_valid, errors = validate_password_strength(v)
        if not is_valid:
            raise ValueError(f"Password requirements not met: {', '.join(errors)}")
        return v
    
    @validator('username')
    def validate_username(cls, v):
        if v and not v.isalnum():
            raise ValueError('Username must contain only letters and numbers')
        return v

class UserLogin(BaseModel):
    """Schema for user login"""
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    """Schema for user updates"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone_number: Optional[str] = Field(None, max_length=20)
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    timezone: Optional[str] = Field(None, max_length=50)
    language: Optional[str] = Field(None, max_length=10)
    notifications_enabled: Optional[bool] = None

class UserResponse(UserBase):
    """Schema for user response"""
    id: int
    role: UserRole
    status: UserStatus
    is_email_verified: bool
    is_phone_verified: bool
    profile_picture_url: Optional[str]
    timezone: str
    language: str
    notifications_enabled: bool
    created_at: datetime
    updated_at: datetime
    last_activity_at: datetime
    last_login_at: Optional[datetime]

    class Config:
        from_attributes = True

class Token(BaseModel):
    """Schema for token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class TokenRefresh(BaseModel):
    """Schema for token refresh"""
    refresh_token: str

class PasswordChange(BaseModel):
    """Schema for password change"""
    current_password: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v
    
    @validator('new_password')
    def validate_password(cls, v):
        is_valid, errors = validate_password_strength(v)
        if not is_valid:
            raise ValueError(f"Password requirements not met: {', '.join(errors)}")
        return v

class PasswordReset(BaseModel):
    """Schema for password reset"""
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation"""
    token: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v
    
    @validator('new_password')
    def validate_password(cls, v):
        is_valid, errors = validate_password_strength(v)
        if not is_valid:
            raise ValueError(f"Password requirements not met: {', '.join(errors)}")
        return v

class EmailVerification(BaseModel):
    """Schema for email verification"""
    token: str

class ResendEmailVerification(BaseModel):
    """Schema for resending email verification"""
    email: EmailStr

class UserInDB(UserResponse):
    """Schema for user in database (internal use)"""
    hashed_password: str
    salt: str
    failed_login_attempts: int
    password_reset_token: Optional[str]
    password_reset_expires: Optional[datetime]
    email_verification_token: Optional[str]

class Message(BaseModel):
    """Generic message schema"""
    message: str

class ErrorResponse(BaseModel):
    """Error response schema"""
    detail: str
    error_code: Optional[str] = None

# OAuth Schemas
class OAuthUserInfo(BaseModel):
    """OAuth user information"""
    email: EmailStr
    first_name: str
    last_name: str
    provider: str
    provider_id: str
    picture: Optional[str] = None

class OAuthToken(BaseModel):
    """OAuth token schema"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str
    expires_in: Optional[int] = None
    scope: Optional[str] = None

# API Key Schemas
class APIKeyCreate(BaseModel):
    """Schema for API key creation"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    expires_at: Optional[datetime] = None

class APIKeyResponse(BaseModel):
    """Schema for API key response"""
    id: int
    name: str
    description: Optional[str]
    key: str  # Only shown once during creation
    created_at: datetime
    expires_at: Optional[datetime]
    is_active: bool

class APIKeyList(BaseModel):
    """Schema for API key list response"""
    id: int
    name: str
    description: Optional[str]
    created_at: datetime
    expires_at: Optional[datetime]
    is_active: bool
    last_used_at: Optional[datetime]

# Two-Factor Authentication Schemas
class TwoFactorSetup(BaseModel):
    """Schema for 2FA setup"""
    secret: str
    qr_code: str
    backup_codes: list[str]

class TwoFactorVerify(BaseModel):
    """Schema for 2FA verification"""
    code: str = Field(..., min_length=6, max_length=6)

class TwoFactorBackupCode(BaseModel):
    """Schema for 2FA backup code"""
    backup_code: str = Field(..., min_length=8, max_length=8)
