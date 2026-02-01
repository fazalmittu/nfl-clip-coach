import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import type { ClipTimestamp, ChatMessage } from '../types';

function formatClipTime(seconds: number): string {
  const hrs = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  if (hrs > 0) {
    return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function formatDown(down?: number, ydstogo?: number): string | null {
  if (!down) return null;
  const ordinal = ['1st', '2nd', '3rd', '4th'][down - 1] || `${down}th`;
  return ydstogo ? `${ordinal} & ${ydstogo}` : ordinal;
}

interface ChatPanelProps {
  messages: ChatMessage[];
  onSend: (message: string) => void;
  onFindClips: (query: string) => void;
  onDismissSuggestClips: (messageIndex: number) => void;
  isLoading: boolean;
  clips: ClipTimestamp[];
  currentClipIndex: number;
  onClipChange: (index: number, sourceClips?: ClipTimestamp[]) => void;
}

export function ChatPanel({
  messages,
  onSend,
  onFindClips,
  onDismissSuggestClips,
  isLoading,
  clips,
  currentClipIndex,
  onClipChange,
}: ChatPanelProps) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, clips]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    onSend(input.trim());
    setInput('');
  };

  const suggested = [
    'Summarize the game',
    'Find touchdown plays',
    'Key moments in Q4',
    'Big runs by running backs',
    '49ers scoring drives',
    'Best plays of the game',
  ];

  return (
    <div className="w-[380px] border-l border-white/[0.06] flex flex-col shrink-0 relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-b from-neutral-950 via-neutral-950/95 to-neutral-950/90 pointer-events-none" aria-hidden />
      <div className="flex flex-col flex-1 min-h-0 relative z-0">
        {/* Header */}
        <div className="px-4 py-3 border-b border-white/[0.06] shrink-0">
          <span className="text-sm font-medium text-neutral-400">Your AI Assistant</span>
        </div>

        <div className="flex-1 overflow-y-auto flex flex-col min-h-0 chat-panel-scroll">
          {messages.length === 0 && clips.length === 0 ? (
            <div className="px-4 pt-6 pb-4">
              <p className="text-sm text-neutral-400 mb-4">Ask about the game or search for plays in the video.</p>
              <p className="text-[11px] font-medium text-neutral-500 uppercase tracking-wider mb-3">Try asking</p>
              <div className="flex flex-wrap gap-2">
                {suggested.map((text) => (
                  <button
                    key={text}
                    type="button"
                    onClick={() => onSend(text)}
                    disabled={isLoading}
                    className="px-3 py-2 rounded-xl text-left text-xs text-amber-200/90 bg-amber-500/10 border border-amber-500/20 hover:bg-amber-500/20 hover:border-amber-500/30 hover:text-amber-100 transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {text}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="px-4 py-4 space-y-4">
              {messages.map((msg, i) => (
                <div key={i} className="space-y-2">
                  <div className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[88%] text-[13px] leading-relaxed ${
                      msg.role === 'user'
                        ? 'bg-white/[0.10] text-neutral-100 px-3.5 py-2 rounded-2xl rounded-br-md border border-white/[0.12]'
                        : 'text-neutral-400 px-3.5 py-2 rounded-2xl rounded-bl-md bg-white/[0.04] border border-white/[0.06]'
                    }`}>
                      {msg.role === 'assistant' ? (
                        <ReactMarkdown
                          components={{
                            p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                            strong: ({ children }) => <strong className="text-neutral-200 font-semibold">{children}</strong>,
                            em: ({ children }) => <em className="text-neutral-300">{children}</em>,
                            ul: ({ children }) => <ul className="list-disc list-inside mb-2 last:mb-0 space-y-0.5">{children}</ul>,
                            ol: ({ children }) => <ol className="list-decimal list-inside mb-2 last:mb-0 space-y-0.5">{children}</ol>,
                            li: ({ children }) => <li className="text-neutral-400">{children}</li>,
                            h1: ({ children }) => <h1 className="text-sm font-semibold text-neutral-200 mb-1">{children}</h1>,
                            h2: ({ children }) => <h2 className="text-sm font-semibold text-neutral-200 mb-1">{children}</h2>,
                            h3: ({ children }) => <h3 className="text-[13px] font-semibold text-neutral-300 mb-1">{children}</h3>,
                            code: ({ children }) => <code className="text-amber-400/90 bg-amber-500/10 px-1 py-0.5 rounded text-[12px]">{children}</code>,
                            hr: () => <hr className="border-white/[0.06] my-2" />,
                          }}
                        >
                          {msg.content}
                        </ReactMarkdown>
                      ) : (
                        msg.content
                      )}
                    </div>
                  </div>
                  {/* "Find clips" action card */}
                  {msg.role === 'assistant' && msg.suggestClips && msg.pendingClipQuery && (
                    <div className="flex justify-start">
                      <div className="max-w-[88%] rounded-xl border border-amber-500/25 bg-amber-500/5 px-4 py-3 shadow-sm">
                        <p className="text-xs text-amber-200/90 mb-3">
                          I can find video clips for this. Jump to matching plays in the game.
                        </p>
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => onFindClips(msg.pendingClipQuery!)}
                            disabled={isLoading}
                            className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-amber-500/20 text-amber-400 text-xs font-medium border border-amber-500/30 hover:bg-amber-500/25 hover:border-amber-500/40 transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" d="m15.75 10.5 4.72-4.72a.75.75 0 0 1 1.28.53v11.38a.75.75 0 0 1-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 0 0 2.25-2.25v-9a2.25 2.25 0 0 0-2.25-2.25h-9A2.25 2.25 0 0 0 2.25 7.5v9a2.25 2.25 0 0 0 2.25 2.25Z" />
                            </svg>
                            Find clips
                          </button>
                          <button
                            type="button"
                            onClick={() => onDismissSuggestClips(i)}
                            className="px-3 py-2 rounded-lg text-xs text-amber-400/70 hover:text-amber-400 hover:bg-amber-500/10 transition-colors cursor-pointer"
                          >
                            Dismiss
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                  {/* Inline clips rendered with amber glass effect */}
                  {msg.clips && msg.clips.length > 0 && (
                    <div className="space-y-2 mt-1">
                      <div className="flex items-center gap-2 px-0.5">
                        <span className="text-[10px] font-semibold text-amber-400/90 uppercase tracking-wider">Clips</span>
                        <span className="text-[10px] bg-amber-500/25 text-amber-400 px-1.5 py-0.5 rounded-full font-medium border border-amber-500/30">{msg.clips.length}</span>
                      </div>
                      <div className="space-y-1.5">
                        {msg.clips.map((clip, ci) => {
                          const isActive = clips.length > 0 && clips[currentClipIndex]?.start_time === clip.start_time;
                          const downStr = formatDown(clip.down, clip.ydstogo);
                          return (
                            <button
                              key={ci}
                              type="button"
                              onClick={() => onClipChange(ci, msg.clips)}
                              className={`w-full text-left rounded-xl px-3 py-2.5 transition-all border cursor-pointer backdrop-blur-sm ${
                                isActive
                                  ? 'bg-amber-500/20 border-amber-500/40 ring-1 ring-amber-500/25 shadow-[0_0_12px_rgba(251,191,36,0.1)]'
                                  : 'bg-amber-500/[0.06] border-amber-500/15 hover:bg-amber-500/[0.12] hover:border-amber-500/25'
                              }`}
                            >
                              <div className="flex items-center gap-2 mb-1">
                                <span className={`flex items-center justify-center w-5 h-5 rounded text-[10px] font-bold shrink-0 ${
                                  isActive ? 'bg-amber-500/25 text-amber-400' : 'bg-white/[0.08] text-neutral-500'
                                }`}>
                                  {ci + 1}
                                </span>
                                <span className={`text-[11px] font-mono tabular-nums ${isActive ? 'text-amber-400' : 'text-neutral-500'}`}>
                                  {formatClipTime(clip.start_time)}
                                </span>
                                {clip.quarter && clip.game_time && (
                                  <span className="text-[10px] text-neutral-600">Q{clip.quarter} {clip.game_time}</span>
                                )}
                                {clip.is_touchdown && <span className="text-[10px] text-amber-400 font-semibold">TD</span>}
                                {clip.is_interception && <span className="text-[10px] text-red-400 font-semibold">INT</span>}
                              </div>
                              {clip.description && (
                                <p className={`text-[12px] leading-snug line-clamp-2 ${isActive ? 'text-amber-100/90' : 'text-amber-200/70'}`}>
                                  {clip.description}
                                </p>
                              )}
                              <div className="flex flex-wrap gap-x-2 gap-y-0.5 mt-1.5 text-[10px]">
                                {downStr && <span className="text-neutral-600">{downStr}</span>}
                                {(clip.passer || clip.rusher) && (
                                  <span className="text-neutral-500">
                                    {clip.passer || clip.rusher}
                                    {clip.receiver ? ` → ${clip.receiver}` : ''}
                                  </span>
                                )}
                                {clip.yards_gained != null && (
                                  <span className={clip.yards_gained > 0 ? 'text-emerald-500/80' : 'text-red-400/80'}>
                                    {clip.yards_gained > 0 ? '+' : ''}{clip.yards_gained} yds
                                  </span>
                                )}
                              </div>
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              ))}

              {isLoading && (
                <div className="flex justify-start">
                  <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/[0.04] border border-white/[0.06]">
                    <svg className="animate-spin h-4 w-4 text-neutral-500" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    <span className="text-xs text-neutral-500">Thinking...</span>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        <form onSubmit={handleSubmit} className="p-3 border-t border-white/[0.06]">
          <div className={`flex items-center gap-2 rounded-xl px-3.5 py-2 transition-all ${
            isLoading
              ? 'bg-white/[0.02] border border-white/[0.04] cursor-not-allowed'
              : 'bg-white/[0.04] border border-white/[0.08] focus-within:ring-1 focus-within:ring-amber-500/20 focus-within:border-amber-500/15'
          }`}>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about the game or search for plays..."
              disabled={isLoading}
              className="flex-1 bg-transparent text-sm text-white placeholder-neutral-600 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              className="p-1.5 rounded-lg text-amber-400/80 hover:text-amber-400 hover:bg-amber-500/15 disabled:opacity-20 disabled:cursor-not-allowed transition-colors cursor-pointer"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 10.5 12 3m0 0 7.5 7.5M12 3v18" />
              </svg>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
