import type { CSSProperties } from "react";
import { Activity, CircleDot, Pause, Play, Radio, RotateCcw } from "lucide-react";
import {
  stemGainControlByName,
  type MasteringControls,
  type MixMode,
  type StemControlState,
} from "../../entities/mastering/model/controls";
import { stemVisuals } from "../../entities/track/model/stems";
import { stemNames, statusLabel, type StemName, type TrackRecord } from "../../entities/track/model/types";
import type { PlaybackSnapshot, PlaybackSource } from "../../features/liveStemMix/lib/StemMixer";
import { usePlaybackTelemetry } from "../../features/liveStemMix/model/usePlaybackTelemetry";

type Props = {
  controls: MasteringControls;
  fileName: string | null;
  mixMode: MixMode;
  mixerReady: boolean;
  playbackRevision: number;
  playbackSource: PlaybackSource;
  playing: boolean;
  readPlaybackSnapshot: () => PlaybackSnapshot;
  stemState: StemControlState;
  track: TrackRecord | null;
  onPlaybackSourceChange: (source: PlaybackSource) => void;
  onResetPlayback: () => void;
  onSeek: (position: number) => void;
  onTogglePlayback: () => void;
};

export function AudioScene({
  controls,
  fileName,
  mixMode,
  mixerReady,
  playbackRevision,
  playbackSource,
  playing,
  readPlaybackSnapshot,
  stemState,
  track,
  onPlaybackSourceChange,
  onResetPlayback,
  onSeek,
  onTogglePlayback,
}: Props) {
  const status = track?.status || "waiting";
  const statusText = statusLabel(status);
  const playbackSnapshot = usePlaybackTelemetry({
    enabled: mixerReady && playing,
    readSnapshot: readPlaybackSnapshot,
    refreshKey: playbackRevision,
  });
  const bars = visualBars(playbackSnapshot, status);
  const currentTime = formatTime(playbackSnapshot.position);
  const duration = formatTime(playbackSnapshot.duration);
  const sourceLabel = playbackSource === "original" ? "Оригинал" : "Stem-preview";

  return (
    <section className={playing ? "panel audio-scene is-playing" : "panel audio-scene"}>
      <div className="audio-scene__head">
        <div>
          <p className="eyebrow">Audio scene</p>
          <h2>{fileName || "Трек не загружен"}</h2>
        </div>
        <div className="scene-status">
          {playing ? <Radio size={17} /> : <CircleDot size={17} />}
          <span>{playing ? "Идет preview" : statusText}</span>
        </div>
      </div>

      <div
        className="playback-console"
        style={{ "--master-level": playbackSnapshot.masterLevel.toFixed(3) } as CSSProperties}
      >
        <div className="playback-console__top">
          <div className="playback-console__title">
            <span>{sourceLabel}</span>
            <strong>
              {currentTime} / {duration}
            </strong>
          </div>
          <div className="source-switch" aria-label="Источник прослушивания">
            <button
              className={playbackSource === "original" ? "active" : ""}
              disabled={!mixerReady}
              onClick={() => onPlaybackSourceChange("original")}
            >
              Оригинал
            </button>
            <button
              className={playbackSource === "mix" ? "active" : ""}
              disabled={!mixerReady}
              onClick={() => onPlaybackSourceChange("mix")}
            >
              Preview
            </button>
          </div>
        </div>

        <div className="playback-console__body">
          <div className="scene-transport">
            <button className="transport-main" onClick={onTogglePlayback} disabled={!mixerReady}>
              {playing ? <Pause size={20} /> : <Play size={20} />}
              {playing ? "Pause" : "Play"}
            </button>
            <button className="transport-reset" onClick={onResetPlayback} disabled={!mixerReady}>
              <RotateCcw size={18} />
            </button>
          </div>

          <div className="wave-stage" aria-label="Обзор аудио">
            <div className="wave-grid">
              {bars.map((bar, index) => (
                <i
                  key={index}
                  style={
                    {
                      "--bar-energy": bar.toFixed(3),
                      "--bar-height": `${Math.round(8 + bar * 86)}%`,
                    } as CSSProperties
                  }
                />
              ))}
            </div>
            <div
              className="playhead"
              style={{ "--playhead-left": `${playheadProgress(playbackSnapshot)}%` } as CSSProperties}
            />
            <input
              aria-label="Позиция воспроизведения"
              className="timeline"
              disabled={!mixerReady || playbackSnapshot.duration <= 0}
              max={Math.max(playbackSnapshot.duration, 0)}
              min={0}
              step={0.05}
              type="range"
              value={Math.min(playbackSnapshot.position, playbackSnapshot.duration || 0)}
              onChange={(event) => onSeek(Number(event.target.value))}
            />
          </div>
        </div>

        <div className="wave-caption">
          <span>{mixerReady ? `${sourceLabel} готов` : "Preview появится после подготовки стемов"}</span>
          <div className="wave-meta">
            <strong>{mixMode === "full" ? "Creative" : "Safe"}</strong>
          </div>
        </div>
      </div>

      <div className="scene-lanes">
        {stemNames.map((stem) => (
          <StemLane
            controls={controls}
            key={stem}
            level={playbackSnapshot.stemLevels[stem]}
            muted={stemState[stem].muted}
            solo={stemState[stem].solo}
            stem={stem}
          />
        ))}
      </div>
    </section>
  );
}

