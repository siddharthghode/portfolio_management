import axios from "axios";
import { storage } from "../utils/storage";

const axiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api",
  headers: { "Content-Type": "application/json" },
});

// Decode JWT payload without a library — JWT is just base64(header).base64(payload).signature
const getTokenExpiry = (token) => {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return payload.exp * 1000; // convert to ms
  } catch {
    return null;
  }
};

const isExpiringSoon = (token) => {
  const expiry = getTokenExpiry(token);
  if (!expiry) return true;
  return expiry - Date.now() < 30_000; // refresh if < 30s remaining
};

// Track in-flight refresh to avoid multiple simultaneous refresh calls
let refreshPromise = null;

const doRefresh = () => {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      const refresh = storage.getRefreshToken();
      const response = await axios.post(
        `${import.meta.env.VITE_API_BASE_URL || "/api"}/token/refresh/`,
        { refresh }
      );
      storage.setTokens(response.data.access, refresh);
      return response.data.access;
    })().finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
};

// ── Request Interceptor ──────────────────────────────────────
// Proactively refresh the access token if it's expiring within 30s
axiosInstance.interceptors.request.use(async (config) => {
  // Skip auth header for token refresh requests to avoid infinite loop
  if (config.url?.includes("/token/refresh/")) return config;

  let token = storage.getAccessToken();

  if (token && isExpiringSoon(token)) {
    try {
      token = await doRefresh();
    } catch {
      storage.clearTokens();
      window.location.href = "/login";
      return Promise.reject(new Error("Session expired"));
    }
  }

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

// ── Response Interceptor ─────────────────────────────────────
// If a 401 slips through (race condition), attempt one silent refresh and retry
axiosInstance.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;

    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      try {
        const newToken = await doRefresh();
        original.headers.Authorization = `Bearer ${newToken}`;
        return axiosInstance(original);
      } catch {
        storage.clearTokens();
        window.location.href = "/login";
      }
    }

    return Promise.reject(error);
  }
);

export default axiosInstance;
