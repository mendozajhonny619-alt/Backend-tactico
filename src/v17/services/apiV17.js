// Relative origin means a single FastAPI serves PC and mobile; localhost on a
// phone would point to the phone, not the PC running the scanner.
const API_BASE = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");

const V17_BASE = `${API_BASE}/v17`;

const DEFAULT_TIMEOUT = 20000;
const COLD_START_TIMEOUT = 70000;

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
  } catch (error) {
    if (error?.name === "AbortError") {
      throw new Error("El motor local tardó demasiado en responder. Comprueba el estado del scanner en PowerShell.");
    }
    throw error;
  } finally {
    clearTimeout(timer);
  }
}

export async function fetchV17Health({ coldStart = false } = {}) {
  return fetchWithTimeout(`${V17_BASE}/health`, {}, coldStart ? COLD_START_TIMEOUT : DEFAULT_TIMEOUT);
}

export async function fetchV17Dashboard({ coldStart = false } = {}) {
  return fetchWithTimeout(`${V17_BASE}/dashboard`, {}, coldStart ? COLD_START_TIMEOUT : DEFAULT_TIMEOUT);
}

export async function fetchV17Signals() {
  return fetchWithTimeout(`${V17_BASE}/signals`, {}, DEFAULT_TIMEOUT);
}

export async function fetchV17History() {
  return fetchWithTimeout(`${V17_BASE}/history`, {}, DEFAULT_TIMEOUT);
}

export async function fetchV17MatchDetail(fixtureId, signalKey = "") {
  if (!fixtureId) throw new Error("No se encontró el fixture del partido.");
  const params = signalKey ? `?signal_key=${encodeURIComponent(signalKey)}` : "";
  return fetchWithTimeout(`${V17_BASE}/match/${encodeURIComponent(fixtureId)}${params}`, {}, 20000);
}

export const V17_API_BASE = V17_BASE;
