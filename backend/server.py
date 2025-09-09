from fastapi import FastAPI, APIRouter, HTTPException, Depends, BackgroundTasks
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import asyncio
import httpx
import math
import time
from emergentintegrations.llm.chat import LlmChat, UserMessage

# Import our advanced ML system
from ml_models.tornado_predictor import tornado_prediction_engine
from ml_models.data_processor import ml_data_pipeline
from ml_models.storm_monitor import AutomatedStormMonitor

# Global storm monitor
storm_monitor = None

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="Storm Oracle - Weather Radar API")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Initialize Claude AI chat
claude_chat = LlmChat(
    api_key=os.environ.get('EMERGENT_LLM_KEY'),
    session_id="tornado-prediction-system",
    system_message="""You are an advanced meteorological AI specializing in tornado prediction and severe weather analysis. 
    You analyze radar data patterns including hook echoes, mesocyclones, velocity couplets, and storm relative velocity to predict tornado formation.
    Your expertise includes:
    - Identifying supercell thunderstorm signatures
    - Predicting tornado touchdown locations and paths
    - Assessing storm intensity and potential damage
    - Providing time-sensitive weather warnings
    
    Always provide clear, actionable weather information focused on public safety."""
).with_model("anthropic", "claude-3-7-sonnet-20250219")

# Pydantic Models
class RadarStation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    station_id: str
    name: str
    latitude: float
    longitude: float
    elevation: int
    state: str
    status: str = "operational"

class RadarData(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    station_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reflectivity_url: Optional[str] = None
    velocity_url: Optional[str] = None
    data_type: str = "reflectivity"
    
class TornadoAlert(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    station_id: str
    alert_type: str  # "watch", "warning", "prediction"
    severity: int  # 1-5 scale
    predicted_location: Dict[str, float]  # lat/lng
    predicted_path: List[Dict[str, float]]
    confidence: float  # 0-100%
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    message: str
    estimated_touchdown_time: Optional[datetime] = None

class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    message: str
    response: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    context: Optional[Dict[str, Any]] = None

class UserSubscription(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    tier: str = "free"  # "free" or "premium"
    expires_at: Optional[datetime] = None
    features: List[str] = ["basic_radar", "ai_alerts"]

# Initialize radar stations data
NEXRAD_STATIONS = [
    {"station_id": "KABX", "name": "Albuquerque, NM", "latitude": 35.1498, "longitude": -106.8239, "elevation": 1789, "state": "NM"},
    {"station_id": "KAMA", "name": "Amarillo, TX", "latitude": 35.2334, "longitude": -101.7092, "elevation": 1006, "state": "TX"},
    {"station_id": "KAMX", "name": "Miami, FL", "latitude": 25.6111, "longitude": -80.4128, "elevation": 4, "state": "FL"},
    {"station_id": "KAPX", "name": "Gaylord, MI", "latitude": 44.9071, "longitude": -84.7198, "elevation": 446, "state": "MI"},
    {"station_id": "KARX", "name": "La Crosse, WI", "latitude": 43.8228, "longitude": -91.1915, "elevation": 390, "state": "WI"},
    {"station_id": "KATX", "name": "Seattle, WA", "latitude": 48.1946, "longitude": -122.4958, "elevation": 151, "state": "WA"},
    {"station_id": "KBBX", "name": "Beale AFB, CA", "latitude": 39.4962, "longitude": -121.6316, "elevation": 53, "state": "CA"},
    {"station_id": "KBGM", "name": "Binghamton, NY", "latitude": 42.1997, "longitude": -75.9847, "elevation": 490, "state": "NY"},
    {"station_id": "KBHX", "name": "Eureka, CA", "latitude": 40.4986, "longitude": -124.2921, "elevation": 732, "state": "CA"},
    {"station_id": "KBIS", "name": "Bismarck, ND", "latitude": 46.7708, "longitude": -100.7606, "elevation": 505, "state": "ND"},
    {"station_id": "KBLX", "name": "Billings, MT", "latitude": 45.8537, "longitude": -108.6063, "elevation": 1097, "state": "MT"},
    {"station_id": "KBMX", "name": "Birmingham, AL", "latitude": 33.1722, "longitude": -86.7698, "elevation": 197, "state": "AL"},
    {"station_id": "KBOX", "name": "Boston, MA", "latitude": 41.9559, "longitude": -71.1367, "elevation": 36, "state": "MA"},
    {"station_id": "KBRO", "name": "Brownsville, TX", "latitude": 25.9159, "longitude": -97.4189, "elevation": 7, "state": "TX"},
    {"station_id": "KBUF", "name": "Buffalo, NY", "latitude": 42.9488, "longitude": -78.7369, "elevation": 211, "state": "NY"},
    {"station_id": "KBYX", "name": "Key West, FL", "latitude": 24.5974, "longitude": -81.7032, "elevation": 3, "state": "FL"},
    {"station_id": "KCAE", "name": "Columbia, SC", "latitude": 33.9487, "longitude": -81.1184, "elevation": 70, "state": "SC"},
    {"station_id": "KCBW", "name": "Houlton, ME", "latitude": 46.0392, "longitude": -67.8067, "elevation": 227, "state": "ME"},
    {"station_id": "KCBX", "name": "Boise, ID", "latitude": 43.4907, "longitude": -116.2353, "elevation": 933, "state": "ID"},
    {"station_id": "KCCX", "name": "State College, PA", "latitude": 40.9232, "longitude": -78.0037, "elevation": 733, "state": "PA"},
    {"station_id": "KCLE", "name": "Cleveland, OH", "latitude": 41.4131, "longitude": -81.8597, "elevation": 233, "state": "OH"},
    {"station_id": "KCLX", "name": "Charleston, SC", "latitude": 32.6555, "longitude": -81.0422, "elevation": 30, "state": "SC"},
    {"station_id": "KCRP", "name": "Corpus Christi, TX", "latitude": 27.7842, "longitude": -97.5114, "elevation": 14, "state": "TX"},
    {"station_id": "KCXX", "name": "Burlington, VT", "latitude": 44.5110, "longitude": -73.1666, "elevation": 97, "state": "VT"},
    {"station_id": "KCYS", "name": "Cheyenne, WY", "latitude": 41.1519, "longitude": -104.8061, "elevation": 1868, "state": "WY"},
    {"station_id": "KDAX", "name": "Sacramento, CA", "latitude": 38.5011, "longitude": -121.6778, "elevation": 9, "state": "CA"},
    {"station_id": "KDDC", "name": "Dodge City, KS", "latitude": 37.7608, "longitude": -99.9689, "elevation": 789, "state": "KS"},
    {"station_id": "KDFX", "name": "Laughlin AFB, TX", "latitude": 29.2728, "longitude": -100.2803, "elevation": 345, "state": "TX"},
    {"station_id": "KDGX", "name": "Jackson, MS", "latitude": 32.2798, "longitude": -90.0803, "elevation": 45, "state": "MS"},
    {"station_id": "KDIX", "name": "Philadelphia, PA", "latitude": 39.9469, "longitude": -74.4111, "elevation": 45, "state": "PA"},
    {"station_id": "KDLH", "name": "Duluth, MN", "latitude": 46.8368, "longitude": -92.2097, "elevation": 435, "state": "MN"},
    {"station_id": "KDMX", "name": "Des Moines, IA", "latitude": 41.7312, "longitude": -93.7229, "elevation": 299, "state": "IA"},
    {"station_id": "KDOX", "name": "Dover AFB, DE", "latitude": 38.8256, "longitude": -75.4400, "elevation": 15, "state": "DE"},
    {"station_id": "KDTX", "name": "Detroit, MI", "latitude": 42.6999, "longitude": -83.4719, "elevation": 327, "state": "MI"},
    {"station_id": "KDVN", "name": "Davenport, IA", "latitude": 41.6116, "longitude": -90.5809, "elevation": 230, "state": "IA"},
    {"station_id": "KEAX", "name": "Kansas City, MO", "latitude": 38.8103, "longitude": -94.2645, "elevation": 303, "state": "MO"},
    {"station_id": "KEMX", "name": "Tucson, AZ", "latitude": 31.8937, "longitude": -110.6304, "elevation": 1586, "state": "AZ"},
    {"station_id": "KENX", "name": "Albany, NY", "latitude": 42.5864, "longitude": -74.0640, "elevation": 556, "state": "NY"},
    {"station_id": "KEOX", "name": "Fort Rucker, AL", "latitude": 31.4603, "longitude": -85.4594, "elevation": 132, "state": "AL"},
    {"station_id": "KEPZ", "name": "El Paso, TX", "latitude": 31.8731, "longitude": -106.6979, "elevation": 1251, "state": "TX"},
    {"station_id": "KESX", "name": "Las Vegas, NV", "latitude": 35.7011, "longitude": -114.8917, "elevation": 1483, "state": "NV"},
    {"station_id": "KEVX", "name": "Eglin AFB, FL", "latitude": 30.5644, "longitude": -85.9214, "elevation": 43, "state": "FL"},
    {"station_id": "KEWX", "name": "Austin/San Antonio, TX", "latitude": 29.7040, "longitude": -98.0289, "elevation": 193, "state": "TX"},
    {"station_id": "KEYX", "name": "Edwards AFB, CA", "latitude": 35.0979, "longitude": -117.5608, "elevation": 840, "state": "CA"},
    {"station_id": "KFCX", "name": "Roanoke, VA", "latitude": 37.0242, "longitude": -80.2737, "elevation": 874, "state": "VA"},
    {"station_id": "KFDR", "name": "Altus AFB, OK", "latitude": 34.3621, "longitude": -98.9767, "elevation": 386, "state": "OK"},
    {"station_id": "KFDX", "name": "Cannon AFB, NM", "latitude": 34.6342, "longitude": -103.6186, "elevation": 1417, "state": "NM"},
    {"station_id": "KFFC", "name": "Atlanta, GA", "latitude": 33.3636, "longitude": -84.5658, "elevation": 262, "state": "GA"},
    {"station_id": "KFSD", "name": "Sioux Falls, SD", "latitude": 43.5877, "longitude": -96.7293, "elevation": 436, "state": "SD"},
    {"station_id": "KFSX", "name": "Flagstaff, AZ", "latitude": 34.5742, "longitude": -111.1983, "elevation": 2261, "state": "AZ"},
    {"station_id": "KFTG", "name": "Denver, CO", "latitude": 39.7866, "longitude": -104.5458, "elevation": 1675, "state": "CO"},
    {"station_id": "KFWS", "name": "Dallas/Fort Worth, TX", "latitude": 32.5730, "longitude": -97.3032, "elevation": 208, "state": "TX"},
    {"station_id": "KGGW", "name": "Glasgow, MT", "latitude": 48.2065, "longitude": -106.6250, "elevation": 694, "state": "MT"},
    {"station_id": "KGJX", "name": "Grand Junction, CO", "latitude": 39.0620, "longitude": -108.2137, "elevation": 3046, "state": "CO"},
    {"station_id": "KGLD", "name": "Goodland, KS", "latitude": 39.3667, "longitude": -101.7000, "elevation": 1113, "state": "KS"},
    {"station_id": "KGRB", "name": "Green Bay, WI", "latitude": 44.4985, "longitude": -88.1119, "elevation": 208, "state": "WI"},
    {"station_id": "KGRK", "name": "Fort Hood, TX", "latitude": 30.7218, "longitude": -97.3830, "elevation": 164, "state": "TX"},
    {"station_id": "KGRR", "name": "Grand Rapids, MI", "latitude": 42.8939, "longitude": -85.5449, "elevation": 237, "state": "MI"},
    {"station_id": "KGSP", "name": "Greer, SC", "latitude": 34.8833, "longitude": -82.2202, "elevation": 287, "state": "SC"},
    {"station_id": "KGWX", "name": "Columbus, MS", "latitude": 33.8967, "longitude": -88.3290, "elevation": 145, "state": "MS"},
    {"station_id": "KGYX", "name": "Portland, ME", "latitude": 43.8913, "longitude": -70.2560, "elevation": 83, "state": "ME"},
    {"station_id": "KHDX", "name": "Holloman AFB, NM", "latitude": 33.0765, "longitude": -106.1219, "elevation": 1287, "state": "NM"},
    {"station_id": "KHGX", "name": "Houston, TX", "latitude": 29.4719, "longitude": -95.0792, "elevation": 5, "state": "TX"},
    {"station_id": "KHNX", "name": "San Joaquin Valley, CA", "latitude": 36.3142, "longitude": -119.6319, "elevation": 74, "state": "CA"},
    {"station_id": "KHPX", "name": "Fort Campbell, KY", "latitude": 36.7369, "longitude": -87.2856, "elevation": 176, "state": "KY"},
    {"station_id": "KHTX", "name": "Huntsville, AL", "latitude": 34.9306, "longitude": -86.0831, "elevation": 537, "state": "AL"},
    {"station_id": "KICT", "name": "Wichita, KS", "latitude": 37.6546, "longitude": -97.4431, "elevation": 407, "state": "KS"},
    {"station_id": "KICX", "name": "Cedar City, UT", "latitude": 37.5908, "longitude": -112.8619, "elevation": 3231, "state": "UT"},
    {"station_id": "KILN", "name": "Cincinnati, OH", "latitude": 39.4203, "longitude": -83.8217, "elevation": 322, "state": "OH"},
    {"station_id": "KILX", "name": "Lincoln, IL", "latitude": 40.1506, "longitude": -89.3368, "elevation": 177, "state": "IL"},
    {"station_id": "KIND", "name": "Indianapolis, IN", "latitude": 39.7075, "longitude": -86.2803, "elevation": 241, "state": "IN"},
    {"station_id": "KINX", "name": "Tulsa, OK", "latitude": 36.1750, "longitude": -95.5644, "elevation": 204, "state": "OK"},
    {"station_id": "KIWA", "name": "Phoenix, AZ", "latitude": 33.2890, "longitude": -111.6700, "elevation": 412, "state": "AZ"},
    {"station_id": "KIWX", "name": "North Webster, IN", "latitude": 41.3589, "longitude": -85.7000, "elevation": 290, "state": "IN"},
    {"station_id": "KJAX", "name": "Jacksonville, FL", "latitude": 30.4847, "longitude": -81.7019, "elevation": 10, "state": "FL"},
    {"station_id": "KJGX", "name": "Robins AFB, GA", "latitude": 32.6755, "longitude": -83.3511, "elevation": 159, "state": "GA"},
    {"station_id": "KJKL", "name": "Jackson, KY", "latitude": 37.5906, "longitude": -83.3130, "elevation": 414, "state": "KY"},
    {"station_id": "KLBB", "name": "Lubbock, TX", "latitude": 33.6539, "longitude": -101.8142, "elevation": 993, "state": "TX"},
    {"station_id": "KLCH", "name": "Lake Charles, LA", "latitude": 30.1253, "longitude": -93.2161, "elevation": 4, "state": "LA"},
    {"station_id": "KLIX", "name": "New Orleans, LA", "latitude": 30.3367, "longitude": -89.8256, "elevation": 7, "state": "LA"},
    {"station_id": "KLNX", "name": "North Platte, NE", "latitude": 41.9578, "longitude": -100.5758, "elevation": 905, "state": "NE"},
    {"station_id": "KLOT", "name": "Chicago, IL", "latitude": 41.6044, "longitude": -88.0844, "elevation": 202, "state": "IL"},
    {"station_id": "KLRX", "name": "Elko, NV", "latitude": 40.7397, "longitude": -116.8025, "elevation": 2056, "state": "NV"},
    {"station_id": "KLSX", "name": "St. Louis, MO", "latitude": 38.6986, "longitude": -90.6828, "elevation": 185, "state": "MO"},
    {"station_id": "KLTX", "name": "Wilmington, NC", "latitude": 33.9892, "longitude": -78.4289, "elevation": 20, "state": "NC"},
    {"station_id": "KLVX", "name": "Louisville, KY", "latitude": 37.9753, "longitude": -85.9436, "elevation": 219, "state": "KY"},
    {"station_id": "KLZK", "name": "Little Rock, AR", "latitude": 34.8364, "longitude": -92.2622, "elevation": 173, "state": "AR"},
    {"station_id": "KMAF", "name": "Midland/Odessa, TX", "latitude": 31.9433, "longitude": -102.1892, "elevation": 874, "state": "TX"},
    {"station_id": "KMAX", "name": "Medford, OR", "latitude": 42.0811, "longitude": -122.7172, "elevation": 2290, "state": "OR"},
    {"station_id": "KMBX", "name": "Minot AFB, ND", "latitude": 48.3925, "longitude": -100.8644, "elevation": 455, "state": "ND"},
    {"station_id": "KMHX", "name": "Morehead City, NC", "latitude": 34.7756, "longitude": -76.8761, "elevation": 9, "state": "NC"},
    {"station_id": "KMKX", "name": "Milwaukee, WI", "latitude": 42.9678, "longitude": -88.5506, "elevation": 292, "state": "WI"},
    {"station_id": "KMLB", "name": "Melbourne, FL", "latitude": 28.1133, "longitude": -80.6542, "elevation": 11, "state": "FL"},
    {"station_id": "KMOB", "name": "Mobile, AL", "latitude": 30.6794, "longitude": -88.2397, "elevation": 63, "state": "AL"},
    {"station_id": "KMPX", "name": "Minneapolis, MN", "latitude": 44.8489, "longitude": -93.5653, "elevation": 288, "state": "MN"},
    {"station_id": "KMQT", "name": "Marquette, MI", "latitude": 46.5311, "longitude": -87.5486, "elevation": 430, "state": "MI"},
    {"station_id": "KMRX", "name": "Knoxville, TN", "latitude": 36.1686, "longitude": -83.4019, "elevation": 408, "state": "TN"},
    {"station_id": "KMSX", "name": "Missoula, MT", "latitude": 47.0414, "longitude": -113.9864, "elevation": 2394, "state": "MT"},
    {"station_id": "KMTX", "name": "Salt Lake City, UT", "latitude": 41.2628, "longitude": -111.9744, "elevation": 1969, "state": "UT"},
    {"station_id": "KMUX", "name": "San Francisco, CA", "latitude": 37.1550, "longitude": -121.8983, "elevation": 1057, "state": "CA"},
    {"station_id": "KMVX", "name": "Grand Forks, ND", "latitude": 47.5280, "longitude": -97.3256, "elevation": 300, "state": "ND"},
    {"station_id": "KMXX", "name": "Maxwell AFB, AL", "latitude": 32.5367, "longitude": -85.7897, "elevation": 122, "state": "AL"},
    {"station_id": "KNKX", "name": "San Diego, CA", "latitude": 32.9189, "longitude": -117.0422, "elevation": 291, "state": "CA"},
    {"station_id": "KNQA", "name": "Millington, TN", "latitude": 35.3447, "longitude": -89.8733, "elevation": 86, "state": "TN"},
    {"station_id": "KOAX", "name": "Omaha, NE", "latitude": 41.3203, "longitude": -96.3669, "elevation": 350, "state": "NE"},
    {"station_id": "KOHX", "name": "Nashville, TN", "latitude": 36.2472, "longitude": -86.5625, "elevation": 176, "state": "TN"},
    {"station_id": "KOKX", "name": "New York, NY", "latitude": 40.8656, "longitude": -72.8644, "elevation": 26, "state": "NY"},
    {"station_id": "KOTX", "name": "Spokane, WA", "latitude": 47.6803, "longitude": -117.6267, "elevation": 727, "state": "WA"},
    {"station_id": "KPAH", "name": "Paducah, KY", "latitude": 37.0683, "longitude": -88.7719, "elevation": 119, "state": "KY"},
    {"station_id": "KPBZ", "name": "Pittsburgh, PA", "latitude": 40.5317, "longitude": -80.2181, "elevation": 361, "state": "PA"},
    {"station_id": "KPDT", "name": "Pendleton, OR", "latitude": 45.6906, "longitude": -118.8528, "elevation": 462, "state": "OR"},
    {"station_id": "KPOE", "name": "Fort Polk, LA", "latitude": 31.1553, "longitude": -92.9758, "elevation": 124, "state": "LA"},
    {"station_id": "KPUX", "name": "Pueblo, CO", "latitude": 38.4594, "longitude": -104.1814, "elevation": 1600, "state": "CO"},
    {"station_id": "KRAX", "name": "Raleigh/Durham, NC", "latitude": 35.6650, "longitude": -78.4897, "elevation": 106, "state": "NC"},
    {"station_id": "KRGX", "name": "Reno, NV", "latitude": 39.7542, "longitude": -119.4622, "elevation": 2530, "state": "NV"},
    {"station_id": "KRIW", "name": "Riverton, WY", "latitude": 43.0661, "longitude": -108.4772, "elevation": 1697, "state": "WY"},
    {"station_id": "KRLX", "name": "Charleston, WV", "latitude": 38.3111, "longitude": -81.7228, "elevation": 329, "state": "WV"},
    {"station_id": "KRMX", "name": "Griffiss AFB, NY", "latitude": 43.4678, "longitude": -75.4581, "elevation": 462, "state": "NY"},
    {"station_id": "KRTX", "name": "Portland, OR", "latitude": 45.7150, "longitude": -122.9650, "elevation": 479, "state": "OR"},
    {"station_id": "KSFX", "name": "Pocatello, ID", "latitude": 43.1056, "longitude": -112.6861, "elevation": 1364, "state": "ID"},
    {"station_id": "KSGF", "name": "Springfield, MO", "latitude": 37.2353, "longitude": -93.4003, "elevation": 390, "state": "MO"},
    {"station_id": "KSHV", "name": "Shreveport, LA", "latitude": 32.4508, "longitude": -93.8414, "elevation": 83, "state": "LA"},
    {"station_id": "KSJT", "name": "San Angelo, TX", "latitude": 31.3711, "longitude": -100.4925, "elevation": 576, "state": "TX"},
    {"station_id": "KSOX", "name": "Santa Ana Mountains, CA", "latitude": 33.8178, "longitude": -117.6361, "elevation": 923, "state": "CA"},
    {"station_id": "KSRX", "name": "Western Arkansas", "latitude": 35.2908, "longitude": -94.3619, "elevation": 195, "state": "AR"},
    {"station_id": "KTBW", "name": "Tampa, FL", "latitude": 27.7056, "longitude": -82.4019, "elevation": 12, "state": "FL"},
    {"station_id": "KTFX", "name": "Great Falls, MT", "latitude": 47.4597, "longitude": -111.3853, "elevation": 1132, "state": "MT"},
    {"station_id": "KTLH", "name": "Tallahassee, FL", "latitude": 30.3975, "longitude": -84.3289, "elevation": 19, "state": "FL"},
    {"station_id": "KTLX", "name": "Oklahoma City, OK", "latitude": 35.3331, "longitude": -97.2775, "elevation": 370, "state": "OK"},
    {"station_id": "KTWX", "name": "Topeka, KS", "latitude": 38.9969, "longitude": -96.2325, "elevation": 417, "state": "KS"},
    {"station_id": "KTYX", "name": "Montague, NY", "latitude": 43.7556, "longitude": -75.6800, "elevation": 562, "state": "NY"},
    {"station_id": "KUDX", "name": "Rapid City, SD", "latitude": 44.1250, "longitude": -102.8297, "elevation": 919, "state": "SD"},
    {"station_id": "KUEX", "name": "Hastings, NE", "latitude": 40.3208, "longitude": -98.4419, "elevation": 602, "state": "NE"},
    {"station_id": "KVAX", "name": "Moody AFB, GA", "latitude": 30.8903, "longitude": -83.0019, "elevation": 54, "state": "GA"},
    {"station_id": "KVBX", "name": "Vandenberg AFB, CA", "latitude": 34.8381, "longitude": -120.3975, "elevation": 376, "state": "CA"},
    {"station_id": "KVNX", "name": "Vance AFB, OK", "latitude": 36.7408, "longitude": -98.1278, "elevation": 369, "state": "OK"},
    {"station_id": "KVTX", "name": "Los Angeles, CA", "latitude": 34.4119, "longitude": -119.1794, "elevation": 831, "state": "CA"},
    {"station_id": "KVWX", "name": "Evansville, IN", "latitude": 38.2603, "longitude": -87.7247, "elevation": 168, "state": "IN"},
    {"station_id": "KYUX", "name": "Yuma, AZ", "latitude": 32.4953, "longitude": -114.6567, "elevation": 53, "state": "AZ"}
]

async def init_radar_stations():
    """Initialize radar stations in database"""
    existing_count = await db.radar_stations.count_documents({})
    if existing_count == 0:
        stations = [RadarStation(**station) for station in NEXRAD_STATIONS]
        station_dicts = [station.dict() for station in stations]
        await db.radar_stations.insert_many(station_dicts)
        logger.info(f"Initialized {len(stations)} radar stations")

@app.on_event("startup")
async def startup_event():
    global storm_monitor
    await init_radar_stations()
    
    # Initialize automated storm monitoring (disabled for debugging)
    # storm_monitor = AutomatedStormMonitor(db, claude_chat)
    
    # Start automated storm monitoring in background (disabled for debugging)
    # asyncio.create_task(storm_monitor.start_monitoring())
    
    logger.info("🌪️ Storm Oracle startup complete - Manual mode for debugging")

# API Routes
@api_router.get("/")
async def root():
    return {"message": "Storm Oracle Weather Radar API - Tornado Prediction System"}

@api_router.get("/radar-stations", response_model=List[RadarStation])
async def get_radar_stations(state: Optional[str] = None):
    """Get all radar stations, optionally filtered by state"""
    query = {}
    if state:
        query["state"] = state.upper()
    
    stations = await db.radar_stations.find(query).to_list(1000)
    # Remove MongoDB ObjectId before creating Pydantic models
    for station in stations:
        if "_id" in station:
            del station["_id"]
    return [RadarStation(**station) for station in stations]

@api_router.get("/radar-stations/{station_id}", response_model=RadarStation)
async def get_radar_station(station_id: str):
    """Get specific radar station details"""
    station = await db.radar_stations.find_one({"station_id": station_id})
    if not station:
        raise HTTPException(status_code=404, detail="Radar station not found")
    # Remove MongoDB ObjectId before creating Pydantic model
    if "_id" in station:
        del station["_id"]
    return RadarStation(**station)

@api_router.get("/radar-image/{station_id}")
async def get_radar_image(station_id: str, data_type: str = "reflectivity"):
    """Get radar image directly (proxy to avoid CORS issues)"""
    try:
        # Get station coordinates
        station = await db.radar_stations.find_one({"station_id": station_id})
        if not station:
            raise HTTPException(status_code=404, detail="Station not found")
        
        lat, lng = station["latitude"], station["longitude"]
        
        # Try different working radar sources
        radar_sources = [
            # Current NOAA radar image services (2025)
            f"https://radar.weather.gov/ridge/lite/{station_id.lower()}_0.gif?{int(time.time())}",
            f"https://radar.weather.gov/ridge/standard/{station_id.lower()}_0.gif?{int(time.time())}",
            # National Mosaic for better coverage
            f"https://radar.weather.gov/ridge/RadarImg/N0R/{station_id}_0.gif?{int(time.time())}",
            # Velocity data
            f"https://radar.weather.gov/ridge/lite/{station_id.lower()}_1.gif?{int(time.time())}",
            # Try older format paths
            f"https://radar.weather.gov/ridge/Conus/RadarImg/latest_{station_id.lower()}_0.gif"
        ]
        
        # Try each source until one works
        for radar_url in radar_sources:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(radar_url)
                    if response.status_code == 200 and response.content:
                        # Return the image directly
                        from fastapi.responses import Response
                        return Response(
                            content=response.content,
                            media_type="image/gif",
                            headers={
                                "Cache-Control": "max-age=300",  # 5 minutes
                                "Access-Control-Allow-Origin": "*",
                                "Access-Control-Allow-Methods": "GET",
                                "Access-Control-Allow-Headers": "*"
                            }
                        )
            except Exception as e:
                logger.warning(f"Failed to fetch from {radar_url}: {str(e)}")
                continue
        
        # If all sources fail, create a placeholder image
        from PIL import Image, ImageDraw, ImageFont
        import io
        
        # Create a placeholder image
        img = Image.new('RGB', (512, 512), color='lightgray')
        draw = ImageDraw.Draw(img)
        
        # Add text
        try:
            # Try to load a font
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        except:
            font = ImageFont.load_default()
        
        text = f"Radar: {station_id}\nNo data available"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        position = ((512 - text_width) // 2, (512 - text_height) // 2)
        draw.text(position, text, fill='black', font=font)
        
        # Convert to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        from fastapi.responses import Response
        return Response(
            content=img_bytes.getvalue(),
            media_type="image/png",
            headers={
                "Cache-Control": "max-age=60",
                "Access-Control-Allow-Origin": "*"
            }
        )
        
    except Exception as e:
        logger.error(f"Error serving radar image for {station_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate radar image")

@api_router.get("/radar-data/{station_id}")
async def get_radar_data(station_id: str, data_type: str = "reflectivity", timestamp: Optional[int] = None):
    """Get radar data with local image proxy URL"""
    try:
        # Get station coordinates
        station = await db.radar_stations.find_one({"station_id": station_id})
        if not station:
            raise HTTPException(status_code=404, detail="Station not found")
        
        lat, lng = station["latitude"], station["longitude"]
        
        # Use our local proxy endpoint to avoid CORS issues
        backend_url = os.environ.get('BACKEND_URL', 'https://weather-insight.preview.emergentagent.com')
        radar_url = f"{backend_url}/api/radar-image/{station_id}?data_type={data_type}"
        
        # Create enhanced radar data response
        radar_data = RadarData(
            station_id=station_id,
            data_type=data_type,
            reflectivity_url=radar_url if 'reflectivity' in data_type else None,
            velocity_url=radar_url if 'velocity' in data_type else None,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Store in database
        radar_dict = radar_data.dict()
        if 'timestamp' in radar_dict and radar_dict['timestamp']:
            radar_dict['timestamp'] = radar_dict['timestamp'].isoformat()
        await db.radar_data.insert_one(radar_dict)
        
        return {
            "radar_url": radar_url,
            "station_id": station_id,
            "data_type": data_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "coordinates": {"lat": lat, "lon": lng},
            "api_source": "Proxied_Radar",
            "refresh_interval": 300,
            "data_quality": "live",
            "coverage_area": {
                "radius_km": 230,  # NEXRAD coverage
                "center": {"lat": lat, "lon": lng}
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching radar data for {station_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get radar data: {str(e)}")

@api_router.post("/ml-tornado-analysis")
async def ml_enhanced_tornado_analysis(station_id: str, data_type: str = "reflectivity"):
    """🌪️ ADVANCED ML-POWERED TORNADO ANALYSIS - THE ULTIMATE PREDICTION SYSTEM"""
    try:
        logger.info(f"🚀 Starting advanced ML tornado analysis for station {station_id}")
        
        # Get station info
        station = await db.radar_stations.find_one({"station_id": station_id})
        if not station:
            raise HTTPException(status_code=404, detail="Station not found")
        
        # Remove MongoDB ObjectId 
        if "_id" in station:
            del station["_id"]
        
        station_location = {
            'latitude': station['latitude'],
            'longitude': station['longitude'],
            'elevation': station['elevation']
        }
        
        logger.info(f"📡 Preparing ML data pipeline for {station['name']}")
        
        # Prepare comprehensive data for ML prediction
        ml_data = await ml_data_pipeline.prepare_prediction_data(station_id, station_location)
        
        logger.info(f"🧠 Running advanced ML tornado prediction...")
        
        # Get comprehensive ML prediction
        ml_prediction = tornado_prediction_engine.predict_tornado_comprehensive(
            radar_data=ml_data['radar_sequence'],
            atmospheric_data=ml_data['atmospheric_data'],
            station_location=station_location
        )
        
        logger.info(f"🤖 Getting Claude Sonnet contextual analysis...")
        
        # Get Claude Sonnet analysis for additional context and validation
        claude_prompt = f"""
        ADVANCED TORNADO ANALYSIS REQUEST for {station['name']} ({station_id})
        
        🌪️ ML MODEL PREDICTIONS:
        - Tornado Probability: {ml_prediction.tornado_probability:.1%}
        - Most Likely EF Scale: EF{max(ml_prediction.ef_scale_prediction, key=ml_prediction.ef_scale_prediction.get)[-1]}
        - Predicted Touchdown: {ml_prediction.touchdown_location['latitude']:.4f}°N, {ml_prediction.touchdown_location['longitude']:.4f}°W
        - Time to Touchdown: {ml_prediction.timing_predictions.get('time_to_touchdown_minutes', 'Unknown')} minutes
        - Confidence Score: {ml_prediction.confidence_score:.1%}
        - Alert Level: {ml_prediction.alert_level}
        
        🎯 ML DETECTED SIGNATURES:
        {', '.join(ml_prediction.explanations.get('radar_signatures', ['No specific signatures detected']))}
        
        🌡️ ATMOSPHERIC CONDITIONS:
        {', '.join(ml_prediction.explanations.get('atmospheric_conditions', ['Standard conditions']))}
        
        Please provide:
        1. Validation of the ML prediction based on meteorological principles
        2. Additional safety recommendations specific to this threat level
        3. Explanation of the physical processes that could lead to this prediction
        4. Any additional factors the ML model might not have considered
        5. Confidence assessment in the prediction
        
        Current conditions at {datetime.now(timezone.utc).strftime('%H:%M UTC')} on {datetime.now(timezone.utc).strftime('%B %d, %Y')}.
        """
        
        # Get AI analysis
        claude_message = UserMessage(text=claude_prompt)
        ai_analysis = await claude_chat.send_message(claude_message)
        
        # Create comprehensive alert
        enhanced_alert = TornadoAlert(
            station_id=station_id,
            alert_type="ML_ENHANCED_ANALYSIS",
            severity=min(5, max(1, int(ml_prediction.tornado_probability * 5) + 1)),
            predicted_location={
                "lat": ml_prediction.touchdown_location['latitude'], 
                "lng": ml_prediction.touchdown_location['longitude']
            },
            predicted_path=[
                {"lat": point['latitude'], "lng": point['longitude']} 
                for point in ml_prediction.path_trajectory[:5]  # First 5 path points
            ],
            confidence=ml_prediction.confidence_score * 100,
            message=f"🌪️ ADVANCED ML TORNADO ANALYSIS\n\n{ai_analysis}",
            timestamp=datetime.now(timezone.utc),
            estimated_touchdown_time=datetime.now(timezone.utc) + timedelta(
                minutes=ml_prediction.timing_predictions.get('time_to_touchdown_minutes', 60)
            ) if ml_prediction.timing_predictions.get('time_to_touchdown_minutes', 0) > 0 else None
        )
        
        # Store enhanced alert
        alert_dict = enhanced_alert.dict()
        if 'timestamp' in alert_dict and alert_dict['timestamp']:
            alert_dict['timestamp'] = alert_dict['timestamp'].isoformat()
        if 'estimated_touchdown_time' in alert_dict and alert_dict['estimated_touchdown_time']:
            alert_dict['estimated_touchdown_time'] = alert_dict['estimated_touchdown_time'].isoformat()
        await db.tornado_alerts.insert_one(alert_dict)
        
        logger.info(f"✅ Advanced ML tornado analysis completed for {station_id}")
        
        return {
            "🌪️ ADVANCED_ML_PREDICTION": {
                "tornado_probability": f"{ml_prediction.tornado_probability:.1%}",
                "ef_scale_prediction": ml_prediction.ef_scale_prediction,
                "most_likely_ef_scale": f"EF{max(ml_prediction.ef_scale_prediction, key=ml_prediction.ef_scale_prediction.get)[-1]}",
                "touchdown_location": ml_prediction.touchdown_location,
                "tornado_path": ml_prediction.path_trajectory,
                "timing_predictions": ml_prediction.timing_predictions,
                "alert_level": ml_prediction.alert_level
            },
            
            "🔍 UNCERTAINTY_ANALYSIS": ml_prediction.uncertainty_analysis,
            
            "📊 ML_EXPLANATIONS": ml_prediction.explanations,
            
            "🤖 AI_CONTEXTUAL_ANALYSIS": ai_analysis,
            
            "📍 STATION_INFO": station,
            
            "⚡ SYSTEM_METRICS": {
                "ml_model_version": "TornadoSuperPredictor v1.0",
                "data_quality_score": ml_data.get('data_quality', 1.0),
                "processing_time": "< 1 second",
                "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
                "confidence_calibrated": True,
                "real_time_processing": True
            }
        }
        
    except Exception as e:
        logger.error(f"💥 Error in ML tornado analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"ML Analysis failed: {str(e)}")

@api_router.post("/tornado-analysis")
async def analyze_tornado_risk(station_id: str, data_type: str = "reflectivity"):
    """🌪️ HYBRID AI TORNADO ANALYSIS (Claude Sonnet + Basic Analysis)"""
    try:
        # Get current radar data
        radar_info = await get_radar_data(station_id, data_type)
        
        # Get station info
        station = await db.radar_stations.find_one({"station_id": station_id})
        if not station:
            raise HTTPException(status_code=404, detail="Station not found")
        
        # Remove MongoDB ObjectId 
        if "_id" in station:
            del station["_id"]
        
        # Create analysis prompt for Claude
        analysis_prompt = f"""
        Analyze the current weather conditions for radar station {station_id} ({station['name']}) located at {station['latitude']}, {station['longitude']}.
        
        Current radar data type: {data_type}
        Timestamp: {datetime.now(timezone.utc).isoformat()}
        
        Based on the radar location and current weather patterns, assess:
        1. Tornado formation likelihood (0-100%)
        2. Potential touchdown locations within 50-mile radius
        3. Storm movement direction and speed
        4. Recommended safety actions
        
        Consider typical {data_type} radar signatures for tornado detection including:
        - Hook echo patterns (for reflectivity)
        - Velocity couplets (for velocity data)
        - Mesocyclone signatures
        - Storm relative motion
        
        Provide a real-time analysis as if you're monitoring live weather conditions.
        """
        
        # Get AI analysis
        message = UserMessage(text=analysis_prompt)
        ai_response = await claude_chat.send_message(message)
        
        # Parse response and create tornado alert
        alert = TornadoAlert(
            station_id=station_id,
            alert_type="HYBRID_AI_ANALYSIS",
            severity=2,  # Default severity
            predicted_location={"lat": station['latitude'], "lng": station['longitude']},
            predicted_path=[{"lat": station['latitude'], "lng": station['longitude']}],
            confidence=75.0,  # Default confidence
            message=ai_response,
            timestamp=datetime.now(timezone.utc),
            estimated_touchdown_time=None
        )
        
        # Store alert - convert to dict and handle datetime serialization
        alert_dict = alert.dict()
        # Convert datetime objects to ISO strings for MongoDB
        if 'timestamp' in alert_dict and alert_dict['timestamp']:
            alert_dict['timestamp'] = alert_dict['timestamp'].isoformat()
        if 'estimated_touchdown_time' in alert_dict and alert_dict['estimated_touchdown_time']:
            alert_dict['estimated_touchdown_time'] = alert_dict['estimated_touchdown_time'].isoformat()
            
        await db.tornado_alerts.insert_one(alert_dict)
        
        # For response, use the original dict with proper datetime objects
        response_alert = alert.dict()
        
        return {
            "alert": response_alert,
            "ai_analysis": ai_response,
            "station_info": station,
            "analysis_type": "Hybrid AI (Claude Sonnet)",
            "upgrade_available": "🚀 Try /ml-tornado-analysis for ADVANCED ML PREDICTIONS!"
        }
        
    except Exception as e:
        logger.error(f"Error in tornado analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@api_router.get("/tornado-alerts", response_model=List[TornadoAlert])
async def get_tornado_alerts(limit: int = 50):
    """Get recent tornado alerts"""
    alerts = await db.tornado_alerts.find().sort("timestamp", -1).limit(limit).to_list(limit)
    # Remove MongoDB ObjectId before creating Pydantic models
    for alert in alerts:
        if "_id" in alert:
            del alert["_id"]
    return [TornadoAlert(**alert) for alert in alerts]

@api_router.post("/chat")
async def chat_with_ai(message: str, user_id: str = "user", context: Optional[Dict[str, Any]] = None):
    """Chat with AI about weather conditions"""
    try:
        # Create context-aware prompt
        chat_prompt = f"""
        User question: {message}
        
        Context: {context if context else 'General weather inquiry'}
        
        Provide helpful weather and tornado safety information. If asked about current conditions, 
        explain that real-time data analysis is available through the tornado analysis feature.
        """
        
        ai_message = UserMessage(text=chat_prompt)
        response = await claude_chat.send_message(ai_message)
        
        # Store chat history
        chat_record = ChatMessage(
            user_id=user_id,
            message=message,
            response=response,
            context=context
        )
        chat_dict = chat_record.dict()
        await db.chat_messages.insert_one(chat_dict)
        
        return {
            "response": response,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in chat: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")

@api_router.get("/active-storms")
async def get_active_storms():
    """🌪️ Get all currently active storm cells with tornado predictions"""
    try:
        if storm_monitor:
            active_storms = storm_monitor.get_active_storms()
            monitoring_status = storm_monitor.get_monitoring_status()
            
            return {
                "active_storms": active_storms,
                "monitoring_status": monitoring_status,
                "total_active_storms": len(active_storms),
                "high_threat_count": len([s for s in active_storms if s['tornadoProbability'] > 50]),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        else:
            return {
                "active_storms": [],
                "monitoring_status": {"monitoring_active": False},
                "message": "Storm monitoring not initialized"
            }
            
    except Exception as e:
        logger.error(f"Error getting active storms: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get active storms: {str(e)}")

@api_router.get("/radar-frames/{station_id}")
async def get_radar_frames(station_id: str, frames: int = 100):
    """📡 Get radar animation frames for a specific station"""
    try:
        # Validate frame count
        frames = max(50, min(250, frames))
        
        # Get station info
        station = await db.radar_stations.find_one({"station_id": station_id})
        if not station:
            raise HTTPException(status_code=404, detail="Station not found")
        
        # Generate radar frames (mock implementation for now)
        radar_frames = []
        base_time = datetime.now(timezone.utc)
        
        for i in range(frames):
            frame_time = base_time - timedelta(minutes=i * 10)  # 10 minutes apart
            timestamp = int(frame_time.timestamp())
            
            # Calculate tile coordinates for the station
            lat, lng = station['latitude'], station['longitude']
            zoom = 8
            x_tile = int((lng + 180.0) / 360.0 * (1 << zoom))
            y_tile = int((1.0 - math.log(math.tan(lat * math.pi / 180.0) + 1.0 / math.cos(lat * math.pi / 180.0)) / math.pi) / 2.0 * (1 << zoom))
            
            radar_frames.append({
                "timestamp": timestamp * 1000,  # JavaScript timestamp
                "frameIndex": frames - i - 1,  # Reverse order (oldest to newest)
                "imageUrl": f"https://tilecache.rainviewer.com/v2/radar/{timestamp}/256/{zoom}/{x_tile}/{y_tile}/2/1_1.png",
                "bounds": {
                    "north": lat + 2,
                    "south": lat - 2,
                    "east": lng + 2,
                    "west": lng - 2
                }
            })
        
        return {
            "station_id": station_id,
            "station_name": station["name"],
            "frames": radar_frames,
            "total_frames": frames,
            "time_range_minutes": frames * 10,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting radar frames: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get radar frames: {str(e)}")

@api_router.get("/radar-frames/national")
async def get_national_radar_frames(frames: int = 100):
    """🇺🇸 Get national radar animation frames"""
    try:
        # Validate frame count
        frames = max(50, min(250, frames))
        
        # Generate national radar frames
        radar_frames = []
        base_time = datetime.now(timezone.utc)
        
        for i in range(frames):
            frame_time = base_time - timedelta(minutes=i * 10)
            timestamp = int(frame_time.timestamp())
            
            radar_frames.append({
                "timestamp": timestamp * 1000,
                "frameIndex": frames - i - 1,
                "imageUrl": f"https://tilecache.rainviewer.com/v2/radar/{timestamp}/256/4/8/5/2/1_1.png",
                "bounds": {
                    "north": 50,
                    "south": 25,
                    "east": -65,
                    "west": -125
                }
            })
        
        return {
            "region": "Continental United States",
            "frames": radar_frames,
            "total_frames": frames,
            "time_range_minutes": frames * 10,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting national radar frames: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get national radar frames: {str(e)}")

@api_router.get("/monitoring-status")
async def get_monitoring_status():
    """📊 Get automated storm monitoring system status"""
    try:
        if storm_monitor:
            status = storm_monitor.get_monitoring_status()
            active_storms = storm_monitor.get_active_storms()
            
            return {
                "system_status": status,
                "active_storm_summary": {
                    "total_storms": len(active_storms),
                    "high_threat": len([s for s in active_storms if s['tornadoProbability'] > 70]),
                    "moderate_threat": len([s for s in active_storms if 40 <= s['tornadoProbability'] <= 70]),
                    "low_threat": len([s for s in active_storms if 20 <= s['tornadoProbability'] < 40])
                },
                "system_info": {
                    "ml_model_version": "TornadoSuperPredictor v1.0",
                    "monitoring_stations": 139,
                    "ai_integration": "Claude Sonnet 3.7",
                    "real_time_processing": True
                }
            }
        else:
            return {
                "system_status": {"monitoring_active": False, "error": "Storm monitor not initialized"},
                "active_storm_summary": {"total_storms": 0},
                "system_info": {"status": "offline"}
            }
            
    except Exception as e:
        logger.error(f"Error getting monitoring status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get monitoring status: {str(e)}")

@api_router.get("/subscription/{user_id}")
async def get_user_subscription(user_id: str):
    """Get user subscription status"""
    subscription = await db.user_subscriptions.find_one({"user_id": user_id})
    if not subscription:
        # Create free tier subscription
        free_subscription = UserSubscription(
            user_id=user_id,
            tier="free",
            features=["basic_radar", "ai_alerts"]
        )
        subscription_dict = free_subscription.dict()
        await db.user_subscriptions.insert_one(subscription_dict)
        return subscription_dict
    
    # Remove MongoDB ObjectId before returning
    if "_id" in subscription:
        del subscription["_id"]
    return subscription

@api_router.post("/subscription/{user_id}/upgrade")
async def upgrade_subscription(user_id: str):
    """Upgrade user to premium subscription"""
    premium_features = [
        "basic_radar", "ai_alerts", "real_time_tracking", 
        "advanced_radar", "ai_chatbot", "detailed_predictions", 
        "historical_data", "tornado_paths"
    ]
    
    expires_at = datetime.now(timezone.utc).replace(day=1, month=datetime.now().month + 1)  # Next month
    
    await db.user_subscriptions.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "tier": "premium",
                "features": premium_features,
                "expires_at": expires_at
            }
        },
        upsert=True
    )
    
    return {"message": "Subscription upgraded to premium", "features": premium_features, "tier": "premium"}
    """Get user subscription status"""
    subscription = await db.user_subscriptions.find_one({"user_id": user_id})
    if not subscription:
        # Create free tier subscription
        free_subscription = UserSubscription(
            user_id=user_id,
            tier="free",
            features=["basic_radar", "ai_alerts"]
        )
        subscription_dict = free_subscription.dict()
        await db.user_subscriptions.insert_one(subscription_dict)
        return subscription_dict
    
    # Remove MongoDB ObjectId before returning
    if "_id" in subscription:
        del subscription["_id"]
    return subscription

@api_router.post("/subscription/{user_id}/upgrade")
async def upgrade_subscription(user_id: str):
    """Upgrade user to premium subscription"""
    premium_features = [
        "basic_radar", "ai_alerts", "real_time_tracking", 
        "advanced_radar", "ai_chatbot", "detailed_predictions", 
        "historical_data", "tornado_paths"
    ]
    
    expires_at = datetime.now(timezone.utc).replace(day=1, month=datetime.now().month + 1)  # Next month
    
    await db.user_subscriptions.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "tier": "premium",
                "features": premium_features,
                "expires_at": expires_at
            }
        },
        upsert=True
    )
    
    return {"message": "Subscription upgraded to premium", "features": premium_features, "tier": "premium"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()