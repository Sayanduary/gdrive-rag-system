import axios from "axios";

const api = axios.create({
  baseURL: "https://gdrive-rag-system-h5sf.onrender.com",
  withCredentials: true,
});

export default api;
