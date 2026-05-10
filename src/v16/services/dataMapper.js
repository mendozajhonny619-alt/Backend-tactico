// src/v16/services/dataMapper.js

// =======================================
// HELPERS
// =======================================

const num = (value, fallback = 0) => {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
};

const text = (value, fallback = "N/A") => {
  if (value === undefined || value === null || value === "") {
    return fallback;
  }

  return String(value);
};

// =======================================
// SCORE BUILDER
// =======================================

const buildScore = (raw) => {
  if (raw?.score && String(raw.score).includes("-")) {
    return String(raw.score);
  }

  const homeScore =
    raw?.home_score ??
    raw?.local_score ??
    raw?.score_home ??
    raw?.marcador_local ??
    0;

  const awayScore =
    raw?.away_score ??
    raw?.visitor_score ??
    raw?.score_away ??
    raw?.marcador_visitante ??
    0;

  return `${homeScore}-${awayScore}`;
};

// =======================================
// MATCH NAME
// =======================================

const buildMatchName = (raw) => {
  return (
    raw?.match_name ||
    raw?.partido ||
    raw?.nombre_partido ||
    (raw?.home && raw?.away
      ? `${raw.home} vs ${raw.away}`
      : null) ||
    (raw?.home_name && raw?.away_name
      ? `${raw.home_name} vs ${raw.away_name}`
      : null) ||
    "PARTIDO"
  );
};

// =======================================
// MAIN MAPPER
// =======================================

export const mapMatchData = (raw) => {
  return {
    // =========================
    // IDs
    // =========================
    id:
      raw?.match_id ||
      raw?.id ||
      `${buildMatchName(raw)}-${raw?.minute || 0}`,

    // =========================
    // EQUIPOS
    // =========================
    home: text(
      raw?.home ||
        raw?.home_name ||
        raw?.home_team ||
        raw?.nombre_local ||
        "Local"
    ),

    away: text(
      raw?.away ||
        raw?.away_name ||
        raw?.away_team ||
        raw?.nombre_visitante ||
        "Visitante"
    ),

    matchName: buildMatchName(raw),

    // =========================
    // PARTIDO
    // =========================
    score: buildScore(raw),

    minute: num(
      raw?.minute ??
        raw?.minuto
    ),

    league: text(
      raw?.league ||
        raw?.liga
    ),

    country: text(
      raw?.country
    ),

    // =========================
    // IA
    // =========================
    aiScore: num(raw?.ai_score),

    signalScore: num(
      raw?.signal_score ||
      raw?.decision_score
    ),

    goalProbability: num(
      raw?.goal_probability
    ),

    overProbability: num(
      raw?.over_probability
    ),

    underProbability: num(
      raw?.under_probability
    ),

    gateScore: num(
      raw?.gate_score
    ),

    // =========================
    // RITMO
    // =========================
    pressureIndex: num(
      raw?.pressure_index
    ),

    rhythmIndex: num(
      raw?.rhythm_index
    ),

    momentum: text(
      raw?.momentum_label
    ),

    dominance: text(
      raw?.dominance
    ),

    // =========================
    // ESTADO
    // =========================
    contextState: text(
      raw?.context_state ||
      raw?.state
    ),

    market: text(
      raw?.market
    ),

    rank: text(
      raw?.rank ||
      raw?.signal_rank
    ),

    // =========================
    // NEXT GOAL
    // =========================
    nextGoalBias: text(
      raw?.next_goal_bias
    ),

    nextGoalConfidence: num(
      raw?.next_goal_confidence
    ),

    scoreHoldProbability: num(
      raw?.score_hold_probability
    ),

    // =========================
    // RIESGO
    // =========================
    riskScore: num(
      raw?.risk_score
    ),

    riskLevel: text(
      raw?.risk_level
    ),

    // =========================
    // STATS
    // =========================
    shots: num(raw?.shots),

    shotsOnTarget: num(
      raw?.shots_on_target
    ),

    corners: num(raw?.corners),

    dangerousAttacks: num(
      raw?.dangerous_attacks
    ),

    xg: num(
      raw?.xg ||
      raw?.xG
    ),

    // =========================
    // RAW ORIGINAL
    // =========================
    raw,
  };
};
