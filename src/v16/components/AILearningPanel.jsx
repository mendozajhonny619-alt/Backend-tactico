import React from "react";
import "../styles/components.css";

const num = (value, fallback = 0) => {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
};

const pct = (value) => `${num(value).toFixed(1)}%`;

const safeObj = (value) =>
  value && typeof value === "object" && !Array.isArray(value) ? value : {};

const entries = (value) =>
  Object.entries(safeObj(value)).sort(
    ([, a], [, b]) => num(b?.winrate) - num(a?.winrate)
  );

const getTone = (stats = {}) => {
  const risk = String(stats?.risk_level || "").toUpperCase();
  const roi = num(stats?.roi);
  const winrate = num(stats?.winrate);

  if (risk.includes("DANGER") || roi < -15 || winrate < 40) return "danger";
  if (risk.includes("STRONG") || roi > 10 || winrate >= 58) return "good";
  if (risk.includes("WEAK") || roi < 0 || winrate < 50) return "warn";
  return "neutral";
};

export default function AILearningPanel({ stats = {}, history = [] }) {
  const byMarket = safeObj(stats?.by_market || stats?.byMarket);
  const byRank = safeObj(stats?.by_rank || stats?.byRank);
  const bySignalMode = safeObj(stats?.by_signal_mode || stats?.bySignalMode);

  const total = num(stats?.history_items || history.length);
  const wins = num(stats?.wins);
  const losses = num(stats?.losses);
  const pending = num(stats?.pending);
  const winrate = num(stats?.winrate);
  const roi = num(stats?.roi);
  const profitUnits = num(stats?.profit_units);

  return (
    <section className="glass-card ai-learning-panel">
      <div className="ai-learning-header">
        <div>
          <span className="ai-learning-eyebrow">MEMORIA Y APRENDIZAJE IA</span>
          <h3>🧬 Rendimiento histórico inteligente</h3>
          <p>
            Lectura del historial para detectar mercados, rangos y patrones más
            confiables.
          </p>
        </div>

        <div className={`ai-learning-status ${roi >= 0 ? "good" : "danger"}`}>
          <span>ROI GLOBAL</span>
          <strong>{`${roi >= 0 ? "+" : ""}${pct(roi)}`}</strong>
        </div>
      </div>

      <div className="ai-learning-kpis">
        <LearningKpi label="Historial" value={total} tone="neutral" />
        <LearningKpi label="Aciertos" value={wins} tone="good" />
        <LearningKpi label="Fallos" value={losses} tone="danger" />
        <LearningKpi label="Pendientes" value={pending} tone="warn" />
        <LearningKpi label="Winrate" value={pct(winrate)} tone="good" />
        <LearningKpi
          label="Unidades"
          value={`${profitUnits >= 0 ? "+" : ""}${profitUnits.toFixed(2)}`}
          tone={profitUnits >= 0 ? "good" : "danger"}
        />
      </div>

      <div className="ai-learning-grid">
        <LearningTable title="Rendimiento por mercado" items={entries(byMarket)} />
        <LearningTable title="Rendimiento por rango" items={entries(byRank)} />
        <LearningTable title="Modo de señal" items={entries(bySignalMode)} />
      </div>

      {history.length > 0 && (
        <div className="ai-learning-last">
          <h4>Últimas señales aprendidas</h4>

          <div className="ai-learning-last-list">
            {history.slice(0, 5).map((item, index) => (
              <div className="ai-learning-last-row" key={item?.signal_key || index}>
                <div>
                  <strong>{item?.match_name || "Partido"}</strong>
                  <span>
                    {item?.market || "N/A"} • {item?.rank || "N/A"}
                  </span>
                </div>

                <b className={String(item?.resultado || item?.status).toUpperCase()}>
                  {item?.resultado || item?.status || "PENDIENTE"}
                </b>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

function LearningKpi({ label, value, tone = "neutral" }) {
  return (
    <div className={`ai-learning-kpi ${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function LearningTable({ title, items = [] }) {
  return (
    <div className="ai-learning-table">
      <h4>{title}</h4>

      {items.length === 0 ? (
        <div className="ai-learning-empty">Sin datos suficientes.</div>
      ) : (
        <div className="ai-learning-table-list">
          {items.slice(0, 6).map(([name, stats]) => (
            <div className={`ai-learning-table-row ${getTone(stats)}`} key={name}>
              <div>
                <strong>{name}</strong>
                <span>
                  {num(stats?.wins)}W / {num(stats?.losses)}L /{" "}
                  {num(stats?.pending)}P
                </span>
              </div>

              <div>
                <b>{pct(stats?.winrate)}</b>
                <small>{`${num(stats?.roi) >= 0 ? "+" : ""}${pct(stats?.roi)}`}</small>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
                 }
