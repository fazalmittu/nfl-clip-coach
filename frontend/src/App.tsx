import { useState } from 'react';
import { QueryInput } from './components/QueryInput';
import { VideoPlayer } from './components/VideoPlayer';
import type { ClipTimestamp, VideoOption, AnalyzeMode, AnalyzeResponse } from './types';
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
  const [mode, setMode] = useState<AnalyzeMode>('video');
  const [chatMessages, setChatMessages] = useState<{ role: 'user' | 'assistant'; content: string }[]>([]);
  const [sessionId] = useState(() => `session-${Date.now()}`);

  const handleQuery = async (query: string) => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_URL}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mode,
          query,
          session_id: sessionId,
        }),
      });

      if (!response.ok) {
        throw new Error(`Request failed: ${response.statusText}`);
      }

      const data: AnalyzeResponse = await response.json();

      if (mode === 'video') {
        setClips(data.clips || []);
        setCurrentClipIndex(0);
        if (!data.clips || data.clips.length === 0) {
          setError('No clips found for your query');
        }
      } else {
        // Chat mode
        setChatMessages(prev => [
          ...prev,
          { role: 'user', content: query },
          { role: 'assistant', content: data.response || 'No response' },
        ]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Request failed');
      if (mode === 'video') {
        setClips([]);
      }
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

      <main className="main">
        <QueryInput
          onSubmit={handleQuery}
          videos={VIDEOS}
          selectedVideo={selectedVideo}
          onVideoChange={setSelectedVideo}
          isLoading={isLoading}
          mode={mode}
          onModeChange={setMode}
        />

        {error && <div className="error-message">{error}</div>}

        {mode === 'video' ? (
          <>
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
          </>
        ) : (
          <div className="chat-messages-inline">
            {chatMessages.length === 0 ? (
              <div className="chat-empty">Ask a question about the game...</div>
            ) : (
              chatMessages.map((msg, i) => (
                <div key={i} className={`chat-message ${msg.role}`}>
                  <strong>{msg.role === 'user' ? 'You' : 'Coach'}:</strong> {msg.content}
                </div>
              ))
            )}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
