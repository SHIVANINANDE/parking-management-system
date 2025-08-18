"""
OAuth service for social login (Google, GitHub)
"""
from typing import Optional, Dict, Any
import httpx
from datetime import datetime
from fastapi import HTTPException, status
from authlib.integrations.starlette_client import OAuth
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User, UserRole, UserStatus
from app.schemas.auth import OAuthUserInfo
from app.core.config import settings
from app.core.security import create_salt, generate_random_password, get_password_hash
from app.services.auth_service import AuthService

class OAuthService:
    """OAuth service for social authentication"""
    
    def __init__(self):
        self.oauth = OAuth()
        self._setup_providers()
    
    def _setup_providers(self):
        """Setup OAuth providers"""
        # Google OAuth
        if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
            self.oauth.register(
                name='google',
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
                server_metadata_url='https://accounts.google.com/.well-known/openid_configuration',
                client_kwargs={'scope': 'openid email profile'}
            )
        
        # GitHub OAuth
        if settings.GITHUB_CLIENT_ID and settings.GITHUB_CLIENT_SECRET:
            self.oauth.register(
                name='github',
                client_id=settings.GITHUB_CLIENT_ID,
                client_secret=settings.GITHUB_CLIENT_SECRET,
                authorize_url='https://github.com/login/oauth/authorize',
                access_token_url='https://github.com/login/oauth/access_token',
                client_kwargs={'scope': 'user:email'}
            )
    
    async def get_google_user_info(self, access_token: str) -> OAuthUserInfo:
        """Get user information from Google"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                'https://www.googleapis.com/oauth2/v2/userinfo',
                headers={'Authorization': f'Bearer {access_token}'}
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to get user info from Google"
                )
            
            data = response.json()
            
            return OAuthUserInfo(
                email=data.get('email'),
                first_name=data.get('given_name', ''),
                last_name=data.get('family_name', ''),
                provider='google',
                provider_id=data.get('id'),
                picture=data.get('picture')
            )
    
    async def get_github_user_info(self, access_token: str) -> OAuthUserInfo:
        """Get user information from GitHub"""
        async with httpx.AsyncClient() as client:
            # Get user profile
            user_response = await client.get(
                'https://api.github.com/user',
                headers={'Authorization': f'token {access_token}'}
            )
            
            if user_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to get user info from GitHub"
                )
            
            user_data = user_response.json()
            
            # Get user emails
            email_response = await client.get(
                'https://api.github.com/user/emails',
                headers={'Authorization': f'token {access_token}'}
            )
            
            if email_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to get user emails from GitHub"
                )
            
            emails = email_response.json()
            primary_email = next(
                (email['email'] for email in emails if email['primary']), 
                emails[0]['email'] if emails else None
            )
            
            if not primary_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No email found in GitHub account"
                )
            
            # Split name
            name = user_data.get('name', '').split(' ', 1)
            first_name = name[0] if name else user_data.get('login', '')
            last_name = name[1] if len(name) > 1 else ''
            
            return OAuthUserInfo(
                email=primary_email,
                first_name=first_name,
                last_name=last_name,
                provider='github',
                provider_id=str(user_data.get('id')),
                picture=user_data.get('avatar_url')
            )
    
    async def authenticate_oauth_user(
        self, 
        db: AsyncSession, 
        provider: str, 
        access_token: str
    ) -> User:
        """Authenticate user via OAuth"""
        # Get user info from provider
        if provider == 'google':
            user_info = await self.get_google_user_info(access_token)
        elif provider == 'github':
            user_info = await self.get_github_user_info(access_token)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported OAuth provider"
            )
        
        # Check if user exists
        result = await db.execute(
            select(User).where(User.email == user_info.email)
        )
        user = result.scalar_one_or_none()
        
        if user:
            # Update user info if needed
            if user_info.picture and not user.profile_picture_url:
                user.profile_picture_url = user_info.picture
            
            # Mark as verified if not already
            if not user.is_email_verified:
                user.is_email_verified = True
                user.status = UserStatus.ACTIVE
            
            user.last_login_at = datetime.utcnow()
            user.last_activity_at = datetime.utcnow()
            await db.commit()
            
            return user
        else:
            # Create new user
            salt = create_salt()
            # Generate a random password for OAuth users
            random_password = generate_random_password()
            hashed_password = get_password_hash(random_password, salt)
            
            user = User(
                email=user_info.email,
                first_name=user_info.first_name,
                last_name=user_info.last_name,
                hashed_password=hashed_password,
                salt=salt,
                role=UserRole.USER,
                status=UserStatus.ACTIVE,
                is_email_verified=True,  # OAuth emails are pre-verified
                profile_picture_url=user_info.picture,
                last_login_at=datetime.utcnow(),
                last_activity_at=datetime.utcnow()
            )
            
            db.add(user)
            await db.commit()
            await db.refresh(user)
            
            return user
    
    def get_authorization_url(self, provider: str, redirect_uri: str) -> str:
        """Get OAuth authorization URL"""
        if provider not in ['google', 'github']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported OAuth provider"
            )
        
        client = getattr(self.oauth, provider)
        if not client:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"{provider.title()} OAuth not configured"
            )
        
        authorization_url = client.create_authorization_url(redirect_uri)
        return authorization_url['url']
    
    async def exchange_code_for_token(
        self, 
        provider: str, 
        code: str, 
        redirect_uri: str
    ) -> str:
        """Exchange authorization code for access token"""
        if provider not in ['google', 'github']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported OAuth provider"
            )
        
        client = getattr(self.oauth, provider)
        if not client:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"{provider.title()} OAuth not configured"
            )
        
        try:
            if provider == 'google':
                token_data = await self._exchange_google_code(code, redirect_uri)
            elif provider == 'github':
                token_data = await self._exchange_github_code(code, redirect_uri)
            
            return token_data['access_token']
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to exchange code for token: {str(e)}"
            )
    
    async def _exchange_google_code(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange Google authorization code for token"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                'https://oauth2.googleapis.com/token',
                data={
                    'client_id': settings.GOOGLE_CLIENT_ID,
                    'client_secret': settings.GOOGLE_CLIENT_SECRET,
                    'code': code,
                    'grant_type': 'authorization_code',
                    'redirect_uri': redirect_uri
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Google token exchange failed: {response.text}")
            
            return response.json()
    
    async def _exchange_github_code(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange GitHub authorization code for token"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                'https://github.com/login/oauth/access_token',
                data={
                    'client_id': settings.GITHUB_CLIENT_ID,
                    'client_secret': settings.GITHUB_CLIENT_SECRET,
                    'code': code,
                    'redirect_uri': redirect_uri
                },
                headers={'Accept': 'application/json'}
            )
            
            if response.status_code != 200:
                raise Exception(f"GitHub token exchange failed: {response.text}")
            
            return response.json()

# Global OAuth service instance
oauth_service = OAuthService()
