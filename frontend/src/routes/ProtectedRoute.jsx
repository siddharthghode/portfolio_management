// src/routes/ProtectedRoute.jsx
//
// WHY THIS FILE EXISTS:
// Without a route guard, unauthenticated users can navigate directly to
// /dashboard or /projects by typing the URL — they'd see broken pages
// or get 401 errors from the API.
//
// ProtectedRoute wraps any route that requires authentication.
// HOW IT WORKS:
//   1. While auth state is loading (token being validated on mount), show a spinner.
//   2. If not authenticated, redirect to /login using React Router's <Navigate>.
//      The `replace` prop replaces the history entry so the back button
//      doesn't return to the protected page.
//   3. If authenticated, render the child route via <Outlet>.

import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function ProtectedRoute() {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return isAuthenticated ? <Outlet /> : <Navigate to="/login" replace />;
}
