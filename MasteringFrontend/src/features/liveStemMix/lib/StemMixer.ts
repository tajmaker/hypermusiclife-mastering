import type { MasteringControls } from "../../../entities/mastering/model/controls";
import { assetUrl } from "../../../shared/api/http";
import { stemNames, type StemName, type TrackRecord } from "../../../entities/track/model/types";

type StemChain = {
  stem: StemName;
  source: AudioBufferSourceNode;
  gain: GainNode;
  filter: BiquadFilterNode;
};

export class StemMixer {
  private context: AudioContext | null = null;
  private buffers = new Map<StemName, AudioBuffer>();
  private chains: StemChain[] = [];
  private startedAt = 0;
  private pausedAt = 0;
  private playing = false;

  async load(track: TrackRecord): Promise<void> {
    this.stop();
    this.context = new AudioContext();
    this.buffers.clear();

    await Promise.all(
      stemNames.map(async (stem) => {
        const url = track.urls.stems[stem];
        if (!url) {
          return;
        }
        const response = await fetch(assetUrl(url));
        const bytes = await response.arrayBuffer();
        const buffer = await this.context!.decodeAudioData(bytes);
        this.buffers.set(stem, buffer);
      }),
    );
  }

  hasAudio(): boolean {
    return this.buffers.size > 0;
  }

  play(controls: MasteringControls): void {
    if (!this.context || !this.hasAudio() || this.playing) {
      return;
    }

    const offset = this.pausedAt;
    this.chains = Array.from(this.buffers.entries()).map(([stem, buffer]) => {
      const source = this.context!.createBufferSource();
      const gain = this.context!.createGain();
      const filter = this.context!.createBiquadFilter();

      source.buffer = buffer;
      filter.type = "highshelf";
      filter.frequency.value = stem === "other" ? 3200 : 4200;
      source.connect(filter).connect(gain).connect(this.context!.destination);
      source.start(0, offset);
      source.onended = () => {
        if (this.playing) {
          this.stop();
        }
      };

      return {stem, source, gain, filter};
    });

    this.startedAt = this.context.currentTime - offset;
    this.playing = true;
    this.applyControls(controls);
  }

  pause(): void {
    if (!this.context || !this.playing) {
      return;
    }
    this.pausedAt = Math.max(0, this.context.currentTime - this.startedAt);
    this.stopSources();
    this.playing = false;
  }

  stop(): void {
    this.pausedAt = 0;
    this.stopSources();
    this.playing = false;
  }

  applyControls(controls: MasteringControls): void {
    if (!this.context) {
      return;
    }

    const values: Record<StemName, {gainDb: number; brightDb: number}> = {
      vocals: {
        gainDb: controls.vocal_gain,
        brightDb: -controls.vocal_deharsh / 18,
      },
      drums: {
        gainDb: controls.drums_gain + controls.drums_punch / 40,
        brightDb: 0,
      },
      bass: {
        gainDb: controls.bass_gain,
        brightDb: 0,
      },
      other: {
        gainDb: controls.music_gain,
        brightDb: controls.music_bright,
      },
    };

    for (const chain of this.chains) {
      const value = values[chain.stem];
      chain.gain.gain.setTargetAtTime(dbToGain(value.gainDb), this.context.currentTime, 0.02);
      chain.filter.gain.setTargetAtTime(value.brightDb, this.context.currentTime, 0.02);
    }
  }

  private stopSources(): void {
    for (const chain of this.chains) {
      try {
        chain.source.stop();
      } catch {
        // Source may already be stopped by the browser.
      }
    }
    this.chains = [];
  }
}

function dbToGain(db: number): number {
  return Math.pow(10, db / 20);
}
