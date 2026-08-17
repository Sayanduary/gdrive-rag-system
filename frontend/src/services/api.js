import axios from "axios";

// Determine base URL:
// In production (Vercel deployment or non-localhost), ALWAYS use relative URL ("")
// so requests pass through Vercel's same-origin proxy (/api/* -> Render backend).
// This guarantees session cookies are set/sent as 1st-party cookies, avoiding browser
// 3rd-party cookie blocks.
// In local development (localhost), use VITE_API_BASE_URL or fallback to http://localhost:8000.
const isLocalhost =
  typeof window !== "undefined" &&
  (window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1");

const API_BASE_URL = isLocalhost
  ? import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"
  : "";

console.log(
  "ZENTRA API BASE URL:",
  API_BASE_URL === "" ? "(relative – Vercel proxy)" : API_BASE_URL,
);

const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,

  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use(
  (config) => {
    console.log("API REQUEST:", {
      method: config.method,
      url: `${config.baseURL}${config.url}`,
    });

    return config;
  },

  (error) => Promise.reject(error),
);

api.interceptors.response.use(
  (response) => {
    console.log("API RESPONSE:", {
      url:
        response.request?.responseURL ||
        `${response.config.baseURL}${response.config.url}`,

      status: response.status,

      data: response.data,
    });

    // DO NOT change this to response.data
    return response;
  },

  async (error) => {
    const config = error.config;

    // Retry transient 502 / 503 Bad Gateway / Service Unavailable errors once (e.g. Render container swap)
    if (
      (error.response?.status === 502 || error.response?.status === 503) &&
      config &&
      !config._retry
    ) {
      config._retry = true;
      console.warn(
        `Transient ${error.response.status} Bad Gateway detected. Retrying ${config.url} in 1.5s...`,
      );
      await new Promise((resolve) => setTimeout(resolve, 1500));
      return api(config);
    }

    console.error("API ERROR:", {
      url: error.config
        ? `${error.config.baseURL}${error.config.url}`
        : undefined,

      status: error.response?.status,

      data: error.response?.data,
    });

    return Promise.reject(error);
  },
);

export default api;
