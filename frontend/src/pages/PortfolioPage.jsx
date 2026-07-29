import { useState, useEffect } from "react";
import { usePortfolio } from "../hooks/usePortfolio";
import portfolioService from "../services/portfolioService";

export default function PortfolioPage() {
  const { portfolio, loading, error, refetch } = usePortfolio();
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");

  useEffect(() => {
    if (portfolio) setForm(portfolio);
  }, [portfolio]);

  const set = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setSaveError("");
    try {
      if (portfolio) {
        await portfolioService.updatePortfolio(portfolio.id, form);
      } else {
        await portfolioService.createPortfolio(form);
      }
      await refetch();
      setEditing(false);
    } catch (err) {
      const errors = err.response?.data?.errors;
      if (errors && typeof errors === "object") {
        const messages = Object.entries(errors)
          .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(", ") : v}`)
          .join(" | ");
        setSaveError(messages);
      } else {
        setSaveError("Failed to save portfolio.");
      }
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <Spinner />;
  if (error) return <p className="text-center text-red-500 py-20">{error}</p>;

  if (!portfolio && !editing) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-20 text-center">
        <p className="text-gray-500 mb-4">No portfolio found. Create one to get started.</p>
        <button onClick={() => { setForm(emptyForm); setEditing(true); }}
          className="bg-blue-600 hover:bg-blue-700 text-white text-sm px-4 py-2 rounded-md transition-colors">
          Create Portfolio
        </button>
      </div>
    );
  }

  if (editing && form) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-10">
        <h1 className="text-xl font-bold text-gray-900 mb-6">
          {portfolio ? "Edit Portfolio" : "Create Portfolio"}
        </h1>
        {saveError && (
          <p className="text-sm text-red-600 bg-red-50 rounded-md px-3 py-2 mb-4">{saveError}</p>
        )}
        <form onSubmit={handleSave} className="space-y-4">
          {[
            { label: "Full Name", field: "full_name" },
            { label: "Headline", field: "headline" },
            { label: "GitHub URL", field: "github" },
            { label: "LinkedIn URL", field: "linkedin" },
          ].map(({ label, field }) => (
            <div key={field}>
              <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
              <input
                type="text"
                value={form[field] || ""}
                onChange={set(field)}
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          ))}
          {[
            { label: "Bio", field: "bio" },
            { label: "Skills (comma-separated)", field: "skills" },
          ].map(({ label, field }) => (
            <div key={field}>
              <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
              <textarea
                rows={3}
                value={form[field] || ""}
                onChange={set(field)}
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          ))}
          <div className="flex gap-3 pt-2">
            <button type="submit" disabled={saving}
              className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm px-4 py-2 rounded-md transition-colors">
              {saving ? "Saving…" : "Save"}
            </button>
            <button type="button" onClick={() => setEditing(false)}
              className="text-sm text-gray-600 hover:text-gray-900 px-4 py-2 rounded-md border border-gray-300 transition-colors">
              Cancel
            </button>
          </div>
        </form>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-10">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{portfolio.full_name}</h1>
          {portfolio.headline && <p className="text-blue-600 text-sm mt-1">{portfolio.headline}</p>}
        </div>
        <button onClick={() => { setForm(portfolio); setEditing(true); }}
          className="text-sm bg-gray-100 hover:bg-gray-200 text-gray-700 px-3 py-1.5 rounded-md transition-colors">
          Edit
        </button>
      </div>

      <Section title="Bio">
        <p className="text-sm text-gray-700 whitespace-pre-line">{portfolio.bio}</p>
      </Section>

      <Section title="Skills">
        <div className="flex flex-wrap gap-2">
          {portfolio.skills.split(",").map((s) => s.trim()).filter(Boolean).map((skill) => (
            <span key={skill} className="bg-blue-50 text-blue-700 text-xs px-2.5 py-1 rounded-full">
              {skill}
            </span>
          ))}
        </div>
      </Section>

      <Section title="Links">
        <div className="flex gap-4">
          {portfolio.github && (
            <a href={portfolio.github} target="_blank" rel="noreferrer"
              className="text-sm text-blue-600 hover:underline">GitHub</a>
          )}
          {portfolio.linkedin && (
            <a href={portfolio.linkedin} target="_blank" rel="noreferrer"
              className="text-sm text-blue-600 hover:underline">LinkedIn</a>
          )}
          {!portfolio.github && !portfolio.linkedin && (
            <p className="text-sm text-gray-400">No links added.</p>
          )}
        </div>
      </Section>
    </div>
  );
}

const emptyForm = { full_name: "", headline: "", bio: "", skills: "", github: "", linkedin: "" };

function Section({ title, children }) {
  return (
    <div className="mb-6">
      <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">{title}</h2>
      {children}
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
