// src/hooks/usePortfolio.js
//
// WHY THIS FILE EXISTS:
// Without custom hooks, every page that needs portfolio data would repeat:
//   const [portfolio, setPortfolio] = useState(null)
//   const [loading, setLoading] = useState(true)
//   const [error, setError] = useState(null)
//   useEffect(() => { portfolioService.getPortfolio().then(...) }, [])
//
// That's 10+ lines of identical state management duplicated across pages.
// This hook encapsulates that pattern once and exposes a clean interface.
// Pages just call: const { portfolio, loading, error, refetch } = usePortfolio()

import { useState, useEffect, useCallback } from "react";
import portfolioService from "../services/portfolioService";

export function usePortfolio() {
  const [portfolio, setPortfolio] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchPortfolio = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await portfolioService.getPortfolio();
      setPortfolio(data);
    } catch (err) {
      setError(err.response?.data?.errors || "Failed to load portfolio.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPortfolio();
  }, [fetchPortfolio]);

  return { portfolio, loading, error, refetch: fetchPortfolio };
}
