import type { EqBand, MasteringControls, MixMode, MixProject } from "../../mastering/model/controls";
import type { TrackRecord } from "../model/types";
import { apiUrl, parseJsonResponse } from "../../../shared/api/http";

export async function uploadTrackFile(file: File): Promise<TrackRecord> {
  const form = new FormData();
  form.append("file", file);

  const response = await fetch(apiUrl("/tracks"), {
    method: "POST",
    body: form,
  });
  return parseJsonResponse<TrackRecord>(response);
}

export async function fetchTrack(trackId: string): Promise<TrackRecord> {
  const response = await fetch(apiUrl(`/tracks/${trackId}`));
  return parseJsonResponse<TrackRecord>(response);
}

export async function requestTrackRender(
  trackId: string,
  controls: MasteringControls,
  mixMode: MixMode,
  mixProject?: MixProject,
): Promise<TrackRecord> {
  const response = await fetch(apiUrl(`/tracks/${trackId}/render`), {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      profile: "safe",
      mastering_preset: "balanced",
      mix_mode: mixMode,
      controls,
      mix_project: mixProject ? serializeMixProject(mixProject) : undefined,
    }),
  });
  return parseJsonResponse<TrackRecord>(response);
}

function serializeMixProject(project: MixProject) {
  return {
    mode: project.mode,
    stems: Object.fromEntries(
      Object.entries(project.stems).map(([stem, processing]) => [
        stem,
        {
          gain_db: processing.gainDb,
          muted: processing.muted,
          solo: processing.solo,
          eq_bands: processing.eqBands.map(serializeEqBand),
        },
      ]),
    ),
  };
}

function serializeEqBand(band: EqBand) {
  return {
    id: band.id,
    type: band.type,
    frequency_hz: band.frequencyHz,
    gain_db: band.gainDb,
    q: band.q,
    enabled: band.enabled,
  };
}
