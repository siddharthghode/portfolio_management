import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center text-center px-4">
      <p className="text-6xl font-bold text-gray-200">404</p>
      <h1 className="text-xl font-semibold text-gray-800 mt-4">Page not found</h1>
      <p className="text-sm text-gray-500 mt-2">The page you're looking for doesn't exist.</p>
      <Link to="/dashboard"
        className="mt-6 text-sm bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md transition-colors">
        Go to Dashboard
      </Link>
    </div>
  );
}
