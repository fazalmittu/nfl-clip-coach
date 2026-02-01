import { useRef, useEffect, useState, useCallback } from 'react';
import type { ClipTimestamp } from '../types';

interface VideoPlayerProps {
  videoSrc: string;
  gameTitle?: string;
  clips: ClipTimestamp[];
  currentClipIndex: number;
  clipSeek?: number;
  onClipChange: (index: number) => void;
  playbackSpeed?: number;
  videoFit?: 'contain' | 'fill';
  onDurationChange?: (duration: number) => void;
}

export function VideoPlayer({
  videoSrc,
  gameTitle,
  clips,
  currentClipIndex,
  clipSeek = 0,
  onClipChange,
  playbackSpeed = 1,
  videoFit = 'contain',
  onDurationChange,
}: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [showVolume, setShowVolume] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const timelineRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const onMeta = () => {
      setDuration(video.duration);
      onDurationChange?.(video.duration);
    };
    const onTime = () => setCurrentTime(video.currentTime);
    const onPlay = () => setIsPlaying(true);
    const onPause = () => setIsPlaying(false);

    video.addEventListener('loadedmetadata', onMeta);
    video.addEventListener('timeupdate', onTime);
    video.addEventListener('play', onPlay);
    video.addEventListener('pause', onPause);

    return () => {
      video.removeEventListener('loadedmetadata', onMeta);
      video.removeEventListener('timeupdate', onTime);
      video.removeEventListener('play', onPlay);
      video.removeEventListener('pause', onPause);
    };
  }, []);

  useEffect(() => {
    if (clips.length > 0 && currentClipIndex >= 0 && videoRef.current) {
      const clip = clips[currentClipIndex];
      videoRef.current.currentTime = clip.start_time;
      videoRef.current.play();
    }
  }, [currentClipIndex, clips, clipSeek]);

  useEffect(() => {
    const v = videoRef.current;
    if (!v) return;
    v.playbackRate = playbackSpeed;
  }, [playbackSpeed]);

  const togglePlay = useCallback(() => {
    const v = videoRef.current;
    if (!v) return;
    v.paused ? v.play() : v.pause();
  }, []);

  const toggleMute = useCallback(() => {
    const v = videoRef.current;
    if (!v) return;
    v.muted = !v.muted;
    setIsMuted(v.muted);
  }, []);

  const handleVolumeChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const v = videoRef.current;
    if (!v) return;
    const val = parseFloat(e.target.value);
    v.volume = val;
    setVolume(val);
    if (val > 0 && v.muted) {
      v.muted = false;
      setIsMuted(false);
    }
  }, []);

  const wasPlayingRef = useRef(false);

  const getPercentFromX = useCallback((clientX: number) => {
    if (!timelineRef.current) return 0;
    const rect = timelineRef.current.getBoundingClientRect();
    return Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
  }, []);

  const handleTimelineMouseDown = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    e.preventDefault();
    const v = videoRef.current;
    if (!v || !duration) return;

    wasPlayingRef.current = !v.paused;
    v.pause();

    const percent = getPercentFromX(e.clientX);
    v.currentTime = percent * duration;
    setCurrentTime(percent * duration);
    setIsDragging(true);
  }, [duration, getPercentFromX]);

  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e: MouseEvent) => {
      if (!videoRef.current || !duration) return;
      const percent = getPercentFromX(e.clientX);
      const time = percent * duration;
      setCurrentTime(time);
      videoRef.current.currentTime = time;
    };

    const handleMouseUp = () => {
      setIsDragging(false);
      if (wasPlayingRef.current && videoRef.current) {
        videoRef.current.play();
      }
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, duration, getPercentFromX]);

  const toggleFullscreen = useCallback(() => {
    const v = videoRef.current;
    if (!v) return;
    if (document.fullscreenElement) {
      document.exitFullscreen();
    } else {
      v.requestFullscreen();
    }
  }, []);

  const skip = useCallback((seconds: number) => {
    const v = videoRef.current;
    if (!v) return;
    v.currentTime = Math.max(0, Math.min(v.duration, v.currentTime + seconds));
  }, []);

  const formatTime = (seconds: number) => {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    if (hrs > 0) {
      return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="bg-white/[0.03] border border-white/[0.06] rounded-2xl overflow-hidden group/player flex flex-col">
      {/* Video with top overlay + fit */}
      <div className="relative cursor-pointer flex-1 min-h-0 flex flex-col" onClick={togglePlay}>
        <div className="relative w-full flex-1 min-h-0 bg-black flex items-center justify-center">
          <video
            ref={videoRef}
            src={videoSrc}
            className="w-full h-full bg-black"
            style={{ objectFit: videoFit }}
          />
        </div>
        {/* Play overlay on pause */}
        {!isPlaying && duration > 0 && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/30 pointer-events-none">
            <div className="w-16 h-16 rounded-full bg-white/10 backdrop-blur-sm flex items-center justify-center">
              <svg className="w-8 h-8 text-white ml-1" fill="currentColor" viewBox="0 0 24 24">
                <path d="M8 5v14l11-7z" />
              </svg>
            </div>
          </div>
        )}
      </div>

      {/* Controls */}
      <div className="px-4 py-3 space-y-2.5">
        {/* Timeline */}
        <div
          ref={timelineRef}
          className="relative h-1 bg-white/[0.08] rounded-full cursor-pointer group/timeline select-none"
          onMouseDown={handleTimelineMouseDown}
        >
          <div
            className="absolute top-0 left-0 h-full bg-amber-500/60 rounded-full pointer-events-none"
            style={{ width: duration ? `${(currentTime / duration) * 100}%` : '0%' }}
          />
          {/* Scrubber dot */}
          <div
            className={`absolute top-1/2 -translate-y-1/2 w-3 h-3 rounded-full bg-amber-400 transition-opacity pointer-events-none shadow-[0_0_6px_rgba(251,191,36,0.5)] ${
              isDragging ? 'opacity-100 scale-125' : 'opacity-0 group-hover/timeline:opacity-100'
            }`}
            style={{ left: duration ? `calc(${(currentTime / duration) * 100}% - 6px)` : '0%' }}
          />
          {/* Clip markers */}
          {clips.map((clip, index) => (
            <div
              key={index}
              className={`absolute top-1/2 -translate-y-1/2 w-2 h-2 rounded-full cursor-pointer transition-all ${
                index === currentClipIndex
                  ? 'bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.6)] scale-150'
                  : 'bg-amber-500/60 hover:bg-amber-400 hover:scale-125'
              }`}
              style={{
                left: duration ? `calc(${(clip.start_time / duration) * 100}% - 4px)` : '0%',
              }}
              onClick={(e) => {
                e.stopPropagation();
                onClipChange(index);
              }}
            />
          ))}
        </div>

        {/* Control bar */}
        <div className="flex items-center gap-2">
          {/* Play/Pause */}
          <button onClick={togglePlay} className="p-1 text-neutral-400 hover:text-white transition-colors cursor-pointer">
            {isPlaying ? (
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z" />
              </svg>
            ) : (
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M8 5v14l11-7z" />
              </svg>
            )}
          </button>

          {/* Skip back */}
          <button onClick={() => skip(-10)} className="p-1 text-neutral-500 hover:text-neutral-300 transition-colors cursor-pointer flex flex-col items-center">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 15 3 9m0 0 6-6M3 9h12a6 6 0 0 1 0 12h-3" />
            </svg>
            <span className="text-[8px] font-mono leading-none mt-0.5">10s</span>
          </button>

          {/* Skip forward */}
          <button onClick={() => skip(10)} className="p-1 text-neutral-500 hover:text-neutral-300 transition-colors cursor-pointer flex flex-col items-center">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="m15 15 6-6m0 0-6-6m6 6H9a6 6 0 0 0 0 12h3" />
            </svg>
            <span className="text-[8px] font-mono leading-none mt-0.5">10s</span>
          </button>

          {/* Volume */}
          <div
            className="relative flex items-center"
            onMouseEnter={() => setShowVolume(true)}
            onMouseLeave={() => setShowVolume(false)}
          >
            <button onClick={toggleMute} className="p-1 text-neutral-500 hover:text-neutral-300 transition-colors cursor-pointer">
              {isMuted || volume === 0 ? (
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M17.25 9.75 19.5 12m0 0 2.25 2.25M19.5 12l2.25-2.25M19.5 12l-2.25 2.25m-10.5-6 4.72-3.72a.75.75 0 0 1 1.28.53v14.88a.75.75 0 0 1-1.28.53l-4.72-3.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.009 9.009 0 0 1 2.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75Z" />
                </svg>
              ) : (
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19.114 5.636a9 9 0 0 1 0 12.728M16.463 8.288a5.25 5.25 0 0 1 0 7.424M6.75 8.25l4.72-3.72a.75.75 0 0 1 1.28.53v14.88a.75.75 0 0 1-1.28.53l-4.72-3.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.009 9.009 0 0 1 2.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75Z" />
                </svg>
              )}
            </button>
            {showVolume && (
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={isMuted ? 0 : volume}
                onChange={handleVolumeChange}
                className="w-16 h-1 ml-1 accent-amber-500 cursor-pointer"
              />
            )}
          </div>

          {/* Time */}
          <span className="text-[11px] font-mono tabular-nums text-neutral-600 ml-1">
            {formatTime(currentTime)} / {formatTime(duration)}
          </span>

          <div className="flex-1" />

          {/* Clip nav */}
          {clips.length > 0 && (
            <div className="flex items-center gap-1.5">
              <button
                onClick={() => currentClipIndex > 0 && onClipChange(currentClipIndex - 1)}
                disabled={currentClipIndex <= 0}
                className="p-1 text-neutral-500 hover:text-neutral-300 disabled:opacity-20 disabled:cursor-not-allowed transition-colors cursor-pointer"
              >
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
                </svg>
              </button>
              <span className="text-[10px] font-mono tabular-nums text-neutral-600 min-w-[32px] text-center">
                {currentClipIndex + 1}/{clips.length}
              </span>
              <button
                onClick={() => currentClipIndex < clips.length - 1 && onClipChange(currentClipIndex + 1)}
                disabled={currentClipIndex >= clips.length - 1}
                className="p-1 text-neutral-500 hover:text-neutral-300 disabled:opacity-20 disabled:cursor-not-allowed transition-colors cursor-pointer"
              >
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
                </svg>
              </button>
            </div>
          )}

          {/* Fullscreen */}
          <button onClick={toggleFullscreen} className="p-1 text-neutral-500 hover:text-neutral-300 transition-colors cursor-pointer">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
