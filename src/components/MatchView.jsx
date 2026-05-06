import React, { useEffect, useMemo, useState } from "react";

const API_URL = "http://127.0.0.1:8000";

export default function MatchView() {
  const [matches, setMatches] = useState([]);

  useEffect(() => {
    fetchMatches();
    const interval = setInterval(fetchMatches, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchMatches = async () => {
    try {
      const res = await fetch(`${API_URL}/live-matches`);
      const data = await res.json();

      setMatches(Array.isArray(data?.items) ? data.items : []);
    } catch (err) {
      console.error("Error cargando partidos:", err);
      setMatches([]);
    }
  };

  const normalizedMatches = useMemo(() => {
    return matches.map((m, index) => {
      const matchName =
        m.match_name ||
        m.partido ||
        m.nombre_partido ||
        (m.home_name && m.away_name ? `${m.home_name} vs ${m.away_name}` : null) ||
        (m.home_team && m.away_team ? `${m.home_team} vs ${m.away_team}` : null) ||
        (m.home && m.away ? `${m.home} vs ${m.away}` : null) ||
        "Partido sin nombre";

      const [home, away] = splitTeams(
        matchName,
        m.home_name || m.home_team || m.home || m.nombre_local,
        m.away_name || m.away_team || m.away || m.nombre_visitante
      );

      return {
        raw: m,
        id: m.match_id || m.id || `${matchName}-${index}`,
        matchName,
        home,
        away,
        minute: toNumber(m.minute ?? m.minuto),
        score: buildScore(m),

        type: m.type || m.signal_type || null,
        market: m.market || null,
        rank: m.rank || m.confidence || null,
        reason: m.reason || m.opportunity_reason || null,

        ai_score: toNumber(m.ai_score),
        goal_probability: toNumber(m.goal_probability),
        over_probability: toNumber(m.over_probability),
        under_probability: toNumber(m.under_probability),
        signal_score: toNumber(m.signal_score),
        gate_score: toNumber(m.gate_score),

        pressure_index: toNumber(m.pressure_index),
        rhythm_index: toNumber(m.rhythm_index),
        goal_window_score: toNumber(m.goal_window_score),
        over_window_score: toNumber(m.over_window_score),
        under_transition_score: toNumber(m.under_transition_score),
        live_decay_factor: toNumber(m.live_decay_factor),
        cooling_detected: Boolean(m.cooling_detected),
        red_alert: Boolean(m.red_alert),

        home_pressure: toNumber(m.home_pressure),
        away_pressure: toNumber(m.away_pressure),

        next_goal_bias: m.next_goal_bias || "N/A",
        next_goal_confidence: toNumber(m.next_goal_confidence),
        score_hold_probability: toNumber(m.score_hold_probability),
        next_goal_support: m.next_goal_support || "N/A",
        next_goal_status: m.next_goal_status || "N/A",
        next_goal_warning: m.next_goal_warning || "N/A",
        next_goal_helper_advice: m.next_goal_helper_advice || "Sin lectura auxiliar.",

        risk_score: toNumber(m.risk_score),
        risk_level: m.risk_level || "N/A",

        shots: toNumber(m.shots),
        shots_on_target: toNumber(m.shots_on_target),
        corners: toNumber(m.corners),
        dangerous_attacks: toNumber(m.dangerous_attacks),
        xg: toNumber(m.xg ?? m.xG),
        home_shots: toNumber(m.home_shots),
        away_shots: toNumber(m.away_shots),
        home_shots_on_target: toNumber(m.home_shots_on_target),
        away_shots_on_target: toNumber(m.away_shots_on_target),
        home_xg: toNumber(m.home_xg),
        away_xg: toNumber(m.away_xg),

        dominance: m.dominance || "N/A",
        attack_side: m.attack_side || "N/A",
        state: m.context_state || m.match_state || m.state || "N/A",
        window_phase: m.window_phase || m.phase || "N/A",
        window_reason: m.window_reason || "N/A",
        data_quality: m.data_quality || m.calidad_datos || "N/A",
        game_quality: m.game_quality || m.calidad_del_juego || "N/A",
      };
    });
  }, [matches]);

  const classifyMatch = (m) => {
    const backendType = String(m.type || "").toUpperCase();
    const backendMarket = String(m.market || "").toUpperCase();

    if (backendType.includes("OVER") || backendMarket === "OVER") return "OVER";
    if (backendType.includes("UNDER") || backendMarket === "UNDER") return "UNDER";
    if (backendType.includes("OBSERVE")) return "OBSERVE";

    const ai = Number(m.ai_score || 0);
    const goal = Number(m.goal_probability || 0);
    const over = Number(m.over_probability || 0);
    const under = Number(m.under_probability || 0);
    const state = String(m.state || "").toUpperCase();

    if (
      ai >= 65 &&
      goal >= 60 &&
      over >= 60 &&
      ["TIBIO", "CALIENTE", "MUY_CALIENTE", "EXPLOSIVO"].some((x) =>
        state.includes(x)
      )
    ) {
      return "OVER";
    }

    if (
      ai >= 60 &&
      under >= 62 &&
      ["CONTROLADO", "FRIO", "MUERTO", "TIBIO"].some((x) =>
        state.includes(x)
      )
    ) {
      return "UNDER";
    }

    return "OBSERVE";
  };

  const sortedMatches = [...normalizedMatches].sort((a, b) => {
    const scoreA =
      Number(a.gate_score || 0) +
      Number(a.signal_score || 0) +
      Number(a.goal_probability || 0) +
      Number(a.ai_score || 0);

    const scoreB =
      Number(b.gate_score || 0) +
      Number(b.signal_score || 0) +
      Number(b.goal_probability || 0) +
      Number(b.ai_score || 0);

    return scoreB - scoreA;
  });

  const overMatches = sortedMatches.filter((m) => classifyMatch(m) === "OVER");
  const underMatches = sortedMatches.filter((m) => classifyMatch(m) === "UNDER");
  const observeMatches = sortedMatches.filter((m) => classifyMatch(m) === "OBSERVE");

  const renderCard = (m) => {
    const type = classifyMatch(m);

    return (
      <div
        key={m.id}
        style={{
          background: "#1e1e2f",
          borderRadius: 12,
          padding: 15,
          margin: 10,
          width: 360,
          boxShadow: "0 0 10px rgba(0,0,0,0.5)",
          color: "#fff",
        }}
      >
        <h4 style={{ marginTop: 0 }}>{m.home} vs {m.away}</h4>

        <p>⏱ Min: {m.minute}</p>
        <p>⚽ Score: {m.score}</p>

        <hr />

        <h4>🧠 Lectura IA</h4>
        <p>Mercado: {m.market || type}</p>
        <p>Rango: {m.rank || "OBSERVACION"}</p>
        <p>Razón: {m.reason || m.window_reason}</p>
        <p>Contexto: {m.state}</p>
        <p>Ventana: {m.window_phase}</p>
        <p>Dominancia: {m.dominance}</p>
        <p>Lado ataque: {m.attack_side}</p>
        <p>Calidad datos: {m.data_quality}</p>
        <p>Calidad partido: {m.game_quality}</p>

        <hr />

        <h4>📊 Métricas Live</h4>
        <p>Presión live: {formatNum(m.pressure_index)}</p>
        <p>Ritmo live: {formatNum(m.rhythm_index)}</p>
        <p>Ventana gol: {formatNum(m.goal_window_score)}</p>
        <p>Ventana OVER: {formatNum(m.over_window_score)}</p>
        <p>Transición UNDER: {formatNum(m.under_transition_score)}%</p>
        <p>Decay live: {formatNum(m.live_decay_factor)}</p>
        <p>Enfriamiento: {m.cooling_detected ? "SI" : "NO"}</p>
        <p>Red alert: {m.red_alert ? "SI" : "NO"}</p>

        <hr />

        <h4>🎯 Probabilidades</h4>
        <p>AI Score: {formatNum(m.ai_score)}</p>
        <p>Prob. gol: {formatNum(m.goal_probability)}%</p>
        <p>OVER: {formatNum(m.over_probability)}%</p>
        <p>UNDER: {formatNum(m.under_probability)}%</p>
        <p>Signal Score: {formatNum(m.signal_score)}</p>
        <p>Gate Score: {formatNum(m.gate_score)}</p>

        <hr />

        <h4>🥅 Lectura próximo gol</h4>
        <p>Sesgo: {m.next_goal_bias}</p>
        <p>Prob. próximo gol: {formatNum(m.next_goal_confidence)}%</p>
        <p>Mantener marcador: {formatNum(m.score_hold_probability)}%</p>
        <p>Soporte: {m.next_goal_support}</p>
        <p>Estado: {m.next_goal_status}</p>
        <p>Alerta: {m.next_goal_warning}</p>
        <p style={{ color: "#ddd" }}>{m.next_goal_helper_advice}</p>

        <hr />

        <h4>🛡 Riesgo</h4>
        <p>Nivel: {m.risk_level}</p>
        <p>Risk Score: {formatNum(m.risk_score)}</p>

        <hr />

        <h4>📈 Estadísticas del partido</h4>
        <p>Tiros: {safeStat(m.shots)}</p>
        <p>Tiros al arco: {safeStat(m.shots_on_target)}</p>
        <p>xG: {safeStat(m.xg)}</p>
        <p>Corners: {safeStat(m.corners)}</p>
        <p>Ataques peligrosos: {safeStat(m.dangerous_attacks)}</p>

        <div style={{ marginTop: 10, fontSize: 13, color: "#ccc" }}>
          <strong>{m.home}</strong>
          <p>Tiros: {safeStat(m.home_shots)}</p>
          <p>Tiros al arco: {safeStat(m.home_shots_on_target)}</p>
          <p>xG: {safeStat(m.home_xg)}</p>
          <p>Presión: {safeStat(m.home_pressure)}</p>

          <strong>{m.away}</strong>
          <p>Tiros: {safeStat(m.away_shots)}</p>
          <p>Tiros al arco: {safeStat(m.away_shots_on_target)}</p>
          <p>xG: {safeStat(m.away_xg)}</p>
          <p>Presión: {safeStat(m.away_pressure)}</p>
        </div>

        <hr />

        <strong
          style={{
            color:
              type === "OVER"
                ? "#00ffcc"
                : type === "UNDER"
                ? "#ffcc00"
                : "#aaa",
          }}
        >
          {type}
        </strong>
      </div>
    );
  };

  return (
    <div style={{ padding: 20, background: "#111827", minHeight: "100vh", color: "#fff" }}>
      <h2>🔥 PANEL INTELIGENTE</h2>

      <h3 style={{ color: "#00ffcc" }}>🚀 SEÑALES OVER</h3>
      <div style={{ display: "flex", flexWrap: "wrap" }}>
        {overMatches.map(renderCard)}
      </div>

      <h3 style={{ color: "#ffcc00" }}>🧊 POSIBLES UNDER</h3>
      <div style={{ display: "flex", flexWrap: "wrap" }}>
        {underMatches.map(renderCard)}
      </div>

      <h3 style={{ color: "#aaa" }}>👀 OBSERVACIÓN</h3>
      <div style={{ display: "flex", flexWrap: "wrap" }}>
        {observeMatches.map(renderCard)}
      </div>
    </div>
  );
}

function splitTeams(matchName, homeFallback, awayFallback) {
  if (homeFallback && awayFallback) {
    return [String(homeFallback), String(awayFallback)];
  }

  if (String(matchName).includes(" vs ")) {
    const [home, away] = String(matchName).split(" vs ");
    return [home?.trim() || "Local", away?.trim() || "Visitante"];
  }

  return [homeFallback || "Local", awayFallback || "Visitante"];
}

function buildScore(item) {
  const direct = item.score || item.marcador || item.marcador_entrada;
  if (direct && String(direct).includes("-")) return String(direct);

  const homeScore =
    item.home_score ??
    item.local_score ??
    item.marcador_local ??
    item.score_home ??
    0;

  const awayScore =
    item.away_score ??
    item.visitor_score ??
    item.marcador_visitante ??
    item.score_away ??
    0;

  return `${homeScore}-${awayScore}`;
}

function toNumber(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

function formatNum(value) {
  return Number(toNumber(value)).toFixed(2);
}

function safeStat(value) {
  const n = Number(value);
  if (!Number.isFinite(n) || n === 0) return "N/D";
  return n.toFixed(2);
}
