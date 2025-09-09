import React, { useState, useEffect } from 'react';
import './FloatingInfoPanel.css';

const FloatingInfoPanel = ({ 
  position = { x: 0, y: 0 },
  data = null,
  visible = false,
  type = 'default', // tornado, storm, lightning, hail, wind, precipitation
  className = ''
}) => {
  const [panelStyle, setPanelStyle] = useState({
    transform: 'translate(-50%, -100%)',
    opacity: 0
  });

  useEffect(() => {
    if (visible && data) {
      // Adjust panel position to stay within viewport
      const viewportWidth = window.innerWidth;
      const viewportHeight = window.innerHeight;
      const panelWidth = 280;
      const panelHeight = 200;
      
      let x = position.x;
      let y = position.y - 20; // Offset above cursor
      
      // Keep panel within horizontal bounds
      if (x + panelWidth/2 > viewportWidth - 20) {
        x = viewportWidth - panelWidth/2 - 20;
      }
      if (x - panelWidth/2 < 20) {
        x = panelWidth/2 + 20;
      }
      
      // Keep panel within vertical bounds
      if (y - panelHeight < 20) {
        y = position.y + 40; // Show below cursor instead
      }
      
      setPanelStyle({
        left: `${x}px`,
        top: `${y}px`,
        transform: 'translate(-50%, -100%)',
        opacity: 1,
        pointerEvents: 'none'
      });
    } else {
      setPanelStyle(prev => ({
        ...prev,
        opacity: 0,
        pointerEvents: 'none'
      }));
    }
  }, [visible, data, position]);

  if (!data || !visible) return null;

  const renderTornadoInfo = () => (
    <div className="tornado-info">
      <div className="panel-header tornado-header">
        <div className="header-icon">🌪️</div>
        <div className="header-content">
          <h3>{data.confirmed ? 'CONFIRMED TORNADO' : 'PREDICTED TORNADO'}</h3>
          <div className="ef-scale">EF{data.ef_scale || data.intensity || 1} Scale</div>
        </div>
      </div>
      <div className="panel-body">
        <div className="info-grid">
          <div className="info-item">
            <span className="label">Confidence:</span>
            <span className={`value confidence-${Math.floor((data.confidence || 75) / 25)}`}>
              {Math.round(data.confidence || 75)}%
            </span>
          </div>
          <div className="info-item">
            <span className="label">Wind Speed:</span>
            <span className="value">{data.wind_speed || (data.intensity * 40 + 65)} mph</span>
          </div>
          <div className="info-item">
            <span className="label">Path Width:</span>
            <span className="value">{data.path_width || (data.intensity * 150 + 50)} yards</span>
          </div>
          <div className="info-item">
            <span className="label">Movement:</span>
            <span className="value">
              {data.movement?.direction || 'Unknown'}° at {data.movement?.speed || 'Unknown'} mph
            </span>
          </div>
        </div>
        {data.message && (
          <div className="alert-message">
            <div className="alert-icon">⚠️</div>
            <div className="alert-text">{data.message}</div>
          </div>
        )}
      </div>
    </div>
  );

  const renderStormInfo = () => (
    <div className="storm-info">
      <div className="panel-header storm-header">
        <div className="header-icon">⛈️</div>
        <div className="header-content">
          <h3>STORM CELL</h3>
          <div className="storm-type">{data.cell_type || 'Severe Thunderstorm'}</div>
        </div>
      </div>
      <div className="panel-body">
        <div className="info-grid">
          <div className="info-item">
            <span className="label">Intensity:</span>
            <span className={`value intensity-${Math.min(Math.floor(data.intensity / 20), 4)}`}>
              {data.intensity?.toFixed(0)} dBZ
            </span>
          </div>
          <div className="info-item">
            <span className="label">Tornado Risk:</span>
            <span className={`value risk-${Math.floor((data.tornado_probability || 0) * 4)}`}>
              {Math.round((data.tornado_probability || 0) * 100)}%
            </span>
          </div>
          <div className="info-item">
            <span className="label">Tops Height:</span>
            <span className="value">{data.echo_tops || 35}k ft</span>
          </div>
          <div className="info-item">
            <span className="label">Movement:</span>
            <span className="value">
              {data.movement?.direction || 90}° at {data.movement?.speed || 25} mph
            </span>
          </div>
        </div>
        {data.features && data.features.length > 0 && (
          <div className="storm-features">
            <span className="features-label">Features:</span>
            <div className="features-list">
              {data.features.map((feature, index) => (
                <span key={index} className="feature-tag">
                  {feature.replace('_', ' ')}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );

  const renderLightningInfo = () => (
    <div className="lightning-info">
      <div className="panel-header lightning-header">
        <div className="header-icon">⚡</div>
        <div className="header-content">
          <h3>LIGHTNING ACTIVITY</h3>
          <div className="strike-rate">{data.strikes_per_minute || 15} strikes/min</div>
        </div>
      </div>
      <div className="panel-body">
        <div className="info-grid">
          <div className="info-item">
            <span className="label">Strike Count:</span>
            <span className="value">{data.strike_count || 1}</span>
          </div>
          <div className="info-item">
            <span className="label">Type:</span>
            <span className="value">{data.strike_type || 'Cloud-to-Ground'}</span>
          </div>
          <div className="info-item">
            <span className="label">Polarity:</span>
            <span className="value">{data.polarity || 'Negative'}</span>
          </div>
          <div className="info-item">
            <span className="label">Current:</span>
            <span className="value">{data.current || 30}kA</span>
          </div>
        </div>
      </div>
    </div>
  );

  const renderHailInfo = () => (
    <div className="hail-info">
      <div className="panel-header hail-header">
        <div className="header-icon">🧊</div>
        <div className="header-content">
          <h3>HAIL FORECAST</h3>
          <div className="hail-size">{data.size_name || 'Quarter'} Size</div>
        </div>
      </div>
      <div className="panel-body">
        <div className="info-grid">
          <div className="info-item">
            <span className="label">Size:</span>
            <span className="value">{data.diameter || 1.0}" diameter</span>
          </div>
          <div className="info-item">
            <span className="label">Probability:</span>
            <span className={`value prob-${Math.floor(data.probability / 25)}`}>
              {data.probability || 50}%
            </span>
          </div>
          <div className="info-item">
            <span className="label">Duration:</span>
            <span className="value">{data.duration || 5}-{(data.duration || 5) + 10} min</span>
          </div>
          <div className="info-item">
            <span className="label">Accumulation:</span>
            <span className="value">{data.accumulation || 'Light'}</span>
          </div>
        </div>
      </div>
    </div>
  );

  const renderWindInfo = () => (
    <div className="wind-info">
      <div className="panel-header wind-header">
        <div className="header-icon">💨</div>
        <div className="header-content">
          <h3>WIND CONDITIONS</h3>
          <div className="wind-strength">{data.strength_category || 'Strong'} Winds</div>
        </div>
      </div>
      <div className="panel-body">
        <div className="info-grid">
          <div className="info-item">
            <span className="label">Speed:</span>
            <span className={`value wind-${Math.floor(data.speed / 20)}`}>
              {data.speed || 45} mph
            </span>
          </div>
          <div className="info-item">
            <span className="label">Gusts:</span>
            <span className="value">{data.gust_speed || data.speed + 15} mph</span>
          </div>
          <div className="info-item">
            <span className="label">Direction:</span>
            <span className="value">
              {data.direction || 180}° ({data.direction_name || 'S'})
            </span>
          </div>
          <div className="info-item">
            <span className="label">Shear:</span>
            <span className="value">{data.shear || 'Moderate'}</span>
          </div>
        </div>
      </div>
    </div>
  );

  const renderPrecipitationInfo = () => (
    <div className="precipitation-info">
      <div className="panel-header precip-header">
        <div className="header-icon">
          {data.type === 'snow' ? '❄️' : data.type === 'sleet' ? '🌨️' : '🌧️'}
        </div>
        <div className="header-content">
          <h3>{(data.type || 'rain').toUpperCase()}</h3>
          <div className="precip-intensity">{data.intensity_name || 'Moderate'} Intensity</div>
        </div>
      </div>
      <div className="panel-body">
        <div className="info-grid">
          <div className="info-item">
            <span className="label">Rate:</span>
            <span className="value">{data.rate || 0.25}"/hr</span>
          </div>
          <div className="info-item">
            <span className="label">Accumulation:</span>
            <span className="value">{data.accumulation || 0.5}"</span>
          </div>
          <div className="info-item">
            <span className="label">Duration:</span>
            <span className="value">{data.duration || 30} min</span>
          </div>
          <div className="info-item">
            <span className="label">Temperature:</span>
            <span className="value">{data.temperature || 65}°F</span>
          </div>
        </div>
      </div>
    </div>
  );

  const renderContent = () => {
    switch (type) {
      case 'tornado':
        return renderTornadoInfo();
      case 'storm':
        return renderStormInfo();
      case 'lightning':
        return renderLightningInfo();
      case 'hail':
        return renderHailInfo();
      case 'wind':
        return renderWindInfo();
      case 'precipitation':
        return renderPrecipitationInfo();
      default:
        return (
          <div className="default-info">
            <div className="panel-header">
              <h3>Weather Data</h3>
            </div>
            <div className="panel-body">
              <pre>{JSON.stringify(data, null, 2)}</pre>
            </div>
          </div>
        );
    }
  };

  return (
    <div 
      className={`floating-info-panel ${type} ${className}`}
      style={panelStyle}
    >
      <div className="panel-content">
        {renderContent()}
      </div>
      <div className="panel-arrow"></div>
    </div>
  );
};

export default FloatingInfoPanel;