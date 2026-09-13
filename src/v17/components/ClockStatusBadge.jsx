import React from "react";

function getClockClass(status) {
  const value = String(status || "").toUpperCase();
  if (value.includes("OK") || value.includes("CONFIRMED")) return "ok";
  if (value.includes("WARNING") || value.includes("WAIT") || value.includes("STALE")) return "warning";
  if (value.includes("BLOCKED") || value.includes("FROZEN")) return "blocked";
  return "neutral";
}

function getClockLabel(status) {
  const value = String(status || "").toUpperCase();
  if (value === "CLOCK_OK") return "RELOJ OK";
  if (value === "CLOCK_STATS_CONFIRMED") return "RELOJ CONFIRMADO";
  if (value === "CLOCK_WARNING") return "RELOJ EN ALERTA";
  if (value === "BLOCKED_CLOCK") return "RELOJ BLOQUEADO";
  return value || "SIN RELOJ";
}

export default function ClockStatusBadge({ status, apiMinute, estimatedMinute, age }) {
  return (
    <div className={`v17-clock-badge ${getClockClass(status)}`}>
      <strong>{getClockLabel(status)}</strong>
      <span>MIN {apiMinute ?? "-"}</span>
      <span>EST {estimatedMinute ?? "-"}</span>
      <span>{age ?? 0}s</span>
    </div>
  );
}
