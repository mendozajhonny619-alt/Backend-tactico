import React from "react";

function getClockClass(status) {
  const value = String(status || "").toUpperCase();

  if (value.includes("OK")) return "ok";
  if (value.includes("WARNING")) return "warning";
  if (value.includes("BLOCKED")) return "blocked";
  if (value.includes("FROZEN")) return "blocked";
  if (value.includes("STALE")) return "warning";

  return "neutral";
}

function getClockLabel(status) {
  const value = String(status || "").toUpperCase();

  if (value === "CLOCK_OK") return "RELOJ OK";
  if (value === "CLOCK_WARNING") return "RELOJ EN ALERTA";
  if (value === "BLOCKED_CLOCK") return "RELOJ BLOQUEADO";

  return value || "SIN RELOJ";
}

export default function ClockStatusBadge({ status, apiMinute, estimatedMinute, age }) {
  const cls = getClockClass(status);

  return (
    <div className={`v17-clock-badge ${cls}`}>
      <strong>{getClockLabel(status)}</strong>
      <span>API {apiMinute ?? "-"}</span>
      <span>EST {estimatedMinute ?? "-"}</span>
      <span>{age ?? 0}s</span>
    </div>
  );
                       }
