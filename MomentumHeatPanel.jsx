// src/v16/components/MomentumHeatPanel.jsx

import React from "react";
import "../styles/components.css";

const MomentumHeatPanel = ({ data = [] }) => {
  const topSignals = data.slice(0, 5);

  return (
    <div className="glass-card momentum-panel">
      <div className="card-header">
        <h3>🔥 Momentum IA</h3>

        <span className="pulse-live">
          ANALIZANDO
        </span>
      </div>

      <div className="momentum-visual">
        <div className="heat-zone high" />
        <div className="heat-zone medium" />
        <div className="heat-zone low" />
      </div>

      <div className="momentum-bars">
        {topSignals.length === 0 ? (
          <span className="no-signals">
            Sin señales activas
          </span>
        ) : (
          topSignals.map((signal, index) => {
            const confidence =
              Number(
                signal.confidence ||
                signal.aiScore ||
                0
              );

            return (
              <div
                key={index}
                className="momentum-row"
              >
                <div className="momentum-info">
                  <span>
                    {signal.type || "SEÑAL"}
                  </span>

                  <strong>
                    {confidence}%
                  </strong>
                </div>

                <div className="momentum-bar-bg">
                  <div
                    className="momentum-bar-fill"
                    style={{
                      width: `${Math.min(
                        100,
                        confidence
                      )}%`,
                    }}
                  />
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

export default MomentumHeatPanel;
