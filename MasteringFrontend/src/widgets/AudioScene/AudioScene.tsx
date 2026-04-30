import type { CSSProperties } from "react";
import { Activity, CircleDot, Radio } from "lucide-react";
import {
  stemGainControlByName,
  type MasteringControls,
  type MixMode,
  type StemControlState,
} from "../../entities/mastering/model/controls";
import { stemVisuals } from "../../entities/track/model/stems";
import { stemNames, statusLabel, type StemName, type TrackRecord } from "../../entities/track/model/types";
import type { PlaybackSnapshot } from "../../features/liveStemMix/lib/StemMixer";
import { usePlaybackTelemetry } from "../../features/liveStemMix/model/usePlaybackTelemetry";

type Props = {
  controls: MasteringControls;
  fileName: string | null;
  mixMode: MixMode;
  mixerReady: boolean;
  playing: boolean;
  readPlaybackSnapshot: () => PlaybackSnapshot;
  stemState: StemControlState;
  track: TrackRecord | null;
};

export function AudioScene({
  controls,
  fileName,
  mixMode,
  mixerReady,
  playing,
  readPlaybackSnapshot,
  stemState,
  track,
}: Props) {
  const status = track?.status || "waiting";
  const statusText = statusLabel(status);
  const playbackSnapshot = usePlaybackTelemetry({
    enabled: mixerReady && playing,
    readSnapshot: readPlaybackSnapshot,
  });

  return (
    <section className={playing ? "panel audio-scene is-playing" : "panel audio-scene"}>
      <div className="audio-scene__head">
        <div>
          <p className="eyebrow">Audio scene</p>
          <h2>{fileName || "Трек не загружен"}</h2>
        </div>
        <div className="scene-status">
          {playing ? <Radio size={17} /> : <CircleDot size={17} />}
          <span>{playing ? "Идёт preview" : statusText}</span>
        </div>
      </div>

      <div className="wave-stage" aria-label="Обзор аудио">
        <div className="wave-grid">
          {Array.from({length: 40}, (_, index) => (
            <i
              key={index}
              style={{"--bar-height": `${barHeight(index, status)}%`} as CSSProperties}
            />
          ))}
        </div>
        <div
          className="playhead"
          style={{"--playhead-left": `${playheadProgress(playbackSnapshot)}%`} as CSSProperties}
        />
        <div className="wave-caption">
          <span>{mixerReady ? "Live preview готов" : "Preview появится после подготовки стемов"}</span>
          <strong>{mixMode === "full" ? "Creative" : "Safe"}</strong>
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

function StemLane({controls, level, muted, solo, stem}: StemLaneProps) {
  const visual = stemVisuals[stem];
  const gain = controls[stemGainControlByName[stem]];
  const normalized = Math.max(0, Math.min(100, ((gain + 60) / 72) * 100));
  const activity = Math.round(level * 100);

  return (
    <div
      className={muted ? "scene-lane muted" : solo ? "scene-lane solo" : "scene-lane"}
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
        <i />
      </div>
      <Activity size={16} />
    </div>
  );
}

function barHeight(index: number, status: TrackRecord["status"] | "waiting"): number {
  if (status === "waiting" || status === "uploaded") {
    return 12 + (index % 4) * 5;
  }
  return 18 + Math.abs(Math.sin(index * 0.55) * 58) + (index % 5) * 3;
}

function playheadProgress(snapshot: PlaybackSnapshot): number {
  if (snapshot.duration <= 0) {
    return 0;
  }
  return Math.max(0, Math.min(100, (snapshot.position / snapshot.duration) * 100));
}
