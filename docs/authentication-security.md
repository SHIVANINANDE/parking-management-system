# Authentication & Security Documentation

## Overview

The Smart Parking Management System implements a comprehensive authentication and security framework with the following features:

- **JWT Authentication** with access and refresh tokens
- **OAuth 2.0 Integration** (Google, GitHub)
- **Rate Limiting** to prevent abuse
- **Security Headers** for enhanced protection
- **Input Validation** with Pydantic
- **Password Security** with bcrypt hashing
- **CORS Configuration** for cross-origin requests
- **Brute Force Protection** for login endpoints

## Architecture

### Authentication Flow

1. **User Registration**
   - Email validation and uniqueness check
   - Strong password requirements
   - Email verification token generation
   - User account creation in pending status

2. **User Login**
   - Credential validation
   - Account status verification
   - JWT access and refresh token generation
   - Redis-based token storage

3. **Token Management**
   - Short-lived access tokens (30 minutes)
   - Long-lived refresh tokens (7 days)
   - Token blacklisting for logout
   - Automatic token refresh

### Security Layers

#### 1. Authentication Layer
- JWT tokens with RS256 algorithm
- Token blacklisting in Redis
- Multi-factor authentication support
- OAuth 2.0 integration

#### 2. Authorization Layer
- Role-based access control (RBAC)
- Resource-level permissions
- API endpoint protection
- Admin panel restrictions

#### 3. Rate Limiting Layer
- Global rate limiting (60 requests/minute)
- Authentication endpoint limits (5 requests/5 minutes)
- IP-based tracking
- Burst protection

#### 4. Security Headers Layer
- Content Security Policy (CSP)
- X-Frame-Options
- X-Content-Type-Options
- Strict-Transport-Security

## API Endpoints

### Authentication Endpoints

#### POST `/api/v1/auth/register`
Register a new user account.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "confirm_password": "SecurePassword123!",
  "first_name": "John",
  "last_name": "Doe"
}
```

**Response:**
```json
{
  "id": 1,
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "status": "pending_verification",
  "created_at": "2025-08-18T08:30:00Z"
}
```

#### POST `/api/v1/auth/login`
Authenticate user and receive tokens.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

#### POST `/api/v1/auth/refresh`
Refresh access token using refresh token.

**Request Body:**
```json
{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

#### GET `/api/v1/auth/me`
Get current user information.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "id": 1,
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "role": "user",
  "status": "active",
  "is_email_verified": true
}
```

#### POST `/api/v1/auth/logout`
Logout user and invalidate tokens.

#### POST `/api/v1/auth/change-password`
Change user password.

#### POST `/api/v1/auth/password-reset`
Request password reset email.

#### POST `/api/v1/auth/verify-email`
Verify email with token.

### OAuth Endpoints

#### GET `/api/v1/auth/oauth/{provider}/authorize`
Get OAuth authorization URL.

**Parameters:**
- `provider`: `google` or `github`
- `redirect_uri`: OAuth callback URL

#### POST `/api/v1/auth/oauth/{provider}/callback`
Handle OAuth callback and login user.

## Security Configuration

### Password Requirements

- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter  
- At least one number
- At least one special character
- Not in common weak passwords list

### Rate Limiting

- **Standard endpoints**: 60 requests per minute
- **Authentication endpoints**: 5 requests per 5 minutes
- **Burst protection**: 10 additional requests

### Security Headers

```http
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'
Referrer-Policy: strict-origin-when-cross-origin
```

## Environment Configuration

### Required Variables

```bash
# Security
SECRET_KEY=your-super-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_MINUTES=10080

# Database & Redis
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/db
REDIS_URL=redis://localhost:6379

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_BURST=10
```

### Optional OAuth Variables

```bash
# Google OAuth
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret

# GitHub OAuth
GITHUB_CLIENT_ID=your-client-id
GITHUB_CLIENT_SECRET=your-client-secret
```

## Testing

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run authentication tests
pytest tests/test_auth.py -v

# Run all tests
pytest tests/ -v
```

### Test Coverage

- User registration validation
- Login/logout flows
- Token management
- Password operations
- OAuth integration
- Rate limiting
- Security headers

## Deployment Considerations

### Production Setup

1. **Environment Variables**
   - Use strong, unique SECRET_KEY
   - Configure OAuth credentials
   - Set up SSL certificates

2. **Database Security**
   - Use connection pooling
   - Enable SSL connections
   - Regular backups

3. **Redis Configuration**
   - Enable authentication
   - Use SSL/TLS
   - Configure persistence

4. **Monitoring**
   - Set up logging
   - Monitor rate limits
   - Track authentication events

### SSL/TLS Configuration

```bash
# Enable SSL
USE_SSL=true
SSL_CERTIFICATE_PATH=/path/to/cert.pem
SSL_PRIVATE_KEY_PATH=/path/to/key.pem
```

### Security Checklist

- [ ] Strong SECRET_KEY configured
- [ ] OAuth credentials secured
- [ ] Database connections encrypted
- [ ] Redis authentication enabled
- [ ] Rate limiting configured
- [ ] Security headers enabled
- [ ] Input validation active
- [ ] Logging and monitoring setup
- [ ] SSL/TLS certificates valid
- [ ] Regular security updates

## Troubleshooting

### Common Issues

1. **Token Validation Errors**
   - Check SECRET_KEY configuration
   - Verify token expiration
   - Confirm Redis connectivity

2. **Rate Limiting Issues**
   - Check Redis configuration
   - Verify rate limit settings
   - Monitor client IP addresses

3. **OAuth Setup Problems**
   - Validate client credentials
   - Check redirect URIs
   - Verify provider settings

4. **Database Connection Errors**
   - Confirm DATABASE_URL format
   - Check database connectivity
   - Verify connection pooling

### Debug Mode

Enable debug mode for development:

```bash
DEBUG=true
ENVIRONMENT=development
```

This provides:
- Detailed error messages
- Request/response logging
- API documentation access
- Enhanced debugging info

## Security Best Practices

1. **Keep dependencies updated**
2. **Use HTTPS in production**
3. **Implement proper logging**
4. **Regular security audits**
5. **Monitor authentication events**
6. **Use strong passwords**
7. **Enable rate limiting**
8. **Validate all inputs**
9. **Implement CSRF protection**
10. **Use security headers**
