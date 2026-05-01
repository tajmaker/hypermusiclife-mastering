import { Loader2, RotateCcw, UploadCloud } from "lucide-react";
import { statusLabel, type TrackRecord } from "../../entities/track/model/types";
import type { SessionProgress } from "../../pages/mastering/model/useMasteringSession";

type Props = {
  busy: boolean;
  canPreview: boolean;
  fileName: string | null;
  message: string;
  playing: boolean;
  progress: SessionProgress;
  track: TrackRecord | null;
  uploadDisabled: boolean;
  onStartOver: () => void;
  onUpload: (file: File | null) => void;
  onResetControls: () => void;
};

export function UploadPanel({
  busy,
  canPreview,
  fileName,
  message,
  playing,
  progress,
  track,
  uploadDisabled,
  onStartOver,
  onUpload,
  onResetControls,
}: Props) {
  const currentStatus = track?.status || "waiting";
  const label = statusLabel(currentStatus);
  const showLoader = progress.tone === "active" || busy;

  return (
    <div className="panel upload">
      <label className={uploadDisabled ? "dropzone disabled" : "dropzone"}>
        <UploadCloud size={34} />
        <span>Загрузить трек</span>
        <small>WAV/MP3/AIFF, для MVP лучше короткие демо</small>
        <input
          type="file"
          accept="audio/*"
          disabled={uploadDisabled}
          onChange={(event) => onUpload(event.target.files?.[0] || null)}
        />
      </label>

      <div className="track-summary">
        <span>{fileName || "Файл не выбран"}</span>
        <strong>{label}</strong>
      </div>

      <div className={`progress-card ${progress.tone}`}>
        <div className="progress-head">
          <span>{progress.title}</span>
          {showLoader ? <Loader2 className="spin" size={16} /> : <strong>{progress.progress}%</strong>}
        </div>
        <div className={progress.indeterminate ? "progress indeterminate" : "progress"}>
          <i style={{ width: `${progress.progress}%` }} />
        </div>
        <small>{progress.detail}</small>
      </div>

      <div className="message">
        {showLoader && <Loader2 className="spin" size={16} />}
        <span>{track?.error_message || message}</span>
      </div>

      {track && (
        <div className="stacked-actions">
          <button className="secondary-action" onClick={onResetControls} disabled={busy || playing || !canPreview}>
            <RotateCcw size={18} />
            Сбросить ручки
          </button>
          <button className="secondary-action" onClick={onStartOver} disabled={busy}>
            Начать заново
          </button>
        </div>
      )}
    </div>
  );
}
