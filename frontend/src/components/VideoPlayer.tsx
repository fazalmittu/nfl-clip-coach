import { useRef, useEffect, useState } from 'react';
import type { ClipTimestamp } from '../types';

interface VideoPlayerProps {
  videoSrc: string;
  clips: ClipTimestamp[];
  currentClipIndex: number;
  onClipChange: (index: number) => void;
}

export function VideoPlayer({
  videoSrc,
  clips,
  currentClipIndex,
  onClipChange
}: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handleLoadedMetadata = () => setDuration(video.duration);
    const handleTimeUpdate = () => setCurrentTime(video.currentTime);

    video.addEventListener('loadedmetadata', handleLoadedMetadata);
    video.addEventListener('timeupdate', handleTimeUpdate);

    return () => {
      video.removeEventListener('loadedmetadata', handleLoadedMetadata);
      video.removeEventListener('timeupdate', handleTimeUpdate);
    };
  }, []);

  // Jump to clip when currentClipIndex changes
  useEffect(() => {
    if (clips.length > 0 && currentClipIndex >= 0 && videoRef.current) {
      const clip = clips[currentClipIndex];
      videoRef.current.currentTime = clip.start_time;
      videoRef.current.play();
    }
  }, [currentClipIndex, clips]);

  const handleTimelineClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!videoRef.current || !duration) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const percent = (e.clientX - rect.left) / rect.width;
    videoRef.current.currentTime = percent * duration;
  };

  const handleClipClick = (index: number) => {
    onClipChange(index);
  };

  const handlePrevClip = () => {
    if (currentClipIndex > 0) {
      onClipChange(currentClipIndex - 1);
    }
  };

  const handleNextClip = () => {
    if (currentClipIndex < clips.length - 1) {
      onClipChange(currentClipIndex + 1);
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="video-player">
      <video
        ref={videoRef}
        src={videoSrc}
        className="video-element"
        controls
      />

      {/* Timeline with clip markers */}
      <div className="timeline-container">
        <div className="timeline" onClick={handleTimelineClick}>
          {/* Progress bar */}
          <div
            className="timeline-progress"
            style={{ width: `${(currentTime / duration) * 100}%` }}
          />

          {/* Clip markers */}
          {clips.map((clip, index) => (
            <div
              key={index}
              className={`clip-marker ${index === currentClipIndex ? 'active' : ''}`}
              style={{
                left: `${(clip.start_time / duration) * 100}%`,
                width: `${((clip.end_time - clip.start_time) / duration) * 100}%`
              }}
              onClick={(e) => {
                e.stopPropagation();
                handleClipClick(index);
              }}
              title={`Clip ${index + 1}: ${formatTime(clip.start_time)} - ${formatTime(clip.end_time)}`}
            />
          ))}
        </div>

        <div className="timeline-times">
          <span>{formatTime(currentTime)}</span>
          <span>{formatTime(duration)}</span>
        </div>
      </div>

      {/* Clip navigation */}
      {clips.length > 0 && (
        <div className="clip-nav">
          <button onClick={handlePrevClip} disabled={currentClipIndex <= 0}>
            ← Prev
          </button>
          <span className="clip-counter">
            Clip {currentClipIndex + 1} of {clips.length}
          </span>
          <button onClick={handleNextClip} disabled={currentClipIndex >= clips.length - 1}>
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
