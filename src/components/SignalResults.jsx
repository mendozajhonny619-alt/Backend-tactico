import React from "react";

export default function SignalResults({ summary, rows }) {
  return (
    <div className="panel">
      <h2>⚡ RENDIMIENTO DE SEÑALES IA</h2>

      {/* RESUMEN */}
      <div className="summary-box">
        <div className="summary-item success">
          <h3>{summary?.aciertos || 0}</h3>
          <p>Aciertos</p>
        </div>

        <div className="summary-item error">
          <h3>{summary?.fallos || 0}</h3>
          <p>Fallos</p>
        </div>

        <div className="summary-item active">
          <h3>{summary?.activas || 0}</h3>
          <p>Activas</p>
        </div>
      </div>

      {/* HISTORIAL */}
      <h3 style={{ marginTop: "20px" }}>📊 HISTORIAL DE PRONÓSTICOS</h3>

      {rows && rows.length > 0 ? (
        rows.map((item) => (
          <div key={item.id} className={`signal-card ${item.state?.toLowerCase()}`}>
            <strong>
              {item.home} vs {item.away}
            </strong>
            <p>{item.league}</p>

            <p>Señal: {item.signal}</p>
            <p>Resultado: {item.result}</p>

            <span className="status">{item.state}</span>
          </div>
        ))
      ) : (
        <div className="panel">No hay historial disponible</div>
      )}
    </div>
  );
}
