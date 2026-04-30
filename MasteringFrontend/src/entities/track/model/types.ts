export type TrackStatus =
  | "uploaded"
  | "separating"
  | "ready_to_mix"
  | "rendering"
  | "done"
  | "failed";

export type StemName = "vocals" | "drums" | "bass" | "other";

export type TrackRecord = {
  track_id: string;
  status: TrackStatus;
  original_path: string;
  work_dir: string;
  model: string;
  stems_dir: string | null;
  output_path: string | null;
  report_path: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  urls: {
    original: string;
    stems: Partial<Record<StemName, string>>;
    download: string | null;
  };
};

export const stemNames: StemName[] = ["vocals", "drums", "bass", "other"];

export function isMixReady(status: TrackStatus): boolean {
  return status === "ready_to_mix" || status === "done";
}

export function isProcessing(status: TrackStatus): boolean {
  return status === "uploaded" || status === "separating" || status === "rendering";
}
