// src/routes/GuestRoute.jsx
//
// Redirects authenticated users away from login/register pages.
// Without this, a logged-in user who navigates to /login would see
// the login form — confusing and unnecessary.
// If authenticated → redirect to /dashboard.
// If not authenticated → render the auth page via <Outlet>.

import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function GuestRoute() {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return isAuthenticated ? <Navigate to="/dashboard" replace /> : <Outlet />;
}
