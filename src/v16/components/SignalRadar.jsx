// src/v16/components/SignalRadar.jsx

import React from "react";
import "../styles/components.css";

const SignalRadar = ({
  rhythm = 0,
  pressure = 0,
  risk = 0,
  xg = 0,
}) => {
  const radarData = [
    {
      label: "Ritmo",
      value: rhythm,
      color: "cyan",
    },
    {
      label: "Presión",
      value: pressure,
      color: "green",
    },
    {
      label: "Riesgo",
      value: risk,
      color: "red",
    },
    {
      label: "xG",
      value: xg,
      color: "purple",
    },
  ];

  return (
    <div className="glass-card radar-card">
      <div className="card-header">
        <h3>🧠 Signal Radar</h3>

        <span className="radar-status">
          IA LIVE
        </span>
      </div>

      <div className="radar-center">
        <div className="radar-ring ring-1" />
        <div className="radar-ring ring-2" />
        <div className="radar-ring ring-3" />

        <div className="radar-core">
          LIVE
        </div>
      </div>

      <div className="radar-stats">
        {radarData.map((item, index) => (
          <div
            key={index}
            className={`radar-item ${item.color}`}
          >
            <span>{item.label}</span>

            <strong>
              {Number(item.value).toFixed(1)}
            </strong>
          </div>
        ))}
      </div>
    </div>
  );
};

export default SignalRadar;
