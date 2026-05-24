import React from "react";
import SignalCardV17 from "./SignalCardV17";

export default function SectionPanelV17({ title, subtitle, items = [], compact = false, emptyText }) {
  return (
    <section className="v17-section-panel">
      <div className="v17-section-header">
        <div>
          <h2>{title}</h2>
          {subtitle ? <p>{subtitle}</p> : null}
        </div>
        <span>{items.length}</span>
      </div>

      {items.length > 0 ? (
        <div className={compact ? "v17-card-list compact" : "v17-card-list"}>
          {items.map((item, index) => (
            <SignalCardV17
              key={item.signal_key || item.signal_id || `${title}-${index}`}
              signal={item}
              compact={compact}
            />
          ))}
        </div>
      ) : (
        <div className="v17-empty">{emptyText || "Sin registros por ahora."}</div>
      )}
    </section>
  );
}
