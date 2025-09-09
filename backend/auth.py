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
    TRIAL = "trial"  # One-week free trial
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

# Trial and subscription utilities
def is_trial_active(user_data: dict) -> bool:
    """Check if user's trial period is still active"""
    if user_data.get("subscription_type") != UserType.TRIAL:
        return False
    
    trial_end = user_data.get("trial_end")
    if not trial_end:
        return False
    
    try:
        # Handle both string and datetime objects
        if isinstance(trial_end, str):
            trial_end_date = datetime.fromisoformat(trial_end.replace('Z', '+00:00'))
        else:
            trial_end_date = trial_end
        
        return datetime.now(timezone.utc) < trial_end_date
    except:
        return False

def get_trial_days_remaining(user_data: dict) -> int:
    """Get number of days remaining in trial"""
    if not is_trial_active(user_data):
        return 0
    
    trial_end = user_data.get("trial_end")
    if not trial_end:
        return 0
    
    try:
        if isinstance(trial_end, str):
            trial_end_date = datetime.fromisoformat(trial_end.replace('Z', '+00:00'))
        else:
            trial_end_date = trial_end
        
        remaining = trial_end_date - datetime.now(timezone.utc)
        return max(0, remaining.days)
    except:
        return 0

def start_free_trial(user_id: str) -> dict:
    """Start a 7-day free trial for premium features"""
    trial_start = datetime.now(timezone.utc)
    trial_end = trial_start + timedelta(days=7)
    
    return {
        "subscription_type": UserType.TRIAL,
        "trial_start": trial_start.isoformat(),
        "trial_end": trial_end.isoformat(),
        "trial_activated": True
    }

# User subscription utilities
def check_subscription_limits(user_type: str, feature: str) -> bool:
    """Check if user can access feature based on subscription"""
    if user_type == UserType.ADMIN:
        return True
    
    if user_type == UserType.PREMIUM:
        return True
    
    # Trial users get full premium access during trial period
    if user_type == UserType.TRIAL:
        return True
    
    # Enhanced FREE TIER features - New updated requirements
    free_features = [
        # Core radar features
        "live_2d_radar_data",     # Live 2D radar data access
        "manual_radar_selection", # Manual radar station selection
        "nearest_radar_auto",     # Auto-select nearest radar to user location
        
        # Map controls and interaction
        "all_map_controls",       # Full access to all map controls
        "zoom_controls",          # Map zoom functionality
        "pan_controls",           # Map panning functionality
        "fullscreen_toggle",      # Fullscreen map view
        
        # Animation features
        "radar_animation",        # Live radar data looping
        "auto_loop_start",        # Auto-start looping on app load
        "normal_speed_default",   # Normal speed looping by default
        "5x_max_speed",           # Up to 5x animation speed
        "100_frame_maximum",      # Maximum 100 frames for animation
        
        # AI and prediction features
        "location_based_ai",      # AI prediction alerts based on user's location
        "visual_prediction_access", # Access to visual data from AI predictions
        "basic_tornado_alerts",   # Basic tornado warning system
        "storm_tracking_basic",   # Basic storm cell tracking
        
        # Data access
        "realtime_data_access",   # Access to real-time weather data
        "weather_alerts",         # Basic weather alert notifications
        "radar_station_info",     # Information about radar stations
    ]
    
    return feature in free_features

def get_subscription_limits(user_type: str) -> dict:
    """Get detailed subscription limits for user type"""
    if user_type == UserType.ADMIN:
        return {
            "max_frames": -1,  # Unlimited
            "max_speed": -1,   # Unlimited
            "api_calls_per_month": -1,  # Unlimited
            "radar_stations": -1,  # All stations
            "historical_data_days": -1,  # Unlimited
            "custom_alert_zones": -1,  # Unlimited
            "radar_data_types": ["2d", "3d", "velocity", "reflectivity", "storm_relative"],
            "advanced_ml_predictions": True,
            "priority_support": True,
        }
    
    if user_type == UserType.PREMIUM:
        return {
            "max_frames": -1,  # Unlimited frames for premium
            "max_speed": -1,   # Unlimited speed
            "api_calls_per_month": -1,  # Unlimited API calls
            "radar_stations": -1,  # All stations
            "historical_data_days": -1,  # Unlimited historical data
            "custom_alert_zones": -1,  # Unlimited custom alert zones
            "radar_data_types": ["2d", "3d", "velocity", "reflectivity", "storm_relative", "differential_reflectivity"],
            "advanced_ml_predictions": True,  # Full ML tornado prediction system
            "real_time_tracking": True,       # Real-time storm tracking
            "advanced_radar_controls": True,  # All advanced radar controls
            "enhanced_ai_alerts": True,       # Enhanced AI alert system
            "detailed_predictions": True,     # Detailed prediction data
            "chatbot_access": True,          # AI chatbot for queries
            "priority_support": True,        # Priority customer support
            "export_data": True,             # Data export capabilities
        }
    
    # Enhanced FREE TIER limits - Updated as per user requirements
    return {
        "max_frames": 100,  # Maximum 100 frames for animation
        "max_speed": 5.0,   # Maximum 5x animation speed
        "api_calls_per_month": 500,  # Increased from 100 to 500 for better UX
        "radar_stations": -1,  # Access to all radar stations
        "historical_data_days": 0,  # No historical data access
        "custom_alert_zones": 1,  # 1 location-based alert zone
        "radar_data_types": ["2d", "reflectivity"],  # Live 2D radar data only
        "advanced_ml_predictions": False,  # Basic predictions only
        "real_time_tracking": True,        # Live radar data looping
        "manual_radar_selection": True,    # Manual radar station selection
        "nearest_radar_auto": True,        # Auto-select nearest radar
        "all_map_controls": True,          # Full access to map controls
        "auto_loop_on_load": True,         # Auto-start looping on app load
        "location_based_ai": True,         # AI predictions for user location
        "visual_prediction_access": True,  # Can see visual prediction data
    }

# Admin access secret method
def check_admin_secret(email: str, secret_code: str) -> bool:
    """Secret method to grant admin access"""
    admin_secret = os.environ.get('ADMIN_SECRET_CODE', 'STORM_ORACLE_ADMIN_2025')
    admin_emails = os.environ.get('ADMIN_EMAILS', '').split(',')
    
    return secret_code == admin_secret and email in admin_emails