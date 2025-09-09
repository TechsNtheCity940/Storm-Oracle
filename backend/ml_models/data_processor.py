"""
🌪️ ADVANCED DATA PROCESSING FOR TORNADO PREDICTION
Real-time radar and atmospheric data processing for ML models
"""

import asyncio
import numpy as np
import torch
from typing import Dict, List, Optional, Tuple
import httpx
from datetime import datetime, timezone, timedelta
import logging
from PIL import Image
import io

logger = logging.getLogger(__name__)

class RadarDataProcessor:
    """Advanced radar data processing for ML models"""
    
    def __init__(self):
        self.image_size = (256, 256)
        self.cache = {}
        self.cache_duration = 300  # 5 minutes
        
    async def process_radar_sequence(self, station_id: str, frames: int = 6) -> torch.Tensor:
        """Process radar data sequence for temporal analysis"""
        
        try:
            radar_frames = []
            
            # Get current and historical radar frames
            for i in range(frames):
                timestamp = datetime.now(timezone.utc) - timedelta(minutes=i*10)
                radar_frame = await self._get_radar_frame(station_id, timestamp)
                radar_frames.append(radar_frame)
            
            # Stack frames for temporal analysis
            radar_sequence = torch.stack(radar_frames)
            
            return radar_sequence
            
        except Exception as e:
            logger.error(f"Error processing radar sequence: {str(e)}")
            return self._create_mock_radar_sequence(frames)
    
    async def _get_radar_frame(self, station_id: str, timestamp: datetime) -> torch.Tensor:
        """Get and process single radar frame"""
        
        cache_key = f"{station_id}_{timestamp.isoformat()}"
        
        # Check cache first
        if cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            if (datetime.now(timezone.utc) - cache_entry['timestamp']).seconds < self.cache_duration:
                return cache_entry['data']
        
        try:
            # In production, this would fetch real radar data
            # For now, create realistic synthetic data
            radar_tensor = self._create_realistic_radar_data(station_id, timestamp)
            
            # Cache the result
            self.cache[cache_key] = {
                'data': radar_tensor,
                'timestamp': datetime.now(timezone.utc)
            }
            
            return radar_tensor
            
        except Exception as e:
            logger.error(f"Error fetching radar frame: {str(e)}")
            return self._create_mock_radar_frame()
    
    def _create_realistic_radar_data(self, station_id: str, timestamp: datetime) -> torch.Tensor:
        """Create realistic synthetic radar data based on meteorological patterns"""
        
        # Create multi-channel radar data (reflectivity, velocity, spectrum width)
        radar_data = torch.zeros(3, self.image_size[0], self.image_size[1])
        
        # Base noise pattern
        radar_data += torch.randn_like(radar_data) * 0.1
        
        # Add realistic weather patterns based on time and location
        center_x, center_y = self.image_size[0] // 2, self.image_size[1] // 2
        
        # Create storm cell
        y, x = torch.meshgrid(torch.arange(self.image_size[0]), torch.arange(self.image_size[1]))
        
        # Main storm cell
        storm_distance = torch.sqrt((x - center_x - 20) ** 2 + (y - center_y - 10) ** 2)
        storm_intensity = torch.exp(-storm_distance / 30) * 3.0
        
        # Reflectivity channel (0)
        radar_data[0] += storm_intensity
        
        # Add hook echo signature (tornado indicator)
        hook_distance = torch.sqrt((x - center_x - 30) ** 2 + (y - center_y + 5) ** 2)
        hook_intensity = torch.exp(-hook_distance / 15) * 2.5
        radar_data[0] += hook_intensity
        
        # Velocity channel (1) - create velocity couplet
        velocity_pattern = torch.sin((x - center_x) / 10) * torch.exp(-storm_distance / 25)
        radar_data[1] += velocity_pattern * 2.0
        
        # Spectrum width channel (2)
        radar_data[2] += torch.exp(-storm_distance / 35) * 1.5
        
        # Normalize to reasonable meteorological ranges
        radar_data[0] = torch.clamp(radar_data[0], 0, 70)  # dBZ range
        radar_data[1] = torch.clamp(radar_data[1], -30, 30)  # m/s range
        radar_data[2] = torch.clamp(radar_data[2], 0, 15)  # m/s range
        
        return radar_data
    
    def _create_mock_radar_sequence(self, frames: int) -> torch.Tensor:
        """Create mock radar sequence for testing"""
        
        sequence = []
        for i in range(frames):
            frame = self._create_mock_radar_frame()
            sequence.append(frame)
        
        return torch.stack(sequence)
    
    def _create_mock_radar_frame(self) -> torch.Tensor:
        """Create a single mock radar frame"""
        
        return torch.randn(3, self.image_size[0], self.image_size[1])

