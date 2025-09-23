import React from 'react';
import './CustomStormMarkers.css';

// Lightning Bolt Marker
export const LightningMarker = ({ 
  intensity = 1, 
  strikeCount = 1,
  position,
  onClick,
  className = ''
}) => {
  const getMarkerStyle = (strikes) => {
    const scales = {
      1: { size: 16, speed: '2s', color: '#fbbf24', opacity: 0.8 },
      2: { size: 22, speed: '1.5s', color: '#f59e0b', opacity: 0.85 },
      3: { size: 28, speed: '1s', color: '#d97706', opacity: 0.9 },
      4: { size: 34, speed: '0.8s', color: '#c2410c', opacity: 0.95 },
      5: { size: 40, speed: '0.6s', color: '#9a3412', opacity: 1 }
    };
    return scales[Math.min(strikes, 5)] || scales[1];
  };

  const style = getMarkerStyle(strikeCount);
  
  return (
    <div 
      className={`lightning-marker ${className}`}
      onClick={onClick}
      style={{
        '--lightning-size': `${style.size}px`,
        '--flash-speed': style.speed,
        '--lightning-color': style.color,
        '--lightning-opacity': style.opacity
      }}
    >
      <div className="lightning-icon">
        ⚡
      </div>
      <div className="strike-count">
        {strikeCount > 1 && strikeCount}
      </div>
      <div className="electrical-field"></div>
    </div>
  );
};

// Hail Marker
export const HailMarker = ({ 
  hailSize = 1, // 1=pea, 2=marble, 3=ping pong, 4=golf ball, 5=tennis ball
  probability = 50,
  position,
  onClick,
  className = ''
}) => {
  const getHailStyle = (size) => {
    const scales = {
      1: { size: 14, color: '#e5e7eb', name: 'Pea', opacity: 0.7 },
      2: { size: 18, color: '#d1d5db', name: 'Marble', opacity: 0.8 },
      3: { size: 24, color: '#9ca3af', name: 'Ping Pong', opacity: 0.85 },
      4: { size: 30, color: '#6b7280', name: 'Golf Ball', opacity: 0.9 },
      5: { size: 38, color: '#4b5563', name: 'Tennis Ball', opacity: 0.95 }
    };
    return scales[Math.min(size, 5)] || scales[1];
  };

  const style = getHailStyle(hailSize);
  
  return (
    <div 
      className={`hail-marker ${className}`}
      onClick={onClick}
      style={{
        '--hail-size': `${style.size}px`,
        '--hail-color': style.color,
        '--hail-opacity': style.opacity
      }}
    >
      <div className="hail-icon">
        🧊
      </div>
      <div className="hail-probability">
        {probability}%
      </div>
      <div className="hail-impact-ring"></div>
      <div className="size-indicator" title={`${style.name} size hail`}>
        {hailSize}
      </div>
    </div>
  );
};

// Wind Speed Indicator with Direction
export const WindMarker = ({ 
  windSpeed = 25, // mph
  direction = 0, // degrees (0 = North, 90 = East, etc.)
  gustSpeed = null,
  position,
  onClick,
  className = ''
}) => {
  const getWindStyle = (speed) => {
    if (speed >= 74) return { color: '#dc2626', level: 'Hurricane', size: 36 }; // Hurricane
    if (speed >= 58) return { color: '#ea580c', level: 'Severe', size: 32 }; // Severe
    if (speed >= 39) return { color: '#f59e0b', level: 'Strong', size: 28 }; // Strong  
    if (speed >= 25) return { color: '#eab308', level: 'Moderate', size: 24 }; // Moderate
    return { color: '#22c55e', level: 'Light', size: 20 }; // Light
  };

  const style = getWindStyle(windSpeed);
  
  return (
    <div 
      className={`wind-marker ${className}`}
      onClick={onClick}
      style={{
        '--wind-size': `${style.size}px`,
        '--wind-color': style.color,
        '--wind-direction': `${direction}deg`
      }}
    >
      <div className="wind-arrow">
        <div className="arrow-shaft"></div>
        <div className="arrow-head"></div>
      </div>
      <div className="wind-speed">
        {windSpeed}
        {gustSpeed && <span className="gust">G{gustSpeed}</span>}
      </div>
      <div className="wind-level">{style.level}</div>
      <div className="wind-flow-lines">
        <div className="flow-line line-1"></div>
        <div className="flow-line line-2"></div>
        <div className="flow-line line-3"></div>
      </div>
    </div>
  );
};

// Precipitation Marker
export const PrecipitationMarker = ({ 
  precipType = 'rain', // rain, snow, sleet, freezing_rain
  intensity = 1, // 1-5 scale
  accumulation = 0,
  position,
  onClick,
  className = ''
}) => {
  const getPrecipStyle = (type, level) => {
    const types = {
      rain: { icon: '🌧️', color: '#3b82f6', unit: 'in' },
      snow: { icon: '❄️', color: '#e5e7eb', unit: 'in' },
      sleet: { icon: '🌨️', color: '#94a3b8', unit: 'in' },
      freezing_rain: { icon: '🧊', color: '#06b6d4', unit: 'in' }
    };
    
    const intensities = {
      1: { name: 'Light', size: 18 },
      2: { name: 'Moderate', size: 22 },
      3: { name: 'Heavy', size: 26 },
      4: { name: 'Very Heavy', size: 30 },
      5: { name: 'Extreme', size: 34 }
    };
    
    return {
      ...types[type],
      ...intensities[Math.min(level, 5)]
    };
  };

  const style = getPrecipStyle(precipType, intensity);
  
  return (
    <div 
      className={`precipitation-marker ${className}`}
      onClick={onClick}
      style={{
        '--precip-size': `${style.size}px`,
        '--precip-color': style.color
      }}
    >
      <div className="precip-icon">
        {style.icon}
      </div>
      <div className="precip-intensity">
        {style.name}
      </div>
      {accumulation > 0 && (
        <div className="accumulation">
          {accumulation}{style.unit}
        </div>
      )}
      <div className="precip-animation">
        <div className="drop drop-1"></div>
        <div className="drop drop-2"></div>
        <div className="drop drop-3"></div>
      </div>
    </div>
  );
};

// Storm Cell Marker (Enhanced)
export const StormCellMarker = ({ 
  cellType = 'supercell', // supercell, multicell, squall_line
  intensity = 3,
  movement = { speed: 25, direction: 90 },
  features = [], // ['mesocyclone', 'hail_shaft', 'wall_cloud']
  position,
  onClick,
  className = ''
}) => {
  const getCellStyle = (type, level) => {
    const types = {
      supercell: { icon: '🌪️', color: '#dc2626', name: 'Supercell' },
      multicell: { icon: '⛈️', color: '#ea580c', name: 'Multicell' },
      squall_line: { icon: '🌩️', color: '#f59e0b', name: 'Squall Line' },
      ordinary: { icon: '🌦️', color: '#22c55e', name: 'Ordinary' }
    };
    
    return {
      ...types[type],
      size: 20 + (level * 6)
    };
  };

  const style = getCellStyle(cellType, intensity);
  
  return (
    <div 
      className={`storm-cell-marker ${cellType} ${className}`}
      onClick={onClick}
      style={{
        '--cell-size': `${style.size}px`,
        '--cell-color': style.color,
        '--movement-direction': `${movement.direction}deg`
      }}
    >
      <div className="cell-icon">
        {style.icon}
      </div>
      <div className="cell-features">
        {features.includes('mesocyclone') && <div className="mesocyclone">🌀</div>}
        {features.includes('hail_shaft') && <div className="hail-shaft">🧊</div>}
        {features.includes('wall_cloud') && <div className="wall-cloud">☁️</div>}
      </div>
      <div className="movement-vector">
        <div className="vector-arrow"></div>
        <div className="speed-label">{movement.speed}mph</div>
      </div>
      <div className="intensity-ring"></div>
    </div>
  );
};

export default {
  LightningMarker,
  HailMarker, 
  WindMarker,
  PrecipitationMarker,
  StormCellMarker
};