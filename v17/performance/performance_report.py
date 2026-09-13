from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from app.v17.performance.performance_charts import PerformanceCharts
from app.v17.performance.performance_learning_ai import PerformanceLearningAI
from app.v17.performance.performance_queries import PerformanceQueries


class PerformanceReport:
    """
    Reporting center for JHONNY ELITE V17 performance.

    EVALUATION_ONLY:
    - no authority
    - no signal publication
    - no official_* mutation
    - no MasterDecisionAI interaction
    - no LiveSignalEngine interaction
    """

    ROLE = "EVALUATION_ONLY"

    def __init__(self, db_path: Optional[str | Path] = None) -> None:
        self.queries = PerformanceQueries(db_path=db_path)
        self.charts = PerformanceCharts()
        self.learning_ai = PerformanceLearningAI()

    def generate(self) -> Dict[str, Any]:
        metrics = self.queries.full_metrics()
        learning = self.learning_ai.generate(metrics)
        text_report = self.render_text(metrics=metrics, learning=learning)

        return {
            "performance_role": self.ROLE,
            "performance_is_official_decision": False,
            "performance_can_publish": False,
            "evaluation_only": True,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "metrics": metrics,
            "learning": learning,
            "text_report": text_report,
        }

    def render_text(
        self,
        metrics: Optional[Dict[str, Any]] = None,
        learning: Optional[Dict[str, Any]] = None,
    ) -> str:
        metrics = metrics or self.queries.full_metrics()
        learning = learning or self.learning_ai.generate(metrics)

        lines = [
            "JHONNY ELITE V17 - Centro de Reporte de Rendimiento",
            "====================================================",
            "",
            "Rol: EVALUATION_ONLY",
            "Autoridad: ninguna",
            "Publicación: no",
            "Modifica official_*: no",
            "Interactúa con MasterDecisionAI: no",
            "Interactúa con LiveSignalEngine: no",
            "",
            self._render_db_status(metrics),
            "",
            self.charts.render_all(metrics),
            "",
            self._render_rankings(metrics),
            "",
            self._render_learning(learning),
        ]

        return "\n".join(lines)

    def save_json(self, output_path: str | Path) -> Path:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        report = self.generate()

        output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

        return output

    def save_text(self, output_path: str | Path) -> Path:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        report = self.generate()
        output.write_text(report["text_report"], encoding="utf-8")

        return output

    def _render_db_status(self, metrics: Dict[str, Any]) -> str:
        db_path = metrics.get("db_path", "")
        database_exists = metrics.get("database_exists", False)
        signal_table = metrics.get("signal_table") or "NO_DETECTADA"
        event_tables = ", ".join(metrics.get("event_tables", [])) or "ninguna"

        return "\n".join(
            [
                "Estado de datos",
                "---------------",
                f"DB: {db_path}",
                f"Existe DB: {database_exists}",
                f"Tabla de señales detectada: {signal_table}",
                f"Tablas de eventos detectadas: {event_tables}",
                f"Señales totales: {metrics.get('total_signals', 0)}",
                f"Señales evaluables: {metrics.get('evaluable_signals', 0)}",
            ]
        )

    def _render_rankings(self, metrics: Dict[str, Any]) -> str:
        sections = [
            self.charts.simple_ranking(
                "Mejores mercados",
                metrics.get("best_markets", []),
            ),
            self.charts.simple_ranking(
                "Peores mercados",
                metrics.get("worst_markets", []),
            ),
            self.charts.simple_ranking(
                "Mejores ligas",
                metrics.get("best_leagues", []),
            ),
            self.charts.simple_ranking(
                "Ligas peligrosas",
                metrics.get("dangerous_leagues", []),
            ),
            self.charts.simple_ranking(
                "Minutos fuertes",
                metrics.get("strong_minutes", []),
            ),
            self.charts.simple_ranking(
                "Minutos débiles",
                metrics.get("weak_minutes", []),
            ),
        ]

        return "\n\n".join(sections)

    def _render_learning(self, learning: Dict[str, Any]) -> str:
        lines = [
            "Recomendaciones y alertas",
            "-------------------------",
        ]

        lines.append("")
        lines.append("Recomendaciones:")

        for item in learning.get("recommendations", []) or [
            "Sin recomendaciones todavía."
        ]:
            lines.append(f"- {item}")

        lines.append("")
        lines.append("Alertas de riesgo:")

        for item in learning.get("risk_alerts", []) or [
            "Sin alertas relevantes."
        ]:
            lines.append(f"- {item}")

        lines.append("")
        lines.append("Sugerencias para aprendizaje futuro:")

        for item in learning.get("learning_suggestions", []) or [
            "Mantener acumulación pasiva de datos."
        ]:
            lines.append(f"- {item}")

        return "\n".join(lines)
