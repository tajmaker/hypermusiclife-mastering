const MAX_FILE_SIZE_MB = 80;
const SUPPORTED_TYPES = ["audio/wav", "audio/mpeg", "audio/aiff", "audio/x-aiff", "audio/flac", "audio/ogg"];
const SUPPORTED_EXTENSIONS = [".wav", ".mp3", ".aiff", ".aif", ".flac", ".ogg", ".oga"];

export function validateAudioFile(file: File): string | null {
  const sizeMb = file.size / 1024 / 1024;
  if (sizeMb > MAX_FILE_SIZE_MB) {
    return `Файл слишком большой: ${sizeMb.toFixed(1)} MB. Лимит MVP: ${MAX_FILE_SIZE_MB} MB.`;
  }

  const lowerName = file.name.toLowerCase();
  const hasKnownExtension = SUPPORTED_EXTENSIONS.some((extension) => lowerName.endsWith(extension));
  const hasKnownType = file.type === "" || SUPPORTED_TYPES.includes(file.type);
  if (!hasKnownExtension || !hasKnownType) {
    return "Неподдерживаемый формат. Используйте WAV, MP3, AIFF, FLAC или OGG.";
  }

  return null;
}
