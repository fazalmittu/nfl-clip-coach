export interface VideoOption {
  name: string;
  path: string;
}

export interface ClipTimestamp {
  start_time: number;
  end_time: number;
  video_path: string;
  description?: string;
}

export type AnalyzeMode = 'video' | 'chat';

export interface AnalyzeRequest {
  mode: AnalyzeMode;
  query: string;
  session_id?: string;
}

export interface AnalyzeResponse {
  mode: AnalyzeMode;
  clips?: ClipTimestamp[];
  response?: string;
}
