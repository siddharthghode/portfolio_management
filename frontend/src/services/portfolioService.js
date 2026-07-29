// src/services/portfolioService.js
//
// All Portfolio API calls in one place.
// Maps directly to the Django backend endpoints:
//   GET    /api/portfolio/       → list (returns paginated)
//   POST   /api/portfolio/       → create
//   GET    /api/portfolio/<id>/  → retrieve
//   PUT    /api/portfolio/<id>/  → update
//   DELETE /api/portfolio/<id>/  → destroy

import axiosInstance from "../api/axiosInstance";

const portfolioService = {
  getPortfolio: async () => {
    const response = await axiosInstance.get("/portfolio/");
    // Backend returns paginated: { count, next, previous, results: [...] }
    // We return results[0] since each user has exactly one portfolio.
    return response.data.results?.[0] || null;
  },

  createPortfolio: async (data) => {
    const response = await axiosInstance.post("/portfolio/", data);
    return response.data;
  },

  updatePortfolio: async (id, data) => {
    const response = await axiosInstance.put(`/portfolio/${id}/`, data);
    return response.data;
  },

  deletePortfolio: async (id) => {
    const response = await axiosInstance.delete(`/portfolio/${id}/`);
    return response.data;
  },
};

export default portfolioService;
