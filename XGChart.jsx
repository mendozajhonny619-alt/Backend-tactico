import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
} from "recharts";

export default function XGChart({ item }) {
  const data = buildXGData(item);
  const homeName = item?.home || item?.home_name || "Local";
  const awayName = item?.away || item?.away_name || "Visitante";

  const homeXG = Number(
    item?.home_xg ??
      item?.home_stats?.xg ??
      item?.home_stats?.xG ??
      0
  );

  const awayXG = Number(
    item?.away_xg ??
      item?.away_stats?.xg ??
      item?.away_stats?.xG ??
      0
  );

  return (
    <div className="xg-chart-box">
      <div className="xg-head">
        <div>
          <h3>🎯 xG / Goles esperados</h3>
          <span>Evolución estimada con datos reales disponibles</span>
        </div>

        <div className="xg-score-boxes">
          <div>
            <small>{homeName}</small>
            <b>{homeXG > 0 ? homeXG.toFixed(2) : "N/A"}</b>
          </div>

          <div>
            <small>{awayName}</small>
            <b>{awayXG > 0 ? awayXG.toFixed(2) : "N/A"}</b>
          </div>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data}>
          <XAxis
            dataKey="minute"
            stroke="#7f8ea3"
            tick={{ fill: "#aebed0", fontSize: 12 }}
          />

          <YAxis
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

          <Legend />

          <Line
            type="monotone"
            dataKey="home"
            name={homeName}
            stroke="#00ff66"
            strokeWidth={3}
            dot={false}
          />

          <Line
            type="monotone"
            dataKey="away"
            name={awayName}
            stroke="#00b7ff"
            strokeWidth={3}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function buildXGData(item) {
  const minute = Math.max(5, Number(item?.minute || 0));

  const homeXG = Number(
    item?.home_xg ??
      item?.home_stats?.xg ??
      item?.home_stats?.xG ??
      0
  );

  const awayXG = Number(
    item?.away_xg ??
      item?.away_stats?.xg ??
      item?.away_stats?.xG ??
      0
  );

  const data = [];

  for (let i = 5; i <= minute; i += 5) {
    const factor = i / Math.max(minute, 1);

    data.push({
      minute: `${i}'`,
      home: Number((homeXG * factor).toFixed(2)),
      away: Number((awayXG * factor).toFixed(2)),
    });
  }

  if (data.length === 0) {
    data.push({
      minute: "0'",
      home: 0,
      away: 0,
    });
  }

  return data;
              }
