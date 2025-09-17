"""
Storm Oracle — Py-ART Radar (Radar Omega–style)
-----------------------------------------------
Live NEXRAD L2 from AWS, multi-product PPI + national composite with real geodesy.
Adds:
- Auto storm motion (VAD + Bunkers-style right mover)
- Beam-aware azimuthal shear overlay + couplet markers
- Custom tornado markers (confirmed/predicted), size by intensity, optional spin
- Lightning/hail/wind overlays
- Easy Mode legends for lay users
"""

import os, io, sys, math, logging
from datetime import datetime, timezone, timedelta
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.transforms import Affine2D
import cartopy.crs as ccrs
import cartopy.feature as cfeature

# Prefer your local Py-ART path (you said: F:/pyart)
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

try:
    from pyproj import CRS, Transformer
except Exception:
    CRS = Transformer = None

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

AWS_BUCKET = "noaa-nexrad-level2"
AWS_REGION = "us-east-1"

DEFAULT_COMPOSITE_STATIONS = [
    "KTLX","KFDR","KAMA","KDDC","KICT","KEAX","KSGF","KLSX","KDVN","KDMX","KOAX","KUEX",
    "KLOT","KGRB","KMKX","KDTX","KCLE","KPBZ","KFCX","KLWX","KOKX","KBOX","KGYX","KCBW",
    "KTLH","KJAX","KTBW","KAMX","KHGX","KEWX","KFWS","KABX","KRIW","KFTG","KRGX",
    "KMAX","KATX","KRTX","KPOE","KLCH","KLIX"
]

FIELD = {
    "base_reflectivity": "reflectivity",
    "reflectivity_hr": "reflectivity",
    "base_velocity": "velocity",
    "velocity_hr": "velocity",
    "storm_relative_velocity": "velocity",
    "spectrum_width": "spectrum_width",
    "zdr": "differential_reflectivity",
    "cc": "cross_correlation_ratio",
    "kdp": "specific_differential_phase",
}

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
def _cmap(name: str): return CMAPS.get(name, CMAPS["NWSRef"])
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
        r = s3.list_objects_v2(Bucket="noaa-nexrad-level2", Prefix=prefix)
        objs = r.get("Contents", [])
        if objs:
            objs.sort(key=lambda o: o["LastModified"])
            return objs[-1]["Key"]
    return None

def _read_l2(station: str):
    key = _latest_key(station)
    if not key: raise RuntimeError(f"No recent L2 on AWS for {station}")
    s3 = _aws_client()
    data = s3.get_object(Bucket="noaa-nexrad-level2", Key=key)["Body"].read()
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

def _ref_category(dbz):
    if np.isnan(dbz): return "No echo"
    if dbz < 10: return "Very light"
    if dbz < 20: return "Light"
    if dbz < 30: return "Moderate"
    if dbz < 40: return "Heavy"
    if dbz < 50: return "Very heavy"
    if dbz < 60: return "Severe"
    return "Extreme"

def _sweep_slice(radar, sweep_idx): return radar.get_slice(sweep_idx)

def _vad_uv_for_sweep(radar, sweep_idx, rmin_km=20.0, rmax_km=80.0):
    sl = _sweep_slice(radar, sweep_idx)
    az = np.deg2rad(radar.azimuth["data"][sl])
    vel = radar.fields["velocity"]["data"][sl, :]
    rng = radar.range["data"] / 1000.0
    gate_mask = (rng >= rmin_km) & (rng <= rmax_km)
    if not gate_mask.any(): gate_mask = rng >= (rng.min()+5)
    v_az = np.ma.mean(vel[:, gate_mask], axis=1).filled(np.nan)
    good = np.isfinite(v_az)
    if good.sum() < 16: raise RuntimeError("Insufficient velocity samples for VAD")
    A = np.column_stack([np.sin(az[good]), np.cos(az[good]), np.ones(good.sum())])
    x, *_ = np.linalg.lstsq(A, v_az[good], rcond=None)
    u_est, v_est, _ = x
    try:
        z = radar.gate_altitude["data"][sl][:, gate_mask]
        z_med = float(np.nanmedian(z))
    except Exception:
        z_med = np.nan
    return u_est, v_est, z_med

def estimate_storm_motion(radar):
    per = []
    for s in range(radar.nsweeps):
        try:
            u, v, z = _vad_uv_for_sweep(radar, s)
            per.append((z, u, v, s))
        except Exception:
            continue
    if not per: raise RuntimeError("VAD failed on all sweeps")
    arr = np.array([(z,u,v,s) for (z,u,v,s) in per if np.isfinite(z)])
    if arr.size == 0:
        z,u,v,s = per[0]; return (u, v, {"method":"VAD(lowest)", "sweep": int(s), "z_m": float(z)})
    low = (arr[:,0] >= 0) & (arr[:,0] <= 2000.0)
    mid = (arr[:,0] >= 4000.0) & (arr[:,0] <= 7000.0)
    if low.any() and mid.any():
        u_low, v_low = float(np.nanmean(arr[low,1])), float(np.nanmean(arr[low,2]))
        u_mid, v_mid = float(np.nanmean(arr[mid,1])), float(np.nanmean(arr[mid,2]))
        u_mean, v_mean = 0.5*(u_low+u_mid), 0.5*(v_low+v_mid)
        Sx, Sy = (u_mid - u_low), (v_mid - v_low)
        mag = math.hypot(Sx, Sy) or 1e-6
        Srx, Sry = (Sy/mag), (-Sx/mag)
        u_rm = u_mean + 7.5 * Srx
        v_rm = v_mean + 7.5 * Sry
        return (u_rm, v_rm, {"method":"Bunkers(VAD 0–2 vs 4–7 km)",
                             "u_low":u_low,"v_low":v_low,"u_mid":u_mid,"v_mid":v_mid})
    idx = int(np.nanargmin(arr[:,0])); z,u,v,s = arr[idx]
    return (u, v, {"method":"VAD(lowest)", "sweep": int(s), "z_m": float(z)})

def _az_shear_geometric(radar, sweep_idx, vel2d):
    sl = _sweep_slice(radar, sweep_idx)
    az = np.deg2rad(radar.azimuth["data"][sl])
    rng = radar.range["data"]
    azp = np.roll(az, -1); azm = np.roll(az, 1)
    dtheta = ((azp - azm) + np.pi) % (2*np.pi) - np.pi
    dtheta = np.where(np.abs(dtheta) < 1e-6, 1e-6*np.sign(dtheta)+1e-6, dtheta)
    dv = np.roll(vel2d, -1, axis=0) - np.roll(vel2d, 1, axis=0)
    r = np.maximum(rng[None, :], 500.0)
    shear = (dv / dtheta[:, None]) / r
    return np.ma.masked_invalid(shear)

def _find_velocity_couplets(vel2d, thresh_pair=45.0):
    arr = vel2d.filled(np.nan) if hasattr(vel2d, "filled") else np.array(vel2d, float)
    hits = []
    for i in range(arr.shape[0]-1):
        diff = arr[i+1] - arr[i]
        j = np.nanargmax(np.abs(diff))
        if np.isfinite(diff[j]) and np.abs(diff[j]) >= thresh_pair:
            hits.append((i, j))
    return hits[:12]

def _draw_tornado_markers(ax, items, marker_path, colorize=None, spin=False):
    if not items: return
    try:
        img = plt.imread(marker_path)
    except Exception as e:
        ax.text(0.5,0.02,f"Marker load failed: {e}", transform=ax.transAxes,
                ha="center", va="bottom", color="red"); return
    for it in items:
        lon, lat = it["lon"], it["lat"]
        inten = float(it.get("intensity", 1.0))
        size_scale = float(it.get("size_scale", 1.0))
        base_deg = 0.35 * size_scale * (0.6 + 0.4*min(max(inten,0.2), 6))
        extent = [lon - base_deg/2, lon + base_deg/2, lat - base_deg/2, lat + base_deg/2]
        rgba = img.copy()
        if colorize is not None and rgba.ndim == 3:
            rgba[..., :3] = np.clip(rgba[..., :3]*np.array(colorize)[None,None,:], 0, 1)
        im = ax.imshow(rgba, extent=extent, transform=ccrs.PlateCarree(), zorder=20)
        if spin:
            angle = 30.0 * inten
            cx, cy = (extent[0]+extent[1])/2, (extent[2]+extent[3])/2
            im.set_transform(Affine2D().rotate_deg_around(cx, cy, angle) + ax.transData)

def _draw_lightning(ax, strikes):
    if not strikes: return
    for s in strikes:
        lon, lat = s["lon"], s["lat"]
        amp = float(s.get("amp", 100.0))
        age = float(s.get("age_sec", 0.0))
        size = 30 + 40*np.clip(amp/200.0, 0, 1)
        alpha = float(np.clip(1.0 - age/900.0, 0.2, 1.0))
        ax.plot(lon, lat, marker="*", markersize=size/6, color="yellow",
                markeredgecolor="white", alpha=alpha, transform=ccrs.PlateCarree(), zorder=15)

def _draw_hail(ax, hail_points):
    if not hail_points: return
    for h in hail_points:
        lon, lat = h["lon"], h["lat"]
        size_in = float(h.get("size_in", h.get("mesh_mm", 25.0)/25.4))
        r = 0.15 * (0.5 + min(size_in, 4.0))
        circ = plt.Circle((lon, lat), r, transform=ccrs.PlateCarree(),
                          edgecolor="white", facecolor="cyan", alpha=0.35, lw=1.2, zorder=10)
        ax.add_patch(circ)

def _draw_wind(ax, vectors):
    if not vectors: return
    lons = np.array([w["lon"] for w in vectors]); lats = np.array([w["lat"] for w in vectors])
    u = np.array([w["u"] for w in vectors]); v = np.array([w["v"] for w in vectors])
    ax.barbs(lons, lats, u, v, transform=ccrs.PlateCarree(), length=5, color="white", zorder=12)

class RadarProcessor:
    def __init__(self, tornado_marker_path: str = "/mnt/data/tornado-marker.png"):
        self.tornado_marker_path = tornado_marker_path

    def get_station(self, station_id: str, product: str = "base_reflectivity",
                    sweep: int = 0, cmap: str = "NWSRef", easy_mode: bool = True,
                    storm_motion_uv: tuple[float,float] | None = None, overlays: dict | None = None):
        try:
            field = FIELD.get(product)
            if field is None: raise ValueError(f"Unsupported product '{product}'. Options: {list(FIELD)}")
            radar, _ = _read_l2(station_id)
            if field not in radar.fields: raise RuntimeError(f"{station_id} volume missing '{field}'")

            display = pyart.graph.RadarMapDisplay(radar)
            if field == "reflectivity": vmin, vmax = (0, 70)
            elif field == "velocity": vmin, vmax = (-35, 35)
            elif field == "spectrum_width": vmin, vmax = (0, 12)
            elif field == "differential_reflectivity": vmin, vmax = (-1, 6)
            elif field == "cross_correlation_ratio": vmin, vmax = (0.7, 1.0)
            elif field == "specific_differential_phase": vmin, vmax = (0, 5)
            else: vmin, vmax = (None, None)

            fig = plt.figure(figsize=(10, 9), facecolor="black")
            ax = plt.axes(projection=ccrs.PlateCarree())
            ax.set_facecolor("black"); _add_features(ax, faint=True); _gridliner(ax)
            cm = _cmap(cmap)

            lat0 = float(radar.latitude["data"][0]); lon0 = float(radar.longitude["data"][0])
            deg_lat = 230.0/111.0; deg_lon = 230.0/(111.0*max(math.cos(math.radians(lat0)), 1e-3))
            ax.set_extent([lon0-deg_lon, lon0+deg_lon, lat0-deg_lat, lat0+deg_lat], crs=ccrs.PlateCarree())

            plot_field_name = field; method_note = None
            if product == "storm_relative_velocity":
                if storm_motion_uv is None:
                    try:
                        u, v, meta = estimate_storm_motion(radar); method_note = meta["method"]
                        storm_motion_uv = (u, v)
                    except Exception as ex:
                        method_note = f"SRV fallback: {ex}; using base vel"; storm_motion_uv = (0.0, 0.0)
                sl = _sweep_slice(radar, sweep)
                vel = radar.fields["velocity"]["data"]
                vel2d = vel if vel.ndim == 2 else vel[sl, :]
                az = np.deg2rad(radar.azimuth["data"][sl])
                u, v = storm_motion_uv
                ux = np.sin(az)[:, None]; uy = np.cos(az)[:, None]
                srv = vel2d - (u*ux + v*uy)
                md = pyart.config.get_metadata("velocity")
                md["data"] = np.ma.masked_invalid(srv)
                md["long_name"] = "storm_relative_velocity"
                radar.add_field("storm_relative_velocity", md, replace_existing=True)
                plot_field_name = "storm_relative_velocity"

            display.plot_ppi_map(
                plot_field_name, sweep=sweep, ax=ax, projection=ccrs.PlateCarree(),
                vmin=vmin, vmax=vmax, cmap=cm, colorbar_flag=True, title_flag=False,
                lat_lines=None, lon_lines=None, embellish=False, raster=False
            )

            human_time = _now()
            title = f"{station_id} • {product.replace('_',' ').title()} • {human_time}"
            if method_note: title += f"\n{method_note}"
            ax.text(0.02, 0.98, title, transform=ax.transAxes, va="top", ha="left",
                    color="white", fontsize=12, fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.4", facecolor="black", alpha=0.6))
            ax.plot([lon0],[lat0], marker="o", markersize=8, markerfacecolor="white",
                    markeredgecolor="red", transform=ccrs.PlateCarree(), zorder=12)

            if product in ("base_velocity","velocity_hr","storm_relative_velocity"):
                sl = _sweep_slice(radar, sweep)
                vel = radar.fields["velocity"]["data"] if product != "storm_relative_velocity" else radar.fields[plot_field_name]["data"]
                vel2d = vel if vel.ndim == 2 else vel[sl, :]
                try:
                    shear = _az_shear_geometric(radar, sweep, vel2d)
                    x, y = display._get_x_y(sweep, True, None)
                    ax.contourf(x, y, np.nan_to_num(shear)*1000.0,
                                levels=[20,30,40,60,80,120],
                                colors=["#7a00ff33","#b100ff33","#ff00ff33","#ff00ff55","#ff00ff77"],
                                transform=display._projection, zorder=10)
                except Exception:
                    pass
                for (i,j) in _find_velocity_couplets(vel2d, thresh_pair=45.0):
                    try:
                        x, y = display._get_x_y(sweep, True, None)
                        ax.plot(x[j], y[i], "wo", ms=5, transform=display._projection, zorder=12)
                    except Exception:
                        break

            if easy_mode:
                lines = []
                if field == "reflectivity":
                    dat = radar.fields[field]["data"]
                    d = dat if dat.ndim == 2 else dat[_sweep_slice(radar, sweep)]
                    vals = np.array(d).astype(float)
                    p90 = np.nanpercentile(vals[np.isfinite(vals)], 90) if np.isfinite(vals).any() else np.nan
                    lines += [f"Top echoes ~{p90:.0f} dBZ ({_ref_category(p90)})",
                              "0–10 very light • 20–30 moderate",
                              "40–50 heavy • 60+ extreme/hail risk"]
                elif "velocity" in product:
                    lines += ["Inbound vs outbound → rotation",
                              "Magenta veil = high azimuthal shear",
                              "Dots = possible couplets"]
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

            overlays = overlays or {}
            _draw_lightning(ax, overlays.get("lightning"))
            _draw_hail(ax, overlays.get("hail"))
            _draw_wind(ax, overlays.get("winds"))
            _draw_tornado_markers(ax, overlays.get("tornado_confirmed"),
                                  self.tornado_marker_path, colorize=None, spin=True)
            _draw_tornado_markers(ax, overlays.get("tornado_predicted"),
                                  self.tornado_marker_path, colorize=(0.3,1.0,0.3), spin=False)

            return _bytes(fig, dpi=170)

        except Exception as e:
            logger.exception("Station render failed"); return self._error_tile(f"{station_id} • {product}: {e}")

    def get_composite(self, product: str = "base_reflectivity", stations: list[str] | None = None,
                      cmap: str = "NWSRef", easy_mode: bool = True):
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
            if field == "reflectivity": vmin, vmax = (0,70)
            elif field == "velocity": vmin, vmax = (-35,35)
            elif field == "spectrum_width": vmin, vmax = (0,12)
            elif field == "differential_reflectivity": vmin, vmax = (-1,6)
            elif field == "cross_correlation_ratio": vmin, vmax = (0.7,1.0)
            elif field == "specific_differential_phase": vmin, vmax = (0,5)
            else: vmin, vmax = (np.nanmin(f), np.nanmax(f))

            fig = plt.figure(figsize=(12.5, 8.5), facecolor="black")
            ax = plt.axes(projection=ccrs.PlateCarree())
            ax.set_facecolor("black"); ax.set_extent([-130, -60, 20, 50], crs=ccrs.PlateCarree())
            _add_features(ax, faint=True); cm = _cmap(cmap)

            plotted = False
            if CRS is not None and hasattr(grid, "projection") and isinstance(grid.projection, dict):
                try:
                    proj = CRS(grid.projection)
                    to_ll = Transformer.from_crs(proj, CRS.from_epsg(4326), always_xy=True)
                    x = grid.x["data"]; y = grid.y["data"]; X, Y = np.meshgrid(x, y)
                    LON, LAT = to_ll.transform(X, Y)
                    pm = ax.pcolormesh(LON, LAT, f, cmap=cm, vmin=vmin, vmax=vmax,
                                       shading="nearest", transform=ccrs.PlateCarree(), alpha=0.95)
                    plotted = True
                except Exception:
                    plotted = False
            if not plotted:
                pm = ax.imshow(np.flipud(f), extent=[-130,-60,20,50], origin="upper",
                               cmap=cm, vmin=vmin, vmax=vmax, alpha=0.95, transform=ccrs.PlateCarree())

            cb = plt.colorbar(pm, ax=ax, shrink=0.7, pad=0.02, aspect=30)
            cb.ax.tick_params(colors="white", labelsize=9)
            label = {
                "reflectivity": "Reflectivity (dBZ)", "velocity": "Velocity (m/s)",
                "spectrum_width": "Spectrum Width (m/s)", "differential_reflectivity": "ZDR (dB)",
                "cross_correlation_ratio": "ρhv", "specific_differential_phase": "KDP (°/km)"
            }.get(field, field)
            cb.set_label(label, color="white", fontsize=11)

            ax.text(0.02, 0.98, f"Storm Oracle — National Composite • {product.replace('_',' ').title()} • {_now()}",
                    transform=ax.transAxes, va="top", ha="left", color="white",
                    fontsize=12, fontweight="bold", bbox=dict(boxstyle="round,pad=0.5", facecolor="black", alpha=0.6))
            if easy_mode and field == "reflectivity":
                ax.text(0.98, 0.02, "0–10 very light\n20–30 moderate\n40–50 heavy\n60+ extreme/hail risk",
                        transform=ax.transAxes, ha="right", va="bottom", color="white", fontsize=9,
                        bbox=dict(boxstyle="round,pad=0.5", facecolor="black", alpha=0.6))
            return _bytes(fig, dpi=150)
        except Exception as e:
            logger.exception("Composite render failed"); return self._error_tile(f"Composite • {product}: {e}")

    def _error_tile(self, msg):
        fig, ax = plt.subplots(1,1, figsize=(6,4), facecolor="black")
        ax.set_facecolor("black")
        ax.text(0.5,0.55,"Radar Error", ha="center", va="center",
                color="white", fontsize=16, fontweight="bold", transform=ax.transAxes,
                bbox=dict(boxstyle="round", facecolor="red", alpha=0.85))
        ax.text(0.5,0.35,str(msg), ha="center", va="center", color="white",
                fontsize=10, transform=ax.transAxes)
        ax.axis("off"); return _bytes(fig, dpi=120)

radar_processor = RadarProcessor()

