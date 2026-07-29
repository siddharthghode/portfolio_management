import { useState } from "react";
import { useProjects } from "../hooks/useProjects";
import projectService from "../services/projectService";

const emptyForm = { title: "", description: "", tech_stack: "", github_link: null, live_demo: null };

export default function ProjectsPage() {
  const [search, setSearch] = useState("");
  const { projects, pagination, loading, error, refetch } = useProjects({ search });
  const [modal, setModal] = useState(null); // null | { mode: "create"|"edit", data }
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");

  const openCreate = () => { setSaveError(""); setModal({ mode: "create", data: { ...emptyForm } }); };
  const openEdit = (p) => { setSaveError(""); setModal({ mode: "edit", data: { ...p } }); };
  const closeModal = () => setModal(null);

  const setField = (field) => (e) =>
    setModal((m) => ({ ...m, data: { ...m.data, [field]: e.target.value } }));

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setSaveError("");
    try {
      if (modal.mode === "edit") {
        await projectService.updateProject(modal.data.id, modal.data);
      } else {
        await projectService.createProject(modal.data);
      }
      await refetch();
      closeModal();
    } catch (err) {
      const errors = err.response?.data?.errors;
      if (errors && typeof errors === "object") {
        const messages = Object.entries(errors)
          .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(", ") : v}`)
          .join(" | ");
        setSaveError(messages);
      } else {
        setSaveError("Failed to save project.");
      }
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id) => {
    if (!confirm("Delete this project?")) return;
    await projectService.deleteProject(id);
    refetch();
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-10">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">
          Projects
          {!loading && (
            <span className="ml-2 text-sm font-normal text-gray-400">({pagination.count})</span>
          )}
        </h1>
        <button onClick={openCreate}
          className="bg-blue-600 hover:bg-blue-700 text-white text-sm px-4 py-2 rounded-md transition-colors">
          + New Project
        </button>
      </div>

      <input
        type="text"
        placeholder="Search projects…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm mb-6 focus:outline-none focus:ring-2 focus:ring-blue-500"
      />

      {loading && <Spinner />}
      {error && <p className="text-red-500 text-sm">{error}</p>}

      {!loading && projects.length === 0 && (
        <p className="text-center text-gray-400 py-20">No projects found.</p>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {projects.map((p) => (
          <div key={p.id} className="bg-white border border-gray-200 rounded-xl p-5">
            <div className="flex items-start justify-between">
              <h2 className="font-semibold text-gray-900">{p.title}</h2>
              <div className="flex gap-2 ml-2 shrink-0">
                <button onClick={() => openEdit(p)}
                  className="text-xs text-gray-500 hover:text-gray-800">Edit</button>
                <button onClick={() => handleDelete(p.id)}
                  className="text-xs text-red-400 hover:text-red-600">Delete</button>
              </div>
            </div>
            <p className="text-sm text-gray-600 mt-2 line-clamp-2">{p.description}</p>
            <div className="flex flex-wrap gap-1.5 mt-3">
              {p.tech_stack.split(",").map((t) => t.trim()).filter(Boolean).map((t) => (
                <span key={t} className="bg-gray-100 text-gray-600 text-xs px-2 py-0.5 rounded-full">{t}</span>
              ))}
            </div>
            <div className="flex gap-3 mt-3">
              {p.github_link && (
                <a href={p.github_link} target="_blank" rel="noreferrer"
                  className="text-xs text-blue-600 hover:underline">GitHub</a>
              )}
              {p.live_demo && (
                <a href={p.live_demo} target="_blank" rel="noreferrer"
                  className="text-xs text-blue-600 hover:underline">Live Demo</a>
              )}
            </div>
          </div>
        ))}
      </div>

      {modal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-lg w-full max-w-md p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              {modal.mode === "edit" ? "Edit Project" : "New Project"}
            </h2>
            {saveError && (
              <p className="text-sm text-red-600 bg-red-50 rounded-md px-3 py-2 mb-4">{saveError}</p>
            )}
            <form onSubmit={handleSave} className="space-y-3">
              {[
                { label: "Title", field: "title" },
                { label: "Tech Stack (comma-separated)", field: "tech_stack" },
                { label: "GitHub Link (optional)", field: "github_link" },
                { label: "Live Demo (optional)", field: "live_demo" },
              ].map(({ label, field }) => (
                <div key={field}>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
                  <input type="text" value={modal.data[field] || ""} onChange={setField(field)}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
              ))}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <textarea rows={3} value={modal.data.description || ""} onChange={setField("description")}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
              <div className="flex gap-3 pt-1">
                <button type="submit" disabled={saving}
                  className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm px-4 py-2 rounded-md transition-colors">
                  {saving ? "Saving…" : "Save"}
                </button>
                <button type="button" onClick={closeModal}
                  className="text-sm text-gray-600 hover:text-gray-900 px-4 py-2 rounded-md border border-gray-300 transition-colors">
                  Cancel
                </button>
              </div>
            </form>
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
