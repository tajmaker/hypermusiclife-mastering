export type TrackStatus =
  | "uploaded"
  | "separating"
  | "ready_to_mix"
  | "rendering"
  | "done"
  | "failed";

export type StemName = "vocals" | "drums" | "bass" | "other";

export type JobStage =
  | "upload_saved"
  | "queued_separation"
  | "separating"
  | "writing_stems"
  | "preview_ready"
  | "queued_render"
  | "rendering_master"
  | "master_ready"
  | "failed";

export type JobEvent = {
  stage: JobStage;
  message: string;
  progress: number | null;
  created_at: string;
};

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
  stage?: JobStage | null;
  progress?: number | null;
  progress_detail?: string | null;
  events?: JobEvent[];
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

export function statusLabel(status: TrackStatus | "waiting"): string {
  const labels: Record<TrackStatus | "waiting", string> = {
    waiting: "Ожидание",
    uploaded: "Файл загружен",
    separating: "Подготовка стемов",
    ready_to_mix: "Готово к миксу",
    rendering: "Подготовка мастера",
    done: "Готово",
    failed: "Ошибка",
  };
  return labels[status];
}

export function statusProgress(status: TrackStatus | "waiting"): number {
  const progress: Record<TrackStatus | "waiting", number> = {
    waiting: 0,
    uploaded: 10,
    separating: 45,
    ready_to_mix: 70,
    rendering: 88,
    done: 100,
    failed: 100,
  };
  return progress[status];
}
