import axios from "axios";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "https://gdrive-rag-system-h5sf.onrender.com";

console.log("ZENTRA API BASE URL:", API_BASE_URL);

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

  (error) => {
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
