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

  // Enhanced radar frames loading with real data
  const loadRadarFrames = useCallback(async (stationId = null, frames = frameCount) => {
    setIsLoading(true);
    try {
      let radarFrames = [];
      
      if (stationId && selectedStation) {
        // Load station-specific radar data
        for (let i = 0; i < frames; i++) {
          const timeOffset = i * 10 * 60 * 1000; // 10 minutes apart
          const timestamp = Date.now() - timeOffset;
          
          try {
            // Try to get real radar data from our API
            const response = await axios.get(`${API}/radar-data/${stationId}?data_type=${dataType}&timestamp=${timestamp}`);
            
            radarFrames.push({
              timestamp,
              frameIndex: frames - i - 1,
              imageUrl: response.data.radar_url,
              bounds: {
                north: selectedStation.latitude + 3,
                south: selectedStation.latitude - 3,
                east: selectedStation.longitude + 3,
                west: selectedStation.longitude - 3
              },
              stationData: response.data
            });
          } catch (error) {
            // Fallback to constructed URLs if API fails
            const radarTypeCode = dataType === 'base_velocity' ? '1' : '0';
            const imageUrl = `https://radar.weather.gov/ridge/lite/${stationId.toLowerCase()}_${radarTypeCode}.gif?${timestamp}`;
            
            radarFrames.push({
              timestamp,
              frameIndex: frames - i - 1,
              imageUrl,
              bounds: {
                north: selectedStation.latitude + 3,
                south: selectedStation.latitude - 3,
                east: selectedStation.longitude + 3,
                west: selectedStation.longitude - 3
              }
            });
          }
        }
      } else {
        // Load national radar data
        try {
          const response = await axios.get(`${API}/radar-frames/national?frames=${frames}&data_type=${dataType}`);
          if (response.data && response.data.frames) {
            radarFrames = response.data.frames;
          } else {
            throw new Error('No frames in response');
          }
        } catch (error) {
          // Generate national radar frames with real URLs
          for (let i = 0; i < frames; i++) {
            const timeOffset = i * 10 * 60 * 1000;
            const timestamp = Date.now() - timeOffset;
            
            radarFrames.push({
              timestamp,
              frameIndex: frames - i - 1,
              imageUrl: `https://radar.weather.gov/ridge/RadarImg/N0R/USA_0.gif?${timestamp}`,
              bounds: {
                north: 50,
                south: 20,
                east: -60,
                west: -130
              }
            });
          }
        }
      }
      
      setRadarFrames(radarFrames.reverse()); // Oldest to newest
      setCurrentFrame(radarFrames.length - 1); // Start with most recent
      
    } catch (error) {
      console.error('Error loading radar frames:', error);
      // Create minimal fallback
      setRadarFrames([]);
    }
    setIsLoading(false);
  }, [frameCount, selectedStation, dataType]);

  // Fullscreen functionality
  const toggleFullscreen = useCallback(() => {
    if (!document.fullscreenElement) {
      mapContainerRef.current?.requestFullscreen?.() || 
      mapContainerRef.current?.webkitRequestFullscreen?.() ||
      mapContainerRef.current?.mozRequestFullScreen?.();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen?.() ||
      document.webkitExitFullscreen?.() ||
      document.mozCancelFullScreen?.();
      setIsFullscreen(false);
    }
  }, []);

  // Listen for fullscreen changes
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };
    
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    document.addEventListener('webkitfullscreenchange', handleFullscreenChange);
    document.addEventListener('mozfullscreenchange', handleFullscreenChange);
    
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
      document.removeEventListener('webkitfullscreenchange', handleFullscreenChange);
      document.removeEventListener('mozfullscreenchange', handleFullscreenChange);
    };
  }, []);

  // Enhanced data type change handler
  const handleDataTypeChange = useCallback((newDataType) => {
    setDataType(newDataType);
    setColorPalette(RADAR_DATA_TYPES[newDataType]?.defaultColors || 'nexrad_reflectivity');
    // Reload frames with new data type
    if (selectedStation) {
      loadRadarFrames(selectedStation.station_id, frameCount);
    } else {
      loadRadarFrames(null, frameCount);
    }
  }, [selectedStation, frameCount, loadRadarFrames]);

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
    <div 
      ref={mapContainerRef}
      className={`relative w-full h-full ${isFullscreen ? 'fixed inset-0 z-[9999] bg-black' : ''}`}
    >
      {/* Modern Collapsible Radar Controls */}
      <Card className={`absolute top-4 left-4 z-[1000] bg-white/90 border-blue-100 backdrop-blur-md shadow-xl transition-all duration-300 rounded-2xl ${controlsCollapsed ? 'w-14' : 'w-80'} ${isFullscreen ? 'max-h-[calc(100vh-2rem)]' : 'max-h-[calc(100vh-8rem)]'}`}>
        <CardHeader className="pb-3 flex-shrink-0">
          <CardTitle className="text-slate-700 text-sm flex items-center justify-between font-semibold">
            {!controlsCollapsed && (
              <span className="flex items-center">
                <div className="p-1.5 bg-gradient-to-br from-blue-100 to-sky-100 rounded-lg mr-2">
                  <MapPin className="h-4 w-4 text-blue-600" />
                </div>
                Radar Control Center
              </span>
            )}
            <div className="flex items-center space-x-1">
              {/* Fullscreen Toggle */}
              <Button
                size="sm"
                variant="ghost"
                onClick={toggleFullscreen}
                className="text-slate-600 hover:bg-blue-50 hover:text-blue-600 p-1.5 rounded-lg transition-all"
                title={isFullscreen ? "Exit Fullscreen" : "Enter Fullscreen"}
              >
                {isFullscreen ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
              </Button>
              
              {/* Collapse Toggle */}
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setControlsCollapsed(!controlsCollapsed)}
                className="text-slate-600 hover:bg-blue-50 hover:text-blue-600 p-1.5 rounded-lg transition-all"
                title={controlsCollapsed ? "Expand Controls" : "Collapse Controls"}
              >
                {controlsCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
              </Button>
            </div>
          </CardTitle>
        </CardHeader>
        
        {!controlsCollapsed && (
          <CardContent className="space-y-5 overflow-y-auto overflow-x-hidden max-h-full pr-2 custom-scrollbar">
            <div className="space-y-5">
              {/* Data Type Selection */}
              <div className="space-y-2">
                <label className="text-xs text-slate-600 font-semibold uppercase tracking-wide">Radar Data Type</label>
                <Select value={dataType} onValueChange={handleDataTypeChange}>
                  <SelectTrigger className="bg-white border-blue-200 text-slate-700 rounded-xl hover:border-blue-300 focus:ring-2 focus:ring-blue-200 transition-all">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-white border-blue-100 rounded-xl shadow-xl max-h-60 overflow-y-auto">
                    {Object.entries(RADAR_DATA_TYPES).map(([key, config]) => (
                      <SelectItem key={key} value={key} className="text-slate-700 hover:bg-blue-50 rounded-lg">
                        {config.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Current Selection Info */}
              {selectedStation && (
                <div className="bg-gradient-to-br from-blue-50 to-sky-50 p-4 rounded-2xl border border-blue-100">
                  <div className="text-slate-700 text-sm font-bold">{selectedStation.name}</div>
                  <div className="text-blue-600 text-xs font-semibold">{selectedStation.station_id}</div>
                  <div className="text-slate-500 text-xs mt-1">
                    📍 {selectedStation.latitude.toFixed(4)}°, {selectedStation.longitude.toFixed(4)}°
                  </div>
                </div>
              )}

              {/* Modern Playback Controls */}
              <div className="space-y-3">
                <label className="text-xs text-slate-600 font-semibold uppercase tracking-wide">Animation Controls</label>
                <div className="flex items-center space-x-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => goToFrame(0)}
                    className="border-blue-200 text-slate-700 hover:bg-blue-50 hover:border-blue-300 rounded-lg transition-all"
                    title="Go to First Frame"
                  >
                    <SkipBack className="h-3 w-3" />
                  </Button>
                  
                  <Button
                    size="sm"
                    onClick={togglePlayback}
                    className={`${isPlaying ? 'bg-gradient-to-r from-red-500 to-rose-600 hover:from-red-600 hover:to-rose-700' : 'bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700'} text-white rounded-lg transition-all shadow-lg hover:shadow-xl`}
                    title={isPlaying ? "Pause Animation" : "Play Animation"}
                  >
                    {isPlaying ? <Pause className="h-3 w-3" /> : <Play className="h-3 w-3" />}
                  </Button>
                  
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => goToFrame(radarFrames.length - 1)}
                    className="border-blue-200 text-slate-700 hover:bg-blue-50 hover:border-blue-300 rounded-lg transition-all"
                    title="Go to Latest Frame"
                  >
                    <SkipForward className="h-3 w-3" />
                  </Button>
                  
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => loadRadarFrames(selectedStation?.station_id)}
                    disabled={isLoading}
                    className="border-blue-200 text-slate-700 hover:bg-blue-50 hover:border-blue-300 rounded-lg transition-all"
                    title="Refresh Radar Data"
                  >
                    <RotateCcw className={`h-3 w-3 ${isLoading ? 'animate-spin text-blue-600' : ''}`} />
                  </Button>
                </div>
              </div>

              {/* Modern Frame Slider */}
              <div className="space-y-3">
                <div className="flex justify-between text-xs text-slate-600 font-medium">
                  <span className="bg-blue-50 px-2 py-1 rounded-lg">Frame {currentFrame + 1} of {radarFrames.length}</span>
                  <span className="bg-sky-50 px-2 py-1 rounded-lg">
                    {radarFrames[currentFrame] 
                      ? new Date(radarFrames[currentFrame].timestamp).toLocaleTimeString()
                      : '--:--'
                    }
                  </span>
                </div>
                <Slider
                  value={[currentFrame]}
                  onValueChange={(value) => goToFrame(value[0])}
                  max={Math.max(0, radarFrames.length - 1)}
                  step={1}
                  className="w-full"
                  disabled={radarFrames.length === 0}
                />
              </div>

              {/* Frame Count Control */}
              <div className="space-y-3">
                <label className="text-xs text-slate-600 font-semibold uppercase tracking-wide">
                  Frames to Load: 
                  <span className="bg-blue-100 text-blue-700 px-2 py-1 rounded-lg ml-2 normal-case">{frameCount}</span>
                  <span className="text-slate-500 ml-1 normal-case">({(frameCount * 10)} min)</span>
                </label>
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
              <div className="space-y-3">
                <label className="text-xs text-slate-600 font-semibold uppercase tracking-wide">
                  Animation Speed: 
                  <span className="bg-green-100 text-green-700 px-2 py-1 rounded-lg ml-2 normal-case">{(1000/playbackSpeed).toFixed(1)}x</span>
                </label>
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
              <div className="space-y-3">
                <label className="text-xs text-slate-600 font-semibold uppercase tracking-wide">
                  Radar Opacity: 
                  <span className="bg-purple-100 text-purple-700 px-2 py-1 rounded-lg ml-2 normal-case">{Math.round(radarOpacity * 100)}%</span>
                </label>
                <Slider
                  value={[radarOpacity]}
                  onValueChange={(value) => setRadarOpacity(value[0])}
                  min={0.1}
                  max={1}
                  step={0.1}
                  className="w-full"
                />
              </div>

              {/* Modern Loading Status */}
              {isLoading && (
                <div className="bg-gradient-to-r from-blue-50 to-sky-50 border border-blue-200 p-4 rounded-2xl">
                  <div className="text-slate-700 text-sm flex items-center font-medium">
                    <RotateCcw className="h-4 w-4 mr-3 animate-spin text-blue-600" />
                    Loading {frameCount} radar frames...
                  </div>
                  <div className="mt-2 bg-blue-100 rounded-full h-2">
                    <div className="bg-gradient-to-r from-blue-500 to-sky-600 h-full rounded-full animate-pulse w-3/4"></div>
                  </div>
                </div>
              )}

              {/* Modern Advanced Settings Toggle */}
              <Button
                size="sm"
                variant="outline"
                onClick={() => setShowAdvancedSettings(!showAdvancedSettings)}
                className="w-full border-blue-200 text-slate-700 hover:bg-blue-50 hover:border-blue-300 rounded-xl transition-all"
              >
                <div className="p-1 bg-gradient-to-br from-blue-100 to-sky-100 rounded-lg mr-2">
                  <Settings className="h-3 w-3 text-blue-600" />
                </div>
                Advanced Settings
                <ChevronRight className={`h-3 w-3 ml-auto transition-transform text-blue-600 ${showAdvancedSettings ? 'rotate-90' : ''}`} />
              </Button>

              {/* Modern Advanced Settings Panel */}
              {showAdvancedSettings && (
                <div className="space-y-4 border-t border-blue-100 pt-4">
                  <div className="space-y-3">
                    <label className="text-xs text-slate-600 flex items-center font-semibold uppercase tracking-wide">
                      <div className="p-1 bg-gradient-to-br from-purple-100 to-pink-100 rounded-lg mr-2">
                        <Palette className="h-3 w-3 text-purple-600" />
                      </div>
                      Color Palette
                    </label>
                    <Select value={colorPalette} onValueChange={setColorPalette}>
                      <SelectTrigger className="bg-white border-blue-200 text-slate-700 rounded-xl hover:border-blue-300 focus:ring-2 focus:ring-blue-200 transition-all">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-white border-blue-100 rounded-xl shadow-xl max-h-48 overflow-y-auto">
                        {Object.entries(COLOR_PALETTES).map(([key, palette]) => (
                          <SelectItem key={key} value={key} className="text-slate-700 hover:bg-blue-50 rounded-lg">
                            <div>
                              <div className="font-semibold">{palette.name}</div>
                              <div className="text-xs text-slate-500">{palette.description}</div>
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Modern Color Preview */}
                  <div className="space-y-2">
                    <label className="text-xs text-slate-600 font-semibold uppercase tracking-wide">Color Preview</label>
                    <div className="flex space-x-1 flex-wrap p-3 bg-gradient-to-br from-gray-50 to-slate-50 rounded-xl border border-gray-200">
                      {COLOR_PALETTES[colorPalette]?.colors.map((color, index) => (
                        <div
                          key={index}
                          className="w-7 h-7 rounded-lg border-2 border-white shadow-md flex-shrink-0 hover:scale-110 transition-transform"
                          style={{ backgroundColor: color }}
                          title={`Intensity Level ${index + 1}`}
                        />
                      ))}
                    </div>
                    <div className="text-xs text-slate-500 bg-blue-50 p-2 rounded-lg">
                      {COLOR_PALETTES[colorPalette]?.description}
                    </div>
                  </div>

                  {/* Modern Metadata */}
                  <div className="space-y-2 text-xs text-slate-600">
                    <div className="border-t border-blue-100 pt-3">
                      <div className="bg-gradient-to-r from-green-50 to-emerald-50 p-3 rounded-xl space-y-1">
                        <div className="font-medium">📡 Data Source: {realRadarData?.api_source || 'National Weather Service'}</div>
                        <div className="font-medium">🔄 Update Interval: {realRadarData?.refresh_interval || 300}s</div>
                        {realRadarData?.coordinates && (
                          <div className="font-medium">
                            📍 Radar Center: {realRadarData.coordinates.lat.toFixed(4)}°, {realRadarData.coordinates.lon.toFixed(4)}°
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
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

      {/* Interactive Map with Fullscreen Support */}
      <MapContainer
        center={mapCenter}
        zoom={mapZoom}
        style={{ 
          height: isFullscreen ? '100vh' : '100%', 
          width: '100%',
          position: isFullscreen ? 'fixed' : 'relative',
          top: isFullscreen ? 0 : 'auto',
          left: isFullscreen ? 0 : 'auto',
          zIndex: isFullscreen ? 9998 : 'auto'
        }}
        ref={mapRef}
        className="radar-map"
        zoomControl={!isFullscreen}
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

      {/* Enhanced CSS for radar visualization, scrolling, and fullscreen */}
      <style jsx global>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.7; transform: scale(1.1); }
        }
        
        .radar-overlay {
          pointer-events: none;
        }
        
        /* Scrollbar styling for controls */
        .overflow-y-auto::-webkit-scrollbar {
          width: 6px;
        }
        
        .overflow-y-auto::-webkit-scrollbar-track {
          background: rgba(71, 85, 105, 0.3);
          border-radius: 3px;
        }
        
        .overflow-y-auto::-webkit-scrollbar-thumb {
          background: rgba(148, 163, 184, 0.6);
          border-radius: 3px;
        }
        
        .overflow-y-auto::-webkit-scrollbar-thumb:hover {
          background: rgba(148, 163, 184, 0.8);
        }
        
        /* Fullscreen map styles */
        .radar-map.fullscreen {
          position: fixed !important;
          top: 0 !important;
          left: 0 !important;
          width: 100vw !important;
          height: 100vh !important;
          z-index: 9998 !important;
        }
        
        /* NEXRAD Reflectivity Color Filters */
        .radar-base_reflectivity-nexrad_reflectivity {
          filter: hue-rotate(0deg) saturate(1.2) contrast(1.1) brightness(1.1);
        }
        
        .radar-hi_res_reflectivity-nexrad_reflectivity {
          filter: hue-rotate(5deg) saturate(1.3) contrast(1.2) brightness(1.15);
        }
        
        .radar-base_reflectivity-high_contrast_reflectivity {
          filter: hue-rotate(240deg) saturate(1.5) contrast(1.3) brightness(1.1);
        }
        
        /* Velocity Color Filters */
        .radar-base_velocity-velocity_standard {
          filter: hue-rotate(120deg) saturate(1.3) contrast(1.2);
        }
        
        .radar-hi_res_velocity-velocity_standard {
          filter: hue-rotate(115deg) saturate(1.4) contrast(1.3);
        }
        
        .radar-storm_relative_velocity-velocity_storm {
          filter: hue-rotate(180deg) saturate(1.4) contrast(1.3) brightness(1.05);
        }
        
        /* MRMS Color Filters */
        .radar-mrms_reflectivity-mrms_standard {
          filter: hue-rotate(60deg) saturate(1.1) contrast(1.2) brightness(1.1);
        }
        
        /* Composite Color Filters */
        .radar-composite_reflectivity-composite {
          filter: hue-rotate(300deg) saturate(1.3) contrast(1.2) brightness(0.95);
        }
        
        /* Echo Tops Color Filters */
        .radar-echo_tops-echo_tops {
          filter: hue-rotate(30deg) saturate(1.2) contrast(1.1) brightness(1.1);
        }
        
        .storm-popup, .station-popup {
          font-family: system-ui, -apple-system, sans-serif;
        }
        
        .radar-map .leaflet-control-attribution {
          background: rgba(0, 0, 0, 0.8);
          color: white;
          border-radius: 4px;
        }
        
        /* Fullscreen controls positioning */
        .fullscreen-controls {
          position: fixed;
          top: 1rem;
          left: 1rem;
          z-index: 9999;
        }
        
        /* Loading overlay */
        .radar-loading {
          background: rgba(0, 0, 0, 0.3);
          backdrop-filter: blur(2px);
        }
        
        /* Enhanced map markers */
        .storm-marker {
          transition: all 0.3s ease;
        }
        
        .storm-marker:hover {
          transform: scale(1.2);
          filter: drop-shadow(0 0 8px rgba(255, 255, 255, 0.8));
        }
        
        .station-marker {
          transition: all 0.2s ease;
        }
        
        .station-marker:hover {
          transform: scale(1.1);
        }
        
        /* Real-time data indicator */
        @keyframes dataLive {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.6; }
        }
        
        .data-live-indicator {
          animation: dataLive 2s infinite;
        }
      `}</style>
    </div>
  );
};

export default InteractiveRadarMap;