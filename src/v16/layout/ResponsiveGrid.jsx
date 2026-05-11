// src/v16/layout/ResponsiveGrid.jsx

import React from "react";

export default function ResponsiveGrid({ children }) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "1.1fr 2fr 1fr",
        gap: "20px",
        alignItems: "start",
        marginTop: "20px",
      }}
    >
      {children}
    </div>
  );
}
