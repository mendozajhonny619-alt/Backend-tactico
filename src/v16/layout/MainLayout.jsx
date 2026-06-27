// src/v16/layout/MainLayout.jsx

import React from "react";
import "../styles/Dashboard.css";

export default function MainLayout({ children }) {
  return (
    <div className="main-layout champions-bg">
      <div className="stadium-lights" />
      <div className="blue-glow-left" />
      <div className="blue-glow-right" />
      <div className="pitch-grid-overlay" />

      <main className="main-content">
        {children}
      </main>
    </div>
  );
}
