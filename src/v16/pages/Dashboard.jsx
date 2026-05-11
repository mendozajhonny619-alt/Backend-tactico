// src/v16/pages/Dashboard.jsx

import React, { useState } from "react";

import MainLayout from "../layout/MainLayout";
import EliteHeader from "../widgets/EliteHeader";
import SystemStatusWidget from "../widgets/SystemStatusWidget";

import LiveMatchCard from "../components/LiveMatchCard";
import SignalRadar from "../components/SignalRadar";
import MomentumHeatPanel from "../components/MomentumHeatPanel";
import RiskMeter from "../components/RiskMeter";
import MatchStatsGrid from "../components/MatchStatsGrid";
import LiveSignalFeed from "../components/LiveSignalFeed";

import useLiveData from "../hooks/useLiveData";

import "../styles/variables.css";
import "../styles/dashboard.css";
import "../styles/components.css";

const Dashboard = () => {
  const [activeView, setActiveView] = useState("live");
  const [selectedMatch, setSelectedMatch] = useState(null);

  const {
    matches = [],
    signals = [],
    history = [],
    opportunities = {},
    systemStatus = {},
    loading = false,
    lastUpdate,
  } = useLiveData() || {};

  const featuredMatch = selectedMatch || matches[0] || null;
  const topMatches = matches.slice(0, 2);

  const feedEvents = signals.map(
    (s) =>
      `${s?.type || s?.market || "SEÑAL"} • ${
        s?.confidence || s?.ai_score || s?.signal_score || 0
      }%`
  );

  const navItems = [
    { id: "live", label: "Señales", icon: "⚡" },
    { id: "opportunities", label: "Oportunidades", icon: "🎯" },
    { id: "results", label: "Resultados", icon: "🏆" },
    { id: "stats", label: "Estadísticas", icon: "📊" },
    { id: "config", label: "Configuración", icon: "⚙️" },
  ];

  return (
    <MainLayout>
      <div className="v16-command-center">
        <EliteHeader />

        <div className="v16-kpi-strip">
          <div className="v16-kpi">
            <span>SISTEMA</span>
            <strong>{systemStatus?.active ? "ACTIVO" : "ACTIVO"}</strong>
          </div>
          <div className="v16-kpi">
            <span>SEÑALES ACTIVAS</span>
            <strong>{signals.length}</strong>
          </div>
          <div className="v16-kpi">
            <span>PARTIDOS EN VIVO</span>
            <strong>{matches.length}</strong>
          </div>
          <div className="v16-kpi">
            <span>PRECISIÓN IA</span>
            <strong>{Number(systemStatus?.precision || 0).toFixed(1)}%</strong>
          </div>
          <div className="v16-kpi">
            <span>ROI HOY</span>
            <strong>{Number(systemStatus?.roi || 0).toFixed(1)}%</strong>
          </div>
          <div className="v16-kpi">
            <span>ÚLTIMA ACTUALIZACIÓN</span>
            <strong>
              {lastUpdate ? new Date(lastUpdate).toLocaleTimeString() : "N/A"}
            </strong>
          </div>
        </div>

        <nav className="v16-nav">
          {navItems.map((item) => (
            <button
              key={item.id}
              className={activeView === item.id ? "active" : ""}
              onClick={() => setActiveView(item.id)}
            >
              <span>{item.icon}</span>
              {item.label}
            </button>
          ))}
        </nav>

        <div className="v16-top-status">
          <SystemStatusWidget status={systemStatus} />
          {loading && (
            <div className="loading-live">
              <span className="live-dot" />
              Cargando datos tácticos en vivo...
            </div>
          )}
        </div>

        {activeView === "live" && (
          <section className="v16-dashboard-grid">
            <aside className="v16-left-zone">
              <div className="zone-title">PARTIDOS LIVE</div>

              {topMatches.length === 0 ? (
                <div className="glass-card empty-v16-card">
                  Sin partidos activos por ahora.
                </div>
              ) : (
                topMatches.map((match, index) => (
                  <div key={match?.id || match?.match_id || index}>
                    <LiveMatchCard match={match} />
                    <button
                      className="v16-detail-btn"
                      onClick={() => {
                        setSelectedMatch(match);
                        setActiveView("detail");
                      }}
                    >
                      Ver detalle del partido
                    </button>
                  </div>
                ))
              )}

              <div className="v16-opportunity-card glass-card">
                <span>OPORTUNIDAD EN VENTANA</span>
                <strong>{featuredMatch?.goal_probability ?? featuredMatch?.goalProbability ?? 0}%</strong>
                <small>{featuredMatch?.market || "LECTURA IA"}</small>
              </div>
            </aside>

            <main className="v16-center-zone">
              <MomentumHeatPanel data={signals} />
              <MatchStatsGrid stats={featuredMatch || {}} />
              <LiveSignalFeed events={feedEvents} />
            </main>

            <aside className="v16-right-zone">
              <SignalRadar
                rhythm={featuredMatch?.rhythm_index ?? featuredMatch?.rhythmIndex ?? 0}
                pressure={featuredMatch?.pressure_index ?? featuredMatch?.pressureIndex ?? 0}
                risk={featuredMatch?.risk_score ?? featuredMatch?.riskScore ?? 0}
                xg={featuredMatch?.xg ?? featuredMatch?.xG ?? 0}
              />

              <RiskMeter
                risk={
                  featuredMatch?.risk_level ||
                  featuredMatch?.riskLevel ||
                  systemStatus?.riskLevel ||
                  systemStatus?.risk_level ||
                  "MEDIO"
                }
              />

              <div className="v16-system-stability glass-card">
                <span>SISTEMA</span>
                <strong>100%</strong>
                <b>ESTABLE</b>
              </div>
            </aside>
          </section>
        )}

        {activeView === "detail" && (
          <section className="v16-screen glass-card">
            <button className="v16-back-btn" onClick={() => setActiveView("live")}>
              ← Volver al panel
            </button>
            <h2>DETALLE DEL PARTIDO</h2>
            <MatchStatsGrid stats={featuredMatch || {}} />
            <SignalRadar
              rhythm={featuredMatch?.rhythm_index ?? featuredMatch?.rhythmIndex ?? 0}
              pressure={featuredMatch?.pressure_index ?? featuredMatch?.pressureIndex ?? 0}
              risk={featuredMatch?.risk_score ?? featuredMatch?.riskScore ?? 0}
              xg={featuredMatch?.xg ?? featuredMatch?.xG ?? 0}
            />
          </section>
        )}

        {activeView === "opportunities" && (
          <section className="v16-screen glass-card">
            <h2>🎯 OPORTUNIDADES</h2>
            <pre>{JSON.stringify(opportunities?.summary || {}, null, 2)}</pre>
          </section>
        )}

        {activeView === "results" && (
          <section className="v16-screen glass-card">
            <h2>🏆 RENDIMIENTO DE SEÑALES IA</h2>
            <div className="v16-results-grid">
              <div><span>Aciertos</span><strong>{history.filter((h) => String(h?.status).toUpperCase().includes("WIN")).length}</strong></div>
              <div><span>Fallos</span><strong>{history.filter((h) => String(h?.status).toUpperCase().includes("LOSS")).length}</strong></div>
              <div><span>Pendientes</span><strong>{history.length}</strong></div>
            </div>
          </section>
        )}

        {activeView === "stats" && (
          <section className="v16-screen glass-card">
            <h2>📊 ESTADÍSTICAS Y RENDIMIENTO</h2>
            <SystemStatusWidget status={systemStatus} />
          </section>
        )}

        {activeView === "config" && (
          <section className="v16-screen glass-card">
            <h2>⚙️ CONFIGURACIÓN Y ALERTAS</h2>
            <p>Modo del sistema: Balanceado</p>
            <p>Confianza mínima: 60%</p>
            <p>Riesgo máximo permitido: Medio</p>
            <p>Actualización live: cada 15 segundos</p>
          </section>
        )}
      </div>
    </MainLayout>
  );
};

export default Dashboard;