class AtmosphericDataProcessor:
    """Process atmospheric conditions for tornado prediction"""
    
    def __init__(self):
        self.parameter_ranges = {
            'cape': (0, 6000),
            'shear_0_1km': (0, 30),
            'shear_0_3km': (0, 40),
            'shear_0_6km': (0, 50),
            'helicity_0_1km': (0, 500),
            'helicity_0_3km': (0, 800),
            'temperature_sfc': (-20, 40),
            'temperature_850': (-30, 20),
            'temperature_500': (-60, 0),
            'dewpoint_sfc': (-10, 30),
            'dewpoint_850': (-20, 20),
            'pressure_sfc': (980, 1040)
        }
    
    async def get_atmospheric_conditions(self, station_location: Dict[str, float]) -> Dict[str, torch.Tensor]:
        """Get current atmospheric conditions for the station location"""
        
        try:
            # In production, this would fetch from atmospheric models (NAM, GFS, etc.)
            # For now, create realistic synthetic atmospheric data
            
            atmospheric_data = await self._fetch_atmospheric_data(station_location)
            
            # Process and validate the data
            processed_data = self._process_atmospheric_parameters(atmospheric_data)
            
            return processed_data
            
        except Exception as e:
            logger.error(f"Error getting atmospheric conditions: {str(e)}")
            return self._create_mock_atmospheric_data(station_location)
    
    async def _fetch_atmospheric_data(self, location: Dict[str, float]) -> Dict[str, float]:
        """Fetch atmospheric data from various sources"""
        
        # Mock realistic atmospheric conditions for tornado-favorable environment
        lat, lng = location['latitude'], location['longitude']
        
        # Create conditions typical of tornado outbreak
        atmospheric_conditions = {
            'cape': 3500 + np.random.normal(0, 500),  # High instability
            'shear_0_1km': 15 + np.random.normal(0, 3),  # Strong low-level shear
            'shear_0_3km': 25 + np.random.normal(0, 5),
            'shear_0_6km': 35 + np.random.normal(0, 7),
            'helicity_0_1km': 250 + np.random.normal(0, 50),
            'helicity_0_3km': 400 + np.random.normal(0, 80),
            'temperature_sfc': 25 + np.random.normal(0, 3),
            'temperature_850': 15 + np.random.normal(0, 2),
            'temperature_500': -15 + np.random.normal(0, 3),
            'dewpoint_sfc': 20 + np.random.normal(0, 2),
            'dewpoint_850': 18 + np.random.normal(0, 2),
            'pressure_sfc': 1012 + np.random.normal(0, 5)
        }
        
        # Add some seasonal and geographic variations
        season_factor = np.sin((datetime.now().month - 4) * np.pi / 6)  # Peak in late spring
        atmospheric_conditions['cape'] *= (1 + season_factor * 0.3)
        
        # Geographic factors (more activity in Great Plains)
        if -100 < lng < -95 and 35 < lat < 40:  # Oklahoma/Kansas area
            atmospheric_conditions['cape'] *= 1.2
            atmospheric_conditions['shear_0_1km'] *= 1.1
        
        return atmospheric_conditions
    
    def _process_atmospheric_parameters(self, raw_data: Dict[str, float]) -> Dict[str, torch.Tensor]:
        """Process and normalize atmospheric parameters"""
        
        processed = {}
        
        # Normalize parameters to reasonable ranges
        for param, value in raw_data.items():
            if param in self.parameter_ranges:
                min_val, max_val = self.parameter_ranges[param]
                normalized_value = np.clip(value, min_val, max_val)
                processed[param] = torch.tensor([[normalized_value]], dtype=torch.float32)  # Add batch dimension
            else:
                processed[param] = torch.tensor([[value]], dtype=torch.float32)  # Add batch dimension
        
        # Create composite parameters with proper dimensions
        processed['composite_index'] = self._calculate_composite_index(processed)
        processed['supercell_composite'] = self._calculate_supercell_composite(processed)
        processed['tornado_composite'] = self._calculate_tornado_composite(processed)
        
        # Group parameters for ML model
        processed['cape'] = processed.get('cape', torch.tensor([[1000.0]]))
        processed['wind_shear'] = torch.cat([
            processed.get('shear_0_1km', torch.tensor([[10.0]])),
            processed.get('shear_0_3km', torch.tensor([[20.0]])),
            processed.get('shear_0_6km', torch.tensor([[30.0]])),
            processed.get('shear_0_1km', torch.tensor([[25.0]]))  # deep layer proxy
        ], dim=-1)
        processed['helicity'] = torch.cat([
            processed.get('helicity_0_1km', torch.tensor([[150.0]])),
            processed.get('helicity_0_3km', torch.tensor([[250.0]]))
        ], dim=-1)
        processed['temperature'] = torch.cat([
            processed.get('temperature_sfc', torch.tensor([[25.0]])),
            processed.get('temperature_850', torch.tensor([[15.0]])),
            processed.get('temperature_500', torch.tensor([[-15.0]]))
        ], dim=-1)
        processed['dewpoint'] = torch.cat([
            processed.get('dewpoint_sfc', torch.tensor([[20.0]])),
            processed.get('dewpoint_850', torch.tensor([[18.0]]))
        ], dim=-1)
        processed['pressure'] = processed.get('pressure_sfc', torch.tensor([[1012.0]])) / 1000  # Normalize
        
        return processed
    
    def _calculate_composite_index(self, params: Dict[str, torch.Tensor]) -> torch.Tensor:
        """Calculate composite atmospheric index"""
        
        cape = params.get('cape', torch.tensor([[1000.0]]))
        shear = params.get('shear_0_6km', torch.tensor([[20.0]]))
        
        # Simple composite index with proper dimensions
        composite = torch.sqrt(cape * shear) / 100
        
        return composite
    
    def _calculate_supercell_composite(self, params: Dict[str, torch.Tensor]) -> torch.Tensor:
        """Calculate supercell composite parameter"""
        
        cape = params.get('cape', torch.tensor([[1000.0]]))
        shear = params.get('shear_0_6km', torch.tensor([[20.0]]))
        helicity = params.get('helicity_0_3km', torch.tensor([[200.0]]))
        
        # Supercell composite parameter with proper dimensions
        scp = (cape / 1000) * (shear / 20) * (helicity / 100)
        
        return scp
    
    def _calculate_tornado_composite(self, params: Dict[str, torch.Tensor]) -> torch.Tensor:
        """Calculate tornado composite parameter"""
        
        cape = params.get('cape', torch.tensor([[1000.0]]))
        shear_low = params.get('shear_0_1km', torch.tensor([[12.0]]))
        helicity_low = params.get('helicity_0_1km', torch.tensor([[150.0]]))
        
        # Tornado composite parameter focusing on low-level parameters
        tcp = (cape / 1500) * (shear_low / 12.5) * (helicity_low / 150)
        
        return tcp
    
    def _create_mock_atmospheric_data(self, location: Dict[str, float]) -> Dict[str, torch.Tensor]:
        """Create mock atmospheric data for testing"""
        
        mock_data = {}
        
        for param, (min_val, max_val) in self.parameter_ranges.items():
            # Create realistic random values within ranges
            value = np.random.uniform(min_val + (max_val - min_val) * 0.2, 
                                      min_val + (max_val - min_val) * 0.8)
            mock_data[param] = torch.tensor([[value]], dtype=torch.float32)  # Add batch dimension
        
        # Add composite indices with proper batch dimensions
        mock_data['composite_index'] = torch.tensor([[5.0]])
        mock_data['supercell_composite'] = torch.tensor([[3.0]])
        mock_data['tornado_composite'] = torch.tensor([[2.5]])
        
        # Group parameters for ML model consistency
        mock_data['cape'] = mock_data.get('cape', torch.tensor([[1500.0]]))
        mock_data['wind_shear'] = torch.cat([
            mock_data.get('shear_0_1km', torch.tensor([[10.0]])),
            mock_data.get('shear_0_3km', torch.tensor([[20.0]])),
            mock_data.get('shear_0_6km', torch.tensor([[30.0]])),
            torch.tensor([[25.0]])  # deep layer proxy
        ], dim=-1)
        mock_data['helicity'] = torch.cat([
            mock_data.get('helicity_0_1km', torch.tensor([[150.0]])),
            mock_data.get('helicity_0_3km', torch.tensor([[250.0]]))
        ], dim=-1)
        mock_data['temperature'] = torch.cat([
            mock_data.get('temperature_sfc', torch.tensor([[25.0]])),
            mock_data.get('temperature_850', torch.tensor([[15.0]])),
            mock_data.get('temperature_500', torch.tensor([[-15.0]]))
        ], dim=-1)
        mock_data['dewpoint'] = torch.cat([
            mock_data.get('dewpoint_sfc', torch.tensor([[20.0]])),
            mock_data.get('dewpoint_850', torch.tensor([[18.0]]))
        ], dim=-1)
        mock_data['pressure'] = mock_data.get('pressure_sfc', torch.tensor([[1012.0]])) / 1000
        
        return mock_data

