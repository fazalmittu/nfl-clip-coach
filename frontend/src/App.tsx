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
      setClips(data.clips || []);
      setCurrentClipIndex(0);

      if (data.clips && data.clips.length > 0) {
        setChatMessages(prev => [
          ...prev,
          { role: 'assistant', content: `Found ${data.clips!.length} clip${data.clips!.length === 1 ? '' : 's'}. Click a clip to jump to it.` },
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
      <header className="flex items-center px-6 py-3 border-b border-white/[0.06] bg-neutral-950/80 backdrop-blur-xl shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-500 to-amber-700 flex items-center justify-center">
            <svg className="w-4 h-4 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
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
            <div className="mx-5 mt-3 px-3.5 py-2.5 bg-red-500/[0.08] border border-red-500/15 rounded-xl text-red-400/90 text-xs shrink-0">
              {error}
            </div>
          )}

          {/* Toolbar above video: Game + Duration only */}
          <div className="shrink-0 mx-5 mt-4 mb-3 px-4 py-3 rounded-xl bg-white/[0.03] border border-white/[0.06] flex flex-wrap items-center gap-6">
            <div className="flex items-center gap-3">
              <span className="text-[11px] font-semibold text-neutral-500 uppercase tracking-wider">Game</span>
              <select
                value={selectedVideo}
                onChange={(e) => setSelectedVideo(e.target.value)}
                className="bg-white/[0.06] border border-white/[0.08] rounded-lg px-3 py-2 text-sm text-neutral-200 focus:outline-none focus:ring-1 focus:ring-amber-500/30 cursor-pointer min-w-[220px]"
              >
                {VIDEOS.map((v) => (
                  <option key={v.path} value={v.path} className="bg-neutral-900">
                    {v.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="h-4 w-px bg-white/[0.08]" aria-hidden />
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-semibold text-neutral-500 uppercase tracking-wider">Duration</span>
              <span className="text-sm font-mono text-neutral-400 tabular-nums">{formatDuration(videoDuration)}</span>
            </div>
          </div>

          <div className="flex-1 min-h-0 px-5 pb-3 flex flex-col">
            <VideoPlayer
              videoSrc={videoUrl}
              clips={clips}
              currentClipIndex={currentClipIndex}
              onClipChange={setCurrentClipIndex}
              playbackSpeed={playbackSpeed}
              videoFit={videoFit}
              onDurationChange={setVideoDuration}
            />
          </div>

          {/* Bottom bar: Speed + Fit + clip details or usage tips (no repeat of chatbot) */}
          <div className="shrink-0 mx-5 mb-5 px-4 py-3 rounded-xl bg-white/[0.03] border border-white/[0.06] flex flex-wrap items-center gap-4 text-sm">
            {/* Speed & Fit — moved from top */}
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-semibold text-neutral-500 uppercase tracking-wider">Speed</span>
              <div className="flex rounded-lg bg-white/[0.04] border border-white/[0.08] p-0.5">
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
            <div className="h-4 w-px bg-white/[0.08]" aria-hidden />
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-semibold text-neutral-500 uppercase tracking-wider">Fit</span>
              <div className="flex rounded-lg bg-white/[0.04] border border-white/[0.08] p-0.5">
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
            <div className="h-4 w-px bg-white/[0.08]" aria-hidden />

            {/* Clip details or usage tips — not repeating chatbot suggestions */}
            {currentClip ? (
              <>
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
              </>
            ) : clips.length > 0 ? (
              <span className="text-neutral-400">{clips.length} clip{clips.length === 1 ? '' : 's'} · pick one in the assistant</span>
            ) : (
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-neutral-500">
                <span>Using the assistant:</span>
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
          onClipChange={setCurrentClipIndex}
        />
      </div>
    </div>
  );
}

export default App;
