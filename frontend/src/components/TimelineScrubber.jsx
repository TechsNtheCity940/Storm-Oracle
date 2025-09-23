import React, { useState, useRef, useEffect, useCallback } from 'react';
import './GameRadarTheme.css';

const TimelineScrubber = ({
  totalFrames = 100,
  currentFrame = 0,
  onFrameChange,
  isPlaying = false,
  onPlayPause,
  playbackSpeed = 1,
  onSpeedChange,
  frameData = [], // Array of frame timestamps or data
  className = ''
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [hoverPosition, setHoverPosition] = useState(null);
  const trackRef = useRef(null);
  const thumbRef = useRef(null);

  // Calculate frame position as percentage
  const framePosition = totalFrames > 0 ? (currentFrame / (totalFrames - 1)) * 100 : 0;

  // Handle mouse/touch interactions
  const handlePointerDown = useCallback((e) => {
    setIsDragging(true);
    e.preventDefault();
  }, []);

  const handlePointerMove = useCallback((e) => {
    if (!trackRef.current) return;

    const rect = trackRef.current.getBoundingClientRect();
    const x = e.clientType === 'touch' ? e.touches[0].clientX : e.clientX;
    const percentage = Math.max(0, Math.min(100, ((x - rect.left) / rect.width) * 100));
    
    if (isDragging) {
      const newFrame = Math.round((percentage / 100) * (totalFrames - 1));
      onFrameChange?.(newFrame);
    } else {
      setHoverPosition(percentage);
    }
  }, [isDragging, totalFrames, onFrameChange]);

  const handlePointerUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  const handlePointerLeave = useCallback(() => {
    setHoverPosition(null);
    setIsDragging(false);
  }, []);

  // Set up global pointer events for dragging
  useEffect(() => {
    if (isDragging) {
      const handleGlobalMove = (e) => handlePointerMove(e);
      const handleGlobalUp = () => handlePointerUp();

      document.addEventListener('mousemove', handleGlobalMove);
      document.addEventListener('mouseup', handleGlobalUp);
      document.addEventListener('touchmove', handleGlobalMove);
      document.addEventListener('touchend', handleGlobalUp);

      return () => {
        document.removeEventListener('mousemove', handleGlobalMove);
        document.removeEventListener('mouseup', handleGlobalUp);
        document.removeEventListener('touchmove', handleGlobalMove);
        document.removeEventListener('touchend', handleGlobalUp);
      };
    }
  }, [isDragging, handlePointerMove, handlePointerUp]);

  // Generate timeline markers
  const generateMarkers = () => {
    const markers = [];
    const markerInterval = Math.max(1, Math.floor(totalFrames / 20)); // Max 20 markers
    
    for (let i = 0; i < totalFrames; i += markerInterval) {
      const position = (i / (totalFrames - 1)) * 100;
      const isMajor = i % (markerInterval * 5) === 0;
      
      markers.push(
        <div
          key={i}
          className={`timeline-marker ${isMajor ? 'major' : ''}`}
          style={{ left: `${position}%` }}
        />
      );
    }
    
    return markers;
  };

  // Format time for display
  const formatTime = (frameIndex) => {
    if (frameData[frameIndex]?.timestamp) {
      return new Date(frameData[frameIndex].timestamp).toLocaleTimeString();
    }
    return `Frame ${frameIndex + 1}`;
  };

  // Speed control options
  const speedOptions = [0.25, 0.5, 1, 2, 3, 5];

  return (
    <div className={`timeline-scrubber ${className}`}>
      {/* Header with controls */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <button
            onClick={onPlayPause}
            className="holo-button flex items-center gap-2"
          >
            {isPlaying ? (
              <>
                <div className="w-2 h-2 bg-current"></div>
                <div className="w-2 h-2 bg-current"></div>
              </>
            ) : (
              <div className="w-0 h-0 border-l-4 border-l-current border-y-2 border-y-transparent"></div>
            )}
            {isPlaying ? 'Pause' : 'Play'}
          </button>
          
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400">Speed:</span>
            <select
              value={playbackSpeed}
              onChange={(e) => onSpeedChange?.(parseFloat(e.target.value))}
              className="bg-slate-800 border border-slate-600 text-white rounded px-2 py-1 text-xs"
            >
              {speedOptions.map(speed => (
                <option key={speed} value={speed}>
                  {speed}x
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="status-indicator">
            <div className={`status-dot ${isPlaying ? 'active' : ''}`}></div>
            {isPlaying ? 'Playing' : 'Paused'}
          </div>
          
          <div className="text-xs text-slate-400">
            {currentFrame + 1} / {totalFrames}
          </div>
        </div>
      </div>

      {/* Timeline track */}
      <div className="relative">
        <div
          ref={trackRef}
          className="timeline-track cursor-pointer"
          onMouseDown={handlePointerDown}
          onMouseMove={handlePointerMove}
          onMouseLeave={handlePointerLeave}
          onTouchStart={handlePointerDown}
          onTouchMove={handlePointerMove}
        >
          {/* Progress bar */}
          <div
            className="timeline-progress"
            style={{ width: `${framePosition}%` }}
          />

          {/* Timeline markers */}
          <div className="timeline-markers">
            {generateMarkers()}
          </div>

          {/* Hover indicator */}
          {hoverPosition !== null && !isDragging && (
            <div
              className="absolute top-0 w-0.5 h-full bg-white opacity-50 pointer-events-none"
              style={{ left: `${hoverPosition}%` }}
            />
          )}
        </div>

        {/* Timeline thumb */}
        <div
          ref={thumbRef}
          className="timeline-thumb"
          style={{ left: `${framePosition}%` }}
          onMouseDown={handlePointerDown}
          onTouchStart={handlePointerDown}
        />

        {/* Current time display */}
        <div
          className="timeline-current-time"
          style={{ '--position': `${framePosition}%` }}
        >
          {formatTime(currentFrame)}
        </div>

        {/* Hover time display */}
        {hoverPosition !== null && !isDragging && (
          <div
            className="absolute top-[-45px] bg-slate-700 text-white px-2 py-1 rounded text-xs whitespace-nowrap pointer-events-none"
            style={{ 
              left: `${hoverPosition}%`,
              transform: 'translateX(-50%)',
              zIndex: 20
            }}
          >
            {formatTime(Math.round((hoverPosition / 100) * (totalFrames - 1)))}
          </div>
        )}
      </div>

      {/* Timeline labels */}
      <div className="timeline-labels">
        <span>{frameData[0] ? formatTime(0) : 'Start'}</span>
        <span className="text-center">Radar Timeline</span>
        <span>{frameData[totalFrames - 1] ? formatTime(totalFrames - 1) : 'End'}</span>
      </div>

      {/* Additional frame info */}
      {frameData[currentFrame] && (
        <div className="mt-3 p-3 bg-slate-800/50 rounded-lg border border-slate-700">
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-4">
              {frameData[currentFrame].data_type && (
                <span className="text-slate-400">
                  Type: <span className="text-white">{frameData[currentFrame].data_type}</span>
                </span>
              )}
              {frameData[currentFrame].intensity && (
                <span className="text-slate-400">
                  Intensity: <span className="text-white">{frameData[currentFrame].intensity} dBZ</span>
                </span>
              )}
            </div>
            
            {frameData[currentFrame].timestamp && (
              <span className="text-slate-400">
                {new Date(frameData[currentFrame].timestamp).toLocaleString()}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default TimelineScrubber;