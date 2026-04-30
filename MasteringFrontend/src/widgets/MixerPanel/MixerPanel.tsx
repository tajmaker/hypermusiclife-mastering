import type { CSSProperties } from "react";
import { Download, Loader2 } from "lucide-react";
import {
  definitionForMode,
  masteringControlDefinitions,
  type MasteringControls,
  type MixMode,
  type StemControlState,
} from "../../entities/mastering/model/controls";
import { stemVisuals } from "../../entities/track/model/stems";
import { stemNames, type StemName } from "../../entities/track/model/types";

type Props = {
  busy: boolean;
  canRender: boolean;
  controls: MasteringControls;
  mixMode: MixMode;
  stemState: StemControlState;
  onChange: (controls: MasteringControls) => void;
  onMixModeChange: (mode: MixMode) => void;
  onRender: () => void;
  onStemStateChange: (state: StemControlState) => void;
};

export function MixerPanel({
  busy,
  canRender,
  controls,
  mixMode,
  stemState,
  onChange,
  onMixModeChange,
  onRender,
  onStemStateChange,
}: Props) {
  function toggleStem(stem: StemName, key: "muted" | "solo") {
    onStemStateChange({
      ...stemState,
      [stem]: {
        ...stemState[stem],
        [key]: !stemState[stem][key],
      },
    });
  }

  return (
    <div className="panel mixer-panel">
      <div className="panel-head">
        <div>
          <p className="eyebrow">Live mix</p>
          <h2>Ручки трека</h2>
          <p className="panel-note">
            Это стартовый пресет микса/мастера, а не настройки разделения на стемы.
          </p>
        </div>
        <button onClick={onRender} disabled={!canRender || busy}>
          {busy ? <Loader2 className="spin" size={18} /> : <Download size={18} />}
          Рендер
        </button>
      </div>

      <div className="mode-switch" aria-label="Режим микса">
        <button className={mixMode === "delta" ? "active" : ""} onClick={() => onMixModeChange("delta")}>
          Safe
        </button>
        <button className={mixMode === "full" ? "active" : ""} onClick={() => onMixModeChange("full")}>
          Creative
        </button>
      </div>
      <p className="mode-hint">
        {mixMode === "delta"
          ? "Safe сохраняет оригинальный микс как основу и добавляет контролируемые правки по стемам."
          : "Creative пересобирает трек из стемов, поэтому solo, mute и сильные уровни работают по-настоящему."}
      </p>

      {mixMode === "full" && (
        <div className="stem-buttons">
          {stemNames.map((stem) => (
            <div
              className="stem-row"
              key={stem}
              style={{"--stem-accent": stemVisuals[stem].accent} as CSSProperties}
            >
              <span>{stemVisuals[stem].label}</span>
              <button
                className={stemState[stem].solo ? "active" : ""}
                onClick={() => toggleStem(stem, "solo")}
              >
                Solo
              </button>
              <button
                className={stemState[stem].muted ? "danger active" : "danger"}
                onClick={() => toggleStem(stem, "muted")}
              >
                Mute
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="sliders">
        {masteringControlDefinitions.map((rawSlider) => {
          const slider = definitionForMode(rawSlider, mixMode);
          return (
            <label className="slider" key={slider.key}>
              <span>{slider.label}</span>
              <input
                type="range"
                min={slider.min}
                max={slider.max}
                step={slider.step}
                value={controls[slider.key]}
                onChange={(event) =>
                  onChange({
                    ...controls,
                    [slider.key]: Number(event.target.value),
                  })
                }
              />
              <output>
                {controls[slider.key].toFixed(slider.step === 1 ? 0 : 1)}
                {slider.suffix}
              </output>
            </label>
          );
        })}
      </div>
    </div>
  );
}
