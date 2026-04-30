import { useEffect, useRef, useState } from "react";
import type { PlaybackSnapshot } from "../lib/StemMixer";

type Params = {
  enabled: boolean;
  readSnapshot: () => PlaybackSnapshot;
};

export function usePlaybackTelemetry({enabled, readSnapshot}: Params): PlaybackSnapshot {
  const [snapshot, setSnapshot] = useState(readSnapshot);
  const readSnapshotRef = useRef(readSnapshot);
  readSnapshotRef.current = readSnapshot;

  useEffect(() => {
    if (!enabled) {
      setSnapshot(readSnapshotRef.current());
      return;
    }

    let frameId = 0;
    let disposed = false;

    const tick = () => {
      if (disposed) return;
      setSnapshot(readSnapshotRef.current());
      frameId = window.requestAnimationFrame(tick);
    };

    frameId = window.requestAnimationFrame(tick);

    return () => {
      disposed = true;
      window.cancelAnimationFrame(frameId);
    };
  }, [enabled]);

  return snapshot;
}
