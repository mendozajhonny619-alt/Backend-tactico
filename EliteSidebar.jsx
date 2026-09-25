export default function EliteSidebar({ activeTab, setActiveTab }) {
  const items = [
    { id: "signals", label: "Dashboard", icon: "🏠", badge: null },
    { id: "opportunities", label: "Señales en Vivo", icon: "⚡", badge: "12" },
    { id: "results", label: "Historial", icon: "🏆", badge: null },
    { id: "stats", label: "Estadísticas", icon: "📊", badge: null },
    { id: "analysis", label: "Análisis", icon: "📈", badge: null },
    { id: "config", label: "Configuración", icon: "⚙️", badge: null },
  ];

  return (
    <aside className="elite-sidebar">
      <div className="elite-logo">
        <div className="elite-logo-icon">⚡</div>
        <div>
          <strong>JHONNY</strong>
          <span>ELITE V16</span>
        </div>
      </div>

      <nav className="elite-menu">
        {items.map((item) => (
          <button
            key={item.id}
            className={`elite-menu-btn ${activeTab === item.id ? "active" : ""}`}
            onClick={() => setActiveTab(item.id)}
          >
            <span>{item.icon}</span>
            <b>{item.label}</b>
            {item.badge ? <em>{item.badge}</em> : null}
          </button>
        ))}
      </nav>

      <div className="elite-analyst">
        <div className="elite-avatar">EA</div>
        <div>
          <strong>Elite Analyst</strong>
          <span>Online</span>
        </div>
      </div>
    </aside>
  );
}
