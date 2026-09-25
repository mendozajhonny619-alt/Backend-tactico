export default function EliteMetricCard({ title, value, sub, tone = "default" }) {
  return (
    <div className={`elite-metric-card ${tone}`}>
      <span>{title}</span>
      <strong>{value}</strong>
      {sub ? <small>{sub}</small> : null}
    </div>
  );
}
