// src/api/axiosInstance.js
//
// WHY THIS FILE EXISTS:
// Without a shared Axios instance, every component would need to:
//   1. Import axios directly
//   2. Manually set baseURL every time
//   3. Manually attach Authorization: Bearer <token> to every request
//   4. Manually handle 401 responses (expired token) everywhere
//
// This file creates ONE configured instance used across the entire app.
// All API calls go through this — baseURL, auth headers, and error
// handling are configured once here and work everywhere automatically.

import axios from "axios";

const axiosInstance = axios.create({
  // Reads from .env — falls back to /api if the variable is missing.
  // In dev, Vite proxies /api → http://127.0.0.1:8000/api (see vite.config.js).
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api",
  headers: {
    "Content-Type": "application/json",
  },
});

// ── Request Interceptor ──────────────────────────────────────
// Runs before every request is sent.
// Reads the access token from localStorage and injects it into
// the Authorization header automatically.
// Without this, every API call would need: headers: { Authorization: `Bearer ${token}` }
axiosInstance.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ── Response Interceptor ─────────────────────────────────────
// Runs after every response is received.
// Handles 401 Unauthorized globally — when the access token expires,
// instead of every component showing a broken state, we redirect to login.
// Later this can be extended to attempt a token refresh before redirecting.
axiosInstance.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clear stale tokens and redirect to login.
      // Using window.location instead of React Router here because
      // this file lives outside the React component tree.
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export default axiosInstance;
