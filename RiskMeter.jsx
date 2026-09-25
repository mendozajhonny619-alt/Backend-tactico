// src/v16/components/RiskMeter.jsx

import React from "react";
import "../styles/components.css";

const RiskMeter = ({ risk }) => {
  const normalized =
    String(risk || "MEDIO").toUpperCase();

  const getRisk = () => {
    if (
      normalized.includes("ALTO") ||
      normalized.includes("HIGH")
    ) {
      return {
        label: "ALTO",
        percent: 85,
        className: "high",
      };
    }

    if (
      normalized.includes("BAJO") ||
      normalized.includes("LOW")
    ) {
      return {
        label: "BAJO",
        percent: 25,
        className: "low",
      };
    }

    return {
      label: "MEDIO",
      percent: 55,
      className: "medium",
    };
  };

  const riskData = getRisk();

  return (
    <div className="glass-card risk-meter">
      <div className="card-header">
        <h3>🛡 Riesgo IA</h3>
      </div>

      <div className="risk-circle-wrapper">
        <div className={`risk-circle ${riskData.className}`}>
          <div className="risk-inner">
            <strong>{riskData.percent}%</strong>
            <span>{riskData.label}</span>
          </div>
        </div>
      </div>

      <div className="risk-bar">
        <div
          className={`risk-fill ${riskData.className}`}
          style={{
            width: `${riskData.percent}%`,
          }}
        />
      </div>

      <p className="risk-description">
        Evaluación contextual basada en presión,
        momentum, ritmo y enfriamiento táctico.
      </p>
    </div>
  );
};

export default RiskMeter;
