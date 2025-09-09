"""
Authentication system for Storm Oracle
Handles user registration, login, email verification, and password reset
"""

import os
import secrets
import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from pydantic import BaseModel, EmailStr
from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi_mail import FastMail, MessageSchema, MessageType, ConnectionConfig
import logging

logger = logging.getLogger(__name__)

# JWT Configuration
SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'storm-oracle-super-secret-key-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 30

# Email Configuration
MAIL_CONFIG = ConnectionConfig(
    MAIL_USERNAME=os.environ.get('MAIL_USERNAME', 'noreply@stormoracle.com'),
    MAIL_PASSWORD=os.environ.get('MAIL_PASSWORD', 'dummy-password'),
    MAIL_FROM=os.environ.get('MAIL_FROM', 'noreply@stormoracle.com'),
    MAIL_PORT=587,
    MAIL_SERVER=os.environ.get('MAIL_SERVER', 'smtp.gmail.com'),
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

fastmail = FastMail(MAIL_CONFIG)

# Security
security = HTTPBearer()

# User Models
class UserBase(BaseModel):
    email: EmailStr
    full_name: str

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: str
    email_verified: bool
    subscription_type: str
    is_admin: bool
    created_at: datetime

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse

class PasswordReset(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

class EmailVerification(BaseModel):
    token: str

# User Types
class UserType:
    FREE = "free"
    PREMIUM = "premium"
    ADMIN = "admin"

# Password utilities
def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

# JWT utilities
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict):
    """Create JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str, token_type: str = "access") -> dict:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != token_type:
            raise HTTPException(status_code=401, detail="Invalid token type")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Email verification utilities
def generate_verification_token() -> str:
    """Generate secure verification token"""
    return secrets.token_urlsafe(32)

async def send_verification_email(email: str, token: str, user_name: str):
    """Send email verification email"""
    try:
        verification_url = f"http://localhost:3000/verify-email?token={token}"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 10px; color: white; text-align: center;">
                <h1 style="margin: 0; font-size: 28px;">🌪️ Storm Oracle</h1>
                <p style="margin: 10px 0 0 0; opacity: 0.9;">Advanced Weather Radar Intelligence</p>
            </div>
            
            <div style="padding: 30px; background: #f8f9fa; border-radius: 10px; margin-top: 20px;">
                <h2 style="color: #333; margin-top: 0;">Welcome, {user_name}!</h2>
                <p style="color: #666; line-height: 1.6;">
                    Thank you for signing up for Storm Oracle. To get started with real-time weather monitoring and AI-powered storm prediction, please verify your email address.
                </p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{verification_url}" style="background: #667eea; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">
                        Verify Email Address
                    </a>
                </div>
                
                <p style="color: #888; font-size: 14px; text-align: center;">
                    This link will expire in 24 hours. If you didn't create an account, please ignore this email.
                </p>
            </div>
        </body>
        </html>
        """
        
        message = MessageSchema(
            subject="Welcome to Storm Oracle - Verify Your Email",
            recipients=[email],
            body=html_content,
            subtype=MessageType.html
        )
        
        await fastmail.send_message(message)
        logger.info(f"Verification email sent to {email}")
        
    except Exception as e:
        logger.error(f"Failed to send verification email to {email}: {str(e)}")
        # Don't raise exception - user creation should succeed even if email fails

async def send_password_reset_email(email: str, token: str, user_name: str):
    """Send password reset email"""
    try:
        reset_url = f"http://localhost:3000/reset-password?token={token}"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 10px; color: white; text-align: center;">
                <h1 style="margin: 0; font-size: 28px;">🌪️ Storm Oracle</h1>
                <p style="margin: 10px 0 0 0; opacity: 0.9;">Password Reset Request</p>
            </div>
            
            <div style="padding: 30px; background: #f8f9fa; border-radius: 10px; margin-top: 20px;">
                <h2 style="color: #333; margin-top: 0;">Hi {user_name},</h2>
                <p style="color: #666; line-height: 1.6;">
                    We received a request to reset your Storm Oracle password. Click the button below to create a new password.
                </p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}" style="background: #dc3545; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">
                        Reset Password
                    </a>
                </div>
                
                <p style="color: #888; font-size: 14px; text-align: center;">
                    This link will expire in 1 hour. If you didn't request this, please ignore this email.
                </p>
            </div>
        </body>
        </html>
        """
        
        message = MessageSchema(
            subject="Storm Oracle - Password Reset Request",
            recipients=[email],
            body=html_content,
            subtype=MessageType.html
        )
        
        await fastmail.send_message(message)
        logger.info(f"Password reset email sent to {email}")
        
    except Exception as e:
        logger.error(f"Failed to send password reset email to {email}: {str(e)}")

# Authentication dependency
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Get current authenticated user"""
    payload = verify_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"user_id": user_id, "email": payload.get("email")}

async def get_admin_user(current_user: dict = Depends(get_current_user)) -> dict:
    """Require admin privileges"""
    # This will be implemented with database check
    return current_user

# User subscription utilities
def check_subscription_limits(user_type: str, feature: str) -> bool:
    """Check if user can access feature based on subscription"""
    if user_type == UserType.ADMIN:
        return True
    
    if user_type == UserType.PREMIUM:
        return True
    
    # Free user limitations
    free_features = [
        "basic_radar",
        "national_view", 
        "basic_alerts",
        "station_selection"
    ]
    
    return feature in free_features

# Admin access secret method
def check_admin_secret(email: str, secret_code: str) -> bool:
    """Secret method to grant admin access"""
    admin_secret = os.environ.get('ADMIN_SECRET_CODE', 'STORM_ORACLE_ADMIN_2025')
    admin_emails = os.environ.get('ADMIN_EMAILS', '').split(',')
    
    return secret_code == admin_secret and email in admin_emails