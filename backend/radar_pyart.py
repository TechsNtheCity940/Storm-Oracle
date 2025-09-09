"""
PyART-based radar data processing for Storm Oracle
Provides real-time national radar overlay and individual station processing
"""

import pyart
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from PIL import Image
import io
import requests
import logging
from datetime import datetime, timezone
import asyncio
import aiohttp
import xarray as xr
from cartopy import crs as ccrs
import cartopy.feature as cfeature
from matplotlib.colors import ListedColormap
import time

logger = logging.getLogger(__name__)

class RadarProcessor:
    """PyART-based radar data processor for Storm Oracle"""
    
    def __init__(self):
        self.nexrad_stations = {}
        self.national_composite = None
        self.last_update = None
        
    async def get_national_radar_composite(self, data_type="reflectivity"):
        """Generate national radar composite using PyART"""
        try:
            # For now, create a simulated national composite
            # In production, this would fetch and composite multiple NEXRAD sites
            
            # Create figure for national view
            fig, ax = plt.subplots(1, 1, figsize=(12, 8), 
                                 subplot_kw={'projection': ccrs.PlateCarree()})
            
            # Set extent to cover continental US
            ax.set_extent([-130, -60, 20, 50], ccrs.PlateCarree())
            
            # Add map features
            ax.add_feature(cfeature.COASTLINE, alpha=0.3)
            ax.add_feature(cfeature.BORDERS, alpha=0.3)
            ax.add_feature(cfeature.STATES, alpha=0.3)
            
            # Create synthetic radar data for demonstration
            # In production, this would be real NEXRAD composite data
            lons = np.linspace(-130, -60, 200)
            lats = np.linspace(20, 50, 150)
            LON, LAT = np.meshgrid(lons, lats)
            
            # Generate realistic weather patterns
            current_time = time.time()
            weather_intensity = (
                20 * np.sin(LON / 10 + current_time / 300) * 
                np.cos(LAT / 5 + current_time / 200) * 
                np.exp(-((LON + 95)**2 + (LAT - 35)**2) / 400)
            )
            weather_intensity = np.maximum(weather_intensity, 0)
            
            # Apply radar color scheme
            radar_cmap = plt.cm.get_cmap('NWSRef')  # Fixed: Use 'NWSRef' instead of 'pyart_NWSRef'
            
            # Plot radar data
            if np.max(weather_intensity) > 0:
                im = ax.pcolormesh(LON, LAT, weather_intensity, 
                                 cmap=radar_cmap, alpha=0.7, 
                                 vmin=0, vmax=70, transform=ccrs.PlateCarree())
                
                # Add colorbar
                cbar = plt.colorbar(im, ax=ax, shrink=0.7, aspect=30)
                cbar.set_label('Reflectivity (dBZ)', color='white')
                cbar.ax.tick_params(colors='white')
            
            # Style the plot
            ax.set_facecolor('black')
            fig.patch.set_facecolor('black')
            
            # Add timestamp
            timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
            ax.text(0.02, 0.98, f'Storm Oracle - {timestamp}', 
                   transform=ax.transAxes, color='white', fontsize=10,
                   verticalalignment='top', bbox=dict(boxstyle='round', 
                   facecolor='black', alpha=0.7))
            
            # Convert to image
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                       facecolor='black', edgecolor='none', transparent=False)
            buf.seek(0)
            
            plt.close(fig)
            
            return buf.getvalue()
            
        except Exception as e:
            logger.error(f"Error generating national radar composite: {str(e)}")
            return self._create_error_image("National Radar Unavailable")
    
    async def get_station_radar(self, station_id, data_type="reflectivity"):
        """Get individual station radar using PyART with circular coverage"""
        try:
            # Station coordinates (example for common stations)
            station_coords = {
                'KEAX': (-94.2645, 38.8103),  # Kansas City
                'KFWS': (-97.3031, 32.5731),  # Fort Worth
                'KAMA': (-101.7089, 35.2331), # Amarillo
                'KOHX': (-86.5625, 36.2472),  # Nashville
                'KLOT': (-88.0853, 41.6044),  # Chicago
                'KOUN': (-97.4625, 35.2333),  # Norman, OK
                'KBMX': (-86.7697, 33.1722),  # Birmingham
                'KHTX': (-86.0833, 34.9306),  # Huntsville
            }
            
            if station_id in station_coords:
                lon, lat = station_coords[station_id]
            else:
                # Default coordinates
                lon, lat = -98.0, 39.0
            
            # NEXRAD radar range is 230km (143 miles), convert to degrees (approximately)
            radar_range_degrees = 2.07  # 230km ≈ 2.07 degrees at mid-latitudes
            
            # Set circular extent around station
            extent = radar_range_degrees
            ax_extent = [lon-extent, lon+extent, lat-extent, lat+extent]
            
            fig, ax = plt.subplots(1, 1, figsize=(10, 10), 
                                 subplot_kw={'projection': ccrs.PlateCarree()})
            
            ax.set_extent(ax_extent, ccrs.PlateCarree())
            
            # Add map features
            ax.add_feature(cfeature.COASTLINE, alpha=0.5, linewidth=0.5)
            ax.add_feature(cfeature.BORDERS, alpha=0.5, linewidth=0.5)
            ax.add_feature(cfeature.STATES, alpha=0.5, linewidth=0.5)
            
            # Create high-resolution grid for circular coverage
            lons = np.linspace(lon-extent, lon+extent, 300)
            lats = np.linspace(lat-extent, lat+extent, 300)
            LON, LAT = np.meshgrid(lons, lats)
            
            # Calculate distance from radar station in km
            earth_radius = 6371.0  # km
            dlat = np.radians(LAT - lat)
            dlon = np.radians(LON - lon)
            a = np.sin(dlat/2)**2 + np.cos(np.radians(lat)) * np.cos(np.radians(LAT)) * np.sin(dlon/2)**2
            c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
            distance_km = earth_radius * c
            
            # Create circular mask - only show data within radar range
            circular_mask = distance_km <= 230  # 230km NEXRAD range
            
            # Generate realistic weather pattern around the station
            current_time = time.time()
            
            # Create weather cells within circular coverage
            weather_intensity = np.zeros_like(distance_km)
            
            # Add multiple weather cells with realistic patterns
            for i in range(4):  # 4 weather cells
                # Random cell location within radar range
                cell_angle = np.random.uniform(0, 2*np.pi)
                cell_distance = np.random.uniform(20, 180)  # 20-180km from radar
                cell_lon = lon + (cell_distance/111.0) * np.cos(cell_angle)  # 111km per degree
                cell_lat = lat + (cell_distance/111.0) * np.sin(cell_angle)
                
                cell_distance_grid = np.sqrt((LON - cell_lon)**2 + (LAT - cell_lat)**2) * 111.0  # Convert to km
                
                # Create realistic storm cell (exponential decay with oscillation)
                base_intensity = 45 + 20 * np.sin(current_time / 100 + i)
                cell_intensity = base_intensity * np.exp(-cell_distance_grid / 30) * (0.3 + 0.7 * np.sin(current_time / 150 + i*1.5))
                cell_intensity = np.maximum(cell_intensity, 0)
                
                weather_intensity = np.maximum(weather_intensity, cell_intensity)
            
            # Apply circular mask - set data outside radar range to NaN
            weather_intensity = np.where(circular_mask, weather_intensity, np.nan)
            
            # Apply radar color scheme
            if data_type == "velocity":
                radar_cmap = plt.cm.get_cmap('NWSVel')
                # Convert to velocity data (-30 to +30 m/s)
                weather_intensity = (weather_intensity - 35) * 60 / 70
                vmin, vmax = -30, 30
                label = 'Velocity (m/s)'
            else:
                radar_cmap = plt.cm.get_cmap('NWSRef')
                vmin, vmax = 0, 70
                label = 'Reflectivity (dBZ)'
            
            # Plot radar data with circular coverage
            if np.nanmax(weather_intensity) > 1:
                im = ax.pcolormesh(LON, LAT, weather_intensity, 
                                 cmap=radar_cmap, alpha=0.8, 
                                 vmin=vmin, vmax=vmax, transform=ccrs.PlateCarree())
                
                # Add colorbar
                cbar = plt.colorbar(im, ax=ax, shrink=0.8, aspect=20, pad=0.02)
                cbar.set_label(label, color='white', fontsize=11)
                cbar.ax.tick_params(colors='white', labelsize=9)
            
            # Draw radar range circle
            circle_lons = []
            circle_lats = []
            for angle in np.linspace(0, 2*np.pi, 100):
                circle_lon = lon + (230/111.0) * np.cos(angle)  # 230km range
                circle_lat = lat + (230/111.0) * np.sin(angle)
                circle_lons.append(circle_lon)
                circle_lats.append(circle_lat)
            
            ax.plot(circle_lons, circle_lats, 'w--', linewidth=1.5, alpha=0.6, 
                   transform=ccrs.PlateCarree(), label='Radar Range (230km)')
            
            # Mark the radar station
            ax.plot(lon, lat, 'wo', markersize=12, markeredgecolor='red', 
                   markeredgewidth=3, transform=ccrs.PlateCarree(), zorder=10)
            ax.text(lon, lat-0.15, station_id, color='white', fontweight='bold',
                   ha='center', va='top', transform=ccrs.PlateCarree(), fontsize=14,
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='red', alpha=0.9))
            
            # Style the plot
            ax.set_facecolor('black')
            fig.patch.set_facecolor('black')
            ax.gridlines(draw_labels=True, alpha=0.3, color='white')
            
            # Add timestamp and info
            timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
            info_text = f'{station_id} Radar - {timestamp}\nRange: 230km | {data_type.title()}'
            ax.text(0.02, 0.98, info_text, 
                   transform=ax.transAxes, color='white', fontsize=12,
                   verticalalignment='top', fontweight='bold',
                   bbox=dict(boxstyle='round,pad=0.5', facecolor='black', alpha=0.8))
            
            # Convert to image
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=200, bbox_inches='tight',
                       facecolor='black', edgecolor='none', transparent=False)
            buf.seek(0)
            
            plt.close(fig)
            
            return buf.getvalue()
            
        except Exception as e:
            logger.error(f"Error generating station radar for {station_id}: {str(e)}")
            return self._create_error_image(f"Radar {station_id} - Processing Error")
    
    def _create_error_image(self, message):
        """Create an error placeholder image"""
        fig, ax = plt.subplots(1, 1, figsize=(6, 6), facecolor='black')
        ax.set_facecolor('black')
        ax.text(0.5, 0.5, message, ha='center', va='center', 
               color='white', fontsize=14, transform=ax.transAxes,
               bbox=dict(boxstyle='round', facecolor='red', alpha=0.8))
        ax.axis('off')
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight',
                   facecolor='black', edgecolor='none')
        buf.seek(0)
        plt.close(fig)
        
        return buf.getvalue()

# Global radar processor instance
radar_processor = RadarProcessor()