import { useState } from 'react';
import type { VideoOption, AnalyzeMode } from '../types';

interface QueryInputProps {
  onSubmit: (query: string) => void;
  videos: VideoOption[];
  selectedVideo: string;
  onVideoChange: (video: string) => void;
  isLoading: boolean;
  mode: AnalyzeMode;
  onModeChange: (mode: AnalyzeMode) => void;
}

export function QueryInput({
  onSubmit,
  videos,
  selectedVideo,
  onVideoChange,
  isLoading,
  mode,
  onModeChange,
}: QueryInputProps) {
  const [query, setQuery] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim() && !isLoading) {
      onSubmit(query.trim());
      if (mode === 'chat') {
        setQuery(''); // Clear input for chat mode
      }
    }
  };

  return (
    <form className="query-input" onSubmit={handleSubmit}>
      <div className="mode-toggle">
        <button
          type="button"
          className={`mode-btn ${mode === 'video' ? 'active' : ''}`}
          onClick={() => onModeChange('video')}
        >
          📹 Clips
        </button>
        <button
          type="button"
          className={`mode-btn ${mode === 'chat' ? 'active' : ''}`}
          onClick={() => onModeChange('chat')}
        >
          💬 Chat
        </button>
      </div>

      {mode === 'video' && (
        <select
          value={selectedVideo}
          onChange={(e) => onVideoChange(e.target.value)}
          className="video-select"
        >
          {videos.map((v) => (
            <option key={v.path} value={v.path}>
              {v.name}
            </option>
          ))}
        </select>
      )}

      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder={mode === 'video'
          ? "Find clips... e.g. 'show me all touchdowns'"
          : "Ask about the game... e.g. 'who scored the most?'"
        }
        className="query-text"
        disabled={isLoading}
      />

      <button type="submit" className="query-submit" disabled={isLoading}>
        {isLoading ? '...' : mode === 'video' ? 'Search' : 'Ask'}
      </button>
    </form>
  );
}
