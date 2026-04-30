import { Download, Loader2, Pause, Play, RotateCcw, UploadCloud } from "lucide-react";
import type { TrackRecord } from "../../entities/track/model/types";
import { assetUrl } from "../../shared/api/http";

type Props = {
  busy: boolean;
  canPreview: boolean;
  message: string;
  playing: boolean;
  track: TrackRecord | null;
  onUpload: (file: File | null) => void;
  onTogglePlayback: () => void;
  onResetPlayback: () => void;
};

export function UploadPanel({
  busy,
  canPreview,
  message,
  playing,
  track,
  onUpload,
  onTogglePlayback,
  onResetPlayback,
}: Props) {
  return (
    <div className="panel upload">
      <label className="dropzone">
        <UploadCloud size={34} />
        <span>Загрузить трек</span>
        <small>WAV/MP3/AIFF, для MVP лучше короткие демо</small>
        <input
          type="file"
          accept="audio/*"
          disabled={busy}
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
          Reset
        </button>
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
    </div>
  );
}
