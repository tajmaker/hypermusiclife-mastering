import type { MasteringControls } from "../../../entities/mastering/model/controls";
import { assetUrl } from "../../../shared/api/http";
import { stemNames, type StemName, type TrackRecord } from "../../../entities/track/model/types";

type StemChain = {
  stem: StemName;
  source: AudioBufferSourceNode;
  gain: GainNode;
  filter: BiquadFilterNode;
  analyser: AnalyserNode;
  analyserData: Uint8Array<ArrayBuffer>;
};

export type MixerState = "empty" | "loading" | "ready" | "playing" | "disposed";

export type PlaybackSnapshot = {
  duration: number;
  failedStems: StemName[];
  position: number;
  state: MixerState;
  stemLevels: Record<StemName, number>;
};

export class StemMixer {
  private context: AudioContext | null = null;
  private buffers = new Map<StemName, AudioBuffer>();
  private chains: StemChain[] = [];
  private failedStems: StemName[] = [];
  private loadVersion = 0;
  private onPlaybackEnded: (() => void) | null = null;
  private startedAt = 0;
  private pausedAt = 0;
  private playing = false;
  private state: MixerState = "empty";

  async load(track: TrackRecord): Promise<void> {
    await this.dispose();
    const loadVersion = this.loadVersion + 1;
    this.loadVersion = loadVersion;
    const context = new AudioContext();
    this.context = context;
    this.state = "loading";
    this.buffers.clear();
    this.failedStems = [];

    await Promise.all(
      stemNames.map(async (stem) => {
        const url = track.urls.stems[stem];
        if (!url) {
          return;
        }
        try {
          const response = await fetch(assetUrl(url));
          if (!response.ok) {
            throw new Error(`Не удалось загрузить ${stem}: HTTP ${response.status}`);
          }
          const bytes = await response.arrayBuffer();
          if (this.context !== context || this.loadVersion !== loadVersion) {
            return;
          }
          const buffer = await context.decodeAudioData(bytes);
          if (this.context !== context || this.loadVersion !== loadVersion) {
            return;
          }
          this.buffers.set(stem, buffer);
        } catch {
          this.failedStems.push(stem);
        }
      }),
    );

    if (this.context !== context || this.loadVersion !== loadVersion) {
      return;
    }
    if (!this.hasAudio()) {
      this.state = "empty";
      throw new Error("Не удалось загрузить аудио для preview.");
    }
    this.state = "ready";
  }

  hasAudio(): boolean {
    return this.buffers.size > 0;
  }

  isReady(): boolean {
    return this.state === "ready" || this.state === "playing";
  }

  isPlaying(): boolean {
    return this.playing;
  }

  getFailedStems(): StemName[] {
    return [...this.failedStems];
  }

  getSnapshot(): PlaybackSnapshot {
    return {
      duration: this.getDuration(),
      failedStems: this.getFailedStems(),
      position: this.getPosition(),
      state: this.state,
      stemLevels: this.getStemLevels(),
    };
  }

  setPlaybackEndedHandler(handler: (() => void) | null): void {
    this.onPlaybackEnded = handler;
  }

  play(controls: MasteringControls): boolean {
    if (!this.context || !this.hasAudio() || this.playing) {
      return false;
    }

    const duration = this.getDuration();
    let offset = duration > 0 && this.pausedAt < duration ? this.pausedAt : 0;
    let playableBuffers = Array.from(this.buffers.entries()).filter(
      ([, buffer]) => buffer.duration > offset + 0.01,
    );
    if (playableBuffers.length === 0) {
      offset = 0;
      playableBuffers = Array.from(this.buffers.entries());
    }

    let remainingSources = playableBuffers.length;
    this.chains = playableBuffers.map(([stem, buffer]) => {
      const source = this.context!.createBufferSource();
      const gain = this.context!.createGain();
      const filter = this.context!.createBiquadFilter();
      const analyser = this.context!.createAnalyser();
      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.78;

      source.buffer = buffer;
      filter.type = "highshelf";
      filter.frequency.value = stem === "other" ? 3200 : 4200;
      source.connect(filter).connect(gain).connect(analyser).connect(this.context!.destination);
      source.start(0, offset);
      source.onended = () => {
        remainingSources -= 1;
        if (remainingSources <= 0 && this.playing) {
          this.stop();
          this.onPlaybackEnded?.();
        }
      };

      return {
        stem,
        source,
        gain,
        filter,
        analyser,
        analyserData: new Uint8Array(analyser.frequencyBinCount) as Uint8Array<ArrayBuffer>,
      };
    });

    this.startedAt = this.context.currentTime - offset;
    this.playing = true;
    this.state = "playing";
    this.applyControls(controls);
    return true;
  }

  pause(): boolean {
    if (!this.context || !this.playing) {
      return false;
    }
    this.pausedAt = Math.max(0, this.context.currentTime - this.startedAt);
    this.stopSources();
    this.playing = false;
    this.state = "ready";
    return true;
  }

  stop(): void {
    this.pausedAt = 0;
    this.stopSources();
    this.playing = false;
    if (this.context && this.hasAudio()) {
      this.state = "ready";
    }
  }

  async dispose(): Promise<void> {
    this.loadVersion += 1;
    this.stop();
    this.buffers.clear();
    this.failedStems = [];
    if (this.context && this.context.state !== "closed") {
      await this.context.close();
    }
    this.context = null;
    this.state = "disposed";
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
      chain.source.onended = null;
      try {
        chain.source.stop();
      } catch {
        // Source may already be stopped by the browser.
      }
    }
    this.chains = [];
  }

  private getDuration(): number {
    return Math.max(0, ...Array.from(this.buffers.values()).map((buffer) => buffer.duration));
  }

  private getPosition(): number {
    if (!this.context || !this.playing) {
      return this.pausedAt;
    }
    const duration = this.getDuration();
    const position = Math.max(0, this.context.currentTime - this.startedAt);
    return duration > 0 ? Math.min(position, duration) : position;
  }

  private getStemLevels(): Record<StemName, number> {
    const levels: Record<StemName, number> = {
      vocals: 0,
      drums: 0,
      bass: 0,
      other: 0,
    };

    if (!this.playing) {
      return levels;
    }

    for (const chain of this.chains) {
      chain.analyser.getByteFrequencyData(chain.analyserData);
      const sum = chain.analyserData.reduce((acc, value) => acc + value, 0);
      levels[chain.stem] = Math.min(1, sum / chain.analyserData.length / 160);
    }

    return levels;
  }
}

function dbToGain(db: number): number {
  return Math.pow(10, db / 20);
}
