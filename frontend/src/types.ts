export interface VideoOption {
  name: string;
  path: string;
}

export interface ClipTimestamp {
  start_time: number;
  end_time?: number;
  video_path: string;
  description?: string;
  play_type?: string;
  down?: number;
  ydstogo?: number;
  yards_gained?: number;
  posteam?: string;
  defteam?: string;
  quarter?: number;
  game_time?: string;
  posteam_score?: number;
  defteam_score?: number;
  passer?: string;
  rusher?: string;
  receiver?: string;
  is_touchdown: boolean;
  is_interception: boolean;
  is_sack: boolean;
  is_fumble: boolean;
  yardline_100?: number;
  wpa?: number;
}

export type AnalyzeMode = 'video' | 'chat';

export interface AnalyzeRequest {
  mode: AnalyzeMode;
  query: string;
  session_id?: string;
  play_buffer_seconds?: number;
  game_name?: string;
}

export interface AnalyzeResponse {
  mode: AnalyzeMode;
  clips?: ClipTimestamp[];
  response?: string;
  suggest_clips?: boolean;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  suggestClips?: boolean;
  pendingClipQuery?: string;
}
