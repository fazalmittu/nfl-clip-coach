import { useState } from 'react';

interface ChatPanelProps {
  isOpen: boolean;
  onToggle: () => void;
}

export function ChatPanel({ isOpen, onToggle }: ChatPanelProps) {
  const [messages] = useState<{ role: 'user' | 'assistant'; content: string }[]>([]);

  return (
    <>
      {/* Toggle button */}
      <button className="chat-toggle" onClick={onToggle}>
        {isOpen ? '→' : '←'} Chat
      </button>

      {/* Chat panel */}
      <div className={`chat-panel ${isOpen ? 'open' : ''}`}>
        <div className="chat-header">
          <h3>Game Analysis</h3>
        </div>

        <div className="chat-messages">
          {messages.length === 0 ? (
            <div className="chat-empty">
              Ask questions about the game...
            </div>
          ) : (
            messages.map((msg, i) => (
              <div key={i} className={`chat-message ${msg.role}`}>
                {msg.content}
              </div>
            ))
          )}
        </div>

        <div className="chat-input-container">
          <input
            type="text"
            placeholder="Coming soon..."
            className="chat-input"
            disabled
          />
          <button className="chat-send" disabled>
            Send
          </button>
        </div>
      </div>
    </>
  );
}
