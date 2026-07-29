// src/hooks/useProjects.js
//
// Encapsulates project list fetching with support for the backend's
// search, filter, and ordering query params.
// Pages call: const { projects, loading, error, refetch } = useProjects({ search: "django" })

import { useState, useEffect, useCallback } from "react";
import projectService from "../services/projectService";

export function useProjects(params = {}) {
  const [projects, setProjects] = useState([]);
  const [pagination, setPagination] = useState({ count: 0, next: null, previous: null });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Serialize params to a string so useEffect dependency comparison works correctly.
  // Objects are compared by reference in JS — without this, the effect would
  // re-run on every render even if the params values haven't changed.
  const paramKey = JSON.stringify(params);

  const fetchProjects = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await projectService.getProjects(params);
      setProjects(data.results || []);
      setPagination({ count: data.count, next: data.next, previous: data.previous });
    } catch (err) {
      setError(err.response?.data?.errors || "Failed to load projects.");
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paramKey]);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  return { projects, pagination, loading, error, refetch: fetchProjects };
}
