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

import "../styles/dashboard.css";

const Dashboard = () => {
  const { matches, signals, systemStatus, loading } = useLiveData();

  const featuredMatch = matches?.[0] || null;

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
        {matches.map((match) => (
          <LiveMatchCard
            key={match.id}
            match={match}
          />
        ))}

        {/* PANEL MOMENTUM */}
        <MomentumHeatPanel data={signals || []} />

        {/* RADAR IA */}
        <SignalRadar
          rhythm={featuredMatch?.rhythm_index || 72}
          pressure={featuredMatch?.pressure_index || 78}
          risk={featuredMatch?.risk_score || 22}
          xg={featuredMatch?.xg || 1.45}
        />

        {/* RIESGO */}
        <RiskMeter
          risk={
            featuredMatch?.risk_level ||
            systemStatus?.riskLevel ||
            "MEDIO"
          }
        />

        {/* STATS */}
        <MatchStatsGrid
          stats={featuredMatch || {}}
        />

        {/* FEED LIVE */}
        <LiveSignalFeed
          events={
            signals?.map(
              (s) =>
                `${s.type || "SEÑAL"} • ${
                  s.confidence || s.aiScore || 0
                }%`
            ) || []
          }
        />
      </ResponsiveGrid>
    </MainLayout>
  );
};

export default Dashboard;
