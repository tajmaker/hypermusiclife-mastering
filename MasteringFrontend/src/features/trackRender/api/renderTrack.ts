import type { MasteringControls, MixMode, MixProject } from "../../../entities/mastering/model/controls";
import { requestTrackRender } from "../../../entities/track/api/trackApi";
import type { TrackRecord } from "../../../entities/track/model/types";

export async function renderTrack(
  trackId: string,
  controls: MasteringControls,
  mixMode: MixMode,
  mixProject?: MixProject,
): Promise<TrackRecord> {
  return requestTrackRender(trackId, controls, mixMode, mixProject);
}
