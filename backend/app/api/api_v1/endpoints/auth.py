"""
Authentication endpoints
"""
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_async_session
from app.schemas.auth import (
    UserCreate, UserLogin, UserResponse, Token, TokenRefresh,
    PasswordChange, PasswordReset, PasswordResetConfirm,
    EmailVerification, ResendEmailVerification, Message
)
from app.services.auth_service import AuthService
from app.services.oauth_service import oauth_service
from app.core.deps import (
    get_current_active_user, 
    verify_refresh_token, 
    rate_limit_auth,
    get_current_user_token
)
from app.core.security import SecurityHeaders
from app.models.user import User
from datetime import datetime

router = APIRouter()
security = HTTPBearer()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_async_session),
    _: Any = Depends(rate_limit_auth)
):
    """Register a new user"""
    # Add security headers
    for header, value in SecurityHeaders.get_security_headers().items():
        response.headers[header] = value
    
    user = await AuthService.create_user(db, user_data)
    return UserResponse.from_orm(user)

@router.post("/login", response_model=Token)
async def login(
    credentials: UserLogin,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_async_session),
    _: Any = Depends(rate_limit_auth)
):
    """Login user and return access token"""
    # Add security headers
    for header, value in SecurityHeaders.get_security_headers().items():
        response.headers[header] = value
    
    access_token, refresh_token, expires_in = await AuthService.login_user(db, credentials)
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=expires_in
    )

@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_data: TokenRefresh,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_async_session)
):
    """Refresh access token"""
    # Add security headers
    for header, value in SecurityHeaders.get_security_headers().items():
        response.headers[header] = value
    
    access_token, new_refresh_token, expires_in = await AuthService.refresh_token(
        db, refresh_data.refresh_token
    )
    
    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=expires_in
    )

@router.post("/logout", response_model=Message)
async def logout(
    request: Request,
    response: Response,
    token: str = Depends(get_current_user_token),
    current_user: User = Depends(get_current_active_user)
):
    """Logout user and invalidate tokens"""
    # Add security headers
    for header, value in SecurityHeaders.get_security_headers().items():
        response.headers[header] = value
    
    await AuthService.logout_user(current_user.id, token)
    
    return Message(message="Successfully logged out")

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_active_user)
):
    """Get current user information"""
    # Add security headers
    for header, value in SecurityHeaders.get_security_headers().items():
        response.headers[header] = value
    
    # Update last activity
    current_user.last_activity_at = datetime.utcnow()
    
    return UserResponse.from_orm(current_user)

@router.post("/change-password", response_model=Message)
async def change_password(
    password_data: PasswordChange,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_active_user)
):
    """Change user password"""
    # Add security headers
    for header, value in SecurityHeaders.get_security_headers().items():
        response.headers[header] = value
    
    await AuthService.change_password(db, current_user, password_data)
    
    return Message(message="Password changed successfully")

@router.post("/password-reset", response_model=Message)
async def request_password_reset(
    reset_data: PasswordReset,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_async_session),
    _: Any = Depends(rate_limit_auth)
):
    """Request password reset"""
    # Add security headers
    for header, value in SecurityHeaders.get_security_headers().items():
        response.headers[header] = value
    
    await AuthService.request_password_reset(db, reset_data.email)
    
    return Message(message="If the email exists, a password reset link has been sent")

@router.post("/password-reset/confirm", response_model=Message)
async def confirm_password_reset(
    reset_data: PasswordResetConfirm,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_async_session),
    _: Any = Depends(rate_limit_auth)
):
    """Confirm password reset with token"""
    # Add security headers
    for header, value in SecurityHeaders.get_security_headers().items():
        response.headers[header] = value
    
    await AuthService.reset_password(db, reset_data)
    
    return Message(message="Password reset successfully")

@router.post("/verify-email", response_model=Message)
async def verify_email(
    verification_data: EmailVerification,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_async_session)
):
    """Verify email with token"""
    # Add security headers
    for header, value in SecurityHeaders.get_security_headers().items():
        response.headers[header] = value
    
    await AuthService.verify_email(db, verification_data.token)
    
    return Message(message="Email verified successfully")

@router.post("/resend-verification", response_model=Message)
async def resend_verification_email(
    resend_data: ResendEmailVerification,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_async_session),
    _: Any = Depends(rate_limit_auth)
):
    """Resend email verification"""
    # Add security headers
    for header, value in SecurityHeaders.get_security_headers().items():
        response.headers[header] = value
    
    await AuthService.resend_verification_email(db, resend_data.email)
    
    return Message(message="If the email exists, a verification link has been sent")

# OAuth endpoints
@router.get("/oauth/{provider}/authorize")
async def oauth_authorize(
    provider: str,
    request: Request,
    response: Response,
    redirect_uri: str = "http://localhost:3000/auth/callback"
):
    """Get OAuth authorization URL"""
    # Add security headers
    for header, value in SecurityHeaders.get_security_headers().items():
        response.headers[header] = value
    
    authorization_url = oauth_service.get_authorization_url(provider, redirect_uri)
    
    return {"authorization_url": authorization_url}

@router.post("/oauth/{provider}/callback", response_model=Token)
async def oauth_callback(
    provider: str,
    code: str,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_async_session),
    redirect_uri: str = "http://localhost:3000/auth/callback"
):
    """Handle OAuth callback and login user"""
    # Add security headers
    for header, value in SecurityHeaders.get_security_headers().items():
        response.headers[header] = value
    
    # Exchange code for access token
    access_token = await oauth_service.exchange_code_for_token(provider, code, redirect_uri)
    
    # Authenticate user
    user = await oauth_service.authenticate_oauth_user(db, provider, access_token)
    
    # Create JWT tokens directly (since OAuth users don't need password validation)
    from app.core.security import create_access_token, create_refresh_token
    import redis
    
    jwt_access_token = create_access_token(
        subject=user.id,
        additional_claims={
            "email": user.email,
            "role": user.role.value,
            "verified": user.is_email_verified
        }
    )
    refresh_token = create_refresh_token(subject=user.id)
    
    # Store refresh token in Redis
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    redis_client.setex(
        f"refresh_token:{user.id}",
        settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60,
        refresh_token
    )
    
    return Token(
        access_token=jwt_access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
