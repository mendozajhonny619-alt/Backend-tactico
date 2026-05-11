// src/v16/pages/Dashboard.jsx

import React from "react";

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
  const {
    matches = [],
    signals = [],
    systemStatus = {},
    loading = false,
  } = useLiveData() || {};

  const featuredMatch = matches[0] || null;
  const topMatches = matches.slice(0, 2);

  const feedEvents = signals.map(
    (s) =>
      `${s?.type || s?.market || "SEÑAL"} • ${
        s?.confidence || s?.ai_score || s?.signal_score || 0
      }%`
  );

  return (
    <MainLayout>
      <div className="v16-command-center">
        <EliteHeader />

        <div className="v16-top-status">
          <SystemStatusWidget status={systemStatus} />

          {loading && (
            <div className="loading-live">
              <span className="live-dot" />
              Cargando datos tácticos en vivo...
            </div>
          )}
        </div>

        <section className="v16-dashboard-grid">
          <aside className="v16-left-zone">
            <div className="zone-title">PARTIDOS LIVE</div>

            {topMatches.length === 0 ? (
              <div className="glass-card empty-v16-card">
                Sin partidos activos por ahora.
              </div>
            ) : (
              topMatches.map((match, index) => (
                <LiveMatchCard
                  key={match?.id || match?.match_id || index}
                  match={match}
                />
              ))
            )}

            <div className="v16-opportunity-card glass-card">
              <span>OPORTUNIDAD EN VENTANA</span>
              <strong>
                {featuredMatch?.goal_probability ?? 0}%
              </strong>
              <small>
                {featuredMatch?.market || "LECTURA IA"}
              </small>
            </div>
          </aside>

          <main className="v16-center-zone">
            <MomentumHeatPanel data={signals} />

            <MatchStatsGrid stats={featuredMatch || {}} />

            <LiveSignalFeed events={feedEvents} />
          </main>

          <aside className="v16-right-zone">
            <SignalRadar
              rhythm={featuredMatch?.rhythm_index ?? 0}
              pressure={featuredMatch?.pressure_index ?? 0}
              risk={featuredMatch?.risk_score ?? 0}
              xg={featuredMatch?.xg ?? 0}
            />

            <RiskMeter
              risk={
                featuredMatch?.risk_level ||
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
      </div>
    </MainLayout>
  );
};

export default Dashboard;
