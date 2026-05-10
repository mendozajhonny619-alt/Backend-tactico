// src/v16/services/api.js

import axios from "axios";

const API_BASE_URL =
  process.env.REACT_APP_API_URL ||
  "https://jhonny-elite-v16-web.onrender.com";

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
});

// ===============================
// LIVE MATCHES
// ===============================

export const fetchLiveMatches = async () => {
  const { data } = await apiClient.get("/live-matches");

  // Algunos backends devuelven:
  // { items: [...] }
  // otros directamente [...]
  if (Array.isArray(data)) return data;

  if (Array.isArray(data?.items)) return data.items;

  return [];
};

export default apiClient;
