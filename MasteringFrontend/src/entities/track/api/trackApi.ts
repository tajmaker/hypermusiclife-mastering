import type { MasteringControls } from "../../mastering/model/controls";
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
): Promise<TrackRecord> {
  const response = await fetch(apiUrl(`/tracks/${trackId}/render`), {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      profile: "safe",
      mastering_preset: "balanced",
      controls,
    }),
  });
  return parseJsonResponse<TrackRecord>(response);
}
