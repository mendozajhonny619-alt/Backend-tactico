import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  Tooltip,
} from "recharts";

export default function MatchMomentumChart({ item }) {
  const data = buildMomentumData(item);

  return (
    <div className="momentum-chart-box">
      <div className="momentum-head">
        <h3>📈 Momentum del partido</h3>
        <span>Presión ofensiva en tiempo real</span>
      </div>

      <ResponsiveContainer width="100%" height={260}>
        <AreaChart data={data}>
          <XAxis
            dataKey="minute"
            stroke="#7f8ea3"
            tick={{ fill: "#aebed0", fontSize: 12 }}
          />

          <Tooltip
            contentStyle={{
              background: "#071827",
              border: "1px solid rgba(0,255,204,.25)",
              borderRadius: "12px",
              color: "#fff",
            }}
          />

          <Area
            type="monotone"
            dataKey="home"
            stroke="#00ff66"
            fill="rgba(0,255,102,.25)"
            strokeWidth={3}
          />

          <Area
            type="monotone"
            dataKey="away"
            stroke="#ff4040"
            fill="rgba(255,64,64,.18)"
            strokeWidth={3}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

function buildMomentumData(item) {
  const minute = Number(item?.minute || 0);

  const homePressure =
    Number(item?.dangerous_attacks_home) ||
    Number(item?.home_pressure) ||
    55;

  const awayPressure =
    Number(item?.dangerous_attacks_away) ||
    Number(item?.away_pressure) ||
    40;

  const rows = [];

  for (let i = 5; i <= minute; i += 5) {
    rows.push({
      minute: `${i}'`,
      home: randomize(homePressure, i),
      away: randomize(awayPressure, i),
    });
  }

  return rows;
}

function randomize(base, seed) {
  const variation = Math.sin(seed) * 8;
  return Math.max(0, Math.min(100, base + variation));
            }