type StemLaneProps = {
  controls: MasteringControls;
  level: number;
  muted: boolean;
  solo: boolean;
  stem: StemName;
};

function StemLane({ controls, level, muted, solo, stem }: StemLaneProps) {
  const visual = stemVisuals[stem];
  const gain = controls[stemGainControlByName[stem]];
  const normalized = Math.max(0, Math.min(100, ((gain + 60) / 72) * 100));
  const activity = Math.round(level * 100);
  const hasSignal = level > 0.035;
  const className = [
    "scene-lane",
    hasSignal ? "live" : "",
    muted ? "muted" : "",
    solo ? "solo" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div
      className={className}
      style={
        {
          "--lane-activity": `${activity}%`,
          "--lane-level": `${normalized}%`,
          "--stem-accent": visual.accent,
        } as CSSProperties
      }
    >
      <div className="scene-lane__label">
        <span>{visual.label}</span>
        <small>{solo ? "Solo" : muted ? "Mute" : `${gain.toFixed(1)} dB`}</small>
      </div>
      <div className="scene-lane__rail">
        <i className="scene-lane__gain" />
        <b className="scene-lane__activity" />
      </div>
      <div className="scene-lane__meter" aria-label={`Activity ${activity}%`}>
        <Activity size={16} />
        <span>{hasSignal ? "Сигнал" : "Тихо"}</span>
      </div>
    </div>
  );
}

function visualBars(
  snapshot: PlaybackSnapshot,
  status: TrackRecord["status"] | "waiting",
): number[] {
  if (snapshot.spectrumBands.some((level) => level > 0.01)) {
    return snapshot.spectrumBands.map((level, index) => {
      const lift = snapshot.masterLevel * 0.32;
      const movement = Math.sin(snapshot.position * 7.5 + index * 0.62) * 0.08;
      return clamp(level * 0.94 + lift + movement, 0.05, 1);
    });
  }

  return Array.from({ length: 32 }, (_, index) => idleBar(index, status));
}

function idleBar(index: number, status: TrackRecord["status"] | "waiting"): number {
  if (status === "waiting" || status === "uploaded") {
    return 0.12 + (index % 4) * 0.045;
  }
  return clamp(0.16 + Math.abs(Math.sin(index * 0.55) * 0.48) + (index % 5) * 0.025, 0.1, 0.82);
}

function playheadProgress(snapshot: PlaybackSnapshot): number {
  if (snapshot.duration <= 0) {
    return 0;
  }
  return Math.max(0, Math.min(100, (snapshot.position / snapshot.duration) * 100));
}

function formatTime(value: number): string {
  if (!Number.isFinite(value) || value <= 0) {
    return "0:00";
  }

  const minutes = Math.floor(value / 60);
  const seconds = Math.floor(value % 60);
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}
