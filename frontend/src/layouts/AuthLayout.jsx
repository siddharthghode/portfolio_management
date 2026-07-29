// src/layouts/AuthLayout.jsx
//
// Wraps unauthenticated pages (Login, Register).
// Separate from MainLayout because auth pages have a different visual
// structure — centered card, no navbar, no sidebar.

import { Outlet } from "react-router-dom";

export default function AuthLayout() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">
            {import.meta.env.VITE_APP_NAME}
          </h1>
        </div>
        {/* Outlet renders Login or Register page */}
        <Outlet />
      </div>
    </div>
  );
}
