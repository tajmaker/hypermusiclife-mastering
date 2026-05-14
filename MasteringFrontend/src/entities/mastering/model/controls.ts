import type { StemName } from "../../track/model/types";

export type MixMode = "delta" | "full";
export type EqBandType = "bell" | "lowShelf" | "highShelf" | "highPass" | "lowPass";

export type EqBand = {
  id: string;
  type: EqBandType;
  frequencyHz: number;
  gainDb: number;
  q: number;
  enabled: boolean;
};

export type StemProcessing = {
  gainDb: number;
  muted: boolean;
  solo: boolean;
  eqBands: EqBand[];
};

export type MixProject = {
  mode: MixMode;
  stems: Record<StemName, StemProcessing>;
};

export type MasteringControls = {
  vocal_gain: number;
  vocal_deharsh: number;
  drums_gain: number;
  drums_punch: number;
  bass_gain: number;
  music_gain: number;
  music_bright: number;
  analog_color: number;
};

export type ControlKey = keyof MasteringControls;

export type ControlDefinition = {
  key: ControlKey;
  label: string;
  min: number;
  max: number;
  step: number;
  suffix: string;
};

export type StemControlState = Record<StemName, {muted: boolean; solo: boolean}>;
export type StemEqBands = Record<StemName, EqBand[]>;

export const defaultControls: MasteringControls = {
  vocal_gain: 0.9,
  vocal_deharsh: 35,
  drums_gain: 0,
  drums_punch: 22,
  bass_gain: -0.6,
  music_gain: 0,
  music_bright: 0.4,
  analog_color: 14,
};

export const defaultStemControlState: StemControlState = {
  vocals: {muted: false, solo: false},
  drums: {muted: false, solo: false},
  bass: {muted: false, solo: false},
  other: {muted: false, solo: false},
};

export const defaultStemEqBands: StemEqBands = {
  vocals: [],
  drums: [],
  bass: [],
  other: [],
};

export const defaultMixProject: MixProject = {
  mode: "delta",
  stems: {
    vocals: {gainDb: defaultControls.vocal_gain, muted: false, solo: false, eqBands: []},
    drums: {gainDb: defaultControls.drums_gain, muted: false, solo: false, eqBands: []},
    bass: {gainDb: defaultControls.bass_gain, muted: false, solo: false, eqBands: []},
    other: {gainDb: defaultControls.music_gain, muted: false, solo: false, eqBands: []},
  },
};

export const masteringControlDefinitions: ControlDefinition[] = [
  {key: "vocal_gain", label: "Вокал", min: -3, max: 3, step: 0.1, suffix: " dB"},
  {key: "vocal_deharsh", label: "Мягкость вокала", min: 0, max: 80, step: 1, suffix: ""},
  {key: "drums_gain", label: "Барабаны", min: -3, max: 3, step: 0.1, suffix: " dB"},
  {key: "drums_punch", label: "Плотность барабанов", min: 0, max: 80, step: 1, suffix: ""},
  {key: "bass_gain", label: "Бас", min: -3, max: 3, step: 0.1, suffix: " dB"},
  {key: "music_gain", label: "Музыка", min: -3, max: 3, step: 0.1, suffix: " dB"},
  {key: "music_bright", label: "Яркость музыки", min: -2, max: 2, step: 0.1, suffix: " dB"},
  {key: "analog_color", label: "Теплота", min: 0, max: 60, step: 1, suffix: ""},
];

export const stemGainControlByName: Record<StemName, ControlKey> = {
  vocals: "vocal_gain",
  drums: "drums_gain",
  bass: "bass_gain",
  other: "music_gain",
};

export function applyStemState(
  controls: MasteringControls,
  stemState: StemControlState,
): MasteringControls {
  const next = {...controls};
  const soloed = Object.entries(stemState)
    .filter(([, state]) => state.solo)
    .map(([stem]) => stem as StemName);

  for (const [stem, state] of Object.entries(stemState) as Array<
    [StemName, {muted: boolean; solo: boolean}]
  >) {
    const key = stemGainControlByName[stem];
    if (soloed.length > 0 && !soloed.includes(stem)) {
      next[key] = -60;
      continue;
    }
    if (state.muted) {
      next[key] = -60;
    }
  }

  return next;
}

export function definitionForMode(
  definition: ControlDefinition,
  mixMode: MixMode,
): ControlDefinition {
  const isStemGain = ["vocal_gain", "drums_gain", "bass_gain", "music_gain"].includes(
    definition.key,
  );
  if (mixMode === "full" && isStemGain) {
    return {...definition, min: -60, max: 12};
  }
  return definition;
}

export function buildMixProjectFromControls(
  controls: MasteringControls,
  stemState: StemControlState,
  mode: MixMode,
  eqBandsByStem: StemEqBands = defaultStemEqBands,
): MixProject {
  return {
    mode,
    stems: {
      vocals: stemProcessing("vocals", controls.vocal_gain, stemState, eqBandsByStem),
      drums: stemProcessing("drums", controls.drums_gain, stemState, eqBandsByStem),
      bass: stemProcessing("bass", controls.bass_gain, stemState, eqBandsByStem),
      other: stemProcessing("other", controls.music_gain, stemState, eqBandsByStem),
    },
  };
}

function stemProcessing(
  stem: StemName,
  gainDb: number,
  stemState: StemControlState,
  eqBandsByStem: StemEqBands,
): StemProcessing {
  return {
    gainDb,
    muted: stemState[stem].muted,
    solo: stemState[stem].solo,
    eqBands: eqBandsByStem[stem],
  };
}
