"""
🌪️ STORM ORACLE - AUTOMATED STORM MONITORING SYSTEM (HF edition)
Continuously monitors radar stations and generates automatic tornado predictions.

- Uses your TornadoSuperPredictor (backend/ml_models/tornado_predictor.py)
- Uses ml_data_pipeline from data_processor.py
- Optional free Hugging Face text assistant for alerts/summaries
"""

from __future__ import annotations
import os
import asyncio
import math
import hashlib
import contextlib
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

# -----------------------------
# Model import (robust pathing)
# -----------------------------
# If running as a package, backend is already importable; otherwise add project root.
try:
    from backend.ml_models.tornado_predictor import TornadoSuperPredictor
except Exception:
    # try to add "<repo_root>/backend" to path if caller runs from repo root
    import sys
    repo_backend = Path(__file__).resolve().parents[1] / "backend"
    if repo_backend.exists():
        sys.path.insert(0, str(repo_backend))
    from ml_models.tornado_predictor import TornadoSuperPredictor  # type: ignore

# -----------------------------
# Data pipeline import
# -----------------------------
try:
    from ml_models.data_processor import ml_data_pipeline
except ModuleNotFoundError:
    from backend.ml_models.data_processor import ml_data_pipeline

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# =============================================================================
# Inference Bridge
# =============================================================================
import torch
from typing import Any, Dict

class InferenceEngine:
    """
    Wraps the tornado predictor model for single-station inference.
    Ensures radar tensor shape matches the model's expected input (C_in=18).
    """

    def __init__(self, model, device: str | None = None):
        self.model = model.eval()
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)

    def _prep_radar(self, x: torch.Tensor) -> torch.Tensor:
        """
        Accepts radar sequences in common shapes and converts to (1, 18, H, W):
        - (T, 3, H, W)  -> permute + reshape -> (1, T*3, H, W)
        - (1, 18, H, W) -> as-is
        - (18, H, W)    -> unsqueeze(0)
        """
        if x is None:
            raise ValueError("radar tensor is None")

        x = x.detach().to(torch.float32)

        # (T, 3, H, W)  (e.g., 6×3×256×256)
        if x.dim() == 4 and x.shape[1] == 3 and x.shape[0] >= 2:
            T, C, H, W = x.shape  # C should be 3
            x = x.permute(1, 0, 2, 3).reshape(1, T * C, H, W)  # -> (1, 18, H, W)

        # (18, H, W)
        elif x.dim() == 3 and x.shape[0] == 18:
            x = x.unsqueeze(0)  # -> (1, 18, H, W)

        # (1, 18, H, W) -> OK
        elif x.dim() == 4 and x.shape[0] == 1 and x.shape[1] == 18:
            pass

        else:
            raise ValueError(f"Unexpected radar tensor shape: {tuple(x.shape)}; expected (T,3,H,W) or (1,18,H,W).")

        return x.to(self.device)

    def _prep_atmo(self, atmo: Dict[str, torch.Tensor] | None) -> Dict[str, torch.Tensor]:
        if not isinstance(atmo, dict):
            return {}
        out: Dict[str, torch.Tensor] = {}
        for k, v in atmo.items():
            try:
                out[k] = v.detach().to(self.device, dtype=torch.float32)
            except Exception:
                out[k] = torch.as_tensor(v, dtype=torch.float32, device=self.device)
        return out

    @torch.inference_mode()
    def predict_one(self, radar_tensor: torch.Tensor, atmo: Dict[str, torch.Tensor] | None) -> Dict[str, Any]:
        x = self._prep_radar(radar_tensor)
        a = self._prep_atmo(atmo)
        y = self.model(x, a)  # model returns dict of tensors

        def py(v):
            if torch.is_tensor(v):
                if v.ndim == 0 or v.numel() == 1:
                    return v.item()
                return v.detach().cpu().numpy().tolist()
            return v

        return {k: py(v) for k, v in (y or {}).items()}


