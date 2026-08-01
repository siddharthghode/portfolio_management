// src/services/authService.js
//
// WHY THIS FILE EXISTS:
// Components should not know about API endpoints, token storage,
// or request structure. That's business logic, not UI logic.
// Services are the bridge between components and the API.
// A component calls authService.login(data) and gets back a user —
// it never touches axios, localStorage, or endpoint strings directly.

import axiosInstance from "../api/axiosInstance";
import { storage } from "../utils/storage";

const authService = {
  login: async (credentials) => {
    const response = await axiosInstance.post("/login/", credentials);
    const { access, refresh } = response.data;
    storage.setTokens(access, refresh);
    return response.data;
  },

  register: async (userData) => {
    const response = await axiosInstance.post("/register/", userData);
    return response.data;
  },

  logout: () => {
    storage.clearTokens();
  },

  refreshToken: async () => {
    const refresh = storage.getRefreshToken();
    const response = await axiosInstance.post("/token/refresh/", { refresh });
    storage.setTokens(response.data.access, refresh);
    return response.data.access;
  },

  getMe: async () => {
    const response = await axiosInstance.get("/me/");
    return response.data;
  },

  isAuthenticated: () => {
    return !!storage.getAccessToken();
  },
};

export default authService;
