import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import sessionService from "../services/sessionService";
import { getDeviceIcon, getBrowserIcon, formatSessionDate } from "../utils/deviceInfo";

const EVENT_LABELS = {
  LOGIN_SUCCESS: "Login",
  LOGIN_FAILED: "Failed login",
  LOGOUT: "Logout",
  SESSION_REVOKED: "Session revoked",
  SESSION_REVOKE_OTHERS: "Revoked other sessions",
  NEW_DEVICE_OBSERVED: "New device observed",
  TOKEN_REFRESH: "Token refreshed",
  REFRESH_REJECTED: "Refresh rejected",
};

const EVENT_COLORS = {
  LOGIN_SUCCESS: "bg-green-100 text-green-700",
  LOGIN_FAILED: "bg-red-100 text-red-700",
  LOGOUT: "bg-gray-100 text-gray-600",
  SESSION_REVOKED: "bg-orange-100 text-orange-700",
  SESSION_REVOKE_OTHERS: "bg-orange-100 text-orange-700",
  NEW_DEVICE_OBSERVED: "bg-yellow-100 text-yellow-700",
  TOKEN_REFRESH: "bg-blue-50 text-blue-600",
  REFRESH_REJECTED: "bg-red-100 text-red-700",
};

export default function ActiveSessionsPage() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [tab, setTab] = useState("sessions");
  const [sessions, setSessions] = useState([]);
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [confirm, setConfirm] = useState(null); // { type: "revoke"|"revoke-others", id? }
  const [acting, setActing] = useState(false);
  const [success, setSuccess] = useState("");

  const fetchSessions = useCallback(async (isBackground = false) => {
    if (!isBackground) setLoading(true);
    setError("");
    try {
      const data = await sessionService.getSessions();
      const list = Array.isArray(data) ? data : (data?.results || []);
      setSessions(list);
    } catch {
      if (!isBackground) setError("Failed to load sessions.");
    } finally {
      if (!isBackground) setLoading(false);
    }
  }, []);

  const fetchEvents = useCallback(async (isBackground = false) => {
    if (!isBackground) setLoading(true);
    setError("");
    try {
      const data = await sessionService.getSecurityEvents();
      const list = Array.isArray(data) ? data : (data?.results || []);
      setEvents(list);
    } catch {
      if (!isBackground) setError("Failed to load security events.");
    } finally {
      if (!isBackground) setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (tab === "sessions") fetchSessions();
    else fetchEvents();
  }, [tab, fetchSessions, fetchEvents]);

  // Keep sessions in sync when switching between browser windows
  useEffect(() => {
    const handleFocus = () => {
      if (tab === "sessions") fetchSessions(true);
      else fetchEvents(true);
    };

    window.addEventListener("focus", handleFocus);
    const onVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        handleFocus();
      }
    };
    document.addEventListener("visibilitychange", onVisibilityChange);

    const interval = setInterval(() => {
      if (document.visibilityState === "visible") {
        handleFocus();
      }
    }, 15000);

    return () => {
      window.removeEventListener("focus", handleFocus);
      document.removeEventListener("visibilitychange", onVisibilityChange);
      clearInterval(interval);
    };
  }, [tab, fetchSessions, fetchEvents]);

  const handleRevoke = async () => {
    if (!confirm) return;
    setActing(true);
    setSuccess("");
    try {
      if (confirm.type === "revoke") {
        const result = await sessionService.revokeSession(confirm.id);
        setSuccess("Session revoked.");
        if (result.was_current) {
          await logout();
          navigate("/login");
          return;
        }
      } else {
        const result = await sessionService.revokeOthers();
        setSuccess(result.message);
      }
      await fetchSessions();
    } catch {
      setError("Action failed. Please try again.");
    } finally {
      setActing(false);
      setConfirm(null);
    }
  };

  const fmt = (dt) => formatSessionDate(dt);

  const sortedSessions = [...sessions].sort((a, b) => {
    if (a.is_current && !b.is_current) return -1;
    if (!a.is_current && b.is_current) return 1;
    return new Date(b.last_seen_at || b.created_at) - new Date(a.last_seen_at || a.created_at);
  });

  const otherCount = sortedSessions.filter((s) => !s.is_current).length;

  return (
    <div className="max-w-3xl mx-auto px-4 py-10">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">Sessions & Security</h1>
      <p className="text-sm text-gray-500 mb-6">Manage where you're logged in and review security activity.</p>

      {success && (
        <div className="bg-green-50 border border-green-200 text-green-700 rounded-lg px-4 py-3 text-sm mb-4">
          {success}
        </div>
      )}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm mb-4">
          {error}
        </div>
      )}

      {/* Tabs and Refresh button */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex gap-1 bg-gray-100 rounded-lg p-1 w-fit">
          {["sessions", "events"].map((t) => (
            <button
              key={t}
              onClick={() => { setTab(t); setError(""); setSuccess(""); }}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                tab === t ? "bg-white text-gray-900 shadow-sm" : "text-gray-500 hover:text-gray-700"
              }`}
            >
              {t === "sessions" ? "Active Sessions" : "Security Events"}
            </button>
          ))}
        </div>

        <button
          onClick={tab === "sessions" ? fetchSessions : fetchEvents}
          disabled={loading}
          className="text-xs bg-white border border-gray-200 hover:bg-gray-50 text-gray-700 px-3 py-1.5 rounded-lg transition-colors font-medium flex items-center gap-1.5 shadow-2xs"
          title="Refresh list"
        >
          <span>↻</span> Refresh
        </button>
      </div>

      {loading ? (
        <Spinner />
      ) : tab === "sessions" ? (
        <>
          {sessions.length === 0 ? (
            <p className="text-center text-gray-400 py-16">No active sessions found.</p>
          ) : (
            <div className="space-y-3 mb-6">
              {sortedSessions.map((s) => (
                <div
                  key={s.id}
                  className={`bg-white border rounded-xl p-4 flex items-start justify-between gap-4 ${
                    s.is_current ? "border-blue-300 ring-1 ring-blue-200" : "border-gray-200"
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <span className="text-2xl mt-0.5">{getBrowserIcon(s.browser, s.device_type)}</span>
                    <div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-semibold text-gray-900">{s.device_name}</span>
                        {s.browser?.toLowerCase().includes("brave") && (
                          <span className="text-xs bg-orange-100 text-orange-700 px-2 py-0.5 rounded-full font-medium">
                            Brave
                          </span>
                        )}
                        {s.browser?.toLowerCase().includes("chrome") && !s.browser?.toLowerCase().includes("brave") && (
                          <span className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full font-medium">
                            Chrome
                          </span>
                        )}
                        {s.browser?.toLowerCase().includes("firefox") && (
                          <span className="text-xs bg-amber-50 text-amber-700 px-2 py-0.5 rounded-full font-medium">
                            Firefox
                          </span>
                        )}
                        {s.is_current && (
                          <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full font-medium">
                            Current
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-gray-500 mt-0.5">
                        {[s.browser, s.operating_system].filter(Boolean).join(" · ")}
                        {s.ip_address && ` · ${s.ip_address}`}
                      </p>
                      <p className="text-xs text-gray-400 mt-1">
                        Signed in {fmt(s.created_at)} · Last active {fmt(s.last_seen_at)}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => setConfirm({ type: "revoke", id: s.id, label: s.device_name })}
                    className="shrink-0 text-xs text-red-500 hover:text-red-700 border border-red-200 hover:border-red-400 px-2.5 py-1 rounded-md transition-colors"
                  >
                    {s.is_current ? "Sign out" : "Revoke"}
                  </button>
                </div>
              ))}
            </div>
          )}

          {otherCount > 0 && (
            <button
              onClick={() => setConfirm({ type: "revoke-others" })}
              className="w-full text-sm border border-red-200 text-red-600 hover:bg-red-50 py-2.5 rounded-xl transition-colors"
            >
              Sign out of {otherCount} other session{otherCount > 1 ? "s" : ""}
            </button>
          )}
        </>
      ) : (
        <div className="space-y-2">
          {events.length === 0 ? (
            <p className="text-center text-gray-400 py-16">No security events found.</p>
          ) : (
            events.map((e) => (
              <div key={e.id} className="bg-white border border-gray-200 rounded-xl px-4 py-3 flex items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${EVENT_COLORS[e.event_type] || "bg-gray-100 text-gray-600"}`}>
                    {EVENT_LABELS[e.event_type] || e.event_type}
                  </span>
                  {e.detail && <span className="text-xs text-gray-500">{e.detail}</span>}
                </div>
                <span className="text-xs text-gray-400 shrink-0">{fmt(e.created_at)}</span>
              </div>
            ))
          )}
        </div>
      )}

      {/* Confirm Dialog */}
      {confirm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-lg w-full max-w-sm p-6">
            <h2 className="text-base font-semibold text-gray-900 mb-2">
              {confirm.type === "revoke" ? "Revoke session?" : "Sign out of other sessions?"}
            </h2>
            <p className="text-sm text-gray-500 mb-5">
              {confirm.type === "revoke"
                ? `This will immediately sign out "${confirm.label}". This cannot be undone.`
                : `This will sign out all sessions except your current one.`}
            </p>
            <div className="flex gap-3">
              <button
                onClick={handleRevoke}
                disabled={acting}
                className="bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white text-sm font-medium px-4 py-2 rounded-md transition-colors"
              >
                {acting ? "Processing…" : "Confirm"}
              </button>
              <button
                onClick={() => setConfirm(null)}
                className="text-sm text-gray-600 hover:text-gray-900 px-4 py-2 rounded-md border border-gray-300 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Spinner() {
  return (
    <div className="flex justify-center py-20">
      <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
    </div>
  );
}
