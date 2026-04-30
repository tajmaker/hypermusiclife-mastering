import type { MasteringControls, MixMode } from "../../../entities/mastering/model/controls";
import { requestTrackRender } from "../../../entities/track/api/trackApi";
import type { TrackRecord } from "../../../entities/track/model/types";

export async function renderTrack(
  trackId: string,
  controls: MasteringControls,
  mixMode: MixMode,
): Promise<TrackRecord> {
  return requestTrackRender(trackId, controls, mixMode);
}
