import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  applyStemState,
  defaultControls,
  defaultStemControlState,
  type MasteringControls,
  type MixMode,
  type StemControlState,
} from "../../../entities/mastering/model/controls";
import { fetchTrack } from "../../../entities/track/api/trackApi";
import { isMixReady, type TrackRecord } from "../../../entities/track/model/types";
import { StemMixer } from "../../../features/liveStemMix/lib/StemMixer";
import { renderTrack } from "../../../features/trackRender/api/renderTrack";
import { uploadTrack } from "../../../features/trackUpload/api/uploadTrack";
import { validateAudioFile } from "../../../features/trackUpload/lib/validateAudioFile";

const INITIAL_MESSAGE = "Загрузите WAV/MP3 и дождитесь подготовки микса.";
const POLL_INTERVAL_MS = 3500;

export function useMasteringSession() {
  const [track, setTrack] = useState<TrackRecord | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [controls, setControls] = useState<MasteringControls>(defaultControls);
  const [stemState, setStemState] = useState<StemControlState>(defaultStemControlState);
  const [mixMode, setMixMode] = useState<MixMode>("delta");
  const [message, setMessage] = useState(INITIAL_MESSAGE);
  const [busy, setBusy] = useState(false);
  const [playing, setPlaying] = useState(false);
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
    mixer.current.applyControls(effectiveControls);
  }, [effectiveControls]);

  useEffect(() => {
    if (!track || track.status !== "ready_to_mix" || mixerReady) {
      return;
    }

    const loadToken = loadTokenRef.current + 1;
    loadTokenRef.current = loadToken;
    setMessage("Стемы готовы. Загружаю их в браузер для живого управления.");
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
        setMessage("Нажмите Play и двигайте ручки во время прослушивания.");
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
    loadTokenRef.current += 1;
    setStemState(defaultStemControlState);
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
      return;
    }

    setPlaying(mixer.current.play(effectiveControls));
  }

  function resetPlayback() {
    mixer.current.stop();
    setPlaying(false);
  }

  function startOver() {
    loadTokenRef.current += 1;
    void mixer.current.dispose();
    setTrack(null);
    setFileName(null);
    setPlaying(false);
    setMixerReady(false);
    setControls(defaultControls);
    setStemState(defaultStemControlState);
    setMixMode("delta");
    setMessage(INITIAL_MESSAGE);
  }

  function resetControls() {
    setControls(defaultControls);
    setStemState(defaultStemControlState);
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
    setMessage("Рендерю финальный мастер с текущими ручками.");

    try {
      const updated = await renderTrack(track.track_id, effectiveControls, mixMode);
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
      fileName,
      message,
      mixerReady,
      mixMode,
      playing,
      readPlaybackSnapshot,
      stemState,
      track,
      uploadDisabled,
    },
    actions: {
      changeControls: setControls,
      changeMixMode,
      changeStemState: setStemState,
      render,
      resetControls,
      resetPlayback,
      startOver,
      togglePlayback,
      upload,
    },
  };
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}
