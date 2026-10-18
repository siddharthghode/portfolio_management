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

  logout: async () => {
    // Revoke server-side session first. Clear local tokens regardless of outcome.
    try {
      await axiosInstance.post("/logout/");
    } catch {
      // Server revocation failed (e.g. already expired) — still clear locally
    } finally {
      storage.clearTokens();
    }
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

  updateMe: async (userData) => {
    const response = await axiosInstance.patch("/me/", userData);
    return response.data;
  },

  isAuthenticated: () => {
    return !!storage.getAccessToken();
  },
};

export default authService;
