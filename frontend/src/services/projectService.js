// src/services/projectService.js
//
// All Project API calls in one place.
// Maps to Django backend endpoints:
//   GET    /api/projects/       → list (paginated, supports ?search=, ?ordering=, ?tech_stack=)
//   POST   /api/projects/       → create
//   GET    /api/projects/<id>/  → retrieve
//   PUT    /api/projects/<id>/  → update
//   DELETE /api/projects/<id>/  → destroy

import axiosInstance from "../api/axiosInstance";

const projectService = {
  // params: { search, ordering, tech_stack, page }
  // Axios serializes the params object into a query string automatically.
  // e.g. { search: "django", ordering: "-created_at" }
  //   → GET /api/projects/?search=django&ordering=-created_at
  getProjects: async (params = {}) => {
    const response = await axiosInstance.get("/projects/", { params });
    return response.data; // { count, next, previous, results: [...] }
  },

  getProject: async (id) => {
    const response = await axiosInstance.get(`/projects/${id}/`);
    return response.data;
  },

  createProject: async (data) => {
    const response = await axiosInstance.post("/projects/", data);
    return response.data;
  },

  updateProject: async (id, data) => {
    const response = await axiosInstance.put(`/projects/${id}/`, data);
    return response.data;
  },

  deleteProject: async (id) => {
    const response = await axiosInstance.delete(`/projects/${id}/`);
    return response.data;
  },
};

export default projectService;