# =============================================================================
# AutomatedStormMonitor
# =============================================================================
class AutomatedStormMonitor:
    """
    Continuously scans stations, calls the ML model, and emits alerts to a DB.
    Expects an async DB (Motor-like) with collections:
      - radar_stations
      - tornado_alerts
      - system_messages
    """

    # hysteresis thresholds to mark a station as "active storm"
    ACTIVE_ENTER = 0.20
    ACTIVE_EXIT  = 0.12

    def __init__(
        self,
        db_connection,
        inference_engine: InferenceEngine,
        assistant: HFWeatherman,
        in_channels: int,
        scan_interval_sec: int = 300,
        priority_interval_sec: int = 120,
        batch_size: int = 8,
    ):
        self.db = db_connection
        self.ie = inference_engine
        self.assistant = assistant
        self.monitoring_active = False
        self.scan_interval = int(scan_interval_sec)
        self.priority_interval = int(priority_interval_sec)
        self.batch_size = int(batch_size)
        self.in_channels = int(in_channels)

        self.active_storms: Dict[str, Dict[str, Any]] = {}
        self._station_locks: Dict[str, asyncio.Lock] = {}

        self.priority_stations = [
            'KTLX','KFDR','KINX','KEAX','KICT','KGLD','KDDC','KTWX',   # Plains
            'KBMX','KHTX','KGWX','KNQA','KOHX','KPAH','KLZK',         # Southeast
            'KLOT','KILX','KDVN','KDMX','KARX','KMPX','KFSD'          # Midwest
        ]
        logger.info("🌪️ Automated Storm Monitor initialized")

    # ---------- lifecycle ----------
    async def start_monitoring(self) -> None:
        if self.monitoring_active:
            logger.warning("Storm monitoring already active"); return
        self.monitoring_active = True
        logger.info("🚀 Starting monitoring loops")
        tasks = [
            asyncio.create_task(self._continuous_storm_scan(), name="scan_all"),
            asyncio.create_task(self._priority_station_monitor(), name="scan_priority"),
            asyncio.create_task(self._cleanup_old_predictions(), name="cleanup"),
            asyncio.create_task(self._generate_national_summary(), name="summary"),
        ]
        try:
            await asyncio.gather(*tasks)
        finally:
            self.monitoring_active = False

    async def stop_monitoring(self) -> None:
        self.monitoring_active = False
        logger.info("🛑 Stop requested")

    # ---------- loops ----------
    async def _continuous_storm_scan(self) -> None:
        while self.monitoring_active:
            try:
                stations = await self.db.radar_stations.find().to_list(2000)
                logger.info(f"🔍 Scanning {len(stations)} stations")
                for i in range(0, len(stations), self.batch_size):
                    batch = stations[i:i+self.batch_size]
                    await asyncio.gather(*(self._scan_station_for_storms(s) for s in batch))
                    await asyncio.sleep(0.25)
                logger.info("✅ Full scan complete")
                await asyncio.sleep(self.scan_interval)
            except Exception as e:
                logger.exception(f"continuous scan error: {e}")
                await asyncio.sleep(60)

    async def _priority_station_monitor(self) -> None:
        while self.monitoring_active:
            try:
                pri = await self.db.radar_stations.find({'station_id': {'$in': self.priority_stations}}).to_list(200)
                await asyncio.gather(*(self._scan_station_for_storms(s) for s in pri))
                await asyncio.sleep(self.priority_interval)
            except Exception as e:
                logger.exception(f"priority monitor error: {e}")
                await asyncio.sleep(60)

    async def _cleanup_old_predictions(self) -> None:
        while self.monitoring_active:
            try:
                cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
                res = await self.db.tornado_alerts.delete_many({
                    'alert_type': 'AUTOMATED_ML_ANALYSIS',
                    'timestamp': {'$lt': cutoff}
                })
                if getattr(res, "deleted_count", 0):
                    logger.info(f"🧹 Deleted {res.deleted_count} old alerts")

                # prune stale active storms (>1h)
                now = datetime.now(timezone.utc)
                stale = [sid for sid, s in self.active_storms.items() if (now - s['last_updated']).total_seconds() > 3600]
                for sid in stale: self.active_storms.pop(sid, None)
                if stale: logger.info(f"🧹 Pruned {len(stale)} stale storms")
                await asyncio.sleep(3600)
            except Exception as e:
                logger.exception(f"cleanup error: {e}")
                await asyncio.sleep(3600)

    async def _generate_national_summary(self) -> None:
        while self.monitoring_active:
            try:
                await asyncio.sleep(1800)  # every 30 min
                if not self.active_storms: continue
                hi = [s for s in self.active_storms.values() if s['tornado_probability'] > 0.5]
                mo = [s for s in self.active_storms.values() if 0.2 < s['tornado_probability'] <= 0.5]
                if not hi and len(mo) <= 5: continue

                def _line(s): return f"- {s['station']['name']} ({s['station']['station_id']}): {s['tornado_probability']:.1%}"
                prompt = (
                    f"National tornado threat summary at {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC}.\n"
                    f"HIGH THREAT AREAS ({len(hi)}):\n" + "\n".join(_line(s) for s in hi[:8]) + "\n\n"
                    f"MODERATE THREAT AREAS ({len(mo)}):\n" + "\n".join(_line(s) for s in mo[:12]) + "\n\n"
                    "Write a concise meteorologist-style outlook for the next 1–3 hours."
                )
                summary = await self.assistant.summarize_alert(prompt)
                await self.db.system_messages.insert_one({
                    "type": "NATIONAL_SUMMARY",
                    "summary": summary,
                    "created_at": datetime.now(timezone.utc)
                })
                logger.info(f"📊 National summary stored ({len(hi)} high, {len(mo)} moderate)")
            except Exception as e:
                logger.exception(f"summary error: {e}")

    # ---------------- Station worker ----------------
    async def _scan_station_for_storms(self, station: Dict[str, Any]) -> Dict[str, Any]:
        """Single-station scan with locking, prediction, and optional alerting."""
        sid = station.get("station_id", "UNKNOWN")
        lock = self._station_locks.setdefault(sid, asyncio.Lock())
        async with lock:
            try:
                station = {k: v for k, v in station.items() if k != "_id"}  # strip Mongo _id
                station_loc = {"latitude": station["latitude"], "longitude": station["longitude"], "elevation": station.get("elevation", 0.0)}

                # Build tensors from your pipeline
                ml_data = await ml_data_pipeline.prepare_prediction_data(sid, station_loc)

                radar = ml_data["radar_sequence"]
                if not isinstance(radar, torch.Tensor):
                    radar = torch.from_numpy(radar).float()

                # Enforce channels = in_channels (e.g., 9 for T=3)
                if radar.ndim == 3 and radar.shape[0] != self.in_channels:
                    # naive fix: truncate or tile to match
                    c = radar.shape[0]
                    if c > self.in_channels:
                        radar = radar[:self.in_channels, :, :]
                    else:
                        reps = math.ceil(self.in_channels / c)
                        radar = radar.repeat(reps, 1, 1)[:self.in_channels, :, :]

                atmo = ml_data.get("atmospheric_data") or {}
                # convert numpy to tensor
                atmo = {k: (torch.as_tensor(v).float() if not isinstance(v, torch.Tensor) else v.float()) for k, v in atmo.items()}

                # If atmospheric data is empty or all NaN, use mock data
                if not atmo or all(torch.isnan(v).all() if isinstance(v, torch.Tensor) else np.isnan(v).all() if isinstance(v, np.ndarray) else True for v in atmo.values()):
                    logger.warning(f"Using fallback atmospheric data for station {sid} due to missing/NaN data")
                    atmo = {
                        "cape": torch.tensor([[1500.0]], dtype=torch.float32),
                        "wind_shear": torch.tensor([[15.0, 25.0, 35.0, 30.0]], dtype=torch.float32),
                        "helicity": torch.tensor([[100.0, 200.0]], dtype=torch.float32),
                        "temperature": torch.tensor([[20.0, 10.0, -10.0]], dtype=torch.float32),
                        "dewpoint": torch.tensor([[15.0, 5.0]], dtype=torch.float32),
                        "pressure": torch.tensor([[100.0]], dtype=torch.float32),
                    }

                pred = self.ie.predict_one(radar, atmo)

                # Extract values from prediction batch (handle tensors properly)
                prob = float(pred.tornado_probability.item() if hasattr(pred.tornado_probability, 'item') else pred.tornado_probability)
                ef = int(pred.most_likely_ef_scale.item() if hasattr(pred.most_likely_ef_scale, 'item') else pred.most_likely_ef_scale)

                # uncertainty_scores is a tensor with 4 values: [confidence, uncertainty_type_1, uncertainty_type_2, uncertainty_type_3]
                # The first value is typically the confidence score
                uncertainty_tensor = pred.uncertainty_scores
                if hasattr(uncertainty_tensor, 'item'):
                    # Single value tensor
                    conf = float(uncertainty_tensor.item())
                else:
                    # Multi-value tensor, take first value as confidence
                    conf = float(uncertainty_tensor[0].item() if hasattr(uncertainty_tensor[0], 'item') else uncertainty_tensor[0])

                # Also extract other values from the prediction
                location_offset = pred.location_offset
                lat_offset = float(location_offset[0].item() if hasattr(location_offset[0], 'item') else location_offset[0])
                lng_offset = float(location_offset[1].item() if hasattr(location_offset[1], 'item') else location_offset[1])

                timing_pred = pred.timing_predictions
                if hasattr(timing_pred, 'item'):
                    time_to_touchdown = float(timing_pred.item())
                else:
                    time_to_touchdown = float(timing_pred[0].item() if hasattr(timing_pred[0], 'item') else timing_pred[0])

                # Store timing prediction in pred for later use
                pred.time_to_touchdown_minutes = time_to_touchdown

                # Map to alert level (same as your earlier logic)
                if prob > 0.8 and ef >= 3 and conf > 0.7:
                    alert = "TORNADO_EMERGENCY"
                elif prob > 0.6 and ef >= 2:
                    alert = "TORNADO_WARNING"
                elif prob > 0.4:
                    alert = "TORNADO_WATCH"
                elif prob > 0.2:
                    alert = "SEVERE_THUNDERSTORM_WARNING"
                else:
                    alert = "NORMAL_CONDITIONS"

                # Store all extracted values in pred dictionary for easy access
                pred.tornado_probability = prob
                pred.most_likely_ef_scale = ef
                pred.confidence_score = conf
                pred.lat_offset = lat_offset
                pred.lng_offset = lng_offset

                # Update active storms with hysteresis
                now = datetime.now(timezone.utc)
                if prob >= self.ACTIVE_ENTER:
                    self.active_storms[sid] = {
                        "station": station,
                        "prediction": pred,
                        "last_updated": now,
                        "tornado_probability": prob,
                        "alert_level": alert,
                    }
                elif sid in self.active_storms and prob < self.ACTIVE_EXIT:
                    self.active_storms.pop(sid, None)

                # Generate alert if meaningful (idempotent by hash)
                if prob > 0.30 or alert != "NORMAL_CONDITIONS":
                    await self._maybe_emit_alert(station, pred, ml_data)

                return {"station_id": sid, "tornado_probability": prob, "alert_level": alert, "status": "success"}

            except Exception as e:
                logger.exception(f"Error scanning station {sid}: {e}")
                return {"station_id": sid, "status": "error", "error": str(e)}

    # ---------------- Alerts ----------------
    async def _maybe_emit_alert(self, station: Dict[str, Any], pred: Dict[str, Any], ml_data: Dict[str, Any]):
        sid = station["station_id"]
        # dedupe on stable "content hash" for 15 minutes
        signature = f"{sid}|{round(pred.tornado_probability, 2)}|{pred.most_likely_ef_scale}|{pred.time_to_touchdown_minutes}"
        sig_hash = hashlib.md5(signature.encode()).hexdigest()
        since = datetime.now(timezone.utc) - timedelta(minutes=15)
        dup = await self.db.tornado_alerts.find_one({
            "station_id": sid,
            "alert_type": "AUTOMATED_ML_ANALYSIS",
            "sig_hash": sig_hash,
            "timestamp": {"$gte": since}
        })
        if dup:
            logger.debug(f"[Alert] Skipping duplicate alert for {sid}")
            return

        # Compose short meteorologist-style message via HF
        prompt = (
            f"Automated tornado risk assessment for {station['name']} ({sid}) at "
            f"{datetime.now(timezone.utc).strftime('%H:%M UTC')}.\n\n"
            f"- Probability: {pred.tornado_probability:.1%}\n"
            f"- Alert Level: {pred.alert_level}\n"
            f"- EF Most Likely: EF{pred.most_likely_ef_scale}\n"
            f"- Confidence: {pred.confidence_score:.1%}\n"
            f"- Data Quality: {ml_data.get('data_quality', 'Unknown')}\n\n"
            "Write a concise alert (<= 150 words) with:\n"
            "1) Immediate threat assessment\n2) Recommended actions\n3) Key meteorological factors"
        )
        with contextlib.suppress(Exception):
            msg = await self.assistant.summarize_alert(prompt)
        if not msg:
            msg = "Automated ML alert: Elevated tornado risk detected. Monitor local warnings and take shelter if advised."

        alert_doc = {
            "station_id": sid,
            "alert_type": "AUTOMATED_ML_ANALYSIS",
            "severity": min(5, max(1, int(pred.tornado_probability * 5) + 1)),
            "predicted_location": {"lat": pred.touchdown_location["latitude"], "lng": pred.touchdown_location["longitude"]},
            "predicted_path": [{"lat": p["latitude"], "lng": p["longitude"]} for p in pred.path_trajectory[:3]],
            "confidence": int(pred.confidence_score * 100),
            "message": msg,
            "timestamp": datetime.now(timezone.utc),
            "estimated_touchdown_time": (
                datetime.now(timezone.utc) + timedelta(minutes=pred.time_to_touchdown_minutes)
                if pred.time_to_touchdown_minutes > 0 else None
            ),
            "sig_hash": sig_hash,
        }
        await self.db.tornado_alerts.insert_one(alert_doc)
        logger.info(f"🚨 Alert stored for {station['name']} — {pred.tornado_probability:.1%} risk")

    # ---------------- Public status ----------------
    def get_active_storms(self) -> List[Dict[str, Any]]:
        items = []
        for sid, s in self.active_storms.items():
            p = s["prediction"]
            items.append({
                "stationId": sid,
                "stationName": s["station"]["name"],
                "latitude": s["station"]["latitude"],
                "longitude": s["station"]["longitude"],
                "tornadoProbability": int(s["tornado_probability"] * 100),
                "alertLevel": s["alert_level"],
                "predictedEFScale": f"EF{p.most_likely_ef_scale}",
                "confidence": int(p.confidence_score * 100),
                "lastUpdated": s["last_updated"].isoformat(),
                "touchdownTime": p.timing_predictions.get("time_to_touchdown_minutes", "Unknown"),
            })
        return sorted(items, key=lambda x: x["tornadoProbability"], reverse=True)

    def get_monitoring_status(self) -> Dict[str, Any]:
        return {
            "monitoring_active": self.monitoring_active,
            "active_storms_count": len(self.active_storms),
            "high_threat_storms": len([s for s in self.active_storms.values() if s["tornado_probability"] > 0.5]),
            "moderate_threat_storms": len([s for s in self.active_storms.values() if 0.2 < s["tornado_probability"] <= 0.5]),
            "scan_interval_minutes": self.scan_interval // 60,
            "priority_stations_count": len(self.priority_stations),
            "last_scan_time": datetime.now(timezone.utc).isoformat(),
        }

# Global instance (optional; create in your server startup)
storm_monitor: Optional[AutomatedStormMonitor] = None
