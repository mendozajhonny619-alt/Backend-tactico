const API_BASE =
  import.meta?.env?.VITE_API_URL ||
  process.env.REACT_APP_API_URL ||
  "http://127.0.0.1:8000";

const V17_BASE = `${API_BASE}/v17`;

const DEFAULT_TIMEOUT = 12000;

async function fetchWithTimeout(url, options = {}, timeout = DEFAULT_TIMEOUT) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status} en ${url}`);
    }

    return await response.json();
  } finally {
    clearTimeout(timer);
  }
}

export async function fetchV17Health() {
  return fetchWithTimeout(`${V17_BASE}/health`, {}, 8000);
}

export async function fetchV17Dashboard() {
  return fetchWithTimeout(`${V17_BASE}/dashboard`, {}, DEFAULT_TIMEOUT);
}

export async function fetchV17Signals() {
  return fetchWithTimeout(`${V17_BASE}/signals`, {}, DEFAULT_TIMEOUT);
}

export async function fetchV17History() {
  return fetchWithTimeout(`${V17_BASE}/history`, {}, DEFAULT_TIMEOUT);
}

export async function fetchV17Debug() {
  return fetchWithTimeout(`${V17_BASE}/debug`, {}, DEFAULT_TIMEOUT);
}

export const V17_API_BASE = V17_BASE;
