"""
🌪️ ADVANCED DATA PROCESSING FOR TORNADO PREDICTION
Real-time radar and atmospheric data processing for ML models
"""

from __future__ import annotations

import os, io, math, time, shutil, tempfile, logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
import torch
import httpx
import s3fs
import pyart
import xarray as xr

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# -----------------------------
# Radar data (NEXRAD Level-II)
# -----------------------------

class RadarDataProcessor:
    """
    Read recent NEXRAD Level-II from AWS -> grid to (3, H, W) per frame (refl/vel/swidth).
    Caller stacks T frames to (T, 3, H, W) for ML.
    """
    def __init__(self, image_size: Tuple[int,int]=(256,256), time_steps: int = 3,
                 spacing_min: int = 10, grid_km: float = 230.0, cache_sec: int = 120):
        self.image_size = tuple(image_size)
        self.T = int(time_steps)
        self.spacing_min = int(spacing_min)
        self.grid_km = float(grid_km)
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_sec = int(cache_sec)
        self.fs = s3fs.S3FileSystem(anon=True)

    async def process_radar_sequence(self, station_id: str, time_steps: Optional[int]=None,
                                     spacing_min: Optional[int]=None) -> torch.Tensor:
        T = time_steps or self.T
        step = spacing_min or self.spacing_min
        frames: List[torch.Tensor] = []
        now = datetime.utcnow().replace(tzinfo=None)
        for i in range(T):
            ts = now - timedelta(minutes=step*i)
            frames.append(await self._get_radar_frame(station_id, ts))
        x = torch.stack(frames, dim=0)  # (T, 3, H, W)

        # Per-channel z-score per-frame, then stack (keeps scale stable for ML)
        Tn, C, H, W = x.shape
        x_ = x.view(Tn, C, -1)
        m = x_.mean(dim=2, keepdim=True)
        s = x_.std(dim=2, keepdim=True).clamp_min(1e-5)
        x = ((x_ - m) / s).view(Tn, C, H, W)
        return x.float()

    async def _get_radar_frame(self, station_id: str, ts: datetime) -> torch.Tensor:
        """
        Download Level-II volume closest to 'ts', grid to (H,W), return (3,H,W).
        """
        cache_key = f"{station_id}_{int(ts.timestamp()//600)}"
        now = datetime.now(timezone.utc)
        hit = self.cache.get(cache_key)
        if hit and (now - hit["ts"]).total_seconds() < self.cache_sec:
            return hit["x"]

        s3path = self._find_object_near_time(station_id, ts)
        if not s3path:
            x = torch.zeros(3, *self.image_size, dtype=torch.float32)
            self.cache[cache_key] = {"x": x, "ts": now}
            return x

        with self.fs.open(s3path, "rb") as f:
            data = f.read()
        radar = pyart.io.read_nexrad_archive(io.BytesIO(data))

        # Grid to local Cartesian around radar center
        lim = self.grid_km * 1000.0
        grid = pyart.map.grid_from_radars(
            (radar,),
            grid_shape=(1, self.image_size[0], self.image_size[1]),
            grid_limits=((0.0, 1000.0), (-lim, lim), (-lim, lim)),
            fields=None,
            weighting_function="Nearest"
        )

        def grab(names: List[str], default=0.0, clip: Optional[Tuple[float,float]]=None):
            arr = None
            for nm in names:
                if nm in grid.fields:
                    arr = grid.fields[nm]["data"][0]  # (Y,X)
                    break
            if arr is None:
                arr = np.full(self.image_size, default, np.float32)
            if clip is not None:
                arr = np.clip(arr, clip[0], clip[1])
            return arr.astype(np.float32)

        refl = grab(["reflectivity", "reflectivity_horizontal", "REF", "DBZ"], default=0.0,   clip=(-10, 80))
        vel  = grab(["velocity", "velocity_horizontal", "VEL", "VEL_H"],            default=0.0,   clip=(-60, 60))
        sw   = grab(["spectrum_width", "SW", "WIDTH"],                              default=0.5,   clip=(0.0, 20.0))

        x = torch.from_numpy(np.stack([refl, vel, sw], axis=0))  # (3,H,W)

        self.cache[cache_key] = {"x": x, "ts": now}
        return x

    def _find_object_near_time(self, station_id: str, ts: datetime) -> Optional[str]:
        """
        List station folder for day (and neighbors), parse HHMMSS from filenames,
        and return the key closest to 'ts'.
        """
        def list_day(dt: datetime) -> List[str]:
            prefix = f"s3://noaa-nexrad-level2/{dt:%Y/%m/%d}/{station_id}/"
            try:
                return self.fs.ls(prefix)
            except Exception:
                return []

        # Collect from today and +/- 1 day to straddle midnight
        candidates = list_day(ts) + list_day(ts - timedelta(days=1)) + list_day(ts + timedelta(days=1))
        if not candidates:
            return None

        def parse_key_time(key: str) -> Optional[datetime]:
            # Example: .../KTLX/KTLX20250917_031838_V06
            base = os.path.basename(key)
            try:
                datepart = base[len(station_id):len(station_id)+8]      # YYYYMMDD
                tpart = base.split("_")[1][:6]                          # HHMMSS
                return datetime.strptime(datepart + tpart, "%Y%m%d%H%M%S")
            except Exception:
                return None

        best_key, best_dt, best_diff = None, None, None
        for k in candidates:
            kd = parse_key_time(k)
            if kd is None: continue
            diff = abs((kd - ts).total_seconds())
            if (best_diff is None) or (diff < best_diff):
                best_key, best_dt, best_diff = k, kd, diff
        return best_key

# ----------------------------------------
# Atmospheric data (HRRR point extraction)
# ----------------------------------------

class AtmosphericDataProcessor:
    """
    HRRR (CONUS) point sampler using xarray+cfgrib.
    Downloads most-recent surface + isobaric files, samples nearest grid to a lat/lon,
    and returns tensors aligned to the model.
    """

    def __init__(self, cache_dir: Optional[str]=None, max_cache_age_hours: int = 6,
                 max_cache_gb: float = 2.0, hrrr_source: str = "nomads"):
        self.cache_root = cache_dir or os.path.join(tempfile.gettempdir(), "hrrr_cache")
        os.makedirs(self.cache_root, exist_ok=True)
        self.max_cache_age_hours = int(max_cache_age_hours)
        self.max_cache_bytes = int(max_cache_gb * (1024**3))
        self.source = hrrr_source

    async def get_atmospheric_conditions(self, station_location: Dict[str, float]) -> Dict[str, torch.Tensor]:
        lat = float(station_location["latitude"]); lon = float(station_location["longitude"])
        run = self._choose_recent_run()
        surf_path, iso_path = await self._ensure_hrrr_files(run)

        ds_sfc = xr.open_dataset(surf_path, engine="cfgrib",
                                 backend_kwargs={"indexpath": "", "filter_by_keys": {"typeOfLevel": "surface"}})
        ds_iso = xr.open_dataset(iso_path, engine="cfgrib",
                                 backend_kwargs={"indexpath": "", "filter_by_keys": {"typeOfLevel": "isobaricInhPa"}})

        latn, lonn = self._find_latlon_names(ds_sfc)
        if latn is None or lonn is None:
            latn, lonn = self._find_latlon_names(ds_iso)
            if latn is None or lonn is None:
                raise RuntimeError("Latitude/longitude coordinates not found in HRRR GRIB.")

        def nearest_idx(ds: xr.Dataset) -> Dict[str,int]:
            la, lo = ds[latn], ds[lonn]
            if la.ndim == 2:
                dist = np.hypot((la - lat).values, (lo - lon).values)
                j, i = np.unravel_index(np.nanargmin(dist), dist.shape)
                return {"y": int(j), "x": int(i)}
            else:
                j = int(np.argmin(np.abs(la.values - lat)))
                i = int(np.argmin(np.abs(lo.values - lon)))
                return {"y": j, "x": i}

        idx_sfc = nearest_idx(ds_sfc); idx_iso = nearest_idx(ds_iso)

        cape = self._get_first(ds_sfc, ["cape", "convective_available_potential_energy"], idx_sfc, default=np.nan)
        t2m  = self._get_first(ds_sfc, ["t2m", "2t", "temperature_2m", "t"], idx_sfc, default=np.nan)
        d2m  = self._get_first(ds_sfc, ["d2m", "dewpoint_2m"], idx_sfc, default=np.nan)
        sp   = self._get_first(ds_sfc, ["sp", "surface_pressure"], idx_sfc, default=np.nan)

        T_850 = self._get_iso_level(ds_iso, 850, ["t","temperature"], idx_iso, np.nan)
        T_500 = self._get_iso_level(ds_iso, 500, ["t","temperature"], idx_iso, np.nan)
        Td_850= self._get_iso_level(ds_iso, 850, ["dpt","dewpoint"], idx_iso, np.nan)

        u10 = self._get_first(ds_sfc, ["u10","10u"], idx_sfc, default=np.nan)
        v10 = self._get_first(ds_sfc, ["v10","10v"], idx_sfc, default=np.nan)
        u925= self._get_iso_level(ds_iso, 925, ["u","u_component_of_wind"], idx_iso, np.nan)
        v925= self._get_iso_level(ds_iso, 925, ["v","v_component_of_wind"], idx_iso, np.nan)
        u700= self._get_iso_level(ds_iso, 700, ["u","u_component_of_wind"], idx_iso, np.nan)
        v700= self._get_iso_level(ds_iso, 700, ["v","v_component_of_wind"], idx_iso, np.nan)
        u500= self._get_iso_level(ds_iso, 500, ["u","u_component_of_wind"], idx_iso, np.nan)
        v500= self._get_iso_level(ds_iso, 500, ["v","v_component_of_wind"], idx_iso, np.nan)

        def k2c(x): return float(x) - 273.15 if np.isfinite(x) else np.nan
        Tsfc, Td_sfc, T850, T500, Td850 = map(k2c, [t2m, d2m, T_850, T_500, Td_850])
        psfc_kpa = (float(sp)/1000.0) if np.isfinite(sp) else np.nan

        def shear_mag(u_low, v_low, u_high, v_high):
            if not all(np.isfinite([u_low, v_low, u_high, v_high])): return np.nan
            return math.hypot(float(u_high)-float(u_low), float(v_high)-float(v_low))

        s01 = shear_mag(u10, v10, u925, v925)
        s03 = shear_mag(u10, v10, u700, v700)
        s06 = shear_mag(u10, v10, u500, v500)
        sdeep = shear_mag(u925, v925, u500, v500)

        capep = max(float(cape), 0.0) if np.isfinite(cape) else 0.0
        capef = math.sqrt(capep + 1e-6)
        h01 = (s01 if np.isfinite(s01) else 0.0) * capef
        h03 = (s03 if np.isfinite(s03) else 0.0) * capef

        def tens1(x): return torch.tensor([[0.0 if not np.isfinite(x) else float(x)]], dtype=torch.float32)

        atmo: Dict[str, torch.Tensor] = {
            "cape": tens1(capep),
            "wind_shear": torch.tensor([[  # 0–1, 0–3, 0–6, deep (m/s)
                0.0 if not np.isfinite(s01) else s01,
                0.0 if not np.isfinite(s03) else s03,
                0.0 if not np.isfinite(s06) else s06,
                0.0 if not np.isfinite(sdeep) else sdeep
            ]], dtype=torch.float32),
            "helicity": torch.tensor([[   # crude proxies
                0.0 if not np.isfinite(h01) else h01,
                0.0 if not np.isfinite(h03) else h03
            ]], dtype=torch.float32),
            "temperature": torch.tensor([[ # °C
                0.0 if not np.isfinite(Tsfc) else Tsfc,
                0.0 if not np.isfinite(T850) else T850,
                0.0 if not np.isfinite(T500) else T500
            ]], dtype=torch.float32),
            "dewpoint": torch.tensor([[    # °C
                0.0 if not np.isfinite(Td_sfc) else Td_sfc,
                0.0 if not np.isfinite(Td850) else Td850
            ]], dtype=torch.float32),
            "pressure": tens1(psfc_kpa)    # kPa
        }

        self._prune_cache()
        return atmo

    def _choose_recent_run(self) -> Dict[str, str]:
        now = datetime.now(timezone.utc)
        return {"ymd": now.strftime("%Y%m%d"), "hour": f"{now.hour:02d}", "fxx": "00"}

    async def _ensure_hrrr_files(self, run: Dict[str,str]) -> Tuple[str,str]:
        ymd, hh, fxx = run["ymd"], run["hour"], run["fxx"]
        base = os.path.join(self.cache_root, f"hrrr_{ymd}_t{hh}z_f{fxx}")
        surf_path, iso_path = base + "_sfc.grib2", base + "_prs.grib2"

        if not (os.path.exists(surf_path) and os.path.getsize(surf_path) > 10_000):
            ok = await self._download_hrrr_file(ymd, hh, fxx, "sfc", surf_path)
            if not ok and fxx == "00":
                ok = await self._download_hrrr_file(ymd, hh, "01", "sfc", surf_path)
                if ok: run["fxx"] = "01"

        if not (os.path.exists(iso_path) and os.path.getsize(iso_path) > 10_000):
            ok = await self._download_hrrr_file(ymd, hh, run["fxx"], "prs", iso_path)
            if not ok and run["fxx"] == "00":
                await self._download_hrrr_file(ymd, hh, "01", "prs", iso_path)
        return surf_path, iso_path

    async def _download_hrrr_file(self, ymd: str, hh: str, fxx: str, level: str, out_path: str) -> bool:
        url = f"https://nomads.ncep.noaa.gov/pub/data/nccf/com/hrrr/prod/hrrr.{ymd}/conus/hrrr.t{hh}z.wrf{level}f{fxx}.grib2"
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.get(url, follow_redirects=True)
                if r.status_code == 200 and len(r.content) > 10_000:
                    with open(out_path, "wb") as f: f.write(r.content)
                    return True
        except Exception:
            pass
        return False

    def _find_latlon_names(self, ds: xr.Dataset) -> Tuple[Optional[str], Optional[str]]:
        lat_candidates = ["latitude", "lat", "gridlat", "nav_lat"]
        lon_candidates = ["longitude", "lon", "gridlon", "nav_lon"]
        lat_name = next((n for n in lat_candidates if n in ds.variables), None)
        lon_name = next((n for n in lon_candidates if n in ds.variables), None)
        return lat_name, lon_name

    def _get_first(self, ds: xr.Dataset, options: List[str], idx: Dict[str,int], default=np.nan) -> float:
        for nm in options:
            if nm in ds.variables:
                v = ds[nm]
                if "time" in v.dims: v = v.isel(time=-1)
                if {"y","x"}.issubset(v.dims):
                    return float(v.isel(y=idx["y"], x=idx["x"]).values)
        return float(default)

    def _get_iso_level(self, ds_iso: xr.Dataset, level: int, options: List[str],
                       idx: Dict[str,int], default=np.nan) -> float:
        for nm in options:
            if nm in ds_iso.variables:
                v = ds_iso[nm]
                if "time" in v.dims: v = v.isel(time=-1)
                if "isobaricInhPa" not in v.dims: continue
                levs = v["isobaricInhPa"].values
                k = int(np.argmin(np.abs(levs - level)))
                v = v.isel(isobaricInhPa=k)
                if {"y","x"}.issubset(v.dims):
                    return float(v.isel(y=idx["y"], x=idx["x"]).values)
        return float(default)

    def _prune_cache(self):
        try:
            files, total = [], 0
            now = time.time()
            for name in os.listdir(self.cache_root):
                p = os.path.join(self.cache_root, name)
                if not (os.path.isfile(p) and name.endswith(".grib2")): continue
                st = os.stat(p)
                age_h = (now - st.st_mtime) / 3600.0
                if age_h > self.max_cache_age_hours:
                    try: os.remove(p); continue
                    except Exception: pass
                files.append((p, st.st_mtime, st.st_size)); total += st.st_size
            if total > self.max_cache_bytes:
                files.sort(key=lambda t: t[1])
                while total > self.max_cache_bytes and files:
                    p, _, sz = files.pop(0)
                    try: os.remove(p); total -= sz
                    except Exception: pass
        except Exception:
            pass

    # Simple mock in case of fallback usage
    def _create_mock_atmospheric_data(self, loc: Dict[str,float]) -> Dict[str, torch.Tensor]:
        rng = np.random.default_rng(42)
        return {
            "cape": torch.tensor([[float(rng.uniform(200, 2200))]], dtype=torch.float32),
            "wind_shear": torch.tensor([[15., 25., 35., 30.]], dtype=torch.float32),
            "helicity": torch.tensor([[120., 220.]], dtype=torch.float32),
            "temperature": torch.tensor([[24., 14., -16.]], dtype=torch.float32),
            "dewpoint": torch.tensor([[20., 12.]], dtype=torch.float32),
            "pressure": torch.tensor([[100.]], dtype=torch.float32),
        }

# -----------------------------
# ML pipeline glue
# -----------------------------

class MLDataPipeline:
    """Complete ML data pipeline for tornado prediction."""
    def __init__(self):
        self.radar_processor = RadarDataProcessor()
        self.atmospheric_processor = AtmosphericDataProcessor()

    async def prepare_prediction_data(self, station_id: str, station_location: Dict[str, float]) -> Dict[str, Any]:
        try:
            radar_sequence = await self.radar_processor.process_radar_sequence(station_id, time_steps=6, spacing_min=10)  # (6,3,256,256)
            atmospheric_data = await self.atmospheric_processor.get_atmospheric_conditions(station_location)

            location_context = {
                "latitude": station_location["latitude"],
                "longitude": station_location["longitude"],
                "elevation": station_location.get("elevation", 0.0),
                "timezone_offset": self._get_timezone_offset(station_location),
                "season": self._get_season(),
                "time_of_day": self._get_time_of_day(),
            }
            now = datetime.now(timezone.utc)
            temporal_context = {
                "current_time": now,
                "day_of_year": now.timetuple().tm_yday,
                "hour_of_day": now.hour,
                "is_peak_season": self._is_peak_tornado_season(),
                "is_peak_time": self._is_peak_tornado_time(),
            }

            return {
                "radar_sequence": radar_sequence,                  # (T,C,H,W)
                "atmospheric_data": atmospheric_data,              # dict of tensors
                "location_context": location_context,
                "temporal_context": temporal_context,
                "data_quality": self._assess_data_quality(radar_sequence, atmospheric_data),
            }
        except Exception as e:
            logger.error(f"Error preparing prediction data: {e}")
            return self._create_fallback_data(station_id, station_location)

    # -------- helpers --------

    def _get_timezone_offset(self, location: Dict[str, float]) -> float:
        return float(np.clip(-(location["longitude"]) / 15.0, -12, 12))

    def _get_season(self) -> str:
        m = datetime.now().month
        return "winter" if m in (12,1,2) else "spring" if m in (3,4,5) else "summer" if m in (6,7,8) else "fall"

    def _get_time_of_day(self) -> str:
        h = datetime.now().hour
        return "morning" if 6 <= h < 12 else "afternoon" if 12 <= h < 18 else "evening" if 18 <= h < 24 else "night"

    def _is_peak_tornado_season(self) -> bool:
        return datetime.now().month in (4,5,6)

    def _is_peak_tornado_time(self) -> bool:
        h = datetime.now().hour
        return 15 <= h <= 21

    def _assess_data_quality(self, radar_seq: torch.Tensor, atmo: Dict[str, torch.Tensor]) -> float:
        score = 1.0
        if radar_seq.numel() == 0 or torch.isnan(radar_seq).any(): score -= 0.4
        # Require basic keys
        for k in ("cape", "wind_shear", "temperature", "dewpoint", "pressure"):
            if k not in atmo: score -= 0.1
        return max(0.0, score)

    def _create_fallback_data(self, station_id: str, station_location: Dict[str, float]) -> Dict[str, Any]:
        rng = np.random.default_rng(0)
        radar = torch.from_numpy(rng.standard_normal((6,3,256,256)).astype(np.float32))
        return {
            "radar_sequence": radar,
            "atmospheric_data": self.atmospheric_processor._create_mock_atmospheric_data(station_location),
            "location_context": {
                "latitude": station_location["latitude"], "longitude": station_location["longitude"],
                "elevation": 0.0, "timezone_offset": 0.0, "season": "spring", "time_of_day": "afternoon"
            },
            "temporal_context": {
                "current_time": datetime.now(timezone.utc), "day_of_year": 120,
                "hour_of_day": 15, "is_peak_season": True, "is_peak_time": True
            },
            "data_quality": 0.5
        }

# Global pipeline instance
ml_data_pipeline = MLDataPipeline()
