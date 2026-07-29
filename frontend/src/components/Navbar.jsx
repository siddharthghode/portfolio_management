// src/components/Navbar.jsx
//
// Shared navigation bar rendered by MainLayout on every authenticated page.
// Uses useAuth() to access the current user and logout action.
// Uses React Router's <Link> and <NavLink> — these update the URL without
// a full page reload, preserving React state and avoiding network requests.

import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const linkClass = ({ isActive }) =>
    `text-sm font-medium transition-colors ${
      isActive ? "text-blue-600" : "text-gray-600 hover:text-gray-900"
    }`;

  return (
    <nav className="bg-white border-b border-gray-200 sticky top-0 z-10">
      <div className="container mx-auto px-4 max-w-5xl flex items-center justify-between h-14">
        <NavLink to="/dashboard" className="font-bold text-gray-900 text-lg">
          {import.meta.env.VITE_APP_NAME}
        </NavLink>

        <div className="flex items-center gap-6">
          <NavLink to="/dashboard" className={linkClass}>
            Dashboard
          </NavLink>
          <NavLink to="/portfolio" className={linkClass}>
            Portfolio
          </NavLink>
          <NavLink to="/projects" className={linkClass}>
            Projects
          </NavLink>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-500">{user?.username}</span>
          <button
            onClick={handleLogout}
            className="text-sm bg-gray-100 hover:bg-gray-200 text-gray-700 px-3 py-1.5 rounded-md transition-colors"
          >
            Logout
          </button>
        </div>
      </div>
    </nav>
  );
}
