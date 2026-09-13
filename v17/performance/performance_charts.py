from __future__ import annotations

from typing import Any, Dict, Iterable, List


class PerformanceCharts:
    """
    Text rendering utilities for performance reports.

    EVALUATION_ONLY. No authority, no publication, no official_* mutation.
    """

    ROLE = "EVALUATION_ONLY"

    def render_all(self, metrics: Dict[str, Any]) -> str:
        sections = [
            self.global_summary_box(metrics.get("global_accuracy", {})),
            self.accuracy_table("Precisión por mercado", metrics.get("by_market", [])),
            self.accuracy_table("Precisión por liga", metrics.get("by_league", [])),
            self.accuracy_table("Precisión por minuto", metrics.get("by_minute", [])),
            self.accuracy_table(
                "Precisión por calidad de datos",
                metrics.get("by_data_source_quality", []),
            ),
            self.calibration_table(metrics.get("confidence_calibration", [])),
        ]

        return "\n\n".join(sections)

    def global_summary_box(self, data: Dict[str, Any]) -> str:
        precision = self._float(data, "precision", "accuracy_pct")
        total = self._int(data, "sample_count", "total")
        decided = self._int(data, "decided")
        won = self._int(data, "won")
        lost = self._int(data, "lost")

        return "\n".join(
            [
                "Resumen global",
                "--------------",
                f"Precisión real: {precision:.2f}% {self.bar(precision)}",
                f"Señales evaluables: {total}",
                f"Decididas: {decided}",
                f"Acertadas: {won}",
                f"Falladas: {lost}",
            ]
        )

    def accuracy_table(
        self,
        title: str,
        rows: Any,
        limit: int = 12,
    ) -> str:
        normalized = self._rows(rows)
        lines = [title, "-" * len(title)]

        if not normalized:
            lines.append("Sin datos suficientes.")
            return "\n".join(lines)

        for row in normalized[:limit]:
            label = str(row.get("label") or row.get("group_key") or "UNKNOWN")
            precision = self._float(row, "precision", "accuracy_pct")
            total = self._int(row, "sample_count", "total")
            decided = self._int(row, "decided")
            won = self._int(row, "won")
            lost = self._int(row, "lost")

            lines.append(
                f"{label[:28]:28} {precision:6.2f}% {self.bar(precision)} "
                f"total={total} dec={decided} W={won} L={lost}"
            )

        return "\n".join(lines)

    def calibration_table(self, rows: Any) -> str:
        normalized = self._rows(rows)
        lines = [
            "Calibración por official_confidence",
            "------------------------------------",
        ]

        if not normalized:
            lines.append("Sin datos suficientes.")
            return "\n".join(lines)

        for row in normalized:
            label = str(row.get("label") or row.get("group_key") or "UNKNOWN")
            precision = self._float(row, "precision", "accuracy_pct")
            avg_conf = self._float(row, "avg_official_confidence")
            gap = self._float(row, "calibration_gap")
            total = self._int(row, "sample_count", "total")

            lines.append(
                f"{label[:10]:10} real={precision:6.2f}% "
                f"conf={avg_conf:6.2f}% "
                f"gap={gap:7.2f} {self.bar(precision)} total={total}"
            )

        return "\n".join(lines)

    def simple_ranking(
        self,
        title: str,
        rows: Any,
        limit: int = 5,
    ) -> str:
        normalized = self._rows(rows)
        lines = [title, "-" * len(title)]

        if not normalized:
            lines.append("Sin datos suficientes.")
            return "\n".join(lines)

        for row in normalized[:limit]:
            label = str(row.get("label") or row.get("group_key") or "UNKNOWN")
            precision = self._float(row, "precision", "accuracy_pct")
            total = self._int(row, "sample_count", "total")
            won = self._int(row, "won")
            lost = self._int(row, "lost")

            lines.append(
                f"- {label}: {precision:.2f}% "
                f"en {total} muestras (W={won}, L={lost})"
            )

        return "\n".join(lines)

    def bar(
        self,
        value: float,
        max_value: float = 100.0,
        width: int = 22,
    ) -> str:
        try:
            ratio = max(0.0, min(float(value) / max_value, 1.0))
        except Exception:
            ratio = 0.0

        filled = int(round(ratio * width))
        return "█" * filled + "░" * (width - filled)

    def _rows(self, rows: Any) -> List[Dict[str, Any]]:
        if isinstance(rows, dict):
            out = []

            for key, value in rows.items():
                if isinstance(value, dict):
                    item = dict(value)
                    item.setdefault("label", key)
                    item.setdefault("group_key", key)
                    out.append(item)

            return out

        if isinstance(rows, Iterable) and not isinstance(rows, (str, bytes)):
            return [row for row in rows if isinstance(row, dict)]

        return []

    def _float(self, row: Dict[str, Any], *keys: str) -> float:
        for key in keys:
            if key in row and row.get(key) not in (None, ""):
                try:
                    return float(row.get(key))
                except Exception:
                    continue

        return 0.0

    def _int(self, row: Dict[str, Any], *keys: str) -> int:
        for key in keys:
            if key in row and row.get(key) not in (None, ""):
                try:
                    return int(float(row.get(key)))
                except Exception:
                    continue

        return 0
