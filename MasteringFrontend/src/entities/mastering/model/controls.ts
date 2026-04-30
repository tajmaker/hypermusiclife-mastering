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
