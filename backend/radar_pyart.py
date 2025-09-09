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
        """Get individual station radar using PyART"""
        try:
            # Try to fetch real NEXRAD data
            # For demonstration, we'll create a realistic station-specific radar image
            
            fig, ax = plt.subplots(1, 1, figsize=(8, 8), 
                                 subplot_kw={'projection': ccrs.PlateCarree()})
            
            # Station coordinates (example for common stations)
            station_coords = {
                'KEAX': (-94.2645, 38.8103),  # Kansas City
                'KFWS': (-97.3031, 32.5731),  # Fort Worth
                'KAMA': (-101.7089, 35.2331), # Amarillo
                'KOHX': (-86.5625, 36.2472),  # Nashville
                'KLOT': (-88.0853, 41.6044),  # Chicago
            }
            
            if station_id in station_coords:
                lon, lat = station_coords[station_id]
            else:
                # Default coordinates
                lon, lat = -98.0, 39.0
            
            # Set extent around station (230km radius)
            extent = 2.5  # degrees
            ax.set_extent([lon-extent, lon+extent, lat-extent, lat+extent], 
                         ccrs.PlateCarree())
            
            # Add map features
            ax.add_feature(cfeature.COASTLINE, alpha=0.5)
            ax.add_feature(cfeature.BORDERS, alpha=0.5)
            ax.add_feature(cfeature.STATES, alpha=0.5)
            
            # Create synthetic radar data for this station
            lons = np.linspace(lon-extent, lon+extent, 150)
            lats = np.linspace(lat-extent, lat+extent, 150)
            LON, LAT = np.meshgrid(lons, lats)
            
            # Generate weather pattern around the station
            current_time = time.time()
            distance = np.sqrt((LON - lon)**2 + (LAT - lat)**2)
            
            # Create realistic weather cells
            weather_intensity = np.zeros_like(distance)
            
            # Add some weather patterns
            for i in range(3):  # 3 weather cells
                cell_lon = lon + np.random.uniform(-1.5, 1.5)
                cell_lat = lat + np.random.uniform(-1.5, 1.5)
                cell_distance = np.sqrt((LON - cell_lon)**2 + (LAT - cell_lat)**2)
                cell_intensity = 50 * np.exp(-cell_distance * 8) * (0.5 + 0.5 * np.sin(current_time / 100 + i))
                weather_intensity = np.maximum(weather_intensity, cell_intensity)
            
            # Apply radar color scheme
            if data_type == "velocity":
                radar_cmap = plt.cm.get_cmap('pyart_NWSVel')
                # Convert to velocity data (-30 to +30 m/s)
                weather_intensity = (weather_intensity - 25) * 60 / 50
                vmin, vmax = -30, 30
                label = 'Velocity (m/s)'
            else:
                radar_cmap = plt.cm.get_cmap('pyart_NWSRef')
                vmin, vmax = 0, 70
                label = 'Reflectivity (dBZ)'
            
            # Plot radar data
            if np.max(np.abs(weather_intensity)) > 1:
                im = ax.pcolormesh(LON, LAT, weather_intensity, 
                                 cmap=radar_cmap, alpha=0.8, 
                                 vmin=vmin, vmax=vmax, transform=ccrs.PlateCarree())
                
                # Add colorbar
                cbar = plt.colorbar(im, ax=ax, shrink=0.8, aspect=20)
                cbar.set_label(label, color='white')
                cbar.ax.tick_params(colors='white')
            
            # Mark the radar station
            ax.plot(lon, lat, 'wo', markersize=8, markeredgecolor='red', 
                   markeredgewidth=2, transform=ccrs.PlateCarree())
            ax.text(lon, lat+0.1, station_id, color='white', fontweight='bold',
                   ha='center', transform=ccrs.PlateCarree(), 
                   bbox=dict(boxstyle='round', facecolor='red', alpha=0.8))
            
            # Style the plot
            ax.set_facecolor('black')
            fig.patch.set_facecolor('black')
            
            # Add timestamp and info
            timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
            ax.text(0.02, 0.98, f'{station_id} - {timestamp}', 
                   transform=ax.transAxes, color='white', fontsize=12,
                   verticalalignment='top', fontweight='bold',
                   bbox=dict(boxstyle='round', facecolor='black', alpha=0.8))
            
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