import React, { useState, useEffect, useRef, useCallback } from 'react';
import { MapContainer, TileLayer, useMap, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Button } from './ui/button';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Slider } from './ui/slider';
import { Badge } from './ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { 
  Play, Pause, SkipBack, SkipForward, RotateCcw, MapPin, AlertTriangle, 
  ChevronLeft, ChevronRight, Settings, Palette, Eye, EyeOff 
} from 'lucide-react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Radar data types configuration
const RADAR_DATA_TYPES = {
  'base_reflectivity': { name: 'Base Reflectivity', defaultColors: 'nexrad_reflectivity' },
  'hi_res_reflectivity': { name: 'Hi-Res Reflectivity', defaultColors: 'nexrad_reflectivity' },
  'base_velocity': { name: 'Base Velocity', defaultColors: 'velocity_standard' },
  'hi_res_velocity': { name: 'Hi-Res Velocity', defaultColors: 'velocity_standard' },
  'storm_relative_velocity': { name: 'Storm Relative Velocity', defaultColors: 'velocity_storm' },
  'mrms_reflectivity': { name: 'MRMS Reflectivity', defaultColors: 'mrms_standard' },
  'composite_reflectivity': { name: 'Composite Reflectivity', defaultColors: 'composite' },
  'echo_tops': { name: 'Echo Tops', defaultColors: 'echo_tops' }
};

// Color palette configurations
const COLOR_PALETTES = {
  nexrad_reflectivity: {
    name: 'NEXRAD Reflectivity',
    description: 'Green → Yellow → Red → Purple → White',
    colors: ['#00ff00', '#ffff00', '#ff8000', '#ff0000', '#ff00ff', '#ffffff']
  },
  high_contrast_reflectivity: {
    name: 'High Contrast',
    description: 'Blue → Cyan → Green → Yellow → Red → Magenta',
    colors: ['#0000ff', '#00ffff', '#00ff00', '#ffff00', '#ff0000', '#ff00ff']
  },
  velocity_standard: {
    name: 'Standard Velocity',
    description: 'Green (approaching) → Red (receding)',
    colors: ['#00ff00', '#80ff80', '#ffffff', '#ff8080', '#ff0000']
  },
  velocity_storm: {
    name: 'Storm Relative',
    description: 'Green → White → Red with Purple rotation',
    colors: ['#00ff00', '#ffffff', '#ff0000', '#8000ff']
  },
  mrms_standard: {
    name: 'MRMS Standard',
    description: 'Enhanced multi-radar mosaic colors',
    colors: ['#404040', '#00ff00', '#ffff00', '#ff8000', '#ff0000', '#8000ff']
  },
  composite: {
    name: 'Composite',
    description: 'Multi-layer composite colors',
    colors: ['#000040', '#0080ff', '#00ff80', '#ffff00', '#ff4000', '#ff0080']
  },
  echo_tops: {
    name: 'Echo Tops',
    description: 'Height-based coloring',
    colors: ['#404040', '#0080ff', '#00ff00', '#ffff00', '#ff8000', '#ff0000']
  }
};

// Fix for default markers
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

const RadarOverlay = ({ radarFrames, currentFrame, opacity, colorPalette, dataType }) => {
  const map = useMap();
  const overlayRef = useRef(null);

  useEffect(() => {
    if (radarFrames.length > 0 && currentFrame < radarFrames.length) {
      // Remove existing overlay
      if (overlayRef.current) {
        map.removeLayer(overlayRef.current);
      }

      const frame = radarFrames[currentFrame];
      if (frame && frame.imageUrl) {
        // Create image overlay with color filter
        const imageBounds = [
          [frame.bounds.south, frame.bounds.west],
          [frame.bounds.north, frame.bounds.east]
        ];

        // Apply color filter based on palette and data type
        const filterClass = `radar-${dataType}-${colorPalette}`;

        overlayRef.current = L.imageOverlay(frame.imageUrl, imageBounds, {
          opacity: opacity,
          interactive: false,
          className: `radar-overlay ${filterClass}`
        }).addTo(map);
      }
    }

    return () => {
      if (overlayRef.current) {
        map.removeLayer(overlayRef.current);
      }
    };
  }, [map, radarFrames, currentFrame, opacity, colorPalette, dataType]);

  return null;
};

