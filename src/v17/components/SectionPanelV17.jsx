import React from "react";
import SignalCardV17 from "./SignalCardV17";

export default function SectionPanelV17({
  title,
  subtitle,
  items = [],
  compact = false,
  dense = false,
  limit = null,
  emptyText,
  onDetail,
  onViewAll,
}) {
  const visibleItems = limit ? items.slice(0, limit) : items;
  return (
    <section className={`v17-section-panel ${dense ? "v17-dense-panel" : ""}`}>
      <div className="v17-section-header">
        <div>
          <h2>{title}</h2>
          {subtitle ? <p>{subtitle}</p> : null}
        </div>
        <div className="v17-section-actions">
          {onViewAll && items.length > visibleItems.length ? (
            <button type="button" onClick={onViewAll}>Ver todas</button>
          ) : null}
          <span>{items.length}</span>
        </div>
      </div>

      {visibleItems.length > 0 ? (
        <div className={`${compact ? "v17-card-list compact" : "v17-card-list"} ${dense ? "dense" : ""}`}>
          {visibleItems.map((item, index) => (
            <SignalCardV17
              key={item.signal_key || item.signal_id || `${title}-${index}`}
              signal={item}
              compact={compact}
              dense={dense}
              onDetail={onDetail}
            />
          ))}
        </div>
      ) : (
        <div className="v17-empty">{emptyText || "Sin registros por ahora."}</div>
      )}
    </section>
  );
}
