import type { MasteringControls } from "../../../entities/mastering/model/controls";
import { stemNames, type StemName, type TrackRecord } from "../../../entities/track/model/types";
import { assetUrl } from "../../../shared/api/http";

type StemChain = {
  stem: StemName | "original";
  source: AudioBufferSourceNode;
  gain: GainNode;
  filter: BiquadFilterNode;
  analyser: AnalyserNode;
  analyserData: Uint8Array<ArrayBuffer>;
};

export type MixerState = "empty" | "loading" | "ready" | "playing" | "disposed";
export type PlaybackSource = "mix" | "original";

export type PlaybackSnapshot = {
  duration: number;
  failedStems: StemName[];
  masterLevel: number;
  position: number;
  source: PlaybackSource;
  spectrumBands: number[];
  state: MixerState;
  stemLevels: Record<StemName, number>;
};

export class StemMixer {
  private context: AudioContext | null = null;
  private buffers = new Map<StemName, AudioBuffer>();
  private originalBuffer: AudioBuffer | null = null;
  private chains: StemChain[] = [];
  private failedStems: StemName[] = [];
  private loadVersion = 0;
  private onPlaybackEnded: (() => void) | null = null;
  private playbackSource: PlaybackSource = "mix";
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
    this.originalBuffer = null;
    this.failedStems = [];

    await Promise.all([
      this.loadOriginal(track, context, loadVersion),
      ...stemNames.map(async (stem) => {
        const url = track.urls.stems[stem];
        if (!url) {
          return;
        }

        try {
          const buffer = await this.fetchAudioBuffer(assetUrl(url), context, loadVersion);
          if (buffer) {
            this.buffers.set(stem, buffer);
          }
        } catch {
          this.failedStems.push(stem);
        }
      }),
    ]);

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
    return this.buffers.size > 0 || Boolean(this.originalBuffer);
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
    const signal = this.getSignalSnapshot();

    return {
      duration: this.getDuration(),
      failedStems: this.getFailedStems(),
      masterLevel: signal.masterLevel,
      position: this.getPosition(),
      source: this.playbackSource,
      spectrumBands: signal.spectrumBands,
      state: this.state,
      stemLevels: signal.stemLevels,
    };
  }

  setPlaybackEndedHandler(handler: (() => void) | null): void {
    this.onPlaybackEnded = handler;
  }

  play(controls: MasteringControls, source: PlaybackSource = this.playbackSource): boolean {
    if (!this.context || !this.hasAudio() || this.playing) {
      return false;
    }

    this.playbackSource = source;
    const allBuffers = this.getPlayableBuffers(source);
    if (allBuffers.length === 0) {
      return false;
    }

    const duration = this.getDuration(source);
    let offset = duration > 0 && this.pausedAt < duration ? this.pausedAt : 0;
    let playableBuffers = allBuffers.filter(([, buffer]) => buffer.duration > offset + 0.01);
    if (playableBuffers.length === 0) {
      offset = 0;
      playableBuffers = allBuffers;
    }

    let remainingSources = playableBuffers.length;
    this.chains = playableBuffers.map(([stem, buffer]) => {
      const sourceNode = this.context!.createBufferSource();
      const gain = this.context!.createGain();
      const filter = this.context!.createBiquadFilter();
      const analyser = this.context!.createAnalyser();
      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.78;

      sourceNode.buffer = buffer;
      filter.type = "highshelf";
      filter.frequency.value = stem === "other" ? 3200 : 4200;
      sourceNode.connect(filter).connect(gain).connect(analyser).connect(this.context!.destination);
      sourceNode.start(0, offset);
      sourceNode.onended = () => {
        remainingSources -= 1;
        if (remainingSources <= 0 && this.playing) {
          this.stop();
          this.onPlaybackEnded?.();
        }
      };

      return {
        stem,
        source: sourceNode,
        gain,
        filter,
        analyser,
        analyserData: new Uint8Array(analyser.frequencyBinCount) as Uint8Array<ArrayBuffer>,
      };
    });

    this.startedAt = this.context.currentTime - offset;
    this.playing = true;
    this.state = "playing";
    this.applyControls(controls, source);
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

  seek(position: number, controls: MasteringControls, source: PlaybackSource = this.playbackSource): void {
    const duration = this.getDuration(source);
    this.pausedAt = duration > 0 ? clamp(position, 0, duration) : 0;
    const wasPlaying = this.playing;
    this.stopSources();
    this.playing = false;
    if (this.context && this.hasAudio()) {
      this.state = "ready";
    }
    if (wasPlaying) {
      this.play(controls, source);
    }
  }

  async dispose(): Promise<void> {
    this.loadVersion += 1;
    this.stop();
    this.buffers.clear();
    this.originalBuffer = null;
    this.failedStems = [];
    if (this.context && this.context.state !== "closed") {
      await this.context.close();
    }
    this.context = null;
    this.state = "disposed";
  }

  applyControls(controls: MasteringControls, source: PlaybackSource = this.playbackSource): void {
    if (!this.context) {
      return;
    }

    if (source === "original") {
      for (const chain of this.chains) {
        chain.gain.gain.setTargetAtTime(1, this.context.currentTime, 0.02);
        chain.filter.gain.setTargetAtTime(0, this.context.currentTime, 0.02);
      }
      return;
    }

    const values: Record<StemName, { gainDb: number; brightDb: number }> = {
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
      if (chain.stem === "original") {
        continue;
      }
      const value = values[chain.stem];
      chain.gain.gain.setTargetAtTime(dbToGain(value.gainDb), this.context.currentTime, 0.02);
      chain.filter.gain.setTargetAtTime(value.brightDb, this.context.currentTime, 0.02);
    }
  }

  private async loadOriginal(
    track: TrackRecord,
    context: AudioContext,
    loadVersion: number,
  ): Promise<void> {
    try {
      const buffer = await this.fetchAudioBuffer(assetUrl(track.urls.original), context, loadVersion);
      if (buffer) {
        this.originalBuffer = buffer;
      }
    } catch {
      this.originalBuffer = null;
    }
  }

  private async fetchAudioBuffer(
    url: string,
    context: AudioContext,
    loadVersion: number,
  ): Promise<AudioBuffer | null> {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Не удалось загрузить аудио: HTTP ${response.status}`);
    }
    const bytes = await response.arrayBuffer();
    if (this.context !== context || this.loadVersion !== loadVersion) {
      return null;
    }
    const buffer = await context.decodeAudioData(bytes);
    if (this.context !== context || this.loadVersion !== loadVersion) {
      return null;
    }
    return buffer;
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

  private getPlayableBuffers(source: PlaybackSource): Array<[StemName | "original", AudioBuffer]> {
    if (source === "original") {
      return this.originalBuffer ? [["original", this.originalBuffer]] : [];
    }
    return Array.from(this.buffers.entries());
  }

  private getDuration(source: PlaybackSource = this.playbackSource): number {
    return Math.max(0, ...this.getPlayableBuffers(source).map(([, buffer]) => buffer.duration));
  }

  private getPosition(): number {
    if (!this.context || !this.playing) {
      return this.pausedAt;
    }
    const duration = this.getDuration();
    const position = Math.max(0, this.context.currentTime - this.startedAt);
    return duration > 0 ? Math.min(position, duration) : position;
  }

  private getSignalSnapshot(): {
    masterLevel: number;
    spectrumBands: number[];
    stemLevels: Record<StemName, number>;
  } {
    const bandCount = 32;
    const levels: Record<StemName, number> = {
      vocals: 0,
      drums: 0,
      bass: 0,
      other: 0,
    };
    const spectrumBands = Array.from({ length: bandCount }, () => 0);

    if (!this.playing) {
      return {
        masterLevel: 0,
        spectrumBands,
        stemLevels: levels,
      };
    }

    let activeChains = 0;
    let masterSum = 0;

    for (const chain of this.chains) {
      chain.analyser.getByteFrequencyData(chain.analyserData);
      const sum = chain.analyserData.reduce((acc, value) => acc + value, 0);
      const stemLevel = Math.min(1, sum / chain.analyserData.length / 160);
      if (chain.stem !== "original") {
        levels[chain.stem] = stemLevel;
      }
      masterSum += stemLevel;
      activeChains += 1;

      const binsPerBand = Math.max(1, Math.floor(chain.analyserData.length / bandCount));
      for (let band = 0; band < bandCount; band += 1) {
        const start = band * binsPerBand;
        const end = band === bandCount - 1 ? chain.analyserData.length : start + binsPerBand;
        let bandSum = 0;
        for (let index = start; index < end; index += 1) {
          bandSum += chain.analyserData[index] || 0;
        }
        const bandAverage = bandSum / Math.max(1, end - start);
        spectrumBands[band] += bandAverage / 190;
      }
    }

    return {
      masterLevel: activeChains > 0 ? Math.min(1, masterSum / activeChains) : 0,
      spectrumBands: spectrumBands.map((level) => Math.min(1, level / Math.max(1, activeChains))),
      stemLevels: levels,
    };
  }
}

function dbToGain(db: number): number {
  return Math.pow(10, db / 20);
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}
