# 🔐 Storm Oracle Admin Access Setup Guide

## Overview
Storm Oracle includes a secret admin access system that allows you to grant full application access to specific email addresses without requiring payment.

## 🛠️ Configuration Setup

### 1. Backend Environment Variables
Add these to your `/app/backend/.env` file:

```env
# Admin Access Configuration
ADMIN_SECRET_CODE=STORM_ORACLE_ADMIN_2025
ADMIN_EMAILS=admin@example.com,john@company.com,jane@enterprise.com
JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production

# Email Configuration (for notifications)
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-specific-password
MAIL_FROM=noreply@stormoracle.com
MAIL_SERVER=smtp.gmail.com
```

### 2. Customize Admin Settings
```bash
# Edit the environment variables
nano /app/backend/.env

# Update with your preferred values:
ADMIN_SECRET_CODE=YOUR_CUSTOM_SECRET_CODE_2025
ADMIN_EMAILS=youremail@domain.com,admin2@domain.com
```

### 3. Restart Backend Service
```bash
# Apply configuration changes
sudo supervisorctl restart backend

# Verify backend is running
sudo supervisorctl status backend
```

## 🎯 Granting Admin Access

### Method 1: API Endpoint (Recommended)
```bash
# Use the secret admin endpoint
curl -X POST "https://your-domain.com/api/auth/admin-access" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "secret_code": "YOUR_CUSTOM_SECRET_CODE_2025"
  }'
```

### Method 2: Direct Database Update
```javascript
// MongoDB direct update (if you have database access)
db.users.updateOne(
  { "email": "user@example.com" },
  { 
    $set: { 
      "is_admin": true,
      "subscription_type": "admin",
      "email_verified": true
    }
  }
)
```

### Method 3: Admin Panel (Future Enhancement)
```javascript
// Frontend admin panel component (to be implemented)
const AdminPanel = () => {
  const grantAdminAccess = async (email) => {
    const response = await fetch('/api/auth/admin-access', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: email,
        secret_code: process.env.ADMIN_SECRET_CODE
      })
    });
    // Handle response
  };
};
```

## 🔍 Verifying Admin Access

### Check User Status:
```bash
# Verify user has admin access
curl -H "Authorization: Bearer USER_JWT_TOKEN" \
  "https://your-domain.com/api/auth/me"

# Expected response:
{
  "id": "user-uuid",
  "email": "user@example.com",
  "full_name": "User Name",
  "email_verified": true,
  "subscription_type": "admin",  # ← Should be "admin"
  "is_admin": true,              # ← Should be true
  "created_at": "2025-01-01T00:00:00Z"
}
```

### Test Premium Features:
```bash
# Test access to premium features
curl -H "Authorization: Bearer USER_JWT_TOKEN" \
  "https://your-domain.com/api/premium/advanced-features"

# Should return full feature list instead of 403 error
```

## 🚨 Security Considerations

### 1. Secure Secret Code
```bash
# Generate a strong secret code
openssl rand -base64 32

# Use this as your ADMIN_SECRET_CODE
ADMIN_SECRET_CODE=your-generated-secret-here
```

### 2. Limit Admin Emails
```env
# Only include trusted email addresses
ADMIN_EMAILS=trusted@domain.com,admin@company.com

# Avoid wildcard domains or generic emails
```

### 3. Monitor Admin Access
```python
# Add logging for admin access grants
@api_router.post("/auth/admin-access")
async def grant_admin_access(email: EmailStr, secret_code: str):
    # Log admin access attempts
    logger.info(f"Admin access attempt for {email} at {datetime.now()}")
    
    if not check_admin_secret(email, secret_code):
        logger.warning(f"Failed admin access attempt for {email}")
        raise HTTPException(status_code=403, detail="Invalid admin credentials")
    
    # Grant access and log success
    logger.info(f"Admin access granted to {email}")
```

## 📋 Admin Features Unlocked

When a user has admin access, they get:

### ✅ **All Premium Features**
- Real-time tornado tracking
- Advanced storm predictions
- Historical radar data access
- Custom alert zones
- Priority email support
- Unlimited API access
- Advanced radar data types
- Full-screen mode
- Animation controls

### ✅ **Admin-Only Features**
- User management capabilities
- System monitoring access
- Advanced ML insights
- Custom configuration options
- Database access tools
- Performance analytics

## 🔧 Admin Access Management

### List Current Admins:
```javascript
// Query all admin users
const adminUsers = await db.users.find({
  "is_admin": true,
  "subscription_type": "admin"
}).toArray();

console.log("Current Admin Users:", adminUsers);
```

### Revoke Admin Access:
```javascript
// Remove admin privileges
await db.users.updateOne(
  { "email": "user@example.com" },
  { 
    $set: { 
      "is_admin": false,
      "subscription_type": "free"  // or "premium" if they paid
    }
  }
);
```

### Batch Admin Management:
```python
# Python script for batch admin operations
import os
from motor.motor_asyncio import AsyncIOMotorClient

async def manage_admins():
    # Connect to database
    client = AsyncIOMotorClient(os.environ.get('MONGO_URL'))
    db = client[os.environ.get('DB_NAME')]
    
    # Get admin emails from environment
    admin_emails = os.environ.get('ADMIN_EMAILS', '').split(',')
    
    # Grant admin access to all listed emails
    for email in admin_emails:
        if email.strip():
            await db.users.update_one(
                {"email": email.strip()},
                {"$set": {
                    "is_admin": True,
                    "subscription_type": "admin",
                    "email_verified": True
                }},
                upsert=False  # Only update existing users
            )
            print(f"Admin access granted to: {email}")

# Run the script
if __name__ == "__main__":
    import asyncio
    asyncio.run(manage_admins())
```

## 🎭 Testing Admin Access

### 1. Create Test User:
```bash
# Register a test user
curl -X POST "https://your-domain.com/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpassword123",
    "full_name": "Test User"
  }'
```

### 2. Grant Admin Access:
```bash
# Grant admin access using secret code
curl -X POST "https://your-domain.com/api/auth/admin-access" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "secret_code": "YOUR_CUSTOM_SECRET_CODE_2025"
  }'
```

### 3. Login and Test:
```bash
# Login as admin user
curl -X POST "https://your-domain.com/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpassword123"
  }'

# Use returned JWT token to access premium features
```

## 🔄 Environment-Specific Configuration

### Development Environment:
```env
ADMIN_SECRET_CODE=DEV_ADMIN_2025
ADMIN_EMAILS=dev@localhost,admin@localhost
```

### Production Environment:
```env
ADMIN_SECRET_CODE=PROD_SUPER_SECRET_ADMIN_CODE_2025
ADMIN_EMAILS=admin@stormoracle.com,ceo@company.com
```

This admin system gives you complete control over who gets full access to Storm Oracle without requiring payment processing.