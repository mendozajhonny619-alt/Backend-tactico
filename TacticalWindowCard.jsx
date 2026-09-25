import React from "react";
import "../styles/components.css";

const TacticalWindowCard = React.memo(({ title, description, intensity, phase }) => {
  const level = String(intensity || "Media").toLowerCase();

  const toneClass =
    level.includes("alta") || level.includes("high")
      ? "v16-window-high"
      : level.includes("media") || level.includes("medium")
      ? "v16-window-medium"
      : "v16-window-low";

  return (
    <div className={`v16-glass-card v16-tactical-window-card ${toneClass}`}>
      <span className="v16-window-label">Ventana táctica</span>
      <h4>{title || phase || "Lectura táctica activa"}</h4>
      <p>{description || "El sistema está evaluando el estado contextual del partido."}</p>
      <strong>Intensidad: {intensity || "Media"}</strong>
    </div>
  );
});

export default TacticalWindowCard;