const StormCellMarkers = ({ stormCells, onStormClick }) => {
  const map = useMap();

  useEffect(() => {
    // Clear existing storm markers
    map.eachLayer((layer) => {
      if (layer.options && layer.options.isStormMarker) {
        map.removeLayer(layer);
      }
    });

    // Add storm cell markers
    stormCells.forEach((storm) => {
      const icon = L.divIcon({
        className: 'storm-cell-marker',
        html: `
          <div class="storm-marker" style="
            background: ${storm.tornadoProbability > 50 ? '#ef4444' : storm.tornadoProbability > 20 ? '#f97316' : '#10b981'};
            border: 2px solid white;
            border-radius: 50%;
            width: 20px;
            height: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 10px;
            font-weight: bold;
            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
            animation: ${storm.tornadoProbability > 70 ? 'pulse 2s infinite' : 'none'};
          ">
            ${storm.tornadoProbability > 50 ? '🌪️' : '⛈️'}
          </div>
        `,
        iconSize: [20, 20],
        iconAnchor: [10, 10]
      });

      const marker = L.marker([storm.latitude, storm.longitude], { 
        icon,
        isStormMarker: true
      }).addTo(map);

      marker.bindPopup(`
        <div class="storm-popup">
          <h3 style="margin: 0 0 8px 0; color: #1f2937;">${storm.stationName}</h3>
          <p style="margin: 4px 0;"><strong>Tornado Probability:</strong> ${storm.tornadoProbability}%</p>
          <p style="margin: 4px 0;"><strong>Alert Level:</strong> ${storm.alertLevel}</p>
          <p style="margin: 4px 0;"><strong>EF Scale:</strong> ${storm.predictedEFScale}</p>
          <button onclick="window.jumpToStorm('${storm.stationId}')" style="
            background: #3b82f6;
            color: white;
            border: none;
            padding: 4px 8px;
            border-radius: 4px;
            cursor: pointer;
            margin-top: 8px;
          ">View Details</button>
        </div>
      `);

      marker.on('click', () => onStormClick(storm));
    });
  }, [map, stormCells, onStormClick]);

  return null;
};

const RadarStationMarkers = ({ radarStations, onStationClick, selectedStation }) => {
  const map = useMap();

  useEffect(() => {
    // Clear existing station markers
    map.eachLayer((layer) => {
      if (layer.options && layer.options.isStationMarker) {
        map.removeLayer(layer);
      }
    });

    // Add radar station markers
    radarStations.forEach((station) => {
      const isSelected = selectedStation && selectedStation.station_id === station.station_id;
      
      const icon = L.divIcon({
        className: 'radar-station-marker',
        html: `
          <div class="station-marker" style="
            background: ${isSelected ? '#8b5cf6' : '#374151'};
            border: 2px solid white;
            border-radius: 4px;
            width: 16px;
            height: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 8px;
            font-weight: bold;
            box-shadow: 0 1px 2px rgba(0,0,0,0.3);
          ">
            📡
          </div>
        `,
        iconSize: [16, 16],
        iconAnchor: [8, 8]
      });

      const marker = L.marker([station.latitude, station.longitude], { 
        icon,
        isStationMarker: true
      }).addTo(map);

      marker.bindPopup(`
        <div class="station-popup">
          <h3 style="margin: 0 0 8px 0; color: #1f2937;">${station.name}</h3>
          <p style="margin: 4px 0;"><strong>ID:</strong> ${station.station_id}</p>
          <p style="margin: 4px 0;"><strong>State:</strong> ${station.state}</p>
          <p style="margin: 4px 0;"><strong>Elevation:</strong> ${station.elevation}ft</p>
          <button onclick="window.selectRadarStation('${station.station_id}')" style="
            background: #8b5cf6;
            color: white;
            border: none;
            padding: 4px 8px;
            border-radius: 4px;
            cursor: pointer;
            margin-top: 8px;
          ">Select Station</button>
        </div>
      `);

      marker.on('click', () => onStationClick(station));
    });
  }, [map, radarStations, onStationClick, selectedStation]);

  return null;
};

const InteractiveRadarMap = ({ 
  radarStations = [], 
  selectedStation, 
  onStationSelect,
  stormCells = [],
  onStormClick 
}) => {
  const [radarFrames, setRadarFrames] = useState([]);
  const [currentFrame, setCurrentFrame] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [frameCount, setFrameCount] = useState(100);
  const [playbackSpeed, setPlaybackSpeed] = useState(500); // ms per frame
  const [radarOpacity, setRadarOpacity] = useState(0.7);
  const [mapCenter, setMapCenter] = useState([39.8283, -98.5795]); // Center of USA
  const [mapZoom, setMapZoom] = useState(5);
  const [isLoading, setIsLoading] = useState(false);
  const [controlsCollapsed, setControlsCollapsed] = useState(false);
  const [dataType, setDataType] = useState('base_reflectivity');
  const [colorPalette, setColorPalette] = useState('nexrad_reflectivity');
  const [showAdvancedSettings, setShowAdvancedSettings] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [realRadarData, setRealRadarData] = useState(null);

  const playbackRef = useRef(null);
  const mapRef = useRef(null);
  const mapContainerRef = useRef(null);

  // Load radar frames with proper error handling
  const loadRadarFrames = useCallback(async (stationId = null, frames = frameCount) => {
    setIsLoading(true);
    try {
      let endpoint;
      if (stationId && selectedStation) {
        endpoint = `${API}/radar-frames/${stationId}?frames=${frames}`;
      } else {
        endpoint = `${API}/radar-frames/national?frames=${frames}`;
      }
      
      const response = await axios.get(endpoint);
      
      if (response.data && response.data.frames) {
        setRadarFrames(response.data.frames);
        setCurrentFrame(response.data.frames.length - 1); // Start with most recent
      } else {
        // Create mock frames if API doesn't return data
        const mockFrames = [];
        for (let i = 0; i < frames; i++) {
          const timestamp = Date.now() - (i * 10 * 60 * 1000); // 10 minutes apart
          mockFrames.push({
            timestamp,
            frameIndex: i,
            imageUrl: `https://radar.weather.gov/ridge/lite/keax_0.gif?${timestamp}`,
            bounds: stationId && selectedStation ? {
              north: selectedStation.latitude + 2,
              south: selectedStation.latitude - 2,
              east: selectedStation.longitude + 2,
              west: selectedStation.longitude - 2
            } : {
              north: 50,
              south: 25,
              east: -65,
              west: -125
            }
          });
        }
        setRadarFrames(mockFrames.reverse());
        setCurrentFrame(mockFrames.length - 1);
      }
    } catch (error) {
      console.error('Error loading radar frames:', error);
      // Create fallback frames
      const fallbackFrames = Array.from({length: frames}, (_, i) => ({
        timestamp: Date.now() - (i * 10 * 60 * 1000),
        frameIndex: i,
        imageUrl: `https://radar.weather.gov/ridge/lite/${stationId ? stationId.toLowerCase() : 'keax'}_0.gif?${Date.now()}`,
        bounds: {
          north: selectedStation ? selectedStation.latitude + 2 : 50,
          south: selectedStation ? selectedStation.latitude - 2 : 25,
          east: selectedStation ? selectedStation.longitude + 2 : -65,
          west: selectedStation ? selectedStation.longitude - 2 : -125
        }
      }));
      setRadarFrames(fallbackFrames.reverse());
      setCurrentFrame(fallbackFrames.length - 1);
    }
    setIsLoading(false);
  }, [frameCount, selectedStation]);

  // Auto-play radar animation
  useEffect(() => {
    if (isPlaying && radarFrames.length > 0) {
      playbackRef.current = setInterval(() => {
        setCurrentFrame((prev) => (prev + 1) % radarFrames.length);
      }, playbackSpeed);
    } else {
      if (playbackRef.current) {
        clearInterval(playbackRef.current);
      }
    }

    return () => {
      if (playbackRef.current) {
        clearInterval(playbackRef.current);
      }
    };
  }, [isPlaying, radarFrames.length, playbackSpeed]);

  // Load national radar on mount
  useEffect(() => {
    loadRadarFrames();
  }, [loadRadarFrames]);

  // Jump to selected station
  useEffect(() => {
    if (selectedStation && mapRef.current) {
      const map = mapRef.current;
      map.setView([selectedStation.latitude, selectedStation.longitude], 8);
      loadRadarFrames(selectedStation.station_id);
    }
  }, [selectedStation, loadRadarFrames]);

  const togglePlayback = () => {
    setIsPlaying(!isPlaying);
  };

  const goToFrame = (frameIndex) => {
    setCurrentFrame(frameIndex);
  };

  const jumpToStorm = (stormData) => {
    if (mapRef.current) {
      mapRef.current.setView([stormData.latitude, stormData.longitude], 9);
    }
  };

  // Global functions for popup buttons
  useEffect(() => {
    window.jumpToStorm = (stationId) => {
      const storm = stormCells.find(s => s.stationId === stationId);
      if (storm) jumpToStorm(storm);
    };

    window.selectRadarStation = (stationId) => {
      const station = radarStations.find(s => s.station_id === stationId);
      if (station) onStationSelect(station);
    };

    return () => {
      delete window.jumpToStorm;
      delete window.selectRadarStation;
    };
  }, [stormCells, radarStations, onStationSelect]);

  const MapEventHandler = () => {
    useMapEvents({
      click: (e) => {
        console.log('Map clicked at:', e.latlng);
      },
      zoomend: (e) => {
        setMapZoom(e.target.getZoom());
      },
      moveend: (e) => {
        const center = e.target.getCenter();
        setMapCenter([center.lat, center.lng]);
      }
    });
    return null;
  };

  return (
    <div className="relative w-full h-full">
      {/* Collapsible Radar Controls */}
      <Card className={`absolute top-4 left-4 z-[1000] bg-slate-800/95 border-slate-700 backdrop-blur-sm transition-all duration-300 ${controlsCollapsed ? 'w-12' : 'w-80'}`}>
        <CardHeader className="pb-3">
          <CardTitle className="text-white text-sm flex items-center justify-between">
            {!controlsCollapsed && (
              <span className="flex items-center">
                <MapPin className="h-4 w-4 mr-2" />
                Radar Control Center
              </span>
            )}
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setControlsCollapsed(!controlsCollapsed)}
              className="text-white hover:bg-slate-700 p-1"
            >
              {controlsCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
            </Button>
          </CardTitle>
        </CardHeader>
        
        {!controlsCollapsed && (
          <CardContent className="space-y-4">
            {/* Data Type Selection */}
            <div className="space-y-2">
              <label className="text-xs text-slate-400">Radar Data Type</label>
              <Select value={dataType} onValueChange={setDataType}>
                <SelectTrigger className="bg-slate-700 border-slate-600 text-white">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-slate-800 border-slate-600">
                  {Object.entries(RADAR_DATA_TYPES).map(([key, config]) => (
                    <SelectItem key={key} value={key} className="text-white hover:bg-slate-700">
                      {config.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Playback Controls */}
            <div className="flex items-center space-x-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => goToFrame(0)}
                className="border-slate-600 text-white hover:bg-slate-700"
              >
                <SkipBack className="h-3 w-3" />
              </Button>
              
              <Button
                size="sm"
                variant="outline"
                onClick={togglePlayback}
                className="border-slate-600 text-white hover:bg-slate-700"
              >
                {isPlaying ? <Pause className="h-3 w-3" /> : <Play className="h-3 w-3" />}
              </Button>
              
              <Button
                size="sm"
                variant="outline"
                onClick={() => goToFrame(radarFrames.length - 1)}
                className="border-slate-600 text-white hover:bg-slate-700"
              >
                <SkipForward className="h-3 w-3" />
              </Button>
              
              <Button
                size="sm"
                variant="outline"
                onClick={() => loadRadarFrames(selectedStation?.station_id)}
                disabled={isLoading}
                className="border-slate-600 text-white hover:bg-slate-700"
              >
                <RotateCcw className="h-3 w-3" />
              </Button>
            </div>

            {/* Frame Slider */}
            <div className="space-y-2">
              <div className="flex justify-between text-xs text-slate-400">
                <span>Frame {currentFrame + 1} of {radarFrames.length}</span>
                <span>{radarFrames[currentFrame] ? new Date(radarFrames[currentFrame].timestamp).toLocaleTimeString() : '--:--'}</span>
              </div>
              <Slider
                value={[currentFrame]}
                onValueChange={(value) => goToFrame(value[0])}
                max={radarFrames.length - 1}
                step={1}
                className="w-full"
              />
            </div>

            {/* Frame Count Control */}
            <div className="space-y-2">
              <label className="text-xs text-slate-400">Frames to Load: {frameCount}</label>
              <Slider
                value={[frameCount]}
                onValueChange={(value) => setFrameCount(value[0])}
                min={50}
                max={250}
                step={10}
                className="w-full"
              />
            </div>

            {/* Speed Control */}
            <div className="space-y-2">
              <label className="text-xs text-slate-400">Speed: {(1000/playbackSpeed).toFixed(1)}x</label>
              <Slider
                value={[playbackSpeed]}
                onValueChange={(value) => setPlaybackSpeed(value[0])}
                min={100}
                max={2000}
                step={100}
                className="w-full"
              />
            </div>

            {/* Opacity Control */}
            <div className="space-y-2">
              <label className="text-xs text-slate-400">Radar Opacity: {Math.round(radarOpacity * 100)}%</label>
              <Slider
                value={[radarOpacity]}
                onValueChange={(value) => setRadarOpacity(value[0])}
                min={0.1}
                max={1}
                step={0.1}
                className="w-full"
              />
            </div>

            {/* Advanced Settings Toggle */}
            <Button
              size="sm"
              variant="outline"
              onClick={() => setShowAdvancedSettings(!showAdvancedSettings)}
              className="w-full border-slate-600 text-white hover:bg-slate-700"
            >
              <Settings className="h-3 w-3 mr-2" />
              Advanced Settings
            </Button>

            {/* Advanced Settings Panel */}
            {showAdvancedSettings && (
              <div className="space-y-3 border-t border-slate-600 pt-3">
                <div className="space-y-2">
                  <label className="text-xs text-slate-400 flex items-center">
                    <Palette className="h-3 w-3 mr-1" />
                    Color Palette
                  </label>
                  <Select value={colorPalette} onValueChange={setColorPalette}>
                    <SelectTrigger className="bg-slate-700 border-slate-600 text-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-slate-800 border-slate-600">
                      {Object.entries(COLOR_PALETTES).map(([key, palette]) => (
                        <SelectItem key={key} value={key} className="text-white hover:bg-slate-700">
                          <div>
                            <div className="font-medium">{palette.name}</div>
                            <div className="text-xs text-slate-400">{palette.description}</div>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Color Preview */}
                <div className="space-y-1">
                  <label className="text-xs text-slate-400">Color Preview</label>
                  <div className="flex space-x-1">
                    {COLOR_PALETTES[colorPalette]?.colors.map((color, index) => (
                      <div
                        key={index}
                        className="w-4 h-4 rounded border border-slate-600"
                        style={{ backgroundColor: color }}
                        title={`Level ${index + 1}`}
                      />
                    ))}
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        )}
      </Card>

      {/* Storm Alerts Panel */}
      {stormCells.length > 0 && (
        <Card className="absolute top-4 right-4 z-[1000] bg-slate-800/95 border-slate-700 backdrop-blur-sm max-w-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-white text-sm flex items-center">
              <AlertTriangle className="h-4 w-4 mr-2 text-red-500" />
              Active Storm Alerts ({stormCells.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 max-h-64 overflow-y-auto">
            {stormCells.map((storm, index) => (
              <div
                key={index}
                onClick={() => jumpToStorm(storm)}
                className="bg-slate-700 p-3 rounded cursor-pointer hover:bg-slate-600 transition-colors"
              >
                <div className="flex justify-between items-start mb-1">
                  <span className="text-white font-medium text-sm">{storm.stationName}</span>
                  <Badge 
                    variant={storm.tornadoProbability > 70 ? "destructive" : storm.tornadoProbability > 40 ? "default" : "secondary"}
                    className="text-xs"
                  >
                    {storm.tornadoProbability}%
                  </Badge>
                </div>
                <div className="text-slate-300 text-xs space-y-1">
                  <div>EF Scale: {storm.predictedEFScale}</div>
                  <div>Alert: {storm.alertLevel}</div>
                  <div>Touchdown: {storm.touchdownTime || 'Estimating...'}</div>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Map Status */}
      <div className="absolute bottom-4 left-4 z-[1000] bg-slate-800/95 backdrop-blur-sm rounded px-3 py-2">
        <div className="text-white text-xs space-y-1">
          <div>Center: {mapCenter[0].toFixed(4)}°, {mapCenter[1].toFixed(4)}°</div>
          <div>Zoom: {mapZoom}</div>
          <div className="flex items-center space-x-2">
            <div className={`w-2 h-2 rounded-full ${isLoading ? 'bg-yellow-500' : 'bg-green-500'}`}></div>
            <span>{isLoading ? 'Loading radar...' : 'Radar data live'}</span>
          </div>
        </div>
      </div>

      {/* Interactive Map */}
      <MapContainer
        center={mapCenter}
        zoom={mapZoom}
        style={{ height: '100%', width: '100%' }}
        ref={mapRef}
        className="radar-map"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        
        <MapEventHandler />
        
        <RadarOverlay 
          radarFrames={radarFrames}
          currentFrame={currentFrame}
          opacity={radarOpacity}
          colorPalette={colorPalette}
          dataType={dataType}
        />
        
        <StormCellMarkers 
          stormCells={stormCells}
          onStormClick={onStormClick}
        />
        
        <RadarStationMarkers 
          radarStations={radarStations}
          onStationClick={onStationSelect}
          selectedStation={selectedStation}
        />
      </MapContainer>

      {/* Enhanced CSS for radar visualization and animations */}
      <style jsx global>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.7; transform: scale(1.1); }
        }
        
        .radar-overlay {
          pointer-events: none;
        }
        
        /* NEXRAD Reflectivity Color Filters */
        .radar-base_reflectivity-nexrad_reflectivity {
          filter: hue-rotate(0deg) saturate(1.2) contrast(1.1);
        }
        
        .radar-base_reflectivity-high_contrast_reflectivity {
          filter: hue-rotate(240deg) saturate(1.5) contrast(1.3);
        }
        
        /* Velocity Color Filters */
        .radar-base_velocity-velocity_standard {
          filter: hue-rotate(120deg) saturate(1.3) contrast(1.2);
        }
        
        .radar-storm_relative_velocity-velocity_storm {
          filter: hue-rotate(180deg) saturate(1.4) contrast(1.3);
        }
        
        /* MRMS Color Filters */
        .radar-mrms_reflectivity-mrms_standard {
          filter: hue-rotate(60deg) saturate(1.1) contrast(1.2) brightness(1.1);
        }
        
        /* Composite Color Filters */
        .radar-composite_reflectivity-composite {
          filter: hue-rotate(300deg) saturate(1.3) contrast(1.2) brightness(0.9);
        }
        
        /* Echo Tops Color Filters */
        .radar-echo_tops-echo_tops {
          filter: hue-rotate(30deg) saturate(1.2) contrast(1.1) brightness(1.1);
        }
        
        .storm-popup, .station-popup {
          font-family: system-ui, -apple-system, sans-serif;
        }
        
        .radar-map .leaflet-control-attribution {
          background: rgba(0, 0, 0, 0.7);
          color: white;
        }
        
        /* Collapsible controls animation */
        .controls-collapsed {
          transform: translateX(-240px);
        }
        
        .controls-expanded {
          transform: translateX(0);
        }
      `}</style>
    </div>
  );
};

export default InteractiveRadarMap;