"""
Storm Oracle — Real Py-ART Radar (Radar Omega–style)
---------------------------------------------------
- Live NEXRAD L2 from AWS Open Data (anonymous S3)
- Station PPI products & national composite grid
- Products: base/hi-res reflectivity, base/hi-res velocity, storm-relative velocity,
            spectrum width, ZDR, CC, KDP
- Rotation visualization: az-shear proxy + couplet dots
- Custom tornado markers (confirmed/predicted), size by intensity, optional spin
- Optional overlays: lightning strikes, hail swaths/points, surface wind vectors
- "Easy Mode": plain-English legend for non-experts

Author: You + ChatGPT
"""

import os, io, sys, math, logging, tempfile
from datetime import datetime, timezone, timedelta
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.transforms import Affine2D
import cartopy.crs as ccrs
import cartopy.feature as cfeature

# Prefer your local Py-ART path if provided (your note: F:/pyart)
_LOCAL_PYART = r"F:/pyart"
if os.path.isdir(_LOCAL_PYART) and _LOCAL_PYART not in sys.path:
    sys.path.insert(0, _LOCAL_PYART)

import pyart
from pyart.graph import cm as pyart_cm

try:
    import boto3
    from botocore import UNSIGNED
    from botocore.client import Config
except Exception:
    boto3 = None

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# -------------------- Config --------------------

AWS_BUCKET = "noaa-nexrad-level2"
AWS_REGION = "us-east-1"

DEFAULT_COMPOSITE_STATIONS = [
    "KTLX","KFDR","KAMA","KDDC","KICT","KEAX","KSGF","KLSX","KDVN","KDMX","KOAX","KUEX",
    "KLOT","KGRB","KMKX","KDTX","KCLE","KPBZ","KFCX","KLWX","KOKX","KBOX","KGYX","KCBW",
    "KTLH","KJAX","KTBW","KAMX","KHGX","KEWX","KFWS","KABX","KRIW","KFTG","KRGX",
    "KMAX","KATX","KRTX","KPOE","KLCH","KLIX"
]

# Field map
FIELD = {
    "base_reflectivity": "reflectivity",               # lowest tilt
    "reflectivity_hr": "reflectivity",                 # plot with finer binning
    "base_velocity": "velocity",
    "velocity_hr": "velocity",
    "storm_relative_velocity": "velocity",
    "spectrum_width": "spectrum_width",
    "zdr": "differential_reflectivity",
    "cc": "cross_correlation_ratio",
    "kdp": "specific_differential_phase",
}

# Colormaps (Radar-Omega vibe)
CMAPS = {
    "NWSRef": pyart_cm.NWSRef,
    "HomeyerRainbow": pyart_cm.HomeyerRainbow,
    "NWSStormClearReflectivity": pyart_cm.NWSStormClearReflectivity,
    "BlueBrown12": pyart_cm.BlueBrown12,
    "Carbone42": pyart_cm.Carbone42,
    "NWSVelocity": pyart_cm.NWSVel,
    "BuDRd18": pyart_cm.BuDRd18,
    "BlueBrown18": pyart_cm.BlueBrown18,
    "viridis": plt.cm.get_cmap("viridis"),
    "twilight": plt.cm.get_cmap("twilight"),
    "turbo": plt.cm.get_cmap("turbo"),
}

def _cmap(name: str):
    return CMAPS.get(name, CMAPS["NWSRef"])

def _now(fmt="%Y-%m-%d %H:%M:%S UTC"): return datetime.now(timezone.utc).strftime(fmt)

def _aws_client():
    if boto3 is None:
        raise RuntimeError("Missing boto3/botocore: pip install boto3 botocore")
    return boto3.client("s3", config=Config(signature_version=UNSIGNED), region_name=AWS_REGION)

def _latest_key(station: str, max_age_h=6):
    s3 = _aws_client()
    now = datetime.utcnow()
    for back in range(max_age_h+1):
        dt = now - timedelta(hours=back)
        prefix = f"{dt:%Y}/{station}/{station}{dt:%Y%m%d}"
        r = s3.list_objects_v2(Bucket=AWS_BUCKET, Prefix=prefix)
        objs = r.get("Contents", [])
        if objs:
            objs.sort(key=lambda o: o["LastModified"])
            return objs[-1]["Key"]
    return None

def _read_l2(station: str):
    key = _latest_key(station)
    if not key: raise RuntimeError(f"No recent L2 on AWS for {station}")
    s3 = _aws_client()
    data = s3.get_object(Bucket=AWS_BUCKET, Key=key)["Body"].read()
    radar = pyart.io.read_nexrad_archive(io.BytesIO(data))
    return radar, key

def _bytes(fig, dpi=170):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight",
                facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig); buf.seek(0)
    return buf.getvalue()

def _add_features(ax, faint=True):
    color, alpha, lw = ("gray", 0.25, 0.4) if faint else ("white", 0.6, 0.8)
    ax.add_feature(cfeature.COASTLINE, edgecolor=color, linewidth=lw, alpha=alpha)
    ax.add_feature(cfeature.BORDERS,   edgecolor=color, linewidth=lw, alpha=alpha)
    ax.add_feature(cfeature.STATES,    edgecolor=color, linewidth=lw, alpha=alpha)

def _gridliner(ax):
    gl = ax.gridlines(draw_labels=True, color="white", alpha=0.25)
    gl.top_labels = gl.right_labels = False
    gl.xlabel_style = {"color":"white","size":8}
    gl.ylabel_style = {"color":"white","size":8}

# --------- Easy Mode text ---------

def _ref_category(dbz):
    if np.isnan(dbz): return "No echo"
    if dbz < 10: return "Very light"
    if dbz < 20: return "Light"
    if dbz < 30: return "Moderate"
    if dbz < 40: return "Heavy"
    if dbz < 50: return "Very heavy"
    if dbz < 60: return "Severe"
    return "Extreme"

# --------- Rotation helpers ---------

def _storm_relative_velocity(radar, sweep_idx, storm_motion_uv):
    """Return SRV field (array) given (u, v) m/s storm motion."""
    vel = radar.fields["velocity"]["data"]
    vel = vel if vel.ndim == 2 else vel[sweep_idx]

    az = np.deg2rad(radar.azimuth["data"])  # per ray
    # Build array of radial unit vectors (east, north)
    ux = np.sin(az)[:, None]  # east component
    uy = np.cos(az)[:, None]  # north component
    u, v = storm_motion_uv
    proj = u*ux + v*uy  # radial projection of storm motion
    return vel - proj

def _az_shear_proxy(radial_vel, gate_km=0.25):
    """
    Simple, fast azimuthal shear proxy from 3x3 finite differences.
    Returns shear magnitude (m/s per km).
    """
    v = radial_vel.filled(np.nan) if hasattr(radial_vel, "filled") else np.array(radial_vel, dtype=float)
    # central differences
    dv_dr = np.abs(np.nan_to_num(v[:, 2:] - v[:, :-2]))  # along range
    dv_da = np.abs(np.nan_to_num(v[2:, :] - v[:-2, :]))  # along azimuth
    # pad back
    dv_dr = np.pad(dv_dr, ((0,0),(1,1)), mode="edge")
    dv_da = np.pad(dv_da, ((1,1),(0,0)), mode="edge")
    # convert to per-km assuming gate_km spacing
    shear = np.sqrt(dv_dr**2 + dv_da**2) / max(gate_km, 0.25)
    return shear

def _find_velocity_couplets(v, thresh_pair=45.0):
    """
    Find inbound/outbound adjacent maxima (very naive).
    Returns list of (ray_idx, gate_idx).
    """
    arr = v.filled(np.nan) if hasattr(v, "filled") else np.array(v, float)
    hits = []
    for i in range(arr.shape[0]-1):
        diff = arr[i+1] - arr[i]
        # strong sign change neighboring gates (approx couplet)
        j = np.nanargmax(np.abs(diff))
        if np.isfinite(diff[j]) and np.abs(diff[j]) >= thresh_pair:
            hits.append((i, j))
    return hits[:10]  # cap

# --------- Overlay helpers ---------

def _draw_tornado_markers(ax, items, marker_path, colorize=None, spin=False):
    """
    items: list[dict] with keys lon, lat, intensity (EF-scale or 0..5), size_scale (optional)
    colorize: (r,g,b) tint multiply in [0,1] or None
    spin: if True, rotate ~intensity*angle for visual motion
    """
    if not items: return
    try:
        img = plt.imread(marker_path)  # supports PNG with alpha
    except Exception as e:
        ax.text(0.5,0.02,f"Marker load failed: {e}", transform=ax.transAxes,
                ha="center", va="bottom", color="red")
        return

    for it in items:
        lon, lat = it["lon"], it["lat"]
        inten = float(it.get("intensity", 1.0))
        size_scale = float(it.get("size_scale", 1.0))
        # base size ~ 0.35 degrees at midlat * scale * intensity factor
        base_deg = 0.35 * size_scale * (0.6 + 0.4*min(max(inten,0.2), 6))
        extent = [lon - base_deg/2, lon + base_deg/2, lat - base_deg/2, lat + base_deg/2]

        if colorize is not None and img.ndim == 3:
            tint = np.array(colorize)[None,None,:]
            rgba = img.copy()
            rgba[..., :3] = np.clip(rgba[..., :3] * tint, 0, 1)
            plot_img = rgba
        else:
            plot_img = img

        im = ax.imshow(plot_img, extent=extent, transform=ccrs.PlateCarree(), zorder=20)
        if spin:
            angle = 30.0 * inten  # deg
            trans_data = Affine2D().rotate_deg_around((extent[0]+extent[1])/2,
                                                      (extent[2]+extent[3])/2,
                                                      angle) + ax.transData
            im.set_transform(trans_data)

def _draw_lightning(ax, strikes):
    """
    strikes: list[dict] with lon, lat, age_sec(optional), amp(optional)
    Visual: star markers with size by amplitude, alpha fades with age
    """
    if not strikes: return
    lons = [s["lon"] for s in strikes]
    lats = [s["lat"] for s in strikes]
    amps = np.array([float(s.get("amp", 1.0)) for s in strikes])
    ages = np.array([float(s.get("age_sec", 0.0)) for s in strikes])
    sizes = 30 + 40*np.clip(amps/200.0, 0, 1)
    alphas = np.clip(1.0 - ages/900.0, 0.2, 1.0)  # fade over 15 min
    for lon, lat, sz, a in zip(lons, lats, sizes, alphas):
        ax.plot(lon, lat, marker="*", markersize=sz/6, color="yellow",
                markeredgecolor="white", alpha=a, transform=ccrs.PlateCarree(), zorder=15)

def _draw_hail(ax, hail_points):
    """
    hail_points: list[dict] with lon, lat, mesh_mm or size_in
    Visual: circles sized by hail diameter, colored cyan/white
    """
    if not hail_points: return
    for h in hail_points:
        lon, lat = h["lon"], h["lat"]
        size_in = float(h.get("size_in", h.get("mesh_mm", 25.0)/25.4))
        r = 0.15 * (0.5 + min(size_in, 4.0))  # deg; cap exaggeration
        circ = plt.Circle((lon, lat), r, transform=ccrs.PlateCarree(),
                          edgecolor="white", facecolor="cyan", alpha=0.35, lw=1.2, zorder=10)
        ax.add_patch(circ)

def _draw_wind(ax, vectors):
    """
    vectors: list[dict] with lon, lat, u, v (m/s)
    Visual: barbs
    """
    if not vectors: return
    lons = np.array([w["lon"] for w in vectors])
    lats = np.array([w["lat"] for w in vectors])
    u = np.array([w["u"] for w in vectors])
    v = np.array([w["v"] for w in vectors])
    ax.barbs(lons, lats, u, v, transform=ccrs.PlateCarree(), length=5, color="white", zorder=12)

# -------------------- Main class --------------------

