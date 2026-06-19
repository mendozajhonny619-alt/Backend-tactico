import React from "react";
import {
  getCardTone,
  getConfidence,
  getMarketLabel,
  getNextGoalLabel,
  getProbableScore,
  getRiskLabel,
  getSignalTitle,
  getTeamInitiative,
  getTeamLogos,
  getTeamNames,
} from "../utils/signalDisplayMapperV17";

export default function SignalCompactCardV17({ signal, onOpenDetail }) {
  const teams = getTeamNames(signal);
  const logos = getTeamLogos(signal);
  const initiative = getTeamInitiative(signal);

  const title = getSignalTitle(signal);
  const market = getMarketLabel(signal);
  const risk = getRiskLabel(signal);
  const confidence = getConfidence(signal);
  const nextGoal = getNextGoalLabel(signal);
  const probableScore = getProbableScore(signal);
  const tone = getCardTone(signal);

  const minute =
    signal.display_minute ||
    signal.estimated_minute ||
    signal.api_minute ||
    signal.minute ||
    signal.minuto ||
    "-";

  const score =
    signal.scoreline ||
    signal.current_score ||
    signal.score ||
    signal.marcador ||
    `${signal.home_score ?? 0}-${signal.away_score ?? 0}`;

  return (
    <div className={`signal-compact-card-v17 ${tone}`}>
      <div className="compact-col compact-match">
        <div className="compact-minute">⏱ {minute}'</div>

        <div className="compact-teams">
          <div className="compact-team">
            {logos.homeLogo && <img src={logos.homeLogo} alt={teams.home} />}
            <span>{teams.home}</span>
          </div>

          <div className="compact-score">{score}</div>

          <div className="compact-team away">
            {logos.awayLogo && <img src={logos.awayLogo} alt={teams.away} />}
            <span>{teams.away}</span>
          </div>
        </div>

        <div className="compact-league">
          {signal.league || signal.liga || "Competición"}
        </div>
      </div>

      <div className="compact-col compact-main-signal">
        <div className="compact-market">{market}</div>
        <div className="compact-title">{title}</div>
        <div className="compact-risk">{risk}</div>
      </div>

      <div className="compact-col compact-confidence">
        <div className="compact-percent">{confidence}%</div>
        <div className="compact-label">Confianza</div>
        <div className="compact-bar">
          <span style={{ width: `${Math.min(confidence, 100)}%` }} />
        </div>
      </div>

      <div className="compact-col compact-next-goal">
        <div className="compact-circle">{nextGoal}</div>
        <div className="compact-label">Próximo gol</div>
      </div>

      <div className="compact-col compact-score-probable">
        <div className="compact-prob-score">{probableScore}</div>
        <div className="compact-label">Resultado probable</div>
      </div>

      <div className="compact-col compact-initiative">
        <div className="initiative-row">
          <span>{teams.home}</span>
          <strong>{initiative.home}%</strong>
        </div>
        <div className="initiative-bar home">
          <span style={{ width: `${initiative.home}%` }} />
        </div>

        <div className="initiative-row away">
          <span>{teams.away}</span>
          <strong>{initiative.away}%</strong>
        </div>
        <div className="initiative-bar away">
          <span style={{ width: `${initiative.away}%` }} />
        </div>
      </div>

      <div className="compact-col compact-action">
        <button type="button" onClick={() => onOpenDetail?.(signal)}>
          Ver detalle
        </button>
      </div>
    </div>
  );
    }
