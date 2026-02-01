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

export interface ClipResponse {
  clips: ClipTimestamp[];
}