class RadarProcessor:
    def __init__(self, tornado_marker_path: str = "/mnt/data/tornado-marker.png"):
        self.tornado_marker_path = tornado_marker_path

    # ---------- Station PPI ----------
    def get_station(
        self,
        station_id: str,
        product: str = "base_reflectivity",
        sweep: int = 0,
        cmap: str = "NWSRef",
        easy_mode: bool = True,
        storm_motion_uv: tuple[float,float] | None = None,
        overlays: dict | None = None,
    ):
        """
        product: one of FIELD.keys()
        storm_motion_uv: (u,v) m/s for SRV (eastward, northward). If None, SRV uses base velocity.
        overlays: {
          "tornado_confirmed": [{"lon":..,"lat":..,"intensity":EF,"size_scale":..}, ...],
          "tornado_predicted": [{"lon":..,"lat":..,"intensity":rating}, ...],
          "lightning": [{"lon":..,"lat":..,"age_sec":..,"amp":..}, ...],
          "hail": [{"lon":..,"lat":..,"size_in":..}, ...],
          "winds": [{"lon":..,"lat":..,"u":..,"v":..}, ...],
        }
        """
        try:
            field = FIELD.get(product)
            if field is None:
                raise ValueError(f"Unsupported product '{product}'. Options: {list(FIELD)}")

            radar, key = _read_l2(station_id)
            if field not in radar.fields:
                raise RuntimeError(f"{station_id} volume missing '{field}'")

            display = pyart.graph.RadarMapDisplay(radar)

            # choose vmin/vmax
            if field == "reflectivity":
                vmin, vmax = (0, 70)
            elif field == "velocity":
                vmin, vmax = (-35, 35)
            elif field == "spectrum_width":
                vmin, vmax = (0, 12)
            elif field == "differential_reflectivity":
                vmin, vmax = (-1, 6)
            elif field == "cross_correlation_ratio":
                vmin, vmax = (0.7, 1.0)
            elif field == "specific_differential_phase":
                vmin, vmax = (0, 5)
            else:
                vmin, vmax = (None, None)

            fig = plt.figure(figsize=(10, 9), facecolor="black")
            ax = plt.axes(projection=ccrs.PlateCarree())
            ax.set_facecolor("black"); _add_features(ax, faint=True); _gridliner(ax)

            cm = _cmap(cmap)

            lat0 = float(radar.latitude["data"][0]); lon0 = float(radar.longitude["data"][0])
            deg_lat = 230.0/111.0
            deg_lon = 230.0/(111.0*max(math.cos(math.radians(lat0)), 1e-3))
            ax.set_extent([lon0-deg_lon, lon0+deg_lon, lat0-deg_lat, lat0+deg_lat], crs=ccrs.PlateCarree())

            # Build field to plot (SRV / hires)
            data = radar.fields[field]["data"]
            if product == "storm_relative_velocity" and storm_motion_uv is not None:
                data = _storm_relative_velocity(radar, sweep, storm_motion_uv)

            # Plot options for "hi-res": use pcolormesh with no shading to retain native bins
            hi_res = product.endswith("_hr") or product == "storm_relative_velocity"
            display.plot_ppi_map(
                field if product != "storm_relative_velocity" else None,
                sweep=sweep,
                ax=ax,
                projection=ccrs.PlateCarree(),
                vmin=vmin, vmax=vmax, cmap=cm,
                colorbar_flag=True, title_flag=False,
                lat_lines=None, lon_lines=None, embellish=False,
                raster=False
            )
            # If we replaced data (SRV), draw it manually over the same axes
            if product == "storm_relative_velocity":
                x, y = display._get_x_y(sweep, True, None)  # meters in map proj
                # convert meters to degrees approx near radar:
                xy = display._get_x_y(sweep, False, None)
                pm = ax.pcolormesh(x, y, data, cmap=cm, vmin=vmin, vmax=vmax, transform=display._projection,
                                   shading="nearest", zorder=9)

            # Title + station mark
            human_time = _now()
            ax.text(0.02, 0.98, f"{station_id} • {product.replace('_',' ').title()} • {human_time}",
                    transform=ax.transAxes, va="top", ha="left", color="white",
                    fontsize=12, fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.4", facecolor="black", alpha=0.6))
            ax.plot([lon0],[lat0], marker="o", markersize=8, markerfacecolor="white",
                    markeredgecolor="red", transform=ccrs.PlateCarree(), zorder=12)

            # Rotation visualization on velocity/SRV
            if product in ("base_velocity","velocity_hr","storm_relative_velocity"):
                vel = radar.fields["velocity"]["data"] if product != "storm_relative_velocity" else data
                vel2d = vel if vel.ndim == 2 else vel[sweep]
                shear = _az_shear_proxy(vel2d)
                # Display translucent magenta veil where shear high
                try:
                    x, y = display._get_x_y(sweep, True, None)
                    ax.contourf(x, y, np.nan_to_num(shear), levels=[20,30,40,60,80,120],
                                colors=["#7a00ff33","#b100ff33","#ff00ff33","#ff00ff55","#ff00ff77"],
                                transform=display._projection, zorder=10)
                except Exception:
                    pass
                # Mark potential couplets
                for (i,j) in _find_velocity_couplets(vel2d, thresh_pair=45.0):
                    try:
                        ray_az = np.deg2rad(radar.azimuth["data"][i])
                        rg = radar.range["data"][j]  # meters
                        # x/y in meters relative to radar; convert by display utility
                        xg, yg = display._get_x_y(sweep, True, None)
                        ax.plot(xg[j], yg[i], "wo", ms=5, transform=display._projection, zorder=12)
                    except Exception:
                        break

            # Easy mode legend
            if easy_mode:
                lines = []
                if field == "reflectivity":
                    d = data if isinstance(data, np.ndarray) else data[sweep]
                    vals = np.array(d).astype(float)
                    p90 = np.nanpercentile(vals[np.isfinite(vals)], 90) if np.isfinite(vals).any() else np.nan
                    lines += [f"Top echoes ~{p90:.0f} dBZ ({_ref_category(p90)})",
                              "0–10 very light • 20–30 moderate",
                              "40–50 heavy • 60+ extreme/hail risk"]
                elif "velocity" in product:
                    lines += ["Inbound vs outbound → rotation",
                              "Magenta veil = high azimuthal shear",
                              "Dots = possible couplets (gate-to-gate shear)"]
                elif field == "cross_correlation_ratio":
                    lines += ["ρhv ~1.0: uniform (rain/snow)",
                              "<0.85 + high dBZ: debris/hail"]
                elif field == "differential_reflectivity":
                    lines += ["High ZDR: big/oblate drops",
                              "Low ZDR + high dBZ: hail"]
                elif field == "specific_differential_phase":
                    lines += ["Higher KDP: heavier rain rates"]
                if lines:
                    ax.text(0.98, 0.02, "\n".join(lines), transform=ax.transAxes,
                            ha="right", va="bottom", color="white", fontsize=9,
                            bbox=dict(boxstyle="round,pad=0.5", facecolor="black", alpha=0.6))

            # ----- Overlays -----
            overlays = overlays or {}
            _draw_lightning(ax, overlays.get("lightning"))
            _draw_hail(ax, overlays.get("hail"))
            _draw_wind(ax, overlays.get("winds"))

            # Tornado markers
            _draw_tornado_markers(ax, overlays.get("tornado_confirmed"),
                                  self.tornado_marker_path, colorize=None, spin=True)
            _draw_tornado_markers(ax, overlays.get("tornado_predicted"),
                                  self.tornado_marker_path, colorize=(0.3,1.0,0.3), spin=False)

            return _bytes(fig, dpi=170)

        except Exception as e:
            logger.exception("Station render failed")
            return self._error_tile(f"{station_id} • {product}: {e}")

    # ---------- National Composite ----------
    def get_composite(
        self,
        product: str = "base_reflectivity",
        stations: list[str] | None = None,
        cmap: str = "NWSRef",
        easy_mode: bool = True
    ):
        """
        Quick-look national mosaic using Py-ART gridding.
        (For production accuracy, reproject grid to lon/lat with pyproj.)
        """
        try:
            field = FIELD.get(product)
            if field is None: raise ValueError(f"Unsupported product '{product}'")

            stations = stations or DEFAULT_COMPOSITE_STATIONS
            radars = []
            for s in stations:
                try:
                    r, _ = _read_l2(s)
                    if field in r.fields: radars.append(r)
                except Exception:
                    continue
            if not radars: raise RuntimeError("No usable radars fetched.")

            grid = pyart.map.grid_from_radars(
                radars, fields=[field],
                grid_shape=(1, 700, 1100),
                grid_limits=((0, 20000.0), (-2500000.0, 2500000.0), (-4000000.0, -500000.0)),
                weighting_function="Barnes2", gridding_algo="map_to_grid",
                roi_func='constant', constant_roi=2000.0
            )
            f = grid.fields[field]["data"][0]

            # color limits as station
            if field == "reflectivity": vmin, vmax = (0,70)
            elif field == "velocity": vmin, vmax = (-35,35)
            elif field == "spectrum_width": vmin, vmax = (0,12)
            elif field == "differential_reflectivity": vmin, vmax = (-1,6)
            elif field == "cross_correlation_ratio": vmin, vmax = (0.7,1.0)
            elif field == "specific_differential_phase": vmin, vmax = (0,5)
            else: vmin, vmax = (np.nanmin(f), np.nanmax(f))

            fig = plt.figure(figsize=(12.5, 8.5), facecolor="black")
            ax = plt.axes(projection=ccrs.PlateCarree())
            ax.set_facecolor("black")
            ax.set_extent([-130, -60, 20, 50], crs=ccrs.PlateCarree())
            _add_features(ax, faint=True)

            im = ax.imshow(np.flipud(f), extent=[-130,-60,20,50], origin="upper",
                           cmap=_cmap(cmap), vmin=vmin, vmax=vmax, alpha=0.95,
                           transform=ccrs.PlateCarree())
            cb = plt.colorbar(im, ax=ax, shrink=0.7, pad=0.02, aspect=30)
            cb.ax.tick_params(colors="white", labelsize=9)
            label = {
                "reflectivity": "Reflectivity (dBZ)",
                "velocity": "Velocity (m/s)",
                "spectrum_width": "Spectrum Width (m/s)",
                "differential_reflectivity": "ZDR (dB)",
                "cross_correlation_ratio": "ρhv",
                "specific_differential_phase": "KDP (°/km)"
            }.get(field, field)
            cb.set_label(label, color="white", fontsize=11)

            ax.text(0.02, 0.98, f"Storm Oracle — National Composite • {product.replace('_',' ').title()} • {_now()}",
                    transform=ax.transAxes, va="top", ha="left", color="white",
                    fontsize=12, fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.5", facecolor="black", alpha=0.6))

            if easy_mode and field == "reflectivity":
                ax.text(0.98, 0.02, "0–10 very light\n20–30 moderate\n40–50 heavy\n60+ extreme/hail risk",
                        transform=ax.transAxes, ha="right", va="bottom", color="white", fontsize=9,
                        bbox=dict(boxstyle="round,pad=0.5", facecolor="black", alpha=0.6))

            return _bytes(fig, dpi=150)

        except Exception as e:
            logger.exception("Composite render failed")
            return self._error_tile(f"Composite • {product}: {e}")

    # ---------- Error tile ----------
    def _error_tile(self, msg):
        fig, ax = plt.subplots(1,1, figsize=(6,4), facecolor="black")
        ax.set_facecolor("black")
        ax.text(0.5,0.55,"Radar Error", ha="center", va="center",
                color="white", fontsize=16, fontweight="bold", transform=ax.transAxes,
                bbox=dict(boxstyle="round", facecolor="red", alpha=0.85))
        ax.text(0.5,0.35,str(msg), ha="center", va="center", color="white",
                fontsize=10, transform=ax.transAxes)
        ax.axis("off")
        return _bytes(fig, dpi=120)

# Global instance
radar_processor = RadarProcessor()
