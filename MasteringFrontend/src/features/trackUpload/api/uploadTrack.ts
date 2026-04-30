import { uploadTrackFile } from "../../../entities/track/api/trackApi";
import type { TrackRecord } from "../../../entities/track/model/types";

export async function uploadTrack(file: File): Promise<TrackRecord> {
  return uploadTrackFile(file);
}
