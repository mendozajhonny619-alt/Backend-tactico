// src/v16/services/api.js

import axios from "axios";

const API_BASE_URL =
  import.meta.env.VITE_API_URL || "https://backend-tactico1.onrender.com";

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
});

const normalizeArray = (data, key) => {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.items)) return data.items;
  if (key && Array.isArray(data?.[key])) return data[key];
  return [];
};

export const fetchLiveMatches = async () => {
  const { data } = await apiClient.get("/live-matches");
  return normalizeArray(data);
};

export const fetchSignals = async () => {
  const { data } = await apiClient.get("/signals");
  return normalizeArray(data, "signals");
};

export const fetchStats = async () => {
  const { data } = await apiClient.get("/stats");
  return data || {};
};

export const fetchHistory = async () => {
  const { data } = await apiClient.get("/history");
  return normalizeArray(data, "history");
};

export const fetchOpportunities = async () => {
  const { data } = await apiClient.get("/opportunities");
  return data || {};
};

export default apiClient;
