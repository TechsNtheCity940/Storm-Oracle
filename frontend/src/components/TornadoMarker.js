import React from 'react';
import './TornadoMarker.css';

const TornadoMarker = ({ 
  intensity = 1, 
  isConfirmed = false, 
  onClick,
  className = ''
}) => {
  // EF Scale mapping to size and rotation speed
  const getMarkerStyle = (efScale) => {
    const scales = {
      0: { size: 20, speed: '3s', opacity: 0.7 },
      1: { size: 30, speed: '2.5s', opacity: 0.8 },
      2: { size: 40, speed: '2s', opacity: 0.85 },
      3: { size: 55, speed: '1.5s', opacity: 0.9 },
      4: { size: 70, speed: '1s', opacity: 0.95 },
      5: { size: 90, speed: '0.8s', opacity: 1 }
    };
    
    return scales[Math.min(efScale, 5)] || scales[1];
  };

  const style = getMarkerStyle(intensity);
  
  return (
    <div 
      className={`tornado-marker ${isConfirmed ? 'confirmed' : 'predicted'} ${className}`}
      onClick={onClick}
      style={{
        '--tornado-size': `${style.size}px`,
        '--rotation-speed': style.speed,
        '--tornado-opacity': style.opacity
      }}
    >
      <div className="tornado-icon">
        <img 
          src="/images/tornado-marker.png" 
          alt={`${isConfirmed ? 'Confirmed' : 'Predicted'} Tornado EF${intensity}`}
          className="tornado-image"
        />
      </div>
      
      {/* Intensity indicator */}
      <div className="intensity-badge">
        EF{intensity}
      </div>
      
      {/* Pulsing danger ring for confirmed tornadoes */}
      {isConfirmed && (
        <div className="danger-ring"></div>
      )}
      
      {/* Status indicator */}
      <div className={`status-dot ${isConfirmed ? 'confirmed-dot' : 'predicted-dot'}`}>
      </div>
    </div>
  );
};

// Component for use with React-Leaflet
export const LeafletTornadoMarker = ({ position, intensity, isConfirmed, data, ...props }) => {
  return (
    <TornadoMarker
      intensity={intensity}
      isConfirmed={isConfirmed}
      position={position}
      onClick={() => props.onClick && props.onClick(data)}
      {...props}
    />
  );
};

export default TornadoMarker;