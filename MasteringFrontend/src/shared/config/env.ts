export const env = {
  apiUrl: (
    import.meta.env.VITE_API_URL ||
    (globalThis.location?.hostname === "127.0.0.1" || globalThis.location?.hostname === "localhost"
      ? "http://127.0.0.1:8010/api/v1"
      : "https://tajmaker-hypermusiclife.hf.space/api/v1")
  ).replace(/\/$/, ""),
};
