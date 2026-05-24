import React from "react";
import { useV17LiveData } from "../hooks/useV17LiveData";
import StatCardV17 from "../components/StatCardV17";
import SectionPanelV17 from "../components/SectionPanelV17";
import HistoryPanelV17 from "../components/HistoryPanelV17";
import "../styles/v17-dashboard.css";

export default function DashboardV17() {
  const { data, stats, loading, error, lastFetchAt, reload } = useV17LiveData();

  return (
    <main className="v17-dashboard">
      <header className="v17-header">
        <div>
          <span className="v17-kicker">JHONNY ELITE</span>
          <h1>V17 Live Signal System</h1>
          <p>
            Panel limpio basado en protocolo maestro. El backend decide, el panel
            muestra.
          </p>
        </div>

        <div className="v17-status-box">
          <span className={error ? "offline" : "online"} />
          <strong>{error ? "ERROR" : "SISTEMA ACTIVO"}</strong>
          <small>
            {lastFetchAt ? `Última actualización ${lastFetchAt.toLocaleTimeString()}` : "Cargando..."}
          </small>
          <button onClick={reload}>Actualizar</button>
        </div>
      </header>

      {error ? <div className="v17-alert error">{error}</div> : null}

      {loading ? (
        <div className="v17-loading">Cargando datos V17...</div>
      ) : (
        <>
          <section className="v17-stats-grid">
            <StatCardV17 label="Partidos vivos" value={stats.liveMatches} />
            <StatCardV17 label="Analizados" value={stats.analyzedMatches} />
            <StatCardV17 label="Top señales" value={stats.publishedSignals} good />
            <StatCardV17 label="Observación" value={stats.observe} />
            <StatCardV17 label="No Bet" value={stats.noBet} />
            <StatCardV17 label="Bloqueados" value={stats.blocked} danger={stats.blocked > 0} />
            <StatCardV17 label="Pendientes" value={stats.pending} />
            <StatCardV17 label="Precisión" value={`${stats.precision}%`} good={stats.precision > 0} />
          </section>

          <div className="v17-message">
            <strong>Lectura general</strong>
            <p>{data.message || "Sistema V17 activo."}</p>
          </div>

          <SectionPanelV17
            title="Top señales live"
            subtitle="Máximo 6 señales. Si no hay ventaja real, no fuerza entradas."
            items={data.top_signals}
            emptyText="No hay señales TOP en este momento. El sistema sigue escaneando."
          />

          <SectionPanelV17
            title="Partidos en observación"
            subtitle="Candidatos con lectura parcial. Pueden subir si aparece confirmación."
            items={data.observe}
            compact
            emptyText="No hay partidos en observación."
          />

          <SectionPanelV17
            title="No Bet"
            subtitle="Partidos vivos sin ventaja suficiente para operar."
            items={data.no_bet}
            compact
            emptyText="No hay partidos clasificados como NO_BET."
          />

          <SectionPanelV17
            title="Bloqueados"
            subtitle="Partidos con bloqueo crítico por reloj, datos o contradicción."
            items={data.blocked}
            compact
            emptyText="No hay partidos bloqueados."
          />

          <HistoryPanelV17
            pending={data.pending_signals}
            closed={data.closed_history}
            learning={data.performance_analysis}
          />
        </>
      )}
    </main>
  );
}
