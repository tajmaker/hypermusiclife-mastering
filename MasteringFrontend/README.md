# Hyper Mastering Frontend

React/Vite интерфейс для stem-aware mastering MVP.

## Local Run

```powershell
npm install
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

Default API:

```text
http://127.0.0.1:8010/api/v1
```

For hosted deploy, set:

```text
VITE_API_URL=https://YOUR-HUGGINGFACE-SPACE.hf.space/api/v1
```

## Flow

1. Upload an audio file.
2. Backend separates it into virtual stems.
3. Browser loads stems through Web Audio API.
4. User changes controls while listening.
5. Backend renders final downloadable master.

## Current MVP Limits

- Live preview is browser-side and approximate.
- Final render still happens on the backend.
- Waveform and A/B compare are planned next.
