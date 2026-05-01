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
        ai_score: toNumber(m.ai_score),
        goal_probability: toNumber(m.goal_probability),
        over_probability: toNumber(m.over_probability),
        under_probability: toNumber(m.under_probability),
        signal_score: toNumber(m.signal_score),
        gate_score: toNumber(m.gate_score),
        state:
          m.context_state ||
          m.match_state ||
          m.state ||
          "N/A",
        window_phase:
          m.window_phase ||
          m.phase ||
          "N/A",
        data_quality:
          m.data_quality ||
          m.calidad_datos ||
          "N/A",
        game_quality:
          m.game_quality ||
          m.calidad_del_juego ||
          "N/A",
      };
    });
  }, [matches]);

  const classifyMatch = (m) => {
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
          width: 280,
          boxShadow: "0 0 10px rgba(0,0,0,0.5)",
          color: "#fff",
        }}
      >
        <h4 style={{ marginTop: 0 }}>{m.home} vs {m.away}</h4>

        <p>⏱ Min: {m.minute}</p>
        <p>⚽ Score: {m.score}</p>

        <hr />

        <p>🧠 AI Score: {formatNum(m.ai_score)}</p>
        <p>🔥 Goal %: {formatNum(m.goal_probability)}</p>
        <p>📈 Over %: {formatNum(m.over_probability)}</p>
        <p>📉 Under %: {formatNum(m.under_probability)}</p>

        <p>🎯 Signal Score: {formatNum(m.signal_score)}</p>
        <p>🚪 Gate Score: {formatNum(m.gate_score)}</p>

        <p>📊 Estado: {m.state}</p>
        <p>🪟 Ventana: {m.window_phase}</p>
        <p>🧾 Data quality: {m.data_quality}</p>

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
