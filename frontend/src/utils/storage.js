// src/utils/storage.js
//
// WHY THIS FILE EXISTS:
// Raw localStorage calls scattered across the codebase are hard to refactor.
// If the key name changes (e.g. "access_token" → "jwt_access"), you'd need
// to find and update every occurrence. Centralizing here means one change fixes all.

export const storage = {
  getAccessToken: () => localStorage.getItem("access_token"),
  getRefreshToken: () => localStorage.getItem("refresh_token"),
  setTokens: (access, refresh) => {
    localStorage.setItem("access_token", access);
    localStorage.setItem("refresh_token", refresh);
  },
  clearTokens: () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
  },
};
