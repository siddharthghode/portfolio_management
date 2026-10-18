import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { usePortfolio } from "../hooks/usePortfolio";
import { useProjects } from "../hooks/useProjects";

export default function DashboardPage() {
  const { user } = useAuth();
  const { portfolio, loading: pLoading } = usePortfolio();
  const { pagination, loading: prLoading } = useProjects();

  return (
    <div className="max-w-5xl mx-auto px-4 py-10">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 mb-1">
            Welcome back, {user?.first_name || user?.username} 👋
          </h1>
          <p className="text-gray-500 text-sm">
            {user?.last_login
              ? `Last login: ${new Date(user.last_login).toLocaleString()}`
              : "Here's an overview of your portfolio."}
          </p>
        </div>
        <Link
          to="/account"
          className="text-xs bg-white border border-gray-200 hover:border-gray-300 text-gray-700 px-3 py-1.5 rounded-lg transition-colors font-medium shadow-xs"
        >
          My Account →
        </Link>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-10">
        <StatCard
          label="Portfolio"
          value={pLoading ? "…" : portfolio ? "Set up" : "Not set up"}
          sub={portfolio?.full_name}
          to="/portfolio"
        />
        <StatCard
          label="Projects"
          value={prLoading ? "…" : pagination.count}
          sub="total projects"
          to="/projects"
        />
        <StatCard
          label="Skills"
          value={pLoading ? "…" : portfolio?.skills ? portfolio.skills.split(",").length : 0}
          sub="listed skills"
          to="/portfolio"
        />
      </div>

      {portfolio && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">
            Portfolio Summary
          </h2>
          <p className="text-lg font-semibold text-gray-900">{portfolio.full_name}</p>
          {portfolio.headline && (
            <p className="text-sm text-blue-600 mt-0.5">{portfolio.headline}</p>
          )}
          <p className="text-sm text-gray-600 mt-3 line-clamp-3">{portfolio.bio}</p>
          <div className="flex gap-3 mt-4">
            {portfolio.github && (
              <a href={portfolio.github} target="_blank" rel="noreferrer"
                className="text-sm text-blue-600 hover:underline">GitHub</a>
            )}
            {portfolio.linkedin && (
              <a href={portfolio.linkedin} target="_blank" rel="noreferrer"
                className="text-sm text-blue-600 hover:underline">LinkedIn</a>
            )}
          </div>
        </div>
      )}

      {!pLoading && !portfolio && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-6 text-center">
          <p className="text-sm text-yellow-800 mb-3">You haven't set up your portfolio yet.</p>
          <Link to="/portfolio"
            className="text-sm bg-yellow-500 hover:bg-yellow-600 text-white px-4 py-2 rounded-md transition-colors">
            Set up Portfolio
          </Link>
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, sub, to }) {
  return (
    <Link to={to}
      className="bg-white border border-gray-200 rounded-xl p-5 hover:shadow-sm transition-shadow">
      <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</p>
      <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </Link>
  );
}
