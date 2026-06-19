export function getMarketLabel(signal = {}) {
  const market =
    signal.final_market ||
    signal.market_direction ||
    signal.suggested_market ||
    signal.market ||
    signal.prediction_market ||
    "";

  const normalized = String(market).toUpperCase();

  if (normalized.includes("OVER")) return "OVER";
  if (normalized.includes("UNDER")) return "UNDER";
  if (normalized.includes("NO_BET")) return "NO RECOMENDADO";
  if (normalized.includes("OBSERVE")) return "OBSERVACIÓN";

  return "OBSERVACIÓN";
}

export function getSignalTitle(signal = {}) {
  const market = getMarketLabel(signal);
  const label =
    signal.panel_label ||
    signal.activation_label ||
    signal.promotion_panel_label ||
    signal.master_status ||
    signal.elite_rank ||
    "";

  const normalized = String(label).toUpperCase();

  if (normalized.includes("NO") && normalized.includes("RECOM")) {
    return "NO RECOMENDADO";
  }

  if (normalized.includes("FUERTE") || normalized.includes("STRONG")) {
    return `${market} FUERTE`;
  }

  if (normalized.includes("CANDIDATE") || normalized.includes("CANDIDATO")) {
    return `${market} CANDIDATO`;
  }

  if (normalized.includes("WAIT") || normalized.includes("OBSERVE")) {
    return "OBSERVACIÓN";
  }

  return `${market} CANDIDATO`;
}

export function getRiskLabel(signal = {}) {
  const risk = String(signal.risk_status || signal.risk_level || "").toUpperCase();

  if (risk.includes("LOW")) return "BAJO RIESGO";
  if (risk.includes("MEDIUM") || risk.includes("CONTROLLED")) return "RIESGO MEDIO";
  if (risk.includes("HIGH")) return "RIESGO ALTO";

  return "RIESGO CONTROLADO";
}

export function getNextGoalLabel(signal = {}) {
  const value =
    signal.prediction_next_goal_probability ||
    signal.next_goal_probability ||
    signal.next_goal ||
    "";

  const normalized = String(value).toUpperCase();

  if (normalized.includes("VERY_HIGH")) return "VERY HIGH";
  if (normalized.includes("HIGH")) return "HIGH";
  if (normalized.includes("MEDIUM")) return "MEDIUM";
  if (normalized.includes("LOW")) return "LOW";

  return "MEDIUM";
}

export function getConfidence(signal = {}) {
  const value =
    signal.master_confidence ??
    signal.elite_score ??
    signal.prediction_confidence ??
    signal.confidence ??
    0;

  return Math.round(Number(value) || 0);
}

export function getProbableScore(signal = {}) {
  return (
    signal.prediction_score ||
    signal.prediction_main_score ||
    signal.probable_score?.probable_score ||
    signal.current_score ||
    signal.scoreline ||
    "-"
  );
}

export function getTeamNames(signal = {}) {
  return {
    home: signal.home_team || signal.home_name || signal.home || "Local",
    away: signal.away_team || signal.away_name || signal.away || "Visitante",
  };
}

export function getTeamLogos(signal = {}) {
  return {
    homeLogo: signal.home_logo || signal.home_team_logo || signal.local_logo || null,
    awayLogo: signal.away_logo || signal.away_team_logo || signal.visitor_logo || null,
  };
}

export function getTeamInitiative(signal = {}) {
  const home =
    signal.home_attack_probability ||
    signal.home_initiative_probability ||
    signal.home_win_probability ||
    50;

  const away =
    signal.away_attack_probability ||
    signal.away_initiative_probability ||
    signal.away_win_probability ||
    100 - Number(home);

  return {
    home: Math.round(Number(home) || 50),
    away: Math.round(Number(away) || 50),
  };
}

export function getCardTone(signal = {}) {
  const title = getSignalTitle(signal);

  if (title.includes("OVER")) return "over";
  if (title.includes("UNDER")) return "under";
  if (title.includes("NO RECOMENDADO")) return "danger";
  return "observe";
    }
