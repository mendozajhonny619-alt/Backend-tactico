import React from "react";
import "../styles/components.css";

const LiveSignalFeed = ({ events = [] }) => {
  const safeEvents = Array.isArray(events) ? events : [];

  return (
    <div className="glass-card live-signal-feed">
      <div className="card-header">
        <h3>📡 Feed Live IA</h3>
        <span className="live-mini-badge">LIVE</span>
      </div>

      {safeEvents.length === 0 ? (
        <p className="no-signals">Sin eventos live por ahora.</p>
      ) : (
        <ul className="live-feed-list">
          {safeEvents.slice(0, 12).map((event, index) => (
            <li key={`${event}-${index}`}>
              <span className="live-dot" />
              {event}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default LiveSignalFeed;
