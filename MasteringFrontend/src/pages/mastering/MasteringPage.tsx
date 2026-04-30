import { useEffect, useMemo, useRef, useState } from "react";
import { defaultControls, type MasteringControls } from "../../entities/mastering/model/controls";
import { fetchTrack } from "../../entities/track/api/trackApi";
import { isMixReady, type TrackRecord } from "../../entities/track/model/types";
import { StemMixer } from "../../features/liveStemMix/lib/StemMixer";
import { renderTrack } from "../../features/trackRender/api/renderTrack";
import { uploadTrack } from "../../features/trackUpload/api/uploadTrack";
import { Hero } from "../../widgets/Hero/Hero";
import { MixerPanel } from "../../widgets/MixerPanel/MixerPanel";
import { UploadPanel } from "../../widgets/UploadPanel/UploadPanel";
import { Workflow } from "../../widgets/Workflow/Workflow";

export function MasteringPage() {
  const [track, setTrack] = useState<TrackRecord | null>(null);
  const [controls, setControls] = useState<MasteringControls>(defaultControls);
  const [message, setMessage] = useState("Загрузите WAV/MP3 и дождитесь подготовки микса.");
  const [busy, setBusy] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [mixerReady, setMixerReady] = useState(false);
  const mixer = useRef(new StemMixer());

  const activeStage = useMemo(() => {
    if (!track) return 0;
    if (track.status === "separating" || track.status === "uploaded") return 1;
    if (track.status === "ready_to_mix") return 2;
    if (track.status === "rendering") return 3;
    if (track.status === "done") return 4;
    return 0;
  }, [track]);

  useEffect(() => {
    if (!track || isMixReady(track.status) || track.status === "failed") {
      return;
    }

    const timer = window.setInterval(async () => {
      const fresh = await fetchTrack(track.track_id);
      setTrack(fresh);
    }, 2500);

    return () => window.clearInterval(timer);
  }, [track]);

  useEffect(() => {
    mixer.current.applyControls(controls);
  }, [controls]);

  useEffect(() => {
    if (!track || track.status !== "ready_to_mix" || mixerReady) {
      return;
    }

    setMessage("Stems готовы. Загружаю их в браузер для живого управления.");
    mixer.current
      .load(track)
      .then(() => {
        setMixerReady(true);
        setMessage("Можно нажать Play и крутить ручки во время прослушивания.");
      })
      .catch((error: unknown) => setMessage(String(error)));
  }, [track, mixerReady]);

  async function handleUpload(file: File | null) {
    if (!file) return;

    setBusy(true);
    setMixerReady(false);
    mixer.current.stop();
    setPlaying(false);
    setMessage("Загружаю трек и запускаю разделение на виртуальные части.");

    try {
      const uploaded = await uploadTrack(file);
      setTrack(uploaded);
    } catch (error: unknown) {
      setMessage(String(error));
    } finally {
      setBusy(false);
    }
  }

  function handleTogglePlayback() {
    if (!mixerReady) return;

    if (playing) {
      mixer.current.pause();
      setPlaying(false);
      return;
    }

    mixer.current.play(controls);
    setPlaying(true);
  }

  function handleResetPlayback() {
    mixer.current.stop();
    setPlaying(false);
  }

  async function handleRender() {
    if (!track) return;

    setBusy(true);
    setMessage("Рендерю финальный мастер с текущими ручками.");

    try {
      const updated = await renderTrack(track.track_id, controls);
      setTrack(updated);
    } catch (error: unknown) {
      setMessage(String(error));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="page">
      <Hero status={track?.status || "waiting"} />
      <Workflow activeStage={activeStage} />
      <section className="workspace">
        <UploadPanel
          busy={busy}
          canPreview={mixerReady}
          message={message}
          playing={playing}
          track={track}
          onUpload={handleUpload}
          onTogglePlayback={handleTogglePlayback}
          onResetPlayback={handleResetPlayback}
        />
        <MixerPanel
          busy={busy}
          canRender={mixerReady}
          controls={controls}
          onChange={setControls}
          onRender={handleRender}
        />
      </section>
    </main>
  );
}
