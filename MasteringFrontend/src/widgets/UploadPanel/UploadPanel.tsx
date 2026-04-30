import { Download, ExternalLink, Loader2, Pause, Play, RotateCcw, UploadCloud } from "lucide-react";
import { statusLabel, statusProgress, type TrackRecord } from "../../entities/track/model/types";
import { assetUrl } from "../../shared/api/http";

type Props = {
  busy: boolean;
  canPreview: boolean;
  fileName: string | null;
  message: string;
  playing: boolean;
  track: TrackRecord | null;
  uploadDisabled: boolean;
  onStartOver: () => void;
  onUpload: (file: File | null) => void;
  onResetControls: () => void;
  onTogglePlayback: () => void;
  onResetPlayback: () => void;
};

export function UploadPanel({
  busy,
  canPreview,
  fileName,
  message,
  playing,
  track,
  uploadDisabled,
  onStartOver,
  onUpload,
  onResetControls,
  onTogglePlayback,
  onResetPlayback,
}: Props) {
  const currentStatus = track?.status || "waiting";
  const label = statusLabel(currentStatus);
  const progress = statusProgress(currentStatus);

  return (
    <div className="panel upload">
      <label className="dropzone">
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

      <div className="transport">
        <button onClick={onTogglePlayback} disabled={!canPreview}>
          {playing ? <Pause size={18} /> : <Play size={18} />}
          {playing ? "Pause" : "Play"}
        </button>
        <button onClick={onResetPlayback} disabled={!canPreview}>
          <RotateCcw size={18} />
          Сбросить
        </button>
      </div>

      {track && (
        <div className="ab-panel">
          <span>Оригинал</span>
          <a className="audio-link" href={assetUrl(track.urls.original)} rel="noreferrer" target="_blank">
            <ExternalLink size={16} />
            Открыть оригинал
          </a>
          <span>Текущий preview</span>
          <button onClick={onTogglePlayback} disabled={!canPreview}>
            {playing ? <Pause size={18} /> : <Play size={18} />}
            {playing ? "Пауза preview" : "Слушать preview"}
          </button>
        </div>
      )}

      <div className="track-summary">
        <span>{fileName || "Файл не выбран"}</span>
        <strong>{label}</strong>
      </div>

      <div className="progress-card">
        <div className="progress-head">
          <span>{label}</span>
          <strong>{progress}%</strong>
        </div>
        <div className={track?.status === "failed" ? "progress failed" : "progress"}>
          <i style={{width: `${progress}%`}} />
        </div>
        {track?.status === "separating" && (
          <small>Подготовка стемов на бесплатном CPU-сервере может занять несколько минут.</small>
        )}
      </div>

      <div className="message">
        {track?.status === "separating" && <Loader2 className="spin" size={16} />}
        <span>{track?.error_message || message}</span>
      </div>

      {track?.urls.download && (
        <a className="download" href={assetUrl(track.urls.download)}>
          <Download size={18} />
          Скачать мастер
        </a>
      )}

      {track && (
        <div className="stacked-actions">
          <button className="secondary-action" onClick={onResetControls} disabled={busy}>
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
