// src/context/AuthContext.jsx
//
// WHY THIS FILE EXISTS:
// Without context, every component that needs to know "is the user logged in?"
// would have to read localStorage directly or receive user as a prop drilled
// down through every parent. That's fragile and repetitive.
//
// AuthContext provides a single source of truth for auth state:
//   - user: the logged-in user object (or null)
//   - isAuthenticated: boolean derived from user
//   - login / logout: actions that update state AND call the service
//
// Any component in the tree can call useAuth() to access this —
// no prop drilling, no duplicate localStorage reads.

import { createContext, useContext, useState, useEffect, useCallback } from "react";
import authService from "../services/authService";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  // loading: true while we check if a stored token is still valid on mount.
  // Without this, the app would flash the login page briefly on every refresh
  // even when the user is already authenticated.
  const [loading, setLoading] = useState(true);

  // On mount: if a token exists in localStorage, fetch the current user
  // to hydrate the auth state. If the token is expired, the axios interceptor
  // will catch the 401 and redirect to /login automatically.
  useEffect(() => {
    const hydrate = async () => {
      if (authService.isAuthenticated()) {
        try {
          const me = await authService.getMe();
          setUser(me);
        } catch {
          // Token invalid or expired — clear it.
          authService.logout();
        }
      }
      setLoading(false);
    };
    hydrate();
  }, []);

  const login = useCallback(async (credentials) => {
    await authService.login(credentials);
    const me = await authService.getMe();
    setUser(me);
    return me;
  }, []);

  // Sync logout across tabs — if tokens are cleared in another tab,
  // this tab detects the storage event and resets auth state.
  useEffect(() => {
    const handleStorage = (e) => {
      if (e.key === "access_token" && !e.newValue) {
        setUser(null);
      }
    };
    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, []);

  const logout = useCallback(() => {
    authService.logout();
    setUser(null);
  }, []);

  const value = {
    user,
    isAuthenticated: !!user,
    loading,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// Custom hook — components import useAuth() instead of useContext(AuthContext).
// This is cleaner and throws a helpful error if used outside AuthProvider.
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside <AuthProvider>");
  }
  return context;
}
