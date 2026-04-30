import type { StemName } from "./types";

export type StemVisualDefinition = {
  label: string;
  shortLabel: string;
  cssVar: string;
  accent: string;
};

export const stemVisuals: Record<StemName, StemVisualDefinition> = {
  vocals: {
    label: "Вокал",
    shortLabel: "Vox",
    cssVar: "--stem-vocals",
    accent: "#f0a56d",
  },
  drums: {
    label: "Барабаны",
    shortLabel: "Drums",
    cssVar: "--stem-drums",
    accent: "#ef705d",
  },
  bass: {
    label: "Бас",
    shortLabel: "Bass",
    cssVar: "--stem-bass",
    accent: "#58cfa8",
  },
  other: {
    label: "Музыка",
    shortLabel: "Music",
    cssVar: "--stem-music",
    accent: "#8aa4ff",
  },
};
