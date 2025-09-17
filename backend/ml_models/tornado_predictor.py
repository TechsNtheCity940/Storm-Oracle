"""
🌪️ STORM ORACLE — Tornado Super-Predictor (training-ready)

- RadarPatternExtractor: multi-scale CNN + spatial attention pooling
- AtmosphericConditionEncoder: per-variable MLPs -> tokens -> attention -> fused vector
- Heads: probability (sigmoid), EF (softmax), location (reg), timing (reg), uncertainty (sigmoid)
- Calibration: learnable temperature (log_temperature)
- ContinuousLearner: online fine-tuning with replay buffer and EMA weights
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any

import torch
import torch.nn as nn
import torch.nn.functional as F


# ----------------------------- Types ---------------------------------

@dataclass
class TornadoPredictionBatch:
    """All outputs are BATCH TENSORS (no Python scalars)."""
    tornado_probability: torch.Tensor        # (B,)
    ef_scale_probs: torch.Tensor             # (B,6)
    most_likely_ef_scale: torch.Tensor       # (B,)
    location_offset: torch.Tensor            # (B,2)
    timing_predictions: torch.Tensor         # (B,3)
    uncertainty_scores: torch.Tensor         # (B,4) in [0,1]
    radar_signatures: torch.Tensor           # (B,3) [hook, meso, couplet]
    atmospheric_indicators: torch.Tensor     # (B,3) [cape, shear_norm, instability]
    logits: Optional[torch.Tensor] = None    # (B,) pre-sigmoid (for calibration/loss)

    # --- Mapping compatibility so monitor code can do out["key"] / out.get("key") ---
    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)


# ---------------------- Building blocks --------------------------------

class SpatialAttentionPool(nn.Module):
    """
    Turns a 2D feature map (B,C,H,W) into (B,C) using a learned query and MHA over H*W tokens.
    """
    def __init__(self, channels: int, num_heads: int = 8):
        super().__init__()
        self.channels = channels
        self.pos_embed = nn.Parameter(torch.randn(1, channels, 1))  # mild per-channel positional bias
        self.query = nn.Parameter(torch.randn(1, 1, channels))      # learned global query token
        self.attn = nn.MultiheadAttention(embed_dim=channels, num_heads=num_heads, batch_first=True)
        self.ln = nn.LayerNorm(channels)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B,C,H,W) -> tokens: (B, H*W, C)
        B, C, H, W = x.shape
        tokens = x.view(B, C, H * W).transpose(1, 2)  # (B, HW, C)
        # broadcast pos_embed over tokens
        tokens = self.ln(tokens + self.pos_embed.expand(B, C, 1).transpose(1, 2))
        q = self.query.expand(B, -1, -1)  # (B,1,C)
        pooled, _ = self.attn(q, tokens, tokens)  # (B,1,C)
        return pooled.squeeze(1)  # (B,C)


class RadarPatternExtractor(nn.Module):
    """
    Advanced radar pattern extraction with spatial attention pooling.
    Accepts variable input_channels (e.g., 3×T for T time steps).
    """
    def __init__(self, input_channels: int = 3):
        super().__init__()
        self.conv1 = nn.Conv2d(input_channels, 64, kernel_size=7, padding=3)
        self.conv2 = nn.Conv2d(64, 128, kernel_size=5, padding=2)
        self.conv3 = nn.Conv2d(128, 256, kernel_size=3, padding=1)
        self.conv4 = nn.Conv2d(256, 512, kernel_size=3, padding=1)

        self.bn4 = nn.BatchNorm2d(512)

        # Specialized detectors
        self.hook_echo_detector = nn.Conv2d(512, 64, kernel_size=3, padding=1)
        self.mesocyclone_detector = nn.Conv2d(512, 64, kernel_size=5, padding=2)
        self.velocity_couplet_detector = nn.Conv2d(512, 64, kernel_size=3, padding=1)

        # Attention pooling to summarize (B,512,H',W') -> (B,512)
        self.pool = SpatialAttentionPool(512, num_heads=8)

        # Combine base + specialists -> 512 + 64*3 = 704 -> project to 1024
        self.proj = nn.Sequential(
            nn.Linear(512 + 64 * 3, 1024),
            nn.ReLU(),
            nn.Dropout(0.5),
        )

    def forward(self, radar_data: torch.Tensor) -> Dict[str, torch.Tensor]:
        # radar_data: (B,C,H,W)
        x = F.relu(self.conv1(radar_data)); x = F.max_pool2d(x, 2)
        x = F.relu(self.conv2(x));          x = F.max_pool2d(x, 2)
        x = F.relu(self.conv3(x));          x = F.max_pool2d(x, 2)
        x = F.relu(self.conv4(x));          x = self.bn4(x)

        hook = F.relu(self.hook_echo_detector(x))
        meso = F.relu(self.mesocyclone_detector(x))
        vel  = F.relu(self.velocity_couplet_detector(x))

        base_vec = self.pool(x)                             # (B,512)
        hook_vec = hook.mean(dim=(2, 3))                    # (B,64)
        meso_vec = meso.mean(dim=(2, 3))                    # (B,64)
        vel_vec  = vel.mean(dim=(2, 3))                     # (B,64)

        fused = torch.cat([base_vec, hook_vec, meso_vec, vel_vec], dim=1)  # (B,704)
        combined = self.proj(fused)  # (B,1024)

        strengths = torch.stack([
            hook_vec.mean(dim=1),      # (B,)
            meso_vec.mean(dim=1),      # (B,)
            vel_vec.mean(dim=1),       # (B,)
        ], dim=1)  # (B,3)

        return {
            "combined_features": combined,
            "signature_strengths": strengths,  # hook, meso, velocity couplet
        }


class AtmosphericConditionEncoder(nn.Module):
    """
    Encode environmental parameters using per-variable MLPs, then treat them as tokens and apply MHA.
    """
    def __init__(self):
        super().__init__()
        self.enc_cape        = nn.Linear(1, 32)
        self.enc_shear       = nn.Linear(4, 64)  # 0–1, 0–3, 0–6, deep
        self.enc_helicity    = nn.Linear(2, 32)  # 0–1, 0–3
        self.enc_temp        = nn.Linear(3, 32)  # sfc, 850, 500
        self.enc_dewpoint    = nn.Linear(2, 32)  # sfc, 850
        self.enc_pressure    = nn.Linear(1, 16)

        # we will embed each of the 6 groups to dim=64 and self-attend
        self.to_64 = nn.ModuleDict({
            "cape":     nn.Linear(32, 64),
            "shear":    nn.Identity(),          # already 64
            "helicity": nn.Linear(32, 64),
            "temp":     nn.Linear(32, 64),
            "dewpoint": nn.Linear(32, 64),
            "pressure": nn.Linear(16, 64),
        })
        self.ln = nn.LayerNorm(64)
        self.attn = nn.MultiheadAttention(embed_dim=64, num_heads=4, batch_first=True)

        self.fuse = nn.Sequential(
            nn.Linear(64 * 6, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
        )

    def forward(self, atmo: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
        dev = next(self.parameters()).device

        def ensure_2d(t: Optional[torch.Tensor], d: int) -> torch.Tensor:
            if t is None:
                t = torch.zeros(1, d, device=dev)
            if not isinstance(t, torch.Tensor):
                t = torch.as_tensor(t, dtype=torch.float32, device=dev)
            if t.ndim == 1:
                t = t.view(1, d)
            return t

        cape = ensure_2d(atmo.get("cape"),        1)
        shear= ensure_2d(atmo.get("wind_shear"),  4)
        hel  = ensure_2d(atmo.get("helicity"),    2)
        temp = ensure_2d(atmo.get("temperature"), 3)
        dew  = ensure_2d(atmo.get("dewpoint"),    2)
        pres = ensure_2d(atmo.get("pressure"),    1)

        cape_e = F.relu(self.enc_cape(cape))           # (B,32)
        shear_e= F.relu(self.enc_shear(shear))         # (B,64)
        hel_e  = F.relu(self.enc_helicity(hel))        # (B,32)
        temp_e = F.relu(self.enc_temp(temp))           # (B,32)
        dew_e  = F.relu(self.enc_dewpoint(dew))        # (B,32)
        pres_e = F.relu(self.enc_pressure(pres))       # (B,16)

        tokens = torch.stack([
            self.ln(self.to_64["cape"](cape_e)),
            self.ln(self.to_64["shear"](shear_e)),
            self.ln(self.to_64["helicity"](hel_e)),
            self.ln(self.to_64["temp"](temp_e)),
            self.ln(self.to_64["dewpoint"](dew_e)),
            self.ln(self.to_64["pressure"](pres_e)),
        ], dim=1)  # (B, 6, 64)

        attn_out, _ = self.attn(tokens, tokens, tokens)  # (B,6,64)
        fused = self.fuse(attn_out.reshape(attn_out.size(0), -1))  # (B,256)

        # easy indicators for explanations/QA
        shear_mag = torch.linalg.vector_norm(shear, dim=-1)  # (B,)
        instab = cape.squeeze(-1) * shear_mag                # (B,)

        return {
            "atmospheric_features": fused,                # (B,256)
            "cape_score": cape.squeeze(-1),               # (B,)
            "shear_magnitude": shear_mag,                 # (B,)
            "instability_index": instab,                  # (B,)
        }


# -------------------------- Main model --------------------------------

class TornadoSuperPredictor(nn.Module):
    def __init__(self, in_channels: int = 3):
        super().__init__()
        self.radar_extractor = RadarPatternExtractor(input_channels=in_channels)
        self.atmo_encoder    = AtmosphericConditionEncoder()

        fused_dim = 1024 + 256

        self.prob_head = nn.Sequential(
            nn.Linear(fused_dim, 512), nn.ReLU(), nn.Dropout(0.4),
            nn.Linear(512, 256), nn.ReLU(),
            nn.Linear(256, 1)
        )
        self.ef_head = nn.Sequential(
            nn.Linear(fused_dim, 512), nn.ReLU(), nn.Dropout(0.4),
            nn.Linear(512, 6)
        )
        self.loc_head = nn.Sequential(
            nn.Linear(fused_dim, 512), nn.ReLU(), nn.Dropout(0.4),
            nn.Linear(512, 2)
        )
        self.time_head = nn.Sequential(
            nn.Linear(fused_dim, 512), nn.ReLU(), nn.Dropout(0.4),
            nn.Linear(512, 3)
        )
        self.unc_head = nn.Sequential(
            nn.Linear(fused_dim, 256), nn.ReLU(),
            nn.Linear(256, 4)
        )

        # temperature parameter for calibration (start at 1.0)
        self.register_parameter("log_temperature", nn.Parameter(torch.zeros(())))

        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, (nn.Linear, nn.Conv2d)):
                if isinstance(m, nn.Linear):
                    nn.init.xavier_uniform_(m.weight)
                else:
                    nn.init.kaiming_uniform_(m.weight, mode="fan_out", nonlinearity="relu")
                if m.bias is not None:
                    nn.init.zeros_(m.bias)

    @property
    def temperature(self) -> torch.Tensor:
        return torch.exp(self.log_temperature)  # positive

    def forward(self, radar_x: torch.Tensor, atmo: Dict[str, torch.Tensor]) -> TornadoPredictionBatch:
        # radar_x: (B,C,H,W), atmo: dict of (B,dim)
        r = self.radar_extractor(radar_x)
        a = self.atmo_encoder(atmo)

        fused = torch.cat([r["combined_features"], a["atmospheric_features"]], dim=1)  # (B,1280)

        logits = self.prob_head(fused).squeeze(-1)             # (B,)
        logits = logits / self.temperature.clamp_min(1e-6)     # calibrated logits
        probs  = torch.sigmoid(logits)                         # (B,)

        ef_logits = self.ef_head(fused)                        # (B,6)
        ef_probs  = F.softmax(ef_logits, dim=-1)
        ef_idx    = ef_probs.argmax(dim=-1)

        loc = self.loc_head(fused)                             # (B,2)
        tim = self.time_head(fused)                            # (B,3)
        unc = torch.sigmoid(self.unc_head(fused))              # (B,4) in [0,1]

        return TornadoPredictionBatch(
            tornado_probability=probs,
            ef_scale_probs=ef_probs,
            most_likely_ef_scale=ef_idx,
            location_offset=loc,
            timing_predictions=tim,
            uncertainty_scores=unc,
            radar_signatures=r["signature_strengths"],
            atmospheric_indicators=torch.stack([
                a["cape_score"], a["shear_magnitude"], a["instability_index"]
            ], dim=1),
            logits=logits,
        )


# --------------------- Continuous learning wrapper --------------------

class ContinuousLearner(nn.Module):
    """
    Light wrapper that adds:
      - optimizer + (optional) pos_weight or focal loss
      - EMA weights for stable inference during online updates
      - small replay buffer to avoid catastrophic forgetting
    """
    def __init__(
        self,
        model: TornadoSuperPredictor,
        lr: float = 1e-4,
        wd: float = 1e-4,
        use_focal: bool = False,
        pos_weight: Optional[float] = None,
        ema_decay: float = 0.999,
        replay_capacity: int = 2048,
        device: Optional[torch.device] = None,
    ):
        super().__init__()
        self.model = model
        self.device = device or next(model.parameters()).device
        self.opt = torch.optim.AdamW(self.model.parameters(), lr=lr, weight_decay=wd)
        self.use_focal = use_focal
        self.pos_weight = None if pos_weight is None else torch.tensor(pos_weight, device=self.device)
        self.ema_decay = ema_decay

        # EMA weights
        self.shadow = {k: v.detach().clone() for k, v in self.model.state_dict().items()}
        self.replay_capacity = replay_capacity
        self._replay: List[Tuple[torch.Tensor, Dict[str, torch.Tensor], torch.Tensor]] = []

    def _bce_loss(self, logits: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
        if self.pos_weight is not None:
            return F.binary_cross_entropy_with_logits(logits, y.float(), pos_weight=self.pos_weight)
        return F.binary_cross_entropy_with_logits(logits, y.float())

    def _focal_loss(self, logits: torch.Tensor, y: torch.Tensor, gamma: float = 2.0, alpha: float = 0.5) -> torch.Tensor:
        p = torch.sigmoid(logits)
        pt = p * y + (1 - p) * (1 - y)
        w = (1 - pt).pow(gamma)
        at = alpha * y + (1 - alpha) * (1 - y)
        loss = -(y * torch.log(p.clamp_min(1e-9)) + (1 - y) * torch.log((1 - p).clamp_min(1e-9))) * w * at
        return loss.mean()

    @torch.no_grad()
    def _update_ema(self):
        for k, v in self.model.state_dict().items():
            self.shadow[k].mul_(self.ema_decay).add_(v, alpha=(1.0 - self.ema_decay))

    def train_step(self, radar_x: torch.Tensor, atmo: Dict[str, torch.Tensor], y: torch.Tensor) -> Dict[str, float]:
        self.model.train()
        out = self.model(radar_x, atmo)   # TornadoPredictionBatch

        logits = out.logits
        if logits is None:
            # safety: recompute
            probs = out.tornado_probability
            logits = torch.log(probs.clamp(1e-6) / (1 - probs.clamp(1e-6)))

        loss = self._focal_loss(logits, y) if self.use_focal else self._bce_loss(logits, y)

        self.opt.zero_grad(set_to_none=True)
        loss.backward()
        nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
        self.opt.step()
        self._update_ema()

        # push to replay
        if self.replay_capacity > 0:
            with torch.no_grad():
                if len(self._replay) >= self.replay_capacity:
                    self._replay.pop(0)
                self._replay.append((
                    radar_x.detach().cpu(),
                    {k: v.detach().cpu() for k, v in atmo.items()},
                    y.detach().cpu()
                ))

        with torch.no_grad():
            prob = out.tornado_probability.mean().item()
        return {"loss": float(loss.item()), "avg_prob": float(prob)}

    @torch.no_grad()
    def ema_state_dict(self) -> Dict[str, torch.Tensor]:
        return {k: v.clone() for k, v in self.shadow.items()}

    @torch.no_grad()
    def load_ema_weights(self):
        self.model.load_state_dict(self.ema_state_dict())

    def replay_step(self, batch_size: int = 16) -> Optional[Dict[str, float]]:
        if not self._replay:
            return None
        import random
        idxs = random.sample(range(len(self._replay)), k=min(batch_size, len(self._replay)))
        xs = torch.cat([self._replay[i][0] for i in idxs], dim=0).to(self.device)
        ys = torch.cat([self._replay[i][2] for i in idxs], dim=0).to(self.device)
        atmo: Dict[str, torch.Tensor] = {}
        keys = list(self._replay[idxs[0]][1].keys())
        for k in keys:
            atmo[k] = torch.cat([self._replay[i][1][k] for i in idxs], dim=0).to(self.device)
        return self.train_step(xs, atmo, ys)
