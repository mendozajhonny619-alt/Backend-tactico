import React from "react";
import "../styles/components.css";

const safe = (value, fallback = "N/A") => {
  if (value === undefined || value === null || value === "") return fallback;
  return value;
};

const num = (value, fallback = 0) => {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
};

const pct = (value) => `${num(value).toFixed(1)}%`;

const getActionLabel = (action) => {
  const value = String(action || "").toUpperCase();

  if (value.includes("ALLOW_ANALYSIS")) return "ANÁLISIS PERMITIDO";
  if (value.includes("CONFIRMATION")) return "ESPERAR CONFIRMACIÓN";
  if (value.includes("OBSERVE_STRICT")) return "OBSERVACIÓN ESTRICTA";
  if (value.includes("OBSERVE")) return "OBSERVAR";
  if (value.includes("WAIT")) return "ESPERAR";

  return safe(action, "SIN ACCIÓN");
};

const getTone = (value) => {
  const text = String(value || "").toUpperCase();

  if (
    text.includes("PREMIUM") ||
    text.includes("STRONG") ||
    text.includes("ENTER") ||
    text.includes("ALLOW") ||
    text.includes("BAJO")
  ) {
    return "good";
  }

  if (
    text.includes("DANGER") ||
    text.includes("ALTO") ||
    text.includes("AVOID") ||
    text.includes("NO_REENTRY")
  ) {
    return "danger";
  }

  if (
    text.includes("WAIT") ||
    text.includes("OBSERVE") ||
    text.includes("MEDIO") ||
    text.includes("CONFIRM")
  ) {
    return "warn";
  }

  return "neutral";
};

export default function AIBrainPanel({ match }) {
  if (!match) return null;

  const sportsSummary =
    match.sports_ai_summary ||
    match.sportsAISummary ||
    match.sports_ai_advice ||
    "La IA todavía no generó una conclusión contextual.";

  const preMatchSummary =
    match.pre_match_summary ||
    match.preMatchSummary ||
    "Sin lectura prepartido disponible.";

  const adaptiveSummary =
    match.adaptive_learning_summary ||
    match.adaptiveLearningSummary ||
    "Sin aprendizaje adaptativo disponible.";

  const nextGoalSummary =
    match.next_goal_summary_ai ||
    match.nextGoalSummaryAi ||
    match.next_goal_helper_advice ||
    match.nextGoalHelperAdvice ||
    "Sin lectura Next Goal IA.";

  const deepSummary =
    match.deep_analysis_summary ||
    match.deepAnalysisSummary ||
    "Sin análisis profundo disponible.";

  const action = getActionLabel(
    match.sports_ai_action ||
      match.sportsAIAction ||
      match.final_decision ||
      match.finalDecision
  );

  const confidence = num(
    match.sports_ai_confidence ??
      match.sportsAIConfidence ??
      match.final_decision_confidence ??
      match.finalDecisionConfidence ??
      match.pre_match_confidence
  );

  const adaptiveAdjustment = num(
    match.adaptive_confidence_adjustment ??
      match.adaptiveConfidenceAdjustment
  );

  const leagueLevel =
    match.sports_ai_league_level ||
    match.league_stability_level ||
    match.leagueStabilityLevel ||
    "NO CLASIFICADA";

  const preMatchPrediction =
    match.pre_match_prediction ||
    match.preMatchPrediction ||
    "BALANCED";

  const nextGoalBias =
    match.next_goal_bias_ai ||
    match.nextGoalBiasAi ||
    match.next_goal_bias ||
    match.nextGoalBias ||
    "NEUTRAL";

  const deepBias =
    match.deep_projection_bias ||
    match.deepProjectionBias ||
    "NEUTRAL";

  const riskFlags =
    match.adaptive_warning_flags ||
    match.sports_ai_risk_flags ||
    match.risk_flags ||
    [];

  return (
    <section className="glass-card ai-brain-panel">
      <div className="ai-brain-header">
        <div>
          <span className="ai-brain-eyebrow">CEREBRO IA DEPORTIVO</span>
          <h3>🧠 Lectura Inteligente del Partido</h3>
          <p>Fusión de prepartido, live, memoria, riesgo y proyección.</p>
        </div>

        <div className={`ai-brain-action ${getTone(action)}`}>
          <span>ACCIÓN IA</span>
          <strong>{action}</strong>
        </div>
      </div>

      <div className="ai-brain-kpis">
        <BrainKpi
          label="Confianza IA"
          value={pct(confidence)}
          tone={getTone(confidence >= 70 ? "good" : confidence >= 50 ? "warn" : "danger")}
        />

        <BrainKpi
          label="Ajuste histórico"
          value={`${adaptiveAdjustment >= 0 ? "+" : ""}${adaptiveAdjustment.toFixed(1)}`}
          tone={getTone(adaptiveAdjustment >= 3 ? "good" : adaptiveAdjustment < 0 ? "danger" : "warn")}
        />

        <BrainKpi
          label="Liga"
          value={leagueLevel}
          tone={getTone(leagueLevel)}
        />

        <BrainKpi
          label="PreMatch"
          value={preMatchPrediction}
          tone={getTone(preMatchPrediction)}
        />

        <BrainKpi
          label="Next Goal"
          value={nextGoalBias}
          tone={getTone(nextGoalBias)}
        />

        <BrainKpi
          label="Deep Bias"
          value={deepBias}
          tone={getTone(deepBias)}
        />
      </div>

      <div className="ai-brain-grid">
        <BrainBlock
          title="Sports AI"
          text={sportsSummary}
          tone={getTone(action)}
        />

        <BrainBlock
          title="Prepartido IA"
          text={preMatchSummary}
          tone={getTone(preMatchPrediction)}
        />

        <BrainBlock
          title="Aprendizaje adaptativo"
          text={adaptiveSummary}
          tone={getTone(adaptiveAdjustment < 0 ? "danger" : "good")}
        />

        <BrainBlock
          title="Next Goal IA"
          text={nextGoalSummary}
          tone={getTone(nextGoalBias)}
        />

        <BrainBlock
          title="Deep Analysis"
          text={deepSummary}
          tone={getTone(deepBias)}
        />
      </div>

      {Array.isArray(riskFlags) && riskFlags.length > 0 && (
        <div className="ai-brain-alerts">
          <span>Alertas IA</span>

          <div>
            {riskFlags.slice(0, 6).map((flag, index) => (
              <b key={`${flag}-${index}`}>{flag}</b>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

function BrainKpi({ label, value, tone = "neutral" }) {
  return (
    <div className={`ai-brain-kpi ${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function BrainBlock({ title, text, tone = "neutral" }) {
  return (
    <div className={`ai-brain-block ${tone}`}>
      <span>{title}</span>
      <p>{safe(text)}</p>
    </div>
  );
  }
