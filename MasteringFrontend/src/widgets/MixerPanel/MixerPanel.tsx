import { Download, Loader2 } from "lucide-react";
import type { MasteringControls } from "../../entities/mastering/model/controls";
import { masteringControlDefinitions } from "../../entities/mastering/model/controls";

type Props = {
  busy: boolean;
  canRender: boolean;
  controls: MasteringControls;
  onChange: (controls: MasteringControls) => void;
  onRender: () => void;
};

export function MixerPanel({busy, canRender, controls, onChange, onRender}: Props) {
  return (
    <div className="panel mixer-panel">
      <div className="panel-head">
        <div>
          <p className="eyebrow">Live mix</p>
          <h2>Ручки трека</h2>
        </div>
        <button onClick={onRender} disabled={!canRender || busy}>
          {busy ? <Loader2 className="spin" size={18} /> : <Download size={18} />}
          Render
        </button>
      </div>

      <div className="sliders">
        {masteringControlDefinitions.map((slider) => (
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
        ))}
      </div>
    </div>
  );
}
