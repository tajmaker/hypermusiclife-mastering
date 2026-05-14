import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  applyStemState,
  buildMixProjectFromControls,
  defaultControls,
  defaultStemEqBands,
  defaultStemControlState,
  type MasteringControls,
  type MixMode,
  type StemEqBands,
  type StemControlState,
} from "../../../entities/mastering/model/controls";
import { fetchTrack } from "../../../entities/track/api/trackApi";
import { isMixReady, type JobStage, type TrackRecord } from "../../../entities/track/model/types";
import { StemMixer, type PlaybackSource } from "../../../features/liveStemMix/lib/StemMixer";
import { renderTrack } from "../../../features/trackRender/api/renderTrack";
import { uploadTrack } from "../../../features/trackUpload/api/uploadTrack";
import { validateAudioFile } from "../../../features/trackUpload/lib/validateAudioFile";

const INITIAL_MESSAGE = "Загрузите WAV/MP3 и дождитесь подготовки микса.";
const POLL_INTERVAL_MS = 3500;

export type SessionProgress = {
  detail: string;
  indeterminate: boolean;
  progress: number;
  title: string;
  tone: "idle" | "active" | "ready" | "failed";
};

export function useMasteringSession() {
  const [track, setTrack] = useState<TrackRecord | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [controls, setControls] = useState<MasteringControls>(defaultControls);
  const [stemState, setStemState] = useState<StemControlState>(defaultStemControlState);
  const [eqBandsByStem, setEqBandsByStem] = useState<StemEqBands>(defaultStemEqBands);
  const [mixMode, setMixMode] = useState<MixMode>("delta");
  const [message, setMessage] = useState(INITIAL_MESSAGE);
  const [busy, setBusy] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [playbackSource, setPlaybackSource] = useState<PlaybackSource>("mix");
  const [playbackRevision, setPlaybackRevision] = useState(0);
  const [mixerReady, setMixerReady] = useState(false);
  const mixer = useRef(new StemMixer());
  const mountedRef = useRef(true);
  const loadTokenRef = useRef(0);

  useEffect(() => {
    mixer.current.setPlaybackEndedHandler(() => {
      if (mountedRef.current) {
        setPlaying(false);
      }
    });

    return () => {
      mountedRef.current = false;
      loadTokenRef.current += 1;
      mixer.current.setPlaybackEndedHandler(null);
      void mixer.current.dispose();
    };
  }, []);

  const effectiveControls = useMemo(
    () => (mixMode === "full" ? applyStemState(controls, stemState) : controls),
    [controls, mixMode, stemState],
  );
  const mixProject = useMemo(
    () => buildMixProjectFromControls(controls, stemState, mixMode, eqBandsByStem),
    [controls, eqBandsByStem, mixMode, stemState],
  );

  const activeStage = useMemo(() => {
    if (!track) return 0;
    if (track.status === "separating" || track.status === "uploaded") return 1;
    if (track.status === "ready_to_mix") return 2;
    if (track.status === "rendering") return 3;
    if (track.status === "done") return 4;
    return 0;
  }, [track]);

  const uploadDisabled = busy || Boolean(track && track.status !== "failed");
  const canPreview = mixerReady;
  const canRender =
    mixerReady && !busy && Boolean(track && track.status !== "rendering" && track.status !== "separating");
  const readPlaybackSnapshot = useCallback(() => mixer.current.getSnapshot(), []);
  const progress = useMemo(
    () => buildProgress(track, mixerReady, busy, message),
    [busy, message, mixerReady, track],
  );

  useEffect(() => {
    if (!track || isMixReady(track.status) || track.status === "failed") {
      return;
    }

    const timer = window.setInterval(async () => {
      try {
        const fresh = await fetchTrack(track.track_id);
        if (mountedRef.current) {
          setTrack(fresh);
        }
      } catch (error: unknown) {
        if (mountedRef.current) {
          setMessage(String(error));
        }
      }
    }, POLL_INTERVAL_MS);

    return () => window.clearInterval(timer);
  }, [track]);

  useEffect(() => {
    mixer.current.applyControls(effectiveControls, playbackSource, mixProject);
  }, [effectiveControls, mixProject, playbackSource]);

  useEffect(() => {
    if (!track || track.status !== "ready_to_mix" || mixerReady) {
      return;
    }

    const loadToken = loadTokenRef.current + 1;
    loadTokenRef.current = loadToken;
    setMessage("Стемы готовы. Загружаю оригинал и preview в браузер.");
    mixer.current
      .load(track)
      .then(() => {
        if (!mountedRef.current || loadTokenRef.current !== loadToken) {
          return;
        }
        setMixerReady(true);
        const failedStems = mixer.current.getFailedStems();
        if (failedStems.length > 0) {
          setMessage("Preview загружен частично: часть стемов недоступна. Можно слушать и двигать ручки.");
          return;
        }
        setMessage("Нажмите Play, сравните оригинал и preview, затем двигайте ручки во время прослушивания.");
      })
      .catch((error: unknown) => {
        if (mountedRef.current && loadTokenRef.current === loadToken) {
          setMessage(String(error));
        }
      });
  }, [track, mixerReady]);

  async function upload(file: File | null) {
    if (!file || uploadDisabled) return;

    const validationError = validateAudioFile(file);
    if (validationError) {
      setMessage(validationError);
      return;
    }

    setBusy(true);
    setFileName(file.name);
    setMixerReady(false);
    setPlaybackSource("mix");
    loadTokenRef.current += 1;
    setStemState(defaultStemControlState);
    setEqBandsByStem(defaultStemEqBands);
    mixer.current.stop();
    setPlaying(false);
    setMessage("Загружаю трек и запускаю виртуальное разделение на стемы.");

    try {
      const uploaded = await uploadTrack(file);
      if (mountedRef.current) {
        setTrack(uploaded);
      }
    } catch (error: unknown) {
      if (mountedRef.current) {
        setMessage(String(error));
      }
    } finally {
      if (mountedRef.current) {
        setBusy(false);
      }
    }
  }

  function togglePlayback() {
    if (!mixerReady) return;

    if (playing) {
      mixer.current.pause();
      setPlaying(false);
      setPlaybackRevision((current) => current + 1);
      return;
    }

    setPlaying(mixer.current.play(effectiveControls, playbackSource, mixProject));
  }

  function resetPlayback() {
    mixer.current.stop();
    setPlaying(false);
    setPlaybackRevision((current) => current + 1);
  }

  function seekPlayback(position: number) {
    if (!mixerReady) return;
    mixer.current.seek(position, effectiveControls, playbackSource, mixProject);
    setPlaybackRevision((current) => current + 1);
  }

  function changePlaybackSource(source: PlaybackSource) {
    if (source === playbackSource) return;

    const wasPlaying = playing;
    const currentPosition = mixer.current.getSnapshot().position;
    mixer.current.pause();
    setPlaybackSource(source);
    mixer.current.seek(currentPosition, effectiveControls, source, mixProject);
    if (wasPlaying) {
      setPlaying(mixer.current.play(effectiveControls, source, mixProject));
      return;
    }
    setPlaying(false);
    setPlaybackRevision((current) => current + 1);
  }

  function startOver() {
    loadTokenRef.current += 1;
    void mixer.current.dispose();
    setTrack(null);
    setFileName(null);
    setPlaying(false);
    setPlaybackSource("mix");
    setMixerReady(false);
    setControls(defaultControls);
    setStemState(defaultStemControlState);
    setEqBandsByStem(defaultStemEqBands);
    setMixMode("delta");
    setMessage(INITIAL_MESSAGE);
  }

  function resetControls() {
    setControls(defaultControls);
    setStemState(defaultStemControlState);
    setEqBandsByStem(defaultStemEqBands);
    setMixMode("delta");
    setMessage("Ручки сброшены в Safe-режим.");
  }

  function changeMixMode(nextMode: MixMode) {
    setMixMode(nextMode);
    if (nextMode === "delta") {
      setStemState(defaultStemControlState);
      setControls((current) => ({
        ...current,
        vocal_gain: clamp(current.vocal_gain, -3, 3),
        drums_gain: clamp(current.drums_gain, -3, 3),
        bass_gain: clamp(current.bass_gain, -3, 3),
        music_gain: clamp(current.music_gain, -3, 3),
      }));
    }
  }

  async function render() {
    if (!track || track.status === "rendering" || track.status === "separating") return;

    setBusy(true);
    setMessage("Готовлю финальный мастер с текущими ручками.");

    try {
      const updated = await renderTrack(track.track_id, effectiveControls, mixMode, mixProject);
      if (mountedRef.current) {
        setTrack(updated);
      }
    } catch (error: unknown) {
      if (mountedRef.current) {
        setMessage(String(error));
      }
    } finally {
      if (mountedRef.current) {
        setBusy(false);
      }
    }
  }

  return {
    state: {
      activeStage,
      busy,
      canPreview,
      canRender,
      controls,
      eqBandsByStem,
      fileName,
      message,
      mixerReady,
      mixMode,
      playbackSource,
      playbackRevision,
      playing,
      progress,
      readPlaybackSnapshot,
      stemState,
      track,
      uploadDisabled,
    },
    actions: {
      changeControls: setControls,
      changeEqBandsByStem: setEqBandsByStem,
      changeMixMode,
      changePlaybackSource,
      changeStemState: setStemState,
      render,
      resetControls,
      resetPlayback,
      seekPlayback,
      startOver,
      togglePlayback,
      upload,
    },
  };
}

