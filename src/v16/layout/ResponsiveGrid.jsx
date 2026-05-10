// src/v16/layout/ResponsiveGrid.jsx

import React from "react";
import "../styles/dashboard.css";

export default function ResponsiveGrid({ children }) {
  return (
    <div className="responsive-grid">
      {children}
    </div>
  );
}
