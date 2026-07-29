// src/App.jsx
//
// The root of the React application.
// Defines the entire route tree using React Router v6's declarative API.
//
// ROUTE STRUCTURE:
//
//   /                     → redirect to /dashboard
//   /login                → GuestRoute → AuthLayout → LoginPage
//   /register             → GuestRoute → AuthLayout → RegisterPage
//   /dashboard            → ProtectedRoute → MainLayout → DashboardPage
//   /portfolio            → ProtectedRoute → MainLayout → PortfolioPage
//   /projects             → ProtectedRoute → MainLayout → ProjectsPage
//   *                     → NotFoundPage
//
// WHY NESTED ROUTES:
//   React Router v6 uses layout routes — a parent route renders a layout
//   component with <Outlet />, and child routes render into that outlet.
//   This means MainLayout renders once and persists across /dashboard,
//   /portfolio, /projects navigations — no remounting, no flicker.
//
// WHY SEPARATE GUEST AND PROTECTED ROUTES:
//   GuestRoute redirects logged-in users away from /login and /register.
//   ProtectedRoute redirects logged-out users away from /dashboard etc.
//   Both check auth state from AuthContext — single source of truth.

import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";

import ProtectedRoute from "./routes/ProtectedRoute";
import GuestRoute from "./routes/GuestRoute";
import MainLayout from "./layouts/MainLayout";
import AuthLayout from "./layouts/AuthLayout";

import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import DashboardPage from "./pages/DashboardPage";
import PortfolioPage from "./pages/PortfolioPage";
import ProjectsPage from "./pages/ProjectsPage";
import NotFoundPage from "./pages/NotFoundPage";

export default function App() {
  return (
    // AuthProvider wraps everything so useAuth() works in any component.
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Root redirect */}
          <Route path="/" element={<Navigate to="/dashboard" replace />} />

          {/* Guest-only routes: redirect to /dashboard if already logged in */}
          <Route element={<GuestRoute />}>
            <Route element={<AuthLayout />}>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
            </Route>
          </Route>

          {/* Protected routes: redirect to /login if not authenticated */}
          <Route element={<ProtectedRoute />}>
            <Route element={<MainLayout />}>
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/portfolio" element={<PortfolioPage />} />
              <Route path="/projects" element={<ProjectsPage />} />
            </Route>
          </Route>

          {/* 404 catch-all */}
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
