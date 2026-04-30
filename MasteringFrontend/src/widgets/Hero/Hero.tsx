import type { TrackStatus } from "../../entities/track/model/types";

type Props = {
  status: TrackStatus | "waiting";
};

export function Hero({status}: Props) {
  return (
    <section className="hero">
      <div>
        <p className="eyebrow">Hyper Mastering</p>
        <h1>Stem-aware mastering for AI tracks</h1>
        <p className="lead">
          Один раз подготавливаем трек, затем вокал, бас, барабаны и музыку
          можно слушать и двигать почти сразу в браузере.
        </p>
      </div>
      <div className="meter">
        <span>API</span>
        <strong>{status}</strong>
      </div>
    </section>
  );
}
