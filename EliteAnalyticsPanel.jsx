import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  XAxis,
  YAxis,
  Tooltip,
} from "recharts";

export default function EliteAnalyticsPanel({ history = [], signals = [] }) {
  const roiData = buildRoiData(history);
  const marketData = buildMarketData(history);
  const rankData = buildRankData(history);
  const liveData = buildLiveData(signals);

  return (
    <section className="elite-analytics-panel">
      <div className="analytics-head">
        <div>
          <h2>📊 Estadísticas y rendimiento</h2>
          <p>Datos calculados desde historial y señales reales del sistema.</p>
        </div>

        <div className="analytics-date">Live Performance</div>
      </div>

      <div className="analytics-grid-top">
        <AnalyticsCard title="Total señales" value={history.length} />
        <AnalyticsCard title="Señales live" value={signals.length} />
        <AnalyticsCard title="Win rate" value={`${calcWinRate(history)}%`} />
        <AnalyticsCard title="ROI estimado" value={`${calcRoi(history)}%`} positive />
      </div>

      <div className="analytics-chart-grid">
        <div className="analytics-card large">
          <h3>Evolución del ROI</h3>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={roiData}>
              <XAxis dataKey="index" stroke="#7f8ea3" />
              <YAxis stroke="#7f8ea3" />
              <Tooltip />
              <Line type="monotone" dataKey="roi" stroke="#00ff66" strokeWidth={3} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="analytics-card large">
          <h3>Rendimiento por mercado</h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={marketData}>
              <XAxis dataKey="name" stroke="#7f8ea3" />
              <YAxis stroke="#7f8ea3" />
              <Tooltip />
              <Bar dataKey="winRate" fill="#00ffcc" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="analytics-card">
          <h3>Distribución por rango</h3>
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie data={rankData} dataKey="value" nameKey="name" innerRadius={55} outerRadius={85}>
                {rankData.map((_, i) => (
                  <Cell key={i} fill={["#00ff66", "#00ffcc", "#ffd54f", "#ff4040"][i % 4]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="analytics-card">
          <h3>Señales live actuales</h3>
          <div className="live-signal-list">
            {liveData.length === 0 ? (
              <div className="empty-box">No hay señales live ahora mismo.</div>
            ) : (
              liveData.slice(0, 8).map((item, index) => (
                <div className="live-signal-row" key={index}>
                  <span>{item.match}</span>
                  <b>{item.market}</b>
                  <em>{item.score}</em>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

function AnalyticsCard({ title, value, positive = false }) {
  return (
    <div className="analytics-kpi">
      <span>{title}</span>
      <b className={positive ? "positive" : ""}>{value}</b>
    </div>
  );
}

function buildRoiData(history) {
  let roi = 0;

  return history.map((item, index) => {
    const result = resultType(item);
    if (result === "win") roi += 1.25;
    if (result === "loss") roi -= 1;

    return {
      index: index + 1,
      roi: Number(roi.toFixed(2)),
    };
  });
}

function buildMarketData(history) {
  const map = {};

  history.forEach((item) => {
    const market = String(item?.market || item?.type || "N/A").toUpperCase();
    if (!map[market]) map[market] = { name: market, wins: 0, losses: 0 };

    const result = resultType(item);
    if (result === "win") map[market].wins += 1;
    if (result === "loss") map[market].losses += 1;
  });

  return Object.values(map).map((row) => ({
    name: row.name,
    winRate:
      row.wins + row.losses > 0
        ? Number(((row.wins / (row.wins + row.losses)) * 100).toFixed(1))
        : 0,
  }));
}

function buildRankData(history) {
  const map = {};

  history.forEach((item) => {
    const rank = String(item?.rank || item?.signal_rank || "N/A").toUpperCase();
    map[rank] = (map[rank] || 0) + 1;
  });

  return Object.entries(map).map(([name, value]) => ({ name, value }));
}

function buildLiveData(signals) {
  return signals.map((item) => ({
    match: item?.match_name || "Partido",
    market: item?.market || item?.type || "N/A",
    score: Number(item?.signal_score || 0).toFixed(1),
  }));
}

function calcWinRate(history) {
  const wins = history.filter((x) => resultType(x) === "win").length;
  const losses = history.filter((x) => resultType(x) === "loss").length;

  if (wins + losses === 0) return "0.0";
  return ((wins / (wins + losses)) * 100).toFixed(1);
}

function calcRoi(history) {
  let roi = 0;

  history.forEach((item) => {
    const result = resultType(item);
    if (result === "win") roi += 1.25;
    if (result === "loss") roi -= 1;
  });

  return roi.toFixed(2);
}

function resultType(item) {
  const text = String(
    item?.resultado_final ||
      item?.status ||
      item?.resultado ||
      item?.result ||
      item?.final_status ||
      item?.history_status ||
      ""
  ).toUpperCase();

  if (text.includes("WIN") || text.includes("ACIERTO") || text.includes("GAN")) return "win";
  if (text.includes("LOSS") || text.includes("FALLO") || text.includes("PERD")) return "loss";

  return "pending";
                                                  }