function buildProgress(
  track: TrackRecord | null,
  mixerReady: boolean,
  busy: boolean,
  message: string,
): SessionProgress {
  if (!track && busy) {
    return {
      detail: "Файл передается на сервер. После загрузки автоматически начнется подготовка стемов.",
      indeterminate: true,
      progress: 20,
      title: "Загрузка трека",
      tone: "active",
    };
  }

  if (!track) {
    return {
      detail: "Выберите аудиофайл, после этого начнется подготовка preview.",
      indeterminate: false,
      progress: 0,
      title: "Ожидание файла",
      tone: "idle",
    };
  }

  const backendProgress = progressFromBackend(track);
  if (backendProgress) {
    if (track.status === "ready_to_mix" && !mixerReady) {
      return {
        detail: "Стемы готовы на сервере, загружаю их в браузер для живого preview.",
        indeterminate: true,
        progress: Math.max(backendProgress.progress, 85),
        title: "Загрузка preview",
        tone: "active",
      };
    }
    return backendProgress;
  }

  if (track.status === "failed") {
    return {
      detail: track.error_message || message,
      indeterminate: false,
      progress: 100,
      title: "Ошибка обработки",
      tone: "failed",
    };
  }

  if (busy && track.status !== "rendering") {
    return {
      detail: "Файл передается на сервер. Следующий шаг запустится автоматически.",
      indeterminate: true,
      progress: 20,
      title: "Загрузка трека",
      tone: "active",
    };
  }

  if (track.status === "uploaded" || track.status === "separating") {
    return {
      detail: "Сервер разделяет трек на вокал, барабаны, бас и музыку. На бесплатном CPU это может занять несколько минут.",
      indeterminate: true,
      progress: 55,
      title: "Подготовка стемов",
      tone: "active",
    };
  }

  if (track.status === "ready_to_mix" && !mixerReady) {
    return {
      detail: "Стемы готовы на сервере, загружаю их в браузер для живого preview.",
      indeterminate: true,
      progress: 85,
      title: "Загрузка preview",
      tone: "active",
    };
  }

  if (track.status === "rendering") {
    return {
      detail: "Собираю финальный мастер с текущими ручками.",
      indeterminate: true,
      progress: 60,
      title: "Подготовка мастера",
      tone: "active",
    };
  }

  if (track.status === "done") {
    return {
      detail: "Финальный файл готов. Можно скачать мастер или начать заново.",
      indeterminate: false,
      progress: 100,
      title: "Мастер готов",
      tone: "ready",
    };
  }

  return {
    detail: "Preview готов: можно слушать оригинал, stem-preview, крутить ручки и получить мастер.",
    indeterminate: false,
    progress: 100,
    title: "Готово к миксу",
    tone: "ready",
  };
}

