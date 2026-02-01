import { useState } from 'react';
import { QueryInput } from './components/QueryInput';
import { VideoPlayer } from './components/VideoPlayer';
import { ChatPanel } from './components/ChatPanel';
import type { ClipTimestamp, VideoOption } from './types';
import './App.css';

const VIDEOS: VideoOption[] = [
  { name: '49ers vs Lions - 2023 NFC Championship', path: 'data/49ers-Lions.mp4' }
];

const API_URL = 'http://localhost:8000';

function App() {
  const [selectedVideo, setSelectedVideo] = useState(VIDEOS[0].path);
  const [clips, setClips] = useState<ClipTimestamp[]>([]);
  const [currentClipIndex, setCurrentClipIndex] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [chatOpen, setChatOpen] = useState(false);

  const handleQuery = async (query: string) => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `${API_URL}/clips?q=${encodeURIComponent(query)}`
      );

      if (!response.ok) {
        throw new Error(`Search failed: ${response.statusText}`);
      }

      const data = await response.json();
      setClips(data.clips);
      setCurrentClipIndex(0);

      if (data.clips.length === 0) {
        setError('No clips found for your query');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed');
      setClips([]);
    } finally {
      setIsLoading(false);
    }
  };

  const videoUrl = `${API_URL}/${selectedVideo}`;

  return (
    <div className="app">
      <header className="header">
        <div className="logo">
          <span className="team-badge">SF</span>
          <h1>NFL Clip Coach</h1>
        </div>
      </header>

      <main className={`main ${chatOpen ? 'chat-open' : ''}`}>
        <QueryInput
          onSubmit={handleQuery}
          videos={VIDEOS}
          selectedVideo={selectedVideo}
          onVideoChange={setSelectedVideo}
          isLoading={isLoading}
        />

        {error && <div className="error-message">{error}</div>}

        <VideoPlayer
          videoSrc={videoUrl}
          clips={clips}
          currentClipIndex={currentClipIndex}
          onClipChange={setCurrentClipIndex}
        />

        {clips.length > 0 && (
          <div className="clip-list">
            <h3>Found {clips.length} clips</h3>
            <div className="clip-items">
              {clips.map((clip, index) => (
                <button
                  key={index}
                  className={`clip-item ${index === currentClipIndex ? 'active' : ''}`}
                  onClick={() => setCurrentClipIndex(index)}
                >
                  <span className="clip-number">#{index + 1}</span>
                  <span className="clip-time">
                    {Math.floor(clip.start_time / 60)}:{String(Math.floor(clip.start_time % 60)).padStart(2, '0')}
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}
      </main>

      <ChatPanel isOpen={chatOpen} onToggle={() => setChatOpen(!chatOpen)} />
    </div>
  );
}

export default App;
