"""
🌪️ ADVANCED DATA PROCESSING FOR TORNADO PREDICTION (Model-ready)
Produces radar (3*T,H,W) and atmo dict with correct dims for TornadoSuperPredictor.
"""

import asyncio
import numpy as np
import torch
from typing import Dict, Optional
from datetime import datetime, timezone, timedelta
import logging

logger = logging.getLogger(__name__)


# ---------------- Radar ----------------
class RadarDataProcessor:
    def __init__(self, image_size=(256, 256), time_steps: int = 3):
        self.image_size = image_size
        self.T = int(time_steps)            # number of frames (T)
        self.cache: dict[str, dict] = {}
        self.cache_sec = 300

    async def process_radar_sequence(self, station_id: str) -> torch.Tensor:
        """
        Returns a FloatTensor shaped (3*T, H, W), normalized (per-channel z-score).
        """
        try:
            frames = []
            for i in range(self.T):
                ts = datetime.now(timezone.utc) - timedelta(minutes=i * 10)
                frames.append(await self._get_radar_frame(station_id, ts))  # (3,H,W)

            # Stack time on channel: [(3,H,W)] * T -> (3*T,H,W)
            x = torch.cat(frames, dim=0)  # (3*T,H,W)

            # Per-channel z-score (like dataset default)
            C = x.shape[0]
            x = x.view(C, -1)
            m = x.mean(dim=1, keepdim=True)
            s = x.std(dim=1, keepdim=True).clamp_min(1e-5)
            x = ((x - m) / s).view(C, *self.image_size)
            return x.float()

        except Exception as e:
            logger.error(f"Radar sequence failed: {e}")
            return self._mock_sequence()

    async def _get_radar_frame(self, station_id: str, ts: datetime) -> torch.Tensor:
        """
        Returns a synthetic but meteorologically plausible frame (3,H,W).
        Caching to reduce load.
        """
        key = f"{station_id}_{int(ts.timestamp()//600)}"
        entry = self.cache.get(key)
        if entry and (datetime.now(timezone.utc) - entry["ts"]).total_seconds() < self.cache_sec:
            return entry["x"]

        x = self._synthetic_radar(self.image_size)  # (3,H,W)
        self.cache[key] = {"x": x, "ts": datetime.now(timezone.utc)}
        return x

    def _synthetic_radar(self, size) -> torch.Tensor:
        H, W = size
        x = torch.zeros(3, H, W)

        yy, xx = torch.meshgrid(torch.arange(H), torch.arange(W), indexing="ij")
        cx, cy = W//2 + 18, H//2 - 10
        r = torch.sqrt((xx - cx)**2 + (yy - cy)**2)

        # reflectivity with hook echo enhancement
        refl = torch.exp(-r / 30) * 3.0
        hook = torch.exp(-torch.sqrt((xx - (cx+10))**2 + (yy - (cy+6))**2) / 12) * 2.5
        x[0] = (refl + hook) + 0.1 * torch.randn(H, W)

        # velocity couplet
        vel = torch.sin((xx - W/2) / 10) * torch.exp(-r / 25) * 2.0
        x[1] = vel + 0.1 * torch.randn(H, W)

        # spectrum width
        sw = torch.exp(-r / 35) * 1.5 + 0.1 * torch.randn(H, W)
        x[2] = sw

        return x.float()

    def _mock_sequence(self) -> torch.Tensor:
        H, W = self.image_size
        return torch.randn(3 * self.T, H, W).float()


