"""
Simple mock backend for Storm Oracle frontend development
Provides minimal API endpoints to prevent black screen
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import json
import os

app = FastAPI(title="Storm Oracle Mock Backend")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock data
MOCK_RADAR_STATIONS = [
    {
        "station_id": "KTLX",
        "name": "Oklahoma City, OK",
        "latitude": 35.333,
        "longitude": -97.278,
        "elevation": 1200,
        "state": "OK"
    },
    {
        "station_id": "KMXX",
        "name": "Maxwell AFB, AL",
        "latitude": 32.537,
        "longitude": -85.789,
        "elevation": 400,
        "state": "AL"
    },
    {
        "station_id": "KOHX",
        "name": "Nashville, TN",
        "latitude": 36.247,
        "longitude": -86.563,
        "elevation": 600,
        "state": "TN"
    }
]

MOCK_STORM_CELLS = [
    {
        "stationId": "KTLX",
        "stationName": "Oklahoma City, OK",
        "latitude": 35.5,
        "longitude": -97.3,
        "tornadoProbability": 75,
        "alertLevel": "WARNING",
        "lastUpdated": "2025-01-23T12:30:00Z",
        "predictedEFScale": 3
    }
]

MOCK_TORNADO_ALERTS = [
    {
        "id": "alert_1",
        "station_id": "KTLX",
        "alert_type": "warning",
        "severity": 3,
        "confidence": 85,
        "message": "Severe thunderstorm with tornado potential detected",
        "latitude": 35.5,
        "longitude": -97.3,
        "timestamp": "2025-01-23T12:30:00Z",
        "confirmed": False
    }
]

# API Routes
@app.get("/api/radar-stations")
async def get_radar_stations():
    """Get available radar stations"""
    return MOCK_RADAR_STATIONS

@app.get("/api/active-storms")
async def get_active_storms():
    """Get active storm cells"""
    return {"active_storms": MOCK_STORM_CELLS}

@app.get("/api/tornado-alerts")
async def get_tornado_alerts():
    """Get tornado alerts"""
    return MOCK_TORNADO_ALERTS

@app.get("/api/subscription/user123")
async def get_user_subscription():
    """Get user subscription info"""
    return {
        "tier": "free",
        "features": ["basic_radar"],
        "limits": {
            "max_frames": 100,
            "max_speed": 5.0
        }
    }

@app.get("/api/monitoring-status")
async def get_monitoring_status():
    """Get monitoring system status"""
    return {
        "system_status": {
            "monitoring_active": True
        },
        "last_check": "2025-01-23T12:30:00Z"
    }

@app.get("/api/radar-data/NATIONAL")
async def get_national_radar_data(data_type: str = "reflectivity"):
    """Get national radar data"""
    return {
        "station_id": "NATIONAL",
        "data_type": data_type,
        "timestamp": "2025-01-23T12:30:00Z",
        "bounds": {
            "north": 50,
            "south": 20,
            "east": -60,
            "west": -130
        }
    }

@app.get("/api/radar-data/{station_id}")
async def get_station_radar_data(station_id: str, data_type: str = "reflectivity"):
    """Get station-specific radar data"""
    station = next((s for s in MOCK_RADAR_STATIONS if s["station_id"] == station_id), None)
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")

    return {
        "station_id": station_id,
        "data_type": data_type,
        "timestamp": "2025-01-23T12:30:00Z",
        "bounds": {
            "north": station["latitude"] + 2.5,
            "south": station["latitude"] - 2.5,
            "east": station["longitude"] + 2.5,
            "west": station["longitude"] - 2.5
        }
    }

@app.get("/api/radar-image/{station_id}")
async def get_radar_image(station_id: str, data_type: str = "reflectivity", frame_time: float = None):
    """Mock radar image endpoint - returns a placeholder image"""
    from fastapi.responses import Response

    # Create a simple 1x1 transparent PNG as a placeholder
    # This is a minimal PNG data URL decoded to bytes
    png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82'

    return Response(content=png_data, media_type="image/png")

@app.get("/api/radar-image/national")
async def get_national_radar_image(data_type: str = "reflectivity", frame_time: float = None):
    """Mock national radar image endpoint - returns a placeholder image"""
    from fastapi.responses import Response

    # Create a simple 1x1 transparent PNG as a placeholder
    png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82'

    return Response(content=png_data, media_type="image/png")

# Auth endpoints (mock)
@app.post("/api/auth/login")
async def login():
    """Mock login"""
    return {
        "access_token": "mock_token_123",
        "token_type": "bearer",
        "user": {
            "id": "user123",
            "email": "user@example.com",
            "full_name": "Test User",
            "subscription_type": "free"
        }
    }

@app.get("/api/auth/me")
async def get_current_user():
    """Mock current user"""
    return {
        "user_id": "user123",
        "email": "user@example.com"
    }

@app.get("/api/subscription/features")
async def get_subscription_features():
    """Mock subscription features"""
    return {
        "subscription_type": "free",
        "limits": {
            "max_frames": 100,
            "max_speed": 5.0
        },
        "trial_info": {"is_trial": False}
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
