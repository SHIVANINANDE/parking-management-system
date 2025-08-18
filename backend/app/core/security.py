"""
Security utilities for authentication and authorization
"""
from datetime import datetime, timedelta
from typing import Any, Union, Optional
import re
from passlib.context import CryptContext
from jose import jwt, JWTError
from fastapi import HTTPException, status
from app.core.config import settings
import secrets
import string

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_salt() -> str:
    """Generate a random salt for password hashing"""
    return secrets.token_urlsafe(32)

def verify_password(plain_password: str, hashed_password: str, salt: str) -> bool:
    """Verify a password against its hash"""
    salted_password = plain_password + salt
    return pwd_context.verify(salted_password, hashed_password)

def get_password_hash(password: str, salt: str) -> str:
    """Hash a password with salt"""
    salted_password = password + salt
    return pwd_context.hash(salted_password)

def validate_password_strength(password: str) -> tuple[bool, list[str]]:
    """
    Validate password strength based on security requirements
    Returns (is_valid, error_messages)
    """
    errors = []
    
    if len(password) < settings.PASSWORD_MIN_LENGTH:
        errors.append(f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters long")
    
    if settings.PASSWORD_REQUIRE_UPPERCASE and not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter")
    
    if settings.PASSWORD_REQUIRE_LOWERCASE and not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter")
    
    if settings.PASSWORD_REQUIRE_NUMBERS and not re.search(r"\d", password):
        errors.append("Password must contain at least one number")
    
    if settings.PASSWORD_REQUIRE_SPECIAL and not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        errors.append("Password must contain at least one special character")
    
    # Check for common weak passwords
    weak_passwords = ["password", "123456", "qwerty", "admin", "user", "guest"]
    if password.lower() in weak_passwords:
        errors.append("Password is too common and easily guessable")
    
    return len(errors) == 0, errors

def create_access_token(
    subject: Union[str, Any], 
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[dict] = None
) -> str:
    """Create JWT access token"""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "access",
        "iat": datetime.utcnow()
    }
    
    if additional_claims:
        to_encode.update(additional_claims)
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(subject: Union[str, Any]) -> str:
    """Create JWT refresh token"""
    expire = datetime.utcnow() + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "refresh",
        "iat": datetime.utcnow()
    }
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_token(token: str, token_type: str = "access") -> Optional[str]:
    """
    Verify JWT token and return subject
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        # Check token type
        if payload.get("type") != token_type:
            return None
        
        # Check expiration
        exp = payload.get("exp")
        if exp is None or datetime.utcnow() > datetime.fromtimestamp(exp):
            return None
        
        subject: str = payload.get("sub")
        if subject is None:
            return None
        
        return subject
    except JWTError:
        return None

def generate_password_reset_token() -> str:
    """Generate a secure password reset token"""
    return secrets.token_urlsafe(32)

def generate_email_verification_token() -> str:
    """Generate a secure email verification token"""
    return secrets.token_urlsafe(32)

def generate_api_key() -> str:
    """Generate a secure API key"""
    return secrets.token_urlsafe(48)

def create_csrf_token() -> str:
    """Generate CSRF token"""
    return secrets.token_urlsafe(32)

def verify_csrf_token(token: str, expected_token: str) -> bool:
    """Verify CSRF token"""
    return secrets.compare_digest(token, expected_token)

class SecurityHeaders:
    """Security headers for HTTP responses"""
    
    @staticmethod
    def get_security_headers() -> dict:
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
        }

def sanitize_input(input_string: str) -> str:
    """Basic input sanitization"""
    if not isinstance(input_string, str):
        return ""
    
    # Remove potentially dangerous characters
    dangerous_chars = ["<", ">", "\"", "'", "&", ";", "(", ")", "|", "`"]
    sanitized = input_string
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, "")
    
    return sanitized.strip()

def is_email_valid(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def generate_random_password(length: int = 12) -> str:
    """Generate a random secure password"""
    characters = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(characters) for _ in range(length))
    
    # Ensure it meets requirements
    is_valid, _ = validate_password_strength(password)
    if not is_valid:
        # Regenerate if it doesn't meet requirements
        return generate_random_password(length)
    
    return password
