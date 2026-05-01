import { useEffect, useMemo, useState } from "react";

const API_BASE = "http://127.0.0.1:8000";

export default function LiveMatches({ onOpenMatch }) {
  const [liveMatches, setLiveMatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    async function loadLiveMatches() {
      try {
        const res = await fetch(`${API_BASE}/live-matches`);
        if (!res.ok) throw new Error("No se pudo cargar /live-matches");

        const json = await res.json();
        if (!active) return;

        setLiveMatches(Array.isArray(json?.items) ? json.items : []);
        setError("");
      } catch (err) {
        if (!active) return;
        setError("No se pudieron cargar los partidos en vivo.");
      } finally {
        if (active) setLoading(false);
      }
    }

    loadLiveMatches();
    const interval = setInterval(loadLiveMatches, 15000);

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  const groupedLeagues = useMemo(() => {
    const groups = {};

    for (const item of liveMatches) {
      const country = item.country || item.pais || "Sin país";
      const league = item.league || item.liga || "Sin liga";
      const key = `${country}__${league}`;

      if (!groups[key]) {
        groups[key] = {
          country,
          league,
          items: [],
        };
      }

      groups[key].items.push(item);
    }

    return Object.values(groups).sort((a, b) => {
      if (a.country !== b.country) return a.country.localeCompare(b.country);
      return a.league.localeCompare(b.league);
    });
  }, [liveMatches]);

  if (loading) {
    return (
      <div className="live-explorer-wrap">
        <div className="live-explorer-box">
          <div className="live-explorer-title">EXPLORADOR DE PARTIDOS EN VIVO</div>
          <div className="empty-box">Cargando partidos en vivo...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="live-explorer-wrap">
        <div className="live-explorer-box">
          <div className="live-explorer-title">EXPLORADOR DE PARTIDOS EN VIVO</div>
          <div className="error-box">{error}</div>
        </div>
      </div>
    );
  }

  if (!groupedLeagues.length) {
    return (
      <div className="live-explorer-wrap">
        <div className="live-explorer-box">
          <div className="live-explorer-title">EXPLORADOR DE PARTIDOS EN VIVO</div>
          <div className="empty-box">
            No hay partidos en vivo disponibles en este momento.
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="live-explorer-wrap">
      <div className="live-explorer-box">
        <div className="live-explorer-title">EXPLORADOR DE PARTIDOS EN VIVO</div>

        {groupedLeagues.map((group, index) => (
          <div
            key={`${group.country}-${group.league}-${index}`}
            className="league-panel"
          >
            <div className="league-panel-header">
              <div className="league-panel-left">
                <span className="league-flag">{flagByCountry(group.country)}</span>
                <div>
                  <div className="league-country-label">
                    {group.country || "Sin país"}
                  </div>
                  <div className="league-title">
                    {group.league || "Sin liga"}
                  </div>
                </div>
              </div>

              <div className="league-panel-icons">
                <span className="league-count-badge">
                  {group.items?.length || 0}
                </span>
              </div>
            </div>

            <div className="league-panel-body">
              {(group.items || []).map((item, idx) => {
                const matchLabel =
                  item.match_name ||
                  item.partido ||
                  item.nombre_partido ||
                  (item.home_name && item.away_name
                    ? `${item.home_name} vs ${item.away_name}`
                    : null) ||
                  (item.home_team && item.away_team
                    ? `${item.home_team} vs ${item.away_team}`
                    : null) ||
                  (item.home && item.away
                    ? `${item.home} vs ${item.away}`
                    : null) ||
                  "Local vs Visitante";

                const [home, away] = splitMatch(
                  matchLabel,
                  item.home_name || item.home_team || item.home || item.nombre_local,
                  item.away_name || item.away_team || item.away || item.nombre_visitante
                );

                const [hg, ag] = splitScore(
                  item.score ||
                    item.marcador ||
                    `${item.home_score ?? item.local_score ?? item.marcador_local ?? 0}-${item.away_score ?? item.visitor_score ?? item.marcador_visitante ?? 0}`
                );

                const pressure = Math.round(
                  Number(item.pressure_score || item.pressure_index || 0)
                );

                const rhythm = Math.round(
                  Number(item.rhythm_score || item.rhythm_index || 0)
                );

                const intensity = guessIntensity({
                  pressure,
                  rhythm,
                  goalProbability: Number(item.goal_probability || 0),
                  overProbability: Number(item.over_probability || 0),
                });

                return (
                  <div
                    key={`${item.match_id || item.id || idx}`}
                    className="live-match-card-pro"
                  >
                    <div className="live-match-top">
                      <div className="live-team-col">
                        <div className="team-crest home">{abbr(home)}</div>
                        <div className="team-name-pro">{home}</div>
                      </div>

                      <div className="live-score-pro">
                        <div className="score-main-pro">
                          {hg} - {ag}
                        </div>
                        <div className="minute-pro">{item.minute || "-"}'</div>
                        <div className="tiny-markers">
                          <span />
                          <span />
                        </div>
                      </div>

                      <div className="live-team-col right">
                        <div className="team-name-pro">{away}</div>
                        <div className="team-crest away">{abbr(away)}</div>
                      </div>
                    </div>

                    <div className="live-match-info">
                      <div>
                        Intensidad: <b>{intensity}</b>
                      </div>
                      <div>
                        Presión: <b className="pressure-number">{pressure}</b>
                      </div>
                      <div>
                        Ritmo: <b>{rhythm}</b>
                      </div>
                      <div>
                        Estado: <b>{item.match_state || item.context_state || "ACTIVO"}</b>
                      </div>
                    </div>

                    <div className="live-mini-stats">
                      <MiniLiveStat
                        label="Tiros al arco"
                        value={
                          item.shots_on_target ||
                          item.tiros_a_target ||
                          item.tiros_al_arco ||
                          0
                        }
                      />
                      <MiniLiveStat
                        label="Ataques"
                        value={item.dangerous_attacks || item.ataques_peligrosos || 0}
                      />
                      <MiniLiveStat
                        label="Corners"
                        value={item.corners || item.córners || 0}
                      />
                      <MiniLiveStat
                        label="xG"
                        value={roundNum(item.xG || item.xg || 0)}
                      />
                    </div>

                    <div className="live-match-actions">
                      <button
                        className="open-small"
                        onClick={() => onOpenMatch && onOpenMatch(item)}
                      >
                        Ver partido
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function MiniLiveStat({ label, value }) {
  return (
    <div className="mini-live-stat">
      <span>{label}</span>
      <b>{value}</b>
    </div>
  );
}

function splitMatch(name = "", homeFallback = "", awayFallback = "") {
  if (homeFallback && awayFallback) {
    return [String(homeFallback), String(awayFallback)];
  }

  if (String(name).includes(" vs ")) {
    const [home, away] = String(name).split(" vs ");
    return [home?.trim() || "Local", away?.trim() || "Visitante"];
  }

  return [homeFallback || "Local", awayFallback || "Visitante"];
}

function splitScore(score = "0-0") {
  const parts = String(score).split("-");
  return [parts[0]?.trim() || "0", parts[1]?.trim() || "0"];
}

function abbr(name = "") {
  return (
    String(name)
      .split(" ")
      .filter(Boolean)
      .slice(0, 2)
      .map((x) => x[0]?.toUpperCase())
      .join("") || "TM"
  );
}

function roundNum(value) {
  return Number(value || 0).toFixed(1);
}

function guessIntensity({
  pressure = 0,
  rhythm = 0,
  goalProbability = 0,
  overProbability = 0,
}) {
  if (pressure >= 70 || rhythm >= 70 || goalProbability >= 70) return "ALTA";
  if (pressure >= 50 || rhythm >= 50 || overProbability >= 55) return "MEDIA";
  return "BAJA";
}

function flagByCountry(country = "") {
  const c = String(country).toLowerCase();

  if (c.includes("spain") || c.includes("españa")) return "🇪🇸";
  if (c.includes("england") || c.includes("inglaterra")) return "🏴";
  if (c.includes("italy") || c.includes("italia")) return "🇮🇹";
  if (c.includes("france") || c.includes("francia")) return "🇫🇷";
  if (c.includes("germany") || c.includes("alemania")) return "🇩🇪";
  if (c.includes("portugal")) return "🇵🇹";
  if (c.includes("netherlands") || c.includes("holanda")) return "🇳🇱";
  if (c.includes("brazil") || c.includes("brasil")) return "🇧🇷";
  if (c.includes("argentina")) return "🇦🇷";
  if (c.includes("colombia")) return "🇨🇴";
  if (c.includes("chile")) return "🇨🇱";
  if (c.includes("ecuador")) return "🇪🇨";
  if (c.includes("mexico")) return "🇲🇽";
  if (c.includes("dominican") || c.includes("dominicana")) return "🇩🇴";
  if (c.includes("iraq")) return "🇮🇶";

  return "🏳️";
}
