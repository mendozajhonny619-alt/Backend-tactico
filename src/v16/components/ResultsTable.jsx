// src/v16/components/ResultsTable.jsx

import React from "react";

const statusClass = (status) => {
  const value = String(status || "").toUpperCase();

  if (value.includes("ACERT")) return "win";
  if (value.includes("FALL")) return "loss";

  return "pending";
};

export default function ResultsTable({
  results = [],
  precision = "0%",
  roi = "0%",
  wins = 0,
  losses = 0,
  pending = 0,
}) {
  return (
    <div className="v16-results-wrapper">
      <div className="v16-results-top">
        <div className="glass-card v16-result-kpi">
          <span>Aciertos</span>
          <strong>{wins}</strong>
        </div>

        <div className="glass-card v16-result-kpi">
          <span>Fallos</span>
          <strong>{losses}</strong>
        </div>

        <div className="glass-card v16-result-kpi">
          <span>Pendientes</span>
          <strong>{pending}</strong>
        </div>

        <div className="glass-card v16-result-kpi">
          <span>Precisión</span>
          <strong>{precision}</strong>
        </div>

        <div className="glass-card v16-result-kpi">
          <span>ROI</span>
          <strong>{roi}</strong>
        </div>
      </div>

      <div className="v16-results-table glass-card">
        <div className="v16-results-head">
          <span>PARTIDO</span>
          <span>MERCADO</span>
          <span>MARCADOR</span>
          <span>ESTADO</span>
          <span>UNIDADES</span>
        </div>

        <div className="v16-results-body">
          {results.map((item, index) => (
            <div
              className="v16-results-row"
              key={item?.id || index}
            >
              <div className="v16-results-match">
                <small>
                  {item?.league || item?.liga || "Liga"}
                </small>

                <strong>
                  {item?.home || item?.local || "Local"} vs{" "}
                  {item?.away || item?.visitante || "Visitante"}
                </strong>

                <p>
                  Min. {item?.minute || item?.minuto || 0}
                </p>
              </div>

              <div className="v16-results-market">
                {item?.market || item?.mercado || "N/A"}
              </div>

              <div className="v16-results-score">
                {item?.score ||
                  item?.finalScore ||
                  item?.final_score ||
                  "0-0"}
              </div>

              <div
                className={`v16-results-status ${statusClass(
                  item?.resultStatus ||
                    item?.result_status ||
                    item?.status
                )}`}
              >
                {item?.resultStatus ||
                  item?.result_status ||
                  "PENDIENTE"}
              </div>

              <div className="v16-results-profit">
                {item?.units ?? "0.00"}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
        }
