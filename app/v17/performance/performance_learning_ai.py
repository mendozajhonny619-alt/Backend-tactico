from __future__ import annotations

from typing import Any, Dict, List


class PerformanceLearningAI:
    """
    Passive learning interpreter for performance metrics.

    It produces recommendations only. It never decides, publishes, ranks
    live signals, promotes signals, activates signals, or mutates official_*.
    """

    ROLE = "EVALUATION_ONLY"

    def generate(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        recommendations: List[str] = []
        risk_alerts: List[str] = []
        learning_suggestions: List[str] = []

        global_metrics = metrics.get("global_accuracy", {}) if isinstance(metrics, dict) else {}
        precision = self._float(global_metrics, "precision", "accuracy_pct")
        decided = self._int(global_metrics, "decided", "sample_count", "total")

        if decided < 30:
            risk_alerts.append(
                "La muestra todavía es pequeña. No conviene tocar reglas de decisión con menos de 30 señales decididas."
            )
        elif precision < 50:
            risk_alerts.append(
                "La precisión global está por debajo de 50%. Antes de avanzar conviene revisar datos, mercados y tramos débiles."
            )
        elif precision >= 60:
            recommendations.append(
                "La precisión global empieza a mostrar ventaja medible. Conviene identificar qué mercados y minutos sostienen ese rendimiento."
            )

        self._analyze_best_worst(
            metrics=metrics,
            key_best="best_markets",
            key_worst="worst_markets",
            good_label="Mercado fuerte",
            bad_label="Mercado débil",
            recommendations=recommendations,
            risk_alerts=risk_alerts,
            learning_suggestions=learning_suggestions,
        )
        self._analyze_best_worst(
            metrics=metrics,
            key_best="best_leagues",
            key_worst="dangerous_leagues",
            good_label="Liga favorable",
            bad_label="Liga peligrosa",
            recommendations=recommendations,
            risk_alerts=risk_alerts,
            learning_suggestions=learning_suggestions,
        )
        self._analyze_best_worst(
            metrics=metrics,
            key_best="strong_minutes",
            key_worst="weak_minutes",
            good_label="Tramo fuerte",
            bad_label="Tramo débil",
            recommendations=recommendations,
            risk_alerts=risk_alerts,
            learning_suggestions=learning_suggestions,
        )
        self._analyze_data_quality(
            metrics,
            recommendations,
            risk_alerts,
            learning_suggestions,
        )
        self._analyze_confidence(
            metrics,
            recommendations,
            risk_alerts,
            learning_suggestions,
        )

        if not recommendations:
            recommendations.append(
                "Mantener el PerformanceEvaluator en modo pasivo hasta acumular más historial resuelto."
            )

        return {
            "performance_role": self.ROLE,
            "performance_is_official_decision": False,
            "performance_can_publish": False,
            "evaluation_only": True,
            "recommendations": recommendations,
            "risk_alerts": risk_alerts,
            "learning_suggestions": learning_suggestions,
        }

    def _analyze_best_worst(
        self,
        *,
        metrics: Dict[str, Any],
        key_best: str,
        key_worst: str,
        good_label: str,
        bad_label: str,
        recommendations: List[str],
        risk_alerts: List[str],
        learning_suggestions: List[str],
    ) -> None:
        best = self._rows(metrics.get(key_best, []))
        worst = self._rows(metrics.get(key_worst, []))

        if best:
            top = best[0]
            recommendations.append(
                f"{good_label}: {self._label(top)} con {self._precision(top):.2f}% en {self._samples(top)} muestras."
            )

        if worst:
            bad = worst[0]
            risk_alerts.append(
                f"{bad_label}: {self._label(bad)} con {self._precision(bad):.2f}% en {self._samples(bad)} muestras."
            )
            learning_suggestions.append(
                f"Auditar {self._label(bad)} antes de permitir que futuras capas usen este patrón como evidencia fuerte."
            )

    def _analyze_data_quality(
        self,
        metrics: Dict[str, Any],
        recommendations: List[str],
        risk_alerts: List[str],
        learning_suggestions: List[str],
    ) -> None:
        for row in self._rows(metrics.get("by_data_source_quality", [])):
            label = self._label(row).upper()
            precision = self._precision(row)
            samples = self._samples(row)

            if samples < 5:
                continue

            if label in {"LOW_BACKUP", "STALE_CACHE"} and precision < 50:
                risk_alerts.append(
                    f"Calidad de datos riesgosa: {label} rinde {precision:.2f}% en {samples} muestras."
                )
                learning_suggestions.append(
                    f"Evaluar si {label} debe reducir peso de evidencia en una fase futura, sin tocar official_* todavía."
                )

            if label == "HIGH" and precision >= 60:
                recommendations.append(
                    f"Las señales con data_source_quality=HIGH muestran ventaja: {precision:.2f}% en {samples} muestras."
                )

    def _analyze_confidence(
        self,
        metrics: Dict[str, Any],
        recommendations: List[str],
        risk_alerts: List[str],
        learning_suggestions: List[str],
    ) -> None:
        for row in self._rows(metrics.get("confidence_calibration", [])):
            label = self._label(row).upper()
            precision = self._precision(row)
            samples = self._samples(row)

            if samples < 5:
                continue

            if label in {"C70_79", "C80_89", "C90_100"} and precision < 55:
                risk_alerts.append(
                    f"Posible mala calibración: {label} tiene {precision:.2f}% real en {samples} muestras."
                )
                learning_suggestions.append(
                    f"Auditar por qué la confianza oficial alta no se traduce en precisión dentro de {label}."
                )

            if label in {"C70_79", "C80_89", "C90_100"} and precision >= 65:
                recommendations.append(
                    f"Confianza oficial bien calibrada en {label}: {precision:.2f}% real en {samples} muestras."
                )

    def _rows(self, value: Any) -> List[Dict[str, Any]]:
        if isinstance(value, dict):
            out = []

            for key, item in value.items():
                if isinstance(item, dict):
                    row = dict(item)
                    row.setdefault("label", key)
                    row.setdefault("group_key", key)
                    out.append(row)

            return out

        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]

        return []

    def _label(self, row: Dict[str, Any]) -> str:
        return str(row.get("label") or row.get("group_key") or "UNKNOWN")

    def _precision(self, row: Dict[str, Any]) -> float:
        return self._float(row, "precision", "accuracy_pct")

    def _samples(self, row: Dict[str, Any]) -> int:
        return self._int(row, "decided", "sample_count", "total")

    def _float(self, row: Dict[str, Any], *keys: str) -> float:
        for key in keys:
            if row.get(key) not in (None, ""):
                try:
                    return float(row.get(key))
                except Exception:
                    continue

        return 0.0

    def _int(self, row: Dict[str, Any], *keys: str) -> int:
        for key in keys:
            if row.get(key) not in (None, ""):
                try:
                    return int(float(row.get(key)))
                except Exception:
                    continue

        return 0