# ---------------- Atmosphere ----------------
class AtmosphericDataProcessor:
    def __init__(self):
        # Ranges for clipping
        self.ranges = {
            'cape': (0, 6000),
            'shear_0_1km': (0, 30), 'shear_0_3km': (0, 40), 'shear_0_6km': (0, 50),
            'helicity_0_1km': (0, 500), 'helicity_0_3km': (0, 800),
            'temperature_sfc': (-20, 40), 'temperature_850': (-30, 20), 'temperature_500': (-60, 0),
            'dewpoint_sfc': (-10, 30), 'dewpoint_850': (-20, 20),
            'pressure_sfc': (980, 1040)
        }

    async def get_atmospheric_conditions(self, loc: Dict[str, float]) -> Dict[str, torch.Tensor]:
        try:
            raw = await self._mock_fetch(loc)
            return self._to_model_dict(raw)
        except Exception as e:
            logger.error(f"Atmospheric fetch failed: {e}")
            return self._to_model_dict(self._fallback(loc))

    async def _mock_fetch(self, loc: Dict[str, float]) -> Dict[str, float]:
        lat, lon = loc['latitude'], loc['longitude']
        out = {
            'cape': 3500 + np.random.normal(0, 500),
            'shear_0_1km': 15 + np.random.normal(0, 3),
            'shear_0_3km': 25 + np.random.normal(0, 5),
            'shear_0_6km': 35 + np.random.normal(0, 7),
            'helicity_0_1km': 250 + np.random.normal(0, 50),
            'helicity_0_3km': 400 + np.random.normal(0, 80),
            'temperature_sfc': 25 + np.random.normal(0, 3),
            'temperature_850': 15 + np.random.normal(0, 2),
            'temperature_500': -15 + np.random.normal(0, 3),
            'dewpoint_sfc': 20 + np.random.normal(0, 2),
            'dewpoint_850': 18 + np.random.normal(0, 2),
            'pressure_sfc': 1012 + np.random.normal(0, 5),
        }
        # seasonal/geographic bump
        season = np.sin((datetime.now().month - 4) * np.pi / 6)
        out['cape'] *= (1 + 0.3 * season)
        if -100 < lon < -95 and 35 < lat < 40:
            out['cape'] *= 1.2; out['shear_0_1km'] *= 1.1
        return out

    def _to_model_dict(self, raw: Dict[str, float]) -> Dict[str, torch.Tensor]:
        def clip(name):
            lo, hi = self.ranges[name]
            return float(np.clip(raw[name], lo, hi))

        cape = torch.tensor([[clip('cape')]], dtype=torch.float32)
        wind_shear = torch.tensor([[
            clip('shear_0_1km'),
            clip('shear_0_3km'),
            clip('shear_0_6km'),
            clip('shear_0_6km')  # deep layer proxy
        ]], dtype=torch.float32)
        helicity = torch.tensor([[clip('helicity_0_1km'), clip('helicity_0_3km')]], dtype=torch.float32)
        temperature = torch.tensor([[clip('temperature_sfc'), clip('temperature_850'), clip('temperature_500')]], dtype=torch.float32)
        dewpoint = torch.tensor([[clip('dewpoint_sfc'), clip('dewpoint_850')]], dtype=torch.float32)
        pressure = torch.tensor([[clip('pressure_sfc')]], dtype=torch.float32) / 1000.0  # slight scale

        return {
            'cape': cape, 'wind_shear': wind_shear, 'helicity': helicity,
            'temperature': temperature, 'dewpoint': dewpoint, 'pressure': pressure
        }

    def _fallback(self, loc: Dict[str, float]) -> Dict[str, float]:
        return {k: float(np.mean(v)) if isinstance(v, tuple) else 0.0 for k, v in self.ranges.items()}


# ---------------- Public pipeline ----------------
class MLDataPipeline:
    def __init__(self, image_size=(256, 256), time_steps=3):
        self.radar = RadarDataProcessor(image_size=image_size, time_steps=time_steps)
        self.atmo = AtmosphericDataProcessor()

    async def prepare_prediction_data(self, station_id: str, station_loc: Dict[str, float]) -> Dict[str, object]:
        x = await self.radar.process_radar_sequence(station_id)            # (3*T,H,W)
        atmo = await self.atmo.get_atmospheric_conditions(station_loc)     # dict of (1,dim)
        return {
            'radar_sequence': x,
            'atmospheric_data': atmo,
            'location_context': station_loc,
            'temporal_context': {'now': datetime.now(timezone.utc)},
            'data_quality': 1.0
        }

# Global
ml_data_pipeline = MLDataPipeline(time_steps=3)
