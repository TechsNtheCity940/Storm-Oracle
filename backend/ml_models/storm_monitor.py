"""
🌪️ STORM ORACLE - AUTOMATED STORM MONITORING SYSTEM (HF edition)
Continuously monitors radar stations and generates automatic tornado predictions.

- Uses your TornadoSuperPredictor (backend/ml_models/tornado_predictor.py)
- Uses ml_data_pipeline from data_processor.py
- Optional free Hugging Face text assistant for alerts/summaries
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import logging
import math
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import torch

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
    # if storm_monitor.py is in same package as data_processor
    from .data_processor import ml_data_pipeline  # type: ignore
except Exception:
    # allow running as a script from repo root
    from data_processor import ml_data_pipeline  # type: ignore

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# =============================================================================
# Inference Bridge
# =============================================================================
class InferenceEngine:
    """
    Wraps TornadoSuperPredictor and returns a stable dict the monitor can use.
    Expects radar input as (C,H,W) or (1,C,H,W). Atmos dict has (1,dim) tensors.
    """

    def __init__(self, weights_path: Optional[str], in_channels: int, device: Optional[str] = None):
        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
        self.model = TornadoSuperPredictor(in_channels=in_channels).to(self.device)
        self.model.eval()
        self.temperature: Optional[float] = None

        if weights_path:
            p = Path(weights_path)
            if not p.exists():
                logger.warning(f"[Inference] Weights not found at {p}. Running with random init.")
            else:
                state = torch.load(p, map_location=self.device)
                if isinstance(state, dict) and any(k.startswith("model.") for k in state.keys()):
                    state = {k.split("model.", 1)[-1]: v for k, v in state.items()}
                missing, unexpected = self.model.load_state_dict(state, strict=False)
                if missing:
                    logger.warning(f"[Inference] Missing keys: {missing[:8]}{'...' if len(missing)>8 else ''}")
                if unexpected:
                    logger.warning(f"[Inference] Unexpected keys: {unexpected[:8]}{'...' if len(unexpected)>8 else ''}")
                logger.info(f"[Inference] Loaded weights from {p}")

    def set_temperature(self, T: float) -> None:
        self.temperature = max(1e-6, float(T))

    @torch.no_grad()
    def predict_one(self, radar_tensor: torch.Tensor, atmo: Optional[Dict[str, torch.Tensor]] = None) -> Dict[str, Any]:
        # Ensure shape (1,C,H,W)
        if radar_tensor.ndim == 3:
            radar_tensor = radar_tensor.unsqueeze(0)
        radar_tensor = radar_tensor.to(self.device, non_blocking=True).float()

        # Ensure required atmos keys / shapes
        atmo = atmo or {}
        def _ensure(name: str, shape: Tuple[int, ...]):
            t = atmo.get(name)
            if t is None:
                atmo[name] = torch.zeros(shape, dtype=torch.float32, device=self.device)
            else:
                t = t if isinstance(t, torch.Tensor) else torch.as_tensor(t, dtype=torch.float32)
                if t.ndim == 1:  # (dim,) -> (1,dim)
                    t = t.unsqueeze(0)
                atmo[name] = t.to(self.device, non_blocking=True)
        _ensure("cape", (1, 1))
        _ensure("wind_shear", (1, 4))
        _ensure("helicity", (1, 2))
        _ensure("temperature", (1, 3))
        _ensure("dewpoint", (1, 2))
        _ensure("pressure", (1, 1))

        out = self.model(radar_tensor, atmo)  # model returns a dict of tensors

        # tornado prob (with optional temperature scaling)
        prob = out.get("tornado_probability")
        if prob is None:
            raise RuntimeError("Model output missing 'tornado_probability'")
        if self.temperature is not None:
            p = prob.clamp(1e-6, 1 - 1e-6)
            logits = torch.log(p / (1 - p)) / self.temperature
            prob = torch.sigmoid(logits)
        prob_f = float(prob[0].item())

        def _grab(name: str, default):
            t = out.get(name, default)
            if isinstance(t, torch.Tensor):
                t = t[0]
                if t.ndim: t = t.tolist()
                else: t = float(t.item())
            return t

        ef_probs = _grab("ef_scale_probs", torch.zeros(6))
        ef_idx = int(_grab("most_likely_ef_scale", torch.tensor([0])))
        loc = _grab("location_offset", torch.tensor([0.0, 0.0]))  # [lat_off, lon_off]
        tim = _grab("timing_predictions", torch.tensor([0.0, 0.0, 0.0]))
        unc = _grab("uncertainty_scores", torch.tensor([0.0, 0.0, 0.0, 0.0]))
        sig = _grab("radar_signatures", torch.tensor([0.0, 0.0, 0.0]))
        ind = _grab("atmospheric_indicators", torch.tensor([0.0, 0.0, 0.0]))

        return {
            "tornado_probability": prob_f,
            "ef_scale_prediction": {f"EF{i}": float(ef_probs[i]) for i in range(6)},
            "most_likely_ef_scale": ef_idx,
            "location_offset": {"lat_offset": float(loc[0]), "lng_offset": float(loc[1])},
            "timing_predictions": {
                "time_to_touchdown_minutes": float(tim[0]),
                "duration_minutes": float(tim[1]),
                "peak_intensity_time_minutes": float(tim[2]),
            },
            "uncertainty_scores": {
                "epistemic": float(unc[0]), "aleatoric": float(unc[1]),
                "total": float(unc[2]), "confidence": float(unc[3]),
            },
            "radar_signatures": {
                "hook_echo_strength": float(sig[0]),
                "mesocyclone_strength": float(sig[1]),
                "velocity_couplet_strength": float(sig[2]),
            },
            "atmospheric_indicators": {
                "cape_score": float(ind[0]),
                "shear_magnitude": float(ind[1]),
                "instability_index": float(ind[2]),
            },
        }

# =============================================================================
# HF assistant (free)
# =============================================================================
class HFWeatherman:
    """
    Small text assistant for alert wording & summaries.
    Falls back to a local template if transformers is unavailable.
    """
    def __init__(self, model_name: str = "google/flan-t5-base", device: Optional[str] = None, max_new_tokens: int = 180):
        self.max_new_tokens = max_new_tokens
        self.pipe = None
        try:
            from transformers import pipeline  # lazy import
            self.device = 0 if (device is None and torch.cuda.is_available()) else device
            self.pipe = pipeline("text2text-generation", model=model_name, tokenizer=model_name, device=self.device)
        except Exception as e:
            logger.warning(f"[HF] transformers not available ({e}); falling back to rule-based text.")

    async def summarize_alert(self, prompt: str) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._gen, prompt)

    async def answer_question(self, question: str, context: Optional[str] = None) -> str:
        q = f"Question: {question}\n"
        if context: q += f"Context: {context}\n"
        q += "Answer succinctly and clearly for a weather app user."
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._gen, q)

    def _gen(self, text: str) -> str:
        if self.pipe is None:
            # fallback
            return "Automated summary: Elevated risk noted. Monitor official warnings. Seek sturdy shelter if a warning is issued."
        out = self.pipe(text, max_new_tokens=self.max_new_tokens, do_sample=False, num_beams=4)
        return out[0]["generated_text"].strip()

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

                pred = self.ie.predict_one(radar, atmo)
                prob = pred["tornado_probability"]
                ef = pred["most_likely_ef_scale"]
                conf = pred["uncertainty_scores"]["confidence"]

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

                # compute absolute touchdown lat/lon from offsets
                lat = station_loc["latitude"] + pred["location_offset"]["lat_offset"] * 0.01
                lon = station_loc["longitude"] + pred["location_offset"]["lng_offset"] * 0.01
                pred["touchdown_location"] = {"latitude": lat, "longitude": lon}
                pred["alert_level"] = alert
                pred["confidence_score"] = conf
                pred["path_trajectory"] = pred.get("path_trajectory") or [
                    {"latitude": lat + i * 0.002, "longitude": lon + i * 0.003, "t": i * 2}
                    for i in range(10)
                ]

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
        # dedupe on stable “content hash” for 15 minutes
        signature = f"{sid}|{round(pred['tornado_probability'], 2)}|{pred['most_likely_ef_scale']}"
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
            f"- Probability: {pred['tornado_probability']:.1%}\n"
            f"- Alert Level: {pred['alert_level']}\n"
            f"- EF Most Likely: EF{pred['most_likely_ef_scale']}\n"
            f"- Confidence: {pred['confidence_score']:.1%}\n"
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
            "severity": min(5, max(1, int(pred["tornado_probability"] * 5) + 1)),
            "predicted_location": {"lat": pred["touchdown_location"]["latitude"], "lng": pred["touchdown_location"]["longitude"]},
            "predicted_path": [{"lat": p["latitude"], "lng": p["longitude"]} for p in pred["path_trajectory"][:3]],
            "confidence": int(pred["confidence_score"] * 100),
            "message": msg,
            "timestamp": datetime.now(timezone.utc),
            "estimated_touchdown_time": (
                datetime.now(timezone.utc) + timedelta(minutes=pred["timing_predictions"].get("time_to_touchdown_minutes", 60))
                if pred["timing_predictions"].get("time_to_touchdown_minutes", 0) > 0 else None
            ),
            "sig_hash": sig_hash,
        }
        await self.db.tornado_alerts.insert_one(alert_doc)
        logger.info(f"🚨 Alert stored for {station['name']} — {pred['tornado_probability']:.1%} risk")

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
                "predictedEFScale": f"EF{p['most_likely_ef_scale']}",
                "confidence": int(p["confidence_score"] * 100),
                "lastUpdated": s["last_updated"].isoformat(),
                "touchdownTime": p["timing_predictions"].get("time_to_touchdown_minutes", "Unknown"),
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
