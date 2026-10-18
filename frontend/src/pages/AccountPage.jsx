import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function AccountPage() {
  const { user, refreshUser, updateProfile, logout } = useAuth();
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({
    email: "",
    first_name: "",
    last_name: "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  useEffect(() => {
    if (user) {
      setForm({
        email: user.email || "",
        first_name: user.first_name || "",
        last_name: user.last_name || "",
      });
    }
  }, [user]);

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      await updateProfile(form);
      setSuccess("Account details updated successfully!");
      setEditing(false);
    } catch (err) {
      const errData = err.response?.data;
      if (errData && typeof errData === "object") {
        const messages = Object.entries(errData)
          .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(", ") : v}`)
          .join(" | ");
        setError(messages);
      } else {
        setError("Failed to update account details.");
      }
    } finally {
      setSaving(false);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return "Never";
    try {
      return new Date(dateString).toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return dateString;
    }
  };

  const initial = (user?.username || "U")[0].toUpperCase();
  const fullName = [user?.first_name, user?.last_name].filter(Boolean).join(" ");

  return (
    <div className="max-w-4xl mx-auto px-4 py-10">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-full bg-blue-600 text-white flex items-center justify-center text-2xl font-bold shadow-sm">
            {initial}
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              {fullName || user?.username}
            </h1>
            <p className="text-sm text-gray-500">@{user?.username}</p>
          </div>
        </div>

        {!editing && (
          <button
            onClick={() => {
              setError("");
              setSuccess("");
              setEditing(true);
            }}
            className="self-start sm:self-auto bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded-md transition-colors"
          >
            Edit Profile
          </button>
        )}
      </div>

      {success && (
        <div className="bg-green-50 border border-green-200 text-green-700 rounded-lg px-4 py-3 text-sm mb-6">
          {success}
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm mb-6">
          {error}
        </div>
      )}

      {/* Editing Form */}
      {editing ? (
        <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm mb-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Edit Account Details</h2>
          <form onSubmit={handleSave} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Username (read-only)
              </label>
              <input
                type="text"
                disabled
                value={user?.username || ""}
                className="w-full bg-gray-50 border border-gray-200 rounded-md px-3 py-2 text-sm text-gray-500 cursor-not-allowed"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
              <input
                type="email"
                required
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">First Name</label>
                <input
                  type="text"
                  value={form.first_name}
                  onChange={(e) => setForm({ ...form, first_name: e.target.value })}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Last Name</label>
                <input
                  type="text"
                  value={form.last_name}
                  onChange={(e) => setForm({ ...form, last_name: e.target.value })}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <div className="flex gap-3 pt-2">
              <button
                type="submit"
                disabled={saving}
                className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium px-4 py-2 rounded-md transition-colors"
              >
                {saving ? "Saving…" : "Save Changes"}
              </button>
              <button
                type="button"
                onClick={() => setEditing(false)}
                className="text-sm text-gray-600 hover:text-gray-900 px-4 py-2 rounded-md border border-gray-300 transition-colors"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      ) : null}

      {/* Account Details Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        {/* Personal Details */}
        <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
          <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-4">
            Account Information
          </h2>
          <dl className="space-y-4">
            <DetailItem label="User ID" value={`#${user?.id}`} />
            <DetailItem label="Username" value={user?.username} />
            <DetailItem label="Email Address" value={user?.email || "Not provided"} />
            <DetailItem label="First Name" value={user?.first_name || "—"} />
            <DetailItem label="Last Name" value={user?.last_name || "—"} />
          </dl>
        </div>

        {/* Activity & Connected Status */}
        <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm flex flex-col justify-between">
          <div>
            <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-4">
              Activity & Portfolio Status
            </h2>
            <dl className="space-y-4">
              <DetailItem
                label="Member Since"
                value={formatDate(user?.date_joined)}
              />
              <DetailItem
                label="Last Login"
                value={formatDate(user?.last_login)}
              />
              <div>
                <dt className="text-xs font-medium text-gray-400">Portfolio</dt>
                <dd className="mt-1 flex items-center justify-between">
                  <span
                    className={`inline-flex items-center text-xs font-medium px-2.5 py-0.5 rounded-full ${
                      user?.has_portfolio
                        ? "bg-green-100 text-green-800"
                        : "bg-yellow-100 text-yellow-800"
                    }`}
                  >
                    {user?.has_portfolio ? "Configured" : "Not created yet"}
                  </span>
                  <Link
                    to="/portfolio"
                    className="text-xs text-blue-600 hover:underline"
                  >
                    {user?.has_portfolio ? "View Portfolio →" : "Set up now →"}
                  </Link>
                </dd>
              </div>

              <div>
                <dt className="text-xs font-medium text-gray-400">Projects</dt>
                <dd className="mt-1 flex items-center justify-between">
                  <span className="text-sm font-semibold text-gray-900">
                    {user?.projects_count ?? 0} {user?.projects_count === 1 ? "project" : "projects"}
                  </span>
                  <Link
                    to="/projects"
                    className="text-xs text-blue-600 hover:underline"
                  >
                    Manage Projects →
                  </Link>
                </dd>
              </div>
            </dl>
          </div>

          <div className="mt-6 pt-4 border-t border-gray-100 flex items-center justify-between">
            <Link
              to="/settings/sessions"
              className="text-xs text-blue-600 hover:text-blue-800 hover:underline font-medium"
            >
              Active Sessions & Devices →
            </Link>
            <button
              onClick={logout}
              className="text-xs text-red-600 hover:text-red-700 hover:underline"
            >
              Sign out from this device
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function DetailItem({ label, value }) {
  return (
    <div>
      <dt className="text-xs font-medium text-gray-400">{label}</dt>
      <dd className="mt-1 text-sm font-semibold text-gray-900">{value}</dd>
    </div>
  );
}
