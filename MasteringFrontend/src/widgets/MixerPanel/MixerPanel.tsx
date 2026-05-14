import type { CSSProperties } from "react";
import { useState } from "react";
import { Download, Loader2 } from "lucide-react";
import {
  definitionForMode,
  type EqBand,
  type EqBandType,
  masteringControlDefinitions,
  type MasteringControls,
  type MixMode,
  type StemEqBands,
  type StemControlState,
} from "../../entities/mastering/model/controls";
import { stemVisuals } from "../../entities/track/model/stems";
import { stemNames, type StemName } from "../../entities/track/model/types";
import { assetUrl } from "../../shared/api/http";

type Props = {
  busy: boolean;
  canRender: boolean;
  controls: MasteringControls;
  downloadUrl: string | null;
  eqBandsByStem: StemEqBands;
  mixMode: MixMode;
  stemState: StemControlState;
  onChange: (controls: MasteringControls) => void;
  onEqBandsChange: (bands: StemEqBands) => void;
  onMixModeChange: (mode: MixMode) => void;
  onRender: () => void;
  onStemStateChange: (state: StemControlState) => void;
};

export function MixerPanel({
  busy,
  canRender,
  controls,
  downloadUrl,
  eqBandsByStem,
  mixMode,
  stemState,
  onChange,
  onEqBandsChange,
  onMixModeChange,
  onRender,
  onStemStateChange,
}: Props) {
  const [selectedStem, setSelectedStem] = useState<StemName>("other");
  const selectedBands = eqBandsByStem[selectedStem];

  function toggleStem(stem: StemName, key: "muted" | "solo") {
    onStemStateChange({
      ...stemState,
      [stem]: {
        ...stemState[stem],
        [key]: !stemState[stem][key],
      },
    });
  }

  function updateBands(stem: StemName, bands: EqBand[]) {
    onEqBandsChange({
      ...eqBandsByStem,
      [stem]: bands,
    });
  }

  function addBand(type: EqBandType) {
    if (selectedBands.length >= 8) return;
    const band: EqBand = {
      id: `${selectedStem}-${Date.now()}-${selectedBands.length}`,
      type,
      frequencyHz: defaultFrequency(type),
      gainDb: type === "highPass" || type === "lowPass" ? 0 : 1.5,
      q: type === "bell" ? 1.2 : 0.7,
      enabled: true,
    };
    updateBands(selectedStem, [...selectedBands, band]);
  }

  function updateBand(index: number, patch: Partial<EqBand>) {
    updateBands(
      selectedStem,
      selectedBands.map((band, bandIndex) =>
        bandIndex === index ? {...band, ...patch} : band,
      ),
    );
  }

  function removeBand(index: number) {
    updateBands(
      selectedStem,
      selectedBands.filter((_, bandIndex) => bandIndex !== index),
    );
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
        {downloadUrl ? (
          <a className="download primary-action" href={assetUrl(downloadUrl)}>
            <Download size={18} />
            Скачать мастер
          </a>
        ) : (
          <button onClick={onRender} disabled={!canRender || busy}>
            {busy ? <Loader2 className="spin" size={18} /> : <Download size={18} />}
            {busy ? "Готовим мастер" : "Получить мастер"}
          </button>
        )}
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
          : "Creative пересобирает трек из стемов, поэтому Solo, Mute и сильные уровни работают по-настоящему."}
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

      <div className="stem-eq">
        <div className="stem-eq__head">
          <div>
            <p className="eyebrow">Stem EQ</p>
            <h3>Эквалайзер стема</h3>
          </div>
          <span>{selectedBands.length}/8 bands</span>
        </div>

        <div className="stem-eq__tabs" aria-label="Выбор стема для EQ">
          {stemNames.map((stem) => (
            <button
              className={selectedStem === stem ? "active" : ""}
              key={stem}
              onClick={() => setSelectedStem(stem)}
            >
              {stemVisuals[stem].label}
            </button>
          ))}
        </div>

        <div className="stem-eq__actions">
          <button onClick={() => addBand("bell")} disabled={selectedBands.length >= 8}>
            Bell
          </button>
          <button onClick={() => addBand("lowShelf")} disabled={selectedBands.length >= 8}>
            Low shelf
          </button>
          <button onClick={() => addBand("highShelf")} disabled={selectedBands.length >= 8}>
            High shelf
          </button>
        </div>

        <div className="stem-eq__bands">
          {selectedBands.length === 0 ? (
            <p className="stem-eq__empty">
              Добавьте точку EQ, чтобы менять только выбранную часть трека.
            </p>
          ) : (
            selectedBands.map((band, index) => (
              <div className="eq-band" key={band.id}>
                <div className="eq-band__top">
                  <label>
                    <input
                      checked={band.enabled}
                      type="checkbox"
                      onChange={(event) => updateBand(index, {enabled: event.target.checked})}
                    />
                    Band {index + 1}
                  </label>
                  <select
                    value={band.type}
                    onChange={(event) => updateBand(index, {type: event.target.value as EqBandType})}
                  >
                    <option value="bell">Bell</option>
                    <option value="lowShelf">Low shelf</option>
                    <option value="highShelf">High shelf</option>
                    <option value="highPass">High pass</option>
                    <option value="lowPass">Low pass</option>
                  </select>
                  <button className="eq-band__remove" onClick={() => removeBand(index)}>
                    Удалить
                  </button>
                </div>

                <label className="eq-control">
                  <span>Частота</span>
                  <input
                    max={20000}
                    min={20}
                    step={10}
                    type="range"
                    value={band.frequencyHz}
                    onChange={(event) => updateBand(index, {frequencyHz: Number(event.target.value)})}
                  />
                  <output>{Math.round(band.frequencyHz)} Hz</output>
                </label>

                <label className="eq-control">
                  <span>Gain</span>
                  <input
                    disabled={band.type === "highPass" || band.type === "lowPass"}
                    max={12}
                    min={-12}
                    step={0.1}
                    type="range"
                    value={band.gainDb}
                    onChange={(event) => updateBand(index, {gainDb: Number(event.target.value)})}
                  />
                  <output>{band.gainDb.toFixed(1)} dB</output>
                </label>

                <label className="eq-control">
                  <span>Q</span>
                  <input
                    max={12}
                    min={0.1}
                    step={0.1}
                    type="range"
                    value={band.q}
                    onChange={(event) => updateBand(index, {q: Number(event.target.value)})}
                  />
                  <output>{band.q.toFixed(1)}</output>
                </label>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

function defaultFrequency(type: EqBandType): number {
  const frequencies: Record<EqBandType, number> = {
    bell: 3000,
    lowShelf: 160,
    highShelf: 6500,
    highPass: 80,
    lowPass: 14000,
  };
  return frequencies[type];
}
