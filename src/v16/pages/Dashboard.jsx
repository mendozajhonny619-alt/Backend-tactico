// src/v16/pages/Dashboard.jsx

import React from "react";

import MainLayout from "../layout/MainLayout";
import ResponsiveGrid from "../layout/ResponsiveGrid";

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

  return (
    <MainLayout>
      <EliteHeader />

      <SystemStatusWidget status={systemStatus} />

      {loading && (
        <div className="loading-live">
          <span className="live-dot" />
          Cargando datos tácticos en vivo...
        </div>
      )}

      <ResponsiveGrid>
        {/* PARTIDOS LIVE */}
        {(matches || []).map((match, index) => (
          <LiveMatchCard
            key={match?.id || match?.match_id || index}
            match={match}
          />
        ))}

        {/* PANEL MOMENTUM */}
        <MomentumHeatPanel data={signals || []} />

        {/* RADAR IA */}
        <SignalRadar
          rhythm={featuredMatch?.rhythm_index ?? 0}
          pressure={featuredMatch?.pressure_index ?? 0}
          risk={featuredMatch?.risk_score ?? 0}
          xg={featuredMatch?.xg ?? 0}
        />

        {/* RIESGO */}
        <RiskMeter
          risk={
            featuredMatch?.risk_level ||
            systemStatus?.riskLevel ||
            systemStatus?.risk_level ||
            "MEDIO"
          }
        />

        {/* STATS */}
        <MatchStatsGrid stats={featuredMatch || {}} />

        {/* FEED LIVE */}
        <LiveSignalFeed
          events={(signals || []).map(
            (s) =>
              `${s?.type || s?.market || "SEÑAL"} • ${
                s?.confidence || s?.ai_score || s?.signal_score || 0
              }%`
          )}
        />
      </ResponsiveGrid>
    </MainLayout>
  );
};

export default Dashboard;