function progressFromBackend(track: TrackRecord): SessionProgress | null {
  const hasBackendProgress = Boolean(track.stage || track.progress != null || track.progress_detail);
  if (!hasBackendProgress) {
    return null;
  }

  const stage = track.stage ?? null;
  const progress = track.progress ?? fallbackProgressForStage(stage, track.status);
  const detail = track.error_message || track.progress_detail || "Обновляю состояние задачи.";
  const title = stage ? titleForStage(stage) : fallbackTitleForStatus(track.status);
  const tone = toneForStage(stage, track.status);

  return {
    detail,
    indeterminate: tone === "active" && progress < 100,
    progress,
    title,
    tone,
  };
}

function titleForStage(stage: JobStage): string {
  const titles: Record<JobStage, string> = {
    upload_saved: "Файл загружен",
    queued_separation: "Ожидание разделения",
    separating: "Подготовка стемов",
    writing_stems: "Сохранение стемов",
    preview_ready: "Готово к миксу",
    queued_render: "Мастер в очереди",
    rendering_master: "Подготовка мастера",
    master_ready: "Мастер готов",
    failed: "Ошибка обработки",
  };
  return titles[stage];
}

function fallbackTitleForStatus(status: TrackRecord["status"]): string {
  const titles: Record<TrackRecord["status"], string> = {
    uploaded: "Файл загружен",
    separating: "Подготовка стемов",
    ready_to_mix: "Готово к миксу",
    rendering: "Подготовка мастера",
    done: "Мастер готов",
    failed: "Ошибка обработки",
  };
  return titles[status];
}

function toneForStage(stage: JobStage | null, status: TrackRecord["status"]): SessionProgress["tone"] {
  if (stage === "failed" || status === "failed") return "failed";
  if (stage === "master_ready" || status === "done") return "ready";
  if (stage === "preview_ready" || status === "ready_to_mix") return "ready";
  return "active";
}

function fallbackProgressForStage(stage: JobStage | null, status: TrackRecord["status"]): number {
  if (!stage) {
    const byStatus: Record<TrackRecord["status"], number> = {
      uploaded: 15,
      separating: 45,
      ready_to_mix: 70,
      rendering: 82,
      done: 100,
      failed: 100,
    };
    return byStatus[status];
  }

  const byStage: Record<JobStage, number> = {
    upload_saved: 15,
    queued_separation: 20,
    separating: 35,
    writing_stems: 62,
    preview_ready: 70,
    queued_render: 72,
    rendering_master: 82,
    master_ready: 100,
    failed: 100,
  };
  return byStage[stage];
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}
