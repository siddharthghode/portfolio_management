// src/layouts/MainLayout.jsx
//
// WHY THIS FILE EXISTS:
// Without a layout component, every page would need to render its own
// Navbar and Footer, duplicating markup and making global UI changes
// require edits to every single page file.
//
// MainLayout wraps all authenticated pages. React Router renders the
// matched page into {children} via <Outlet />.
// The Navbar and Footer render once here and persist across page navigations.

import { Outlet } from "react-router-dom";
import Navbar from "../components/Navbar";

export default function MainLayout() {
  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <Navbar />
      {/* Outlet renders the matched child route's page component */}
      <main className="flex-1 container mx-auto px-4 py-8 max-w-5xl">
        <Outlet />
      </main>
      <footer className="bg-white border-t border-gray-200 py-4 text-center text-sm text-gray-500">
        © {new Date().getFullYear()} {import.meta.env.VITE_APP_NAME}
      </footer>
    </div>
  );
}
