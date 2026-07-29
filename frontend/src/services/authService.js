// src/services/authService.js
//
// WHY THIS FILE EXISTS:
// Components should not know about API endpoints, token storage,
// or request structure. That's business logic, not UI logic.
// Services are the bridge between components and the API.
// A component calls authService.login(data) and gets back a user —
// it never touches axios, localStorage, or endpoint strings directly.

import axiosInstance from "../api/axiosInstance";

const authService = {
  login: async (credentials) => {
    // POST /api/login/ → { access, refresh }
    const response = await axiosInstance.post("/login/", credentials);
    const { access, refresh } = response.data;
    localStorage.setItem("access_token", access);
    localStorage.setItem("refresh_token", refresh);
    return response.data;
  },

  register: async (userData) => {
    // POST /api/register/ → { message: "Registration successful" }
    const response = await axiosInstance.post("/register/", userData);
    return response.data;
  },

  logout: () => {
    // JWT is stateless — logout is client-side only.
    // We simply remove the tokens from storage.
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
  },

  refreshToken: async () => {
    // POST /api/token/refresh/ → { access }
    // Called when the access token expires but refresh token is still valid.
    const refresh = localStorage.getItem("refresh_token");
    const response = await axiosInstance.post("/token/refresh/", { refresh });
    localStorage.setItem("access_token", response.data.access);
    return response.data.access;
  },

  getMe: async () => {
    // GET /api/me/ → { id, username, email }
    const response = await axiosInstance.get("/me/");
    return response.data;
  },

  isAuthenticated: () => {
    return !!localStorage.getItem("access_token");
  },
};

export default authService;
