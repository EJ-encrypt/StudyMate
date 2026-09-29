import axios from "axios";

export const apiClient = axios.create({
  // Defaults to the origin that served the page. In production the API serves
  // the frontend, so relative URLs are correct and the app works behind any
  // host name without rebuilding. Only the Vite dev server, which runs on a
  // different port from the API, needs VITE_API_BASE_URL set.
  baseURL: import.meta.env.VITE_API_BASE_URL || "",
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("studymate_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