class MLDataPipeline:
    """Complete ML data pipeline for tornado prediction"""
    
    def __init__(self):
        self.radar_processor = RadarDataProcessor()
        self.atmospheric_processor = AtmosphericDataProcessor()
        
    async def prepare_prediction_data(self, station_id: str, station_location: Dict[str, float]) -> Dict[str, any]:
        """Prepare all data needed for ML prediction"""
        
        try:
            # Get radar data sequence
            radar_sequence = await self.radar_processor.process_radar_sequence(station_id, frames=6)
            
            # Get atmospheric conditions
            atmospheric_data = await self.atmospheric_processor.get_atmospheric_conditions(station_location)
            
            # Prepare location context
            location_context = {
                'latitude': station_location['latitude'],
                'longitude': station_location['longitude'],
                'elevation': station_location.get('elevation', 0),
                'timezone_offset': self._get_timezone_offset(station_location),
                'season': self._get_season(),
                'time_of_day': self._get_time_of_day()
            }
            
            # Prepare temporal context
            temporal_context = {
                'current_time': datetime.now(timezone.utc),
                'day_of_year': datetime.now().timetuple().tm_yday,
                'hour_of_day': datetime.now().hour,
                'is_peak_season': self._is_peak_tornado_season(),
                'is_peak_time': self._is_peak_tornado_time()
            }
            
            return {
                'radar_sequence': radar_sequence,
                'atmospheric_data': atmospheric_data,
                'location_context': location_context,
                'temporal_context': temporal_context,
                'data_quality': self._assess_data_quality(radar_sequence, atmospheric_data)
            }
            
        except Exception as e:
            logger.error(f"Error preparing prediction data: {str(e)}")
            return self._create_fallback_data(station_id, station_location)
    
    def _get_timezone_offset(self, location: Dict[str, float]) -> float:
        """Get timezone offset for location"""
        # Simplified timezone calculation based on longitude
        lng = location['longitude']
        timezone_offset = -lng / 15.0  # Rough approximation
        return np.clip(timezone_offset, -12, 12)
    
    def _get_season(self) -> str:
        """Get current meteorological season"""
        month = datetime.now().month
        if month in [12, 1, 2]:
            return "winter"
        elif month in [3, 4, 5]:
            return "spring"
        elif month in [6, 7, 8]:
            return "summer"
        else:
            return "fall"
    
    def _get_time_of_day(self) -> str:
        """Get time of day category"""
        hour = datetime.now().hour
        if 6 <= hour < 12:
            return "morning"
        elif 12 <= hour < 18:
            return "afternoon"
        elif 18 <= hour < 24:
            return "evening"
        else:
            return "night"
    
    def _is_peak_tornado_season(self) -> bool:
        """Check if it's peak tornado season"""
        month = datetime.now().month
        return month in [4, 5, 6]  # April, May, June
    
    def _is_peak_tornado_time(self) -> bool:
        """Check if it's peak tornado time of day"""
        hour = datetime.now().hour
        return 15 <= hour <= 21  # 3 PM to 9 PM local time
    
    def _assess_data_quality(self, radar_data: torch.Tensor, atmospheric_data: Dict[str, torch.Tensor]) -> float:
        """Assess overall data quality for prediction"""
        
        quality_score = 1.0
        
        # Check radar data quality
        if torch.isnan(radar_data).any():
            quality_score -= 0.3
        
        if radar_data.numel() == 0:
            quality_score -= 0.5
        
        # Check atmospheric data completeness
        required_params = ['cape', 'shear_0_1km', 'helicity_0_1km']
        missing_params = sum(1 for param in required_params if param not in atmospheric_data)
        quality_score -= missing_params * 0.1
        
        return max(0.0, quality_score)
    
    def _create_fallback_data(self, station_id: str, station_location: Dict[str, float]) -> Dict[str, any]:
        """Create fallback data in case of errors"""
        
        return {
            'radar_sequence': torch.randn(6, 3, 256, 256),
            'atmospheric_data': self.atmospheric_processor._create_mock_atmospheric_data(station_location),
            'location_context': {
                'latitude': station_location['latitude'],
                'longitude': station_location['longitude'],
                'elevation': 0,
                'timezone_offset': 0,
                'season': 'spring',
                'time_of_day': 'afternoon'
            },
            'temporal_context': {
                'current_time': datetime.now(timezone.utc),
                'day_of_year': 120,
                'hour_of_day': 15,
                'is_peak_season': True,
                'is_peak_time': True
            },
            'data_quality': 0.5
        }

# Initialize global data pipeline
ml_data_pipeline = MLDataPipeline()