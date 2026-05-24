import React from "react";

function safe(value, fallback = "—") {
  return value === null || value === undefined || value === "" ? fallback : value;
}

function initials(name) {
  const text = String(name || "").trim();
  if (!text) return "FC";

  const parts = text.split(" ").filter(Boolean);

  if (parts.length === 1) {
    return parts[0].slice(0, 2).toUpperCase();
  }

  return `${parts[0][0] || ""}${parts[1][0] || ""}`.toUpperCase();
}

function countryFlag(country) {
  const text = String(country || "").toUpperCase();

  if (text.includes("BRAZIL") || text.includes("BRASIL")) return "🇧🇷";
  if (text.includes("USA") || text.includes("UNITED STATES")) return "🇺🇸";
  if (text.includes("MEXICO")) return "🇲🇽";
  if (text.includes("ARGENTINA")) return "🇦🇷";
  if (text.includes("BOLIVIA")) return "🇧🇴";
  if (text.includes("CHILE")) return "🇨🇱";
  if (text.includes("COLOMBIA")) return "🇨🇴";
  if (text.includes("PERU")) return "🇵🇪";
  if (text.includes("URUGUAY")) return "🇺🇾";
  if (text.includes("PARAGUAY")) return "🇵🇾";
  if (text.includes("ECUADOR")) return "🇪🇨";
  if (text.includes("VENEZUELA")) return "🇻🇪";
  if (text.includes("CANADA")) return "🇨🇦";

  return "🏳️";
}

function TeamLogo({ name, logo }) {
  if (logo) {
    return (
      <div className="v17-team-logo">
        <img src={logo} alt={name || "team"} />
      </div>
    );
  }

  return <div className="v17-team-logo fallback">{initials(name)}</div>;
}

export default function TeamIdentityV17({ signal }) {
  const homeLogo =
    signal.home_logo ||
    signal.home_team_logo ||
    signal.local_logo ||
    signal.team_home_logo;

  const awayLogo =
    signal.away_logo ||
    signal.away_team_logo ||
    signal.visitor_logo ||
    signal.team_away_logo;

  const leagueLogo =
    signal.league_logo ||
    signal.competition_logo ||
    signal.tournament_logo;

  return (
    <div className="v17-identity">
      <div className="v17-league-strip">
        <div className="v17-league-left">
          {leagueLogo ? (
            <img className="v17-league-logo" src={leagueLogo} alt="league" />
          ) : (
            <span className="v17-flag">{countryFlag(signal.country)}</span>
          )}

          <div>
            <strong>{safe(signal.league, "Liga no identificada")}</strong>
            <span>{safe(signal.country, "País no identificado")}</span>
          </div>
        </div>

        <div className="v17-minute-pill">
          API {safe(signal.api_minute)}
          <small>EST {safe(signal.estimated_minute)}</small>
        </div>
      </div>

      <div className="v17-scoreboard">
        <div className="v17-team-side">
          <TeamLogo name={signal.home_team} logo={homeLogo} />
          <strong>{safe(signal.home_team)}</strong>
        </div>

        <div className="v17-score-center">
          <span>{safe(signal.scoreline || signal.current_score, "0-0")}</span>
          <small>{safe(signal.status, "LIVE")}</small>
        </div>

        <div className="v17-team-side right">
          <TeamLogo name={signal.away_team} logo={awayLogo} />
          <strong>{safe(signal.away_team)}</strong>
        </div>
      </div>
    </div>
  );
            }
