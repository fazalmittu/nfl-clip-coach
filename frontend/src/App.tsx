import { useState } from 'react';
import { VideoPlayer } from './components/VideoPlayer';
import { ChatPanel } from './components/ChatPanel';
import type { ClipTimestamp, VideoOption, AnalyzeResponse, ChatMessage } from './types';
import './App.css';

const VIDEOS: VideoOption[] = [
  { name: '49ers vs Lions - 2023 NFC Championship', path: 'data/49ers-Lions.mp4' }
];

const API_URL = 'http://localhost:8000';

const SPEED_OPTIONS = [0.5, 0.75, 1, 1.25, 1.5, 2];

function formatDuration(seconds: number): string {
  if (!seconds || !Number.isFinite(seconds)) return '—';
  const hrs = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  if (hrs > 0) {
    return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function App() {
  const [selectedVideo, setSelectedVideo] = useState(VIDEOS[0].path);
  const selectedVideoName = VIDEOS.find((v) => v.path === selectedVideo)?.name ?? selectedVideo;
  const [clips, setClips] = useState<ClipTimestamp[]>([]);
  const [currentClipIndex, setCurrentClipIndex] = useState(0);
  const [clipSeek, setClipSeek] = useState(0);
  const [videoDuration, setVideoDuration] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [sessionId] = useState(() => `session-${Date.now()}`);

  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const [videoFit, setVideoFit] = useState<'contain' | 'fill'>('contain');

  const handleSend = async (message: string) => {
    setChatMessages(prev => [...prev, { role: 'user', content: message }]);
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_URL}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mode: 'chat',
          query: message,
          session_id: sessionId,
          game_name: selectedVideoName,
        }),
      });

      if (!response.ok) throw new Error(`Request failed: ${response.statusText}`);

      const data: AnalyzeResponse = await response.json();
      setChatMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: data.response || 'No response',
          suggestClips: data.suggest_clips ?? false,
          pendingClipQuery: data.suggest_clips ? message : undefined,
        },
      ]);
    } catch (err) {
      setChatMessages(prev => [
        ...prev,
        { role: 'assistant', content: err instanceof Error ? err.message : 'Sorry, something went wrong.' },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFindClips = async (query: string) => {
    // Auto-dismiss all "Find clips" suggestion cards
    setChatMessages(prev =>
      prev.map(msg =>
        msg.suggestClips ? { ...msg, suggestClips: false, pendingClipQuery: undefined } : msg
      )
    );
    setIsLoading(true);
    setError(null);
    setClips([]);

    try {
      const response = await fetch(`${API_URL}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mode: 'video',
          query,
          session_id: sessionId,
          play_buffer_seconds: 15,
          game_name: selectedVideoName,
        }),
      });

      if (!response.ok) throw new Error(`Request failed: ${response.statusText}`);

      const data: AnalyzeResponse = await response.json();
      const foundClips = data.clips || [];
      setClips(foundClips);
      setCurrentClipIndex(0);

      if (foundClips.length > 0) {
        setChatMessages(prev => [
          ...prev,
          {
            role: 'assistant',
            content: `Found ${foundClips.length} clip${foundClips.length === 1 ? '' : 's'}. Click a clip to jump to it.`,
            clips: foundClips,
          },
        ]);
      } else {
        setChatMessages(prev => [
          ...prev,
          { role: 'assistant', content: 'No clips found for that query. Try describing a different play or moment.' },
        ]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Request failed');
      setChatMessages(prev => [
        ...prev,
        { role: 'assistant', content: 'Sorry, something went wrong finding clips.' },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClipChange = (index: number, sourceClips?: ClipTimestamp[]) => {
    if (sourceClips && sourceClips !== clips) {
      setClips(sourceClips);
    }
    setCurrentClipIndex(index);
    setClipSeek(prev => prev + 1);
  };

  const dismissSuggestClips = (index: number) => {
    setChatMessages(prev =>
      prev.map((msg, i) =>
        i === index && msg.role === 'assistant' && msg.suggestClips
          ? { ...msg, suggestClips: false, pendingClipQuery: undefined }
          : msg
      )
    );
  };

  const videoUrl = `${API_URL}/${selectedVideo}`;
  const currentClip = clips.length > 0 && currentClipIndex >= 0 ? clips[currentClipIndex] : null;

  return (
    <div className="h-screen bg-neutral-950 text-white flex flex-col overflow-hidden">
      {/* Navbar: logo top left (no glass), amber color */}
      <header className="flex items-center px-6 py-3 border-b border-white/6 bg-neutral-950/80 backdrop-blur-xl shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-amber-500/15 border border-amber-500/30 backdrop-blur-sm shadow-[0_0_12px_rgba(251,191,36,0.15)] flex items-center justify-center">
            <svg className="w-4 h-4 text-amber-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="m15.75 10.5 4.72-4.72a.75.75 0 0 1 1.28.53v11.38a.75.75 0 0 1-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 0 0 2.25-2.25v-9a2.25 2.25 0 0 0-2.25-2.25h-9A2.25 2.25 0 0 0 2.25 7.5v9a2.25 2.25 0 0 0 2.25 2.25Z" />
            </svg>
          </div>
          <span className="text-base font-semibold tracking-tight text-white">Clip Coach</span>
        </div>
      </header>

      {/* Main: left = toolbar + video + info strip, right = assistant */}
      <div className="flex flex-1 min-h-0">
        <div className="flex-1 flex flex-col overflow-hidden min-w-0">
          {error && (
            <div className="mx-5 mt-3 px-3.5 py-2.5 bg-red-500/8 border border-red-500/15 rounded-xl text-red-400/90 text-xs shrink-0">
              {error}
            </div>
          )}

          {/* Toolbar above video */}
          <div className="shrink-0 mx-5 mt-4 mb-3 px-5 py-3.5 rounded-2xl bg-white/3 border border-white/6 flex items-center justify-between backdrop-blur-sm">
            <div className="flex items-center">
              <select
                value={selectedVideo}
                onChange={(e) => setSelectedVideo(e.target.value)}
                className="bg-transparent text-sm font-medium text-neutral-200 focus:outline-none cursor-pointer appearance-none pr-5 hover:text-white transition-colors"
                style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' fill='none' viewBox='0 0 24 24' stroke='%23737373' stroke-width='2'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' d='m19.5 8.25-7.5 7.5-7.5-7.5'/%3E%3C/svg%3E")`, backgroundRepeat: 'no-repeat', backgroundPosition: 'right center' }}
              >
                {VIDEOS.map((v) => (
                  <option key={v.path} value={v.path} className="bg-neutral-900">
                    {v.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg bg-white/4 border border-white/6">
              <svg className="w-3.5 h-3.5 text-neutral-500" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
              </svg>
              <span className="text-sm font-mono text-neutral-300 tabular-nums">{formatDuration(videoDuration)}</span>
            </div>
          </div>

          <div className="flex-1 min-h-0 px-5 pb-3 flex flex-col">
            <VideoPlayer
              videoSrc={videoUrl}
              clips={clips}
              currentClipIndex={currentClipIndex}
              clipSeek={clipSeek}
              onClipChange={handleClipChange}
              playbackSpeed={playbackSpeed}
              videoFit={videoFit}
              onDurationChange={setVideoDuration}
            />
          </div>

          {/* Bottom bar: Speed left, Fit right, clip details centered below */}
          <div className="shrink-0 mx-5 mb-5 px-4 py-3 rounded-xl bg-white/3 border border-white/6 text-sm space-y-2.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-[11px] font-semibold text-neutral-500 uppercase tracking-wider">Speed</span>
                <div className="flex rounded-lg bg-white/4 border border-white/8 p-0.5">
                  {SPEED_OPTIONS.map((s) => (
                    <button
                      key={s}
                      type="button"
                      onClick={() => setPlaybackSpeed(s)}
                      className={`px-2.5 py-1.5 rounded-md text-xs font-mono transition-all cursor-pointer ${
                        playbackSpeed === s
                          ? 'bg-amber-500/25 text-amber-400 border border-amber-500/40 shadow-[0_0_12px_rgba(251,191,36,0.15)]'
                          : 'text-neutral-500 hover:text-neutral-400 border border-transparent'
                      }`}
                    >
                      {s}x
                    </button>
                  ))}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[11px] font-semibold text-neutral-500 uppercase tracking-wider">Fit</span>
                <div className="flex rounded-lg bg-white/4 border border-white/8 p-0.5">
                  <button
                    type="button"
                    onClick={() => setVideoFit('contain')}
                    className={`px-3 py-1.5 rounded-md text-xs transition-all cursor-pointer ${
                      videoFit === 'contain'
                        ? 'bg-amber-500/25 text-amber-400 border border-amber-500/40 shadow-[0_0_12px_rgba(251,191,36,0.15)]'
                        : 'text-neutral-500 hover:text-neutral-400 border border-transparent'
                    }`}
                  >
                    Fit
                  </button>
                  <button
                    type="button"
                    onClick={() => setVideoFit('fill')}
                    className={`px-3 py-1.5 rounded-md text-xs transition-all cursor-pointer ${
                      videoFit === 'fill'
                        ? 'bg-amber-500/25 text-amber-400 border border-amber-500/40 shadow-[0_0_12px_rgba(251,191,36,0.15)]'
                        : 'text-neutral-500 hover:text-neutral-400 border border-transparent'
                    }`}
                  >
                    Fill
                  </button>
                </div>
              </div>
            </div>

            {/* Clip details centered below, or usage tip */}
            {currentClip ? (
              <div className="flex flex-wrap items-center justify-center gap-x-3 gap-y-1 pt-3 mt-1 border-t border-white/6">
                <span className="text-amber-400/90 font-medium">Clip {currentClipIndex + 1} of {clips.length}</span>
                {currentClip.quarter != null && currentClip.game_time && (
                  <>
                    <span className="text-neutral-600">·</span>
                    <span className="text-neutral-400 font-mono">Q{currentClip.quarter} {currentClip.game_time}</span>
                  </>
                )}
                {currentClip.posteam_score != null && currentClip.defteam_score != null && (
                  <>
                    <span className="text-neutral-600">·</span>
                    <span className="text-neutral-400">{currentClip.posteam} {currentClip.posteam_score} – {currentClip.defteam} {currentClip.defteam_score}</span>
                  </>
                )}
                {(currentClip.down != null || currentClip.ydstogo != null) && (
                  <>
                    <span className="text-neutral-600">·</span>
                    <span className="text-neutral-400">
                      {currentClip.down != null && (['1st', '2nd', '3rd', '4th'][currentClip.down - 1] ?? `${currentClip.down}th`)}
                      {currentClip.ydstogo != null && ` & ${currentClip.ydstogo}`}
                    </span>
                  </>
                )}
                {(currentClip.passer || currentClip.rusher) && (
                  <>
                    <span className="text-neutral-600">·</span>
                    <span className="text-neutral-300">
                      {currentClip.passer || currentClip.rusher}
                      {currentClip.receiver ? ` → ${currentClip.receiver}` : ''}
                    </span>
                  </>
                )}
                {currentClip.yards_gained != null && (
                  <>
                    <span className="text-neutral-600">·</span>
                    <span className={currentClip.yards_gained > 0 ? 'text-emerald-400' : 'text-red-400/90'}>
                      {currentClip.yards_gained > 0 ? '+' : ''}{currentClip.yards_gained} yds
                    </span>
                  </>
                )}
              </div>
            ) : clips.length > 0 ? (
              <div className="flex justify-center pt-3 mt-1 border-t border-white/6">
                <span className="text-neutral-400">{clips.length} clip{clips.length === 1 ? '' : 's'} · pick one in the assistant</span>
              </div>
            ) : (
              <div className="flex justify-center pt-3 mt-1 border-t border-white/6 text-xs text-neutral-500">
                <span>Ask questions or describe a play → get answers; when clips are suggested, tap <strong className="text-amber-400/80 font-medium">Find clips</strong> to jump to video.</span>
              </div>
            )}
          </div>
        </div>

        <ChatPanel
          messages={chatMessages}
          onSend={handleSend}
          onFindClips={handleFindClips}
          onDismissSuggestClips={dismissSuggestClips}
          isLoading={isLoading}
          clips={clips}
          currentClipIndex={currentClipIndex}
          onClipChange={handleClipChange}
        />
      </div>
    </div>
  );
}

export default App;
