import { useState } from 'react';
import type { VideoOption } from '../types';

interface QueryInputProps {
  onSubmit: (query: string) => void;
  videos: VideoOption[];
  selectedVideo: string;
  onVideoChange: (video: string) => void;
  isLoading: boolean;
}

export function QueryInput({
  onSubmit,
  videos,
  selectedVideo,
  onVideoChange,
  isLoading
}: QueryInputProps) {
  const [query, setQuery] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim() && !isLoading) {
      onSubmit(query.trim());
    }
  };

  return (
    <form className="query-input" onSubmit={handleSubmit}>
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

      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Ask about plays... e.g. 'show me all touchdowns'"
        className="query-text"
        disabled={isLoading}
      />

      <button type="submit" className="query-submit" disabled={isLoading}>
        {isLoading ? 'Searching...' : 'Search'}
      </button>
    </form>
  );
}
