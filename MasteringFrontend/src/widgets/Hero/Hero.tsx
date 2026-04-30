import type { TrackStatus } from "../../entities/track/model/types";

type Props = {
  status: TrackStatus | "waiting";
};

export function Hero({status}: Props) {
  return (
    <section className="hero">
      <div>
        <p className="eyebrow">Hyper Mastering</p>
        <h1>Stem-aware мастеринг для AI-треков</h1>
        <p className="lead">
          Один раз подготавливаем трек, затем управляем вокалом, барабанами,
          басом и музыкой прямо в браузере перед финальным рендером.
        </p>
      </div>
      <div className="meter">
        <span>API</span>
        <strong>{status}</strong>
      </div>
    </section>
  );
}
