from __future__ import annotations

from typing import Any, Dict, List


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except Exception:
        return default


def normalize_market(value: Any) -> str:
    text = str(value or "").upper()

    if "OVER" in text:
        return "OVER"

    if "UNDER" in text:
        return "UNDER"

    if "SOBRE" in text:
        return "OVER"

    if "BAJO" in text:
        return "UNDER"

    return "OTHER"


class PanelDecisionAI:
    """
    Capa final de traducción visual para V17.

    No reemplaza a MasterDecisionAI, DecisionExplainerAI ni SignalRanker.
    Su función es traducir la inteligencia del backend a etiquetas claras
    para el panel visual.

    Objetivo:
    - Si OVER cumple mayoría, mostrar OVER.
    - Si UNDER cumple mayoría, mostrar UNDER.
    - Si falta 1 o 2 filtros no críticos, no ocultar la lectura.
    - Si hay bloqueo crítico, no mostrar como señal.
    - Evitar que el frontend dependa de OTHER / OBSERVE / WAIT_CONFIRMATION.
    """

    def evaluate(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(signal, dict):
            return self._empty()

        market = normalize_market(
            signal.get("market_direction")
            or signal.get("master_market")
            or signal.get("market")
            or signal.get("suggested_market")
            or signal.get("market_category")
        )

        master_status = str(signal.get("master_status") or "").upper()
        master_rank = str(signal.get("master_rank") or "").upper()
        elite_rank = str(signal.get("elite_rank") or "").upper()

        candidate_level = str(signal.get("candidate_level") or "").upper()
        majority_support = bool(signal.get("majority_support"))
        support_ratio = safe_float(signal.get("support_ratio"), 0.0)
        support_score = safe_int(signal.get("support_score"), 0)
        non_critical_missing_count = safe_int(signal.get("non_critical_missing_count"), 99)

        over_candidate_level = str(signal.get("over_candidate_level") or "").upper()
        over_candidate_active = bool(signal.get("over_candidate_active"))
        over_support_ratio = safe_float(signal.get("over_support_ratio"), 0.0)
        over_support_score = safe_int(signal.get("over_support_score"), 0)

        critical_block = bool(signal.get("critical_block"))
        hard_blockers = signal.get("hard_blockers", []) or []
        over_blockers = signal.get("over_blockers", []) or []

        risk_status = str(signal.get("risk_status") or "").upper()
        clock_status = str(signal.get("clock_status") or "").upper()
        data_quality = str(signal.get("data_quality") or "").upper()

        can_publish = bool(signal.get("can_publish"))
        should_observe = bool(signal.get("should_observe"))
        should_block = bool(signal.get("should_block"))

        risk_score = safe_float(signal.get("risk_score"), 0.0)
        elite_score = safe_float(signal.get("elite_score"), 0.0)
        master_confidence = safe_float(signal.get("master_confidence"), 0.0)

        real_offensive_volume = self._has_real_offensive_volume(signal)
        low_stats = self._has_low_stats_warning(signal)

        if self._has_critical_block(
            critical_block=critical_block,
            should_block=should_block,
            hard_blockers=hard_blockers,
            risk_status=risk_status,
            clock_status=clock_status,
        ):
            return self._blocked(signal)

        if market == "OVER":
            return self._panel_for_main_over(
                signal=signal,
                can_publish=can_publish,
                master_status=master_status,
                elite_rank=elite_rank,
                majority_support=majority_support,
                support_ratio=support_ratio,
                support_score=support_score,
                non_critical_missing_count=non_critical_missing_count,
                risk_status=risk_status,
                risk_score=risk_score,
                real_offensive_volume=real_offensive_volume,
                low_stats=low_stats,
                elite_score=elite_score,
                master_confidence=master_confidence,
            )

        if market == "UNDER":
            return self._panel_for_main_under(
                signal=signal,
                can_publish=can_publish,
                master_status=master_status,
                elite_rank=elite_rank,
                candidate_level=candidate_level,
                majority_support=majority_support,
                support_ratio=support_ratio,
                support_score=support_score,
                non_critical_missing_count=non_critical_missing_count,
                risk_status=risk_status,
                risk_score=risk_score,
                real_offensive_volume=real_offensive_volume,
                low_stats=low_stats,
                elite_score=elite_score,
                master_confidence=master_confidence,
            )

        if over_candidate_active or over_candidate_level in {
            "OVER_STRONG_CANDIDATE",
            "OVER_HIGH_OBSERVATION",
        }:
            return self._panel_for_alternative_over(
                signal=signal,
                over_candidate_level=over_candidate_level,
                over_support_ratio=over_support_ratio,
                over_support_score=over_support_score,
                over_blockers=over_blockers,
                risk_status=risk_status,
                risk_score=risk_score,
                real_offensive_volume=real_offensive_volume,
            )

        if candidate_level in {"STRONG_CANDIDATE", "HIGH_OBSERVATION"}:
            inferred_market = self._infer_candidate_market(signal)

            if inferred_market == "UNDER":
                return self._under_candidate(signal)

            if inferred_market == "OVER":
                return self._over_candidate(signal)

            return self._high_observation(signal)

        if should_observe or master_status in {"OBSERVE", "WAIT_CONFIRMATION"}:
            return self._normal_observation(signal)

        return self._no_bet(signal)

    def _panel_for_main_over(
        self,
        signal: Dict[str, Any],
        can_publish: bool,
        master_status: str,
        elite_rank: str,
        majority_support: bool,
        support_ratio: float,
        support_score: int,
        non_critical_missing_count: int,
        risk_status: str,
        risk_score: float,
        real_offensive_volume: bool,
        low_stats: bool,
        elite_score: float,
        master_confidence: float,
    ) -> Dict[str, Any]:
        if (
            can_publish
            and master_status in {"ENTER", "OPERABLE"}
            and elite_rank in {"PREMIUM", "FUERTE", "BUENA", "OPERABLE"}
            and real_offensive_volume
            and risk_status not in {"HIGH_RISK", "EXTREME_RISK"}
        ):
            return {
                "panel_decision_version": "V17_PANEL_DECISION_1",
                "panel_label": "SEÑAL OVER",
                "panel_market": "OVER",
                "panel_decision": "MOSTRAR_SEÑAL",
                "panel_signal_type": "TOP_OVER_SIGNAL",
                "panel_priority": 96,
                "panel_confidence_label": self._confidence_label(elite_score, master_confidence),
                "panel_entry_permission": "OPERABLE",
                "panel_badge": "OVER",
                "panel_color_hint": "green",
                "panel_reason": "OVER cumple condiciones suficientes para mostrarse como señal principal.",
                "panel_warning": self._soft_warning_text(signal),
                "panel_show_as_signal": True,
                "panel_show_as_candidate": False,
                "panel_show_as_observation": False,
            }

        if majority_support and support_ratio >= 0.62 and real_offensive_volume:
            return {
                "panel_decision_version": "V17_PANEL_DECISION_1",
                "panel_label": "OVER CANDIDATO FUERTE",
                "panel_market": "OVER",
                "panel_decision": "MOSTRAR_CANDIDATO",
                "panel_signal_type": "OVER_STRONG_CANDIDATE",
                "panel_priority": 88,
                "panel_confidence_label": "ALTA",
                "panel_entry_permission": "ESPERAR_CONFIRMACION",
                "panel_badge": "OVER",
                "panel_color_hint": "yellow",
                "panel_reason": (
                    f"OVER cumple mayoría de requisitos con soporte {support_score}, "
                    "pero todavía requiere confirmación final."
                ),
                "panel_warning": self._soft_warning_text(signal),
                "panel_show_as_signal": False,
                "panel_show_as_candidate": True,
                "panel_show_as_observation": True,
            }

        return self._over_candidate(signal)

    def _panel_for_main_under(
        self,
        signal: Dict[str, Any],
        can_publish: bool,
        master_status: str,
        elite_rank: str,
        candidate_level: str,
        majority_support: bool,
        support_ratio: float,
        support_score: int,
        non_critical_missing_count: int,
        risk_status: str,
        risk_score: float,
        real_offensive_volume: bool,
        low_stats: bool,
        elite_score: float,
        master_confidence: float,
    ) -> Dict[str, Any]:
        if (
            can_publish
            and master_status in {"ENTER", "OPERABLE"}
            and elite_rank in {"PREMIUM", "FUERTE", "BUENA", "OPERABLE"}
            and risk_status not in {"HIGH_RISK", "EXTREME_RISK"}
            and not real_offensive_volume
        ):
            return {
                "panel_decision_version": "V17_PANEL_DECISION_1",
                "panel_label": "SEÑAL UNDER",
                "panel_market": "UNDER",
                "panel_decision": "MOSTRAR_SEÑAL",
                "panel_signal_type": "TOP_UNDER_SIGNAL",
                "panel_priority": 95,
                "panel_confidence_label": self._confidence_label(elite_score, master_confidence),
                "panel_entry_permission": "OPERABLE",
                "panel_badge": "UNDER",
                "panel_color_hint": "blue",
                "panel_reason": "UNDER cumple condiciones suficientes para mostrarse como señal principal.",
                "panel_warning": self._soft_warning_text(signal),
                "panel_show_as_signal": True,
                "panel_show_as_candidate": False,
                "panel_show_as_observation": False,
            }

        if (
            candidate_level == "STRONG_CANDIDATE"
            or majority_support
            or support_ratio >= 0.60
        ):
            if non_critical_missing_count <= 3 and risk_status not in {"HIGH_RISK", "EXTREME_RISK"}:
                return {
                    "panel_decision_version": "V17_PANEL_DECISION_1",
                    "panel_label": "UNDER CANDIDATO FUERTE",
                    "panel_market": "UNDER",
                    "panel_decision": "MOSTRAR_CANDIDATO",
                    "panel_signal_type": "UNDER_STRONG_CANDIDATE",
                    "panel_priority": 86,
                    "panel_confidence_label": "ALTA",
                    "panel_entry_permission": "ESPERAR_CONFIRMACION",
                    "panel_badge": "UNDER",
                    "panel_color_hint": "cyan",
                    "panel_reason": (
                        f"UNDER cumple mayoría de requisitos con soporte {support_score}, "
                        "pero todavía requiere confirmación final."
                    ),
                    "panel_warning": self._soft_warning_text(signal),
                    "panel_show_as_signal": False,
                    "panel_show_as_candidate": True,
                    "panel_show_as_observation": True,
                }

        return self._under_candidate(signal)

    def _panel_for_alternative_over(
        self,
        signal: Dict[str, Any],
        over_candidate_level: str,
        over_support_ratio: float,
        over_support_score: int,
        over_blockers: List[Any],
        risk_status: str,
        risk_score: float,
        real_offensive_volume: bool,
    ) -> Dict[str, Any]:
        if over_blockers:
            return self._normal_observation(signal)

        if over_candidate_level == "OVER_STRONG_CANDIDATE":
            return {
                "panel_decision_version": "V17_PANEL_DECISION_1",
                "panel_label": "OVER CANDIDATO FUERTE",
                "panel_market": "OVER",
                "panel_decision": "MOSTRAR_CANDIDATO",
                "panel_signal_type": "OVER_STRONG_CANDIDATE",
                "panel_priority": 89,
                "panel_confidence_label": "ALTA",
                "panel_entry_permission": "ESPERAR_CONFIRMACION",
                "panel_badge": "OVER",
                "panel_color_hint": "yellow",
                "panel_reason": signal.get("why_over_candidate")
                or f"OVER cumple mayoría ofensiva con soporte {over_support_score}.",
                "panel_warning": signal.get("why_over_not_ready"),
                "panel_show_as_signal": False,
                "panel_show_as_candidate": True,
                "panel_show_as_observation": True,
            }

        if over_candidate_level == "OVER_HIGH_OBSERVATION":
            return {
                "panel_decision_version": "V17_PANEL_DECISION_1",
                "panel_label": "OVER EN CRECIMIENTO",
                "panel_market": "OVER",
                "panel_decision": "MOSTRAR_OBSERVACION_ALTA",
                "panel_signal_type": "OVER_HIGH_OBSERVATION",
                "panel_priority": 82,
                "panel_confidence_label": "MEDIA ALTA",
                "panel_entry_permission": "ESPERAR_CONFIRMACION",
                "panel_badge": "OVER WATCH",
                "panel_color_hint": "orange",
                "panel_reason": signal.get("why_over_candidate")
                or "OVER tiene volumen ofensivo visible y debe mostrarse en el panel.",
                "panel_warning": signal.get("why_over_not_ready"),
                "panel_show_as_signal": False,
                "panel_show_as_candidate": True,
                "panel_show_as_observation": True,
            }

        if over_support_ratio >= 0.58 and real_offensive_volume:
            return self._over_candidate(signal)

        return self._normal_observation(signal)

    def _over_candidate(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "panel_decision_version": "V17_PANEL_DECISION_1",
            "panel_label": "OVER EN OBSERVACIÓN",
            "panel_market": "OVER",
            "panel_decision": "MOSTRAR_OBSERVACION",
            "panel_signal_type": "OVER_NORMAL_OBSERVATION",
            "panel_priority": 68,
            "panel_confidence_label": "MEDIA",
            "panel_entry_permission": "NO_OPERAR_AUN",
            "panel_badge": "OVER",
            "panel_color_hint": "orange",
            "panel_reason": signal.get("why_over_candidate")
            or "OVER tiene señales parciales, pero todavía no alcanza confirmación suficiente.",
            "panel_warning": signal.get("why_over_not_ready"),
            "panel_show_as_signal": False,
            "panel_show_as_candidate": False,
            "panel_show_as_observation": True,
        }

    def _under_candidate(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "panel_decision_version": "V17_PANEL_DECISION_1",
            "panel_label": "UNDER EN CONSERVACIÓN",
            "panel_market": "UNDER",
            "panel_decision": "MOSTRAR_OBSERVACION_ALTA",
            "panel_signal_type": "UNDER_HIGH_OBSERVATION",
            "panel_priority": 76,
            "panel_confidence_label": "MEDIA ALTA",
            "panel_entry_permission": "ESPERAR_CONFIRMACION",
            "panel_badge": "UNDER",
            "panel_color_hint": "cyan",
            "panel_reason": signal.get("recommended_panel_message")
            or signal.get("why_selected")
            or "UNDER tiene lectura de conservación, pero todavía requiere confirmación.",
            "panel_warning": self._soft_warning_text(signal),
            "panel_show_as_signal": False,
            "panel_show_as_candidate": True,
            "panel_show_as_observation": True,
        }

    def _high_observation(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        inferred_market = self._infer_candidate_market(signal)

        return {
            "panel_decision_version": "V17_PANEL_DECISION_1",
            "panel_label": "OBSERVACIÓN ALTA",
            "panel_market": inferred_market,
            "panel_decision": "MOSTRAR_OBSERVACION_ALTA",
            "panel_signal_type": "HIGH_OBSERVATION",
            "panel_priority": 70,
            "panel_confidence_label": "MEDIA ALTA",
            "panel_entry_permission": "ESPERAR_CONFIRMACION",
            "panel_badge": inferred_market if inferred_market != "OTHER" else "WATCH",
            "panel_color_hint": "yellow",
            "panel_reason": signal.get("recommended_panel_message")
            or "La lectura cumple varios requisitos, pero todavía no alcanza señal final.",
            "panel_warning": self._soft_warning_text(signal),
            "panel_show_as_signal": False,
            "panel_show_as_candidate": True,
            "panel_show_as_observation": True,
        }

    def _normal_observation(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        inferred_market = self._infer_candidate_market(signal)

        return {
            "panel_decision_version": "V17_PANEL_DECISION_1",
            "panel_label": "OBSERVACIÓN",
            "panel_market": inferred_market,
            "panel_decision": "MOSTRAR_OBSERVACION",
            "panel_signal_type": "NORMAL_OBSERVATION",
            "panel_priority": 50,
            "panel_confidence_label": "MEDIA",
            "panel_entry_permission": "NO_OPERAR_AUN",
            "panel_badge": inferred_market if inferred_market != "OTHER" else "WATCH",
            "panel_color_hint": "gray",
            "panel_reason": signal.get("recommended_panel_message")
            or signal.get("main_reading")
            or "El partido tiene señales parciales, pero requiere más confirmación.",
            "panel_warning": self._soft_warning_text(signal),
            "panel_show_as_signal": False,
            "panel_show_as_candidate": False,
            "panel_show_as_observation": True,
        }

    def _no_bet(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "panel_decision_version": "V17_PANEL_DECISION_1",
            "panel_label": "NO BET",
            "panel_market": "OTHER",
            "panel_decision": "NO_MOSTRAR_COMO_SEÑAL",
            "panel_signal_type": "NO_BET",
            "panel_priority": 10,
            "panel_confidence_label": "BAJA",
            "panel_entry_permission": "NO_OPERAR",
            "panel_badge": "NO BET",
            "panel_color_hint": "gray",
            "panel_reason": "No existe mayoría suficiente para mostrar señal.",
            "panel_warning": self._soft_warning_text(signal),
            "panel_show_as_signal": False,
            "panel_show_as_candidate": False,
            "panel_show_as_observation": False,
        }

    def _blocked(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        hard_blockers = signal.get("hard_blockers", []) or []
        logic_warnings = signal.get("logic_warnings", []) or []

        reason_items = hard_blockers[:3] or logic_warnings[:3]

        return {
            "panel_decision_version": "V17_PANEL_DECISION_1",
            "panel_label": "BLOQUEADO",
            "panel_market": "OTHER",
            "panel_decision": "BLOQUEAR_VISUALMENTE",
            "panel_signal_type": "TECHNICAL_BLOCK",
            "panel_priority": 0,
            "panel_confidence_label": "BLOQUEADO",
            "panel_entry_permission": "NO_OPERAR",
            "panel_badge": "BLOCK",
            "panel_color_hint": "red",
            "panel_reason": "Bloqueo crítico activo: " + ", ".join(map(str, reason_items)),
            "panel_warning": self._soft_warning_text(signal),
            "panel_show_as_signal": False,
            "panel_show_as_candidate": False,
            "panel_show_as_observation": False,
        }

    def _empty(self) -> Dict[str, Any]:
        return {
            "panel_decision_version": "V17_PANEL_DECISION_1",
            "panel_label": "NO DATA",
            "panel_market": "OTHER",
            "panel_decision": "NO_DATA",
            "panel_signal_type": "NO_DATA",
            "panel_priority": 0,
            "panel_confidence_label": "BAJA",
            "panel_entry_permission": "NO_OPERAR",
            "panel_badge": "NO DATA",
            "panel_color_hint": "gray",
            "panel_reason": "No hay datos válidos para evaluar.",
            "panel_warning": "",
            "panel_show_as_signal": False,
            "panel_show_as_candidate": False,
            "panel_show_as_observation": False,
        }

    def _has_critical_block(
        self,
        critical_block: bool,
        should_block: bool,
        hard_blockers: List[Any],
        risk_status: str,
        clock_status: str,
    ) -> bool:
        if critical_block or should_block:
            return True

        if hard_blockers:
            return True

        if risk_status == "EXTREME_RISK":
            return True

        if clock_status in {"BLOCKED_CLOCK", "CLOCK_FROZEN"}:
            return True

        return False

    def _has_real_offensive_volume(self, signal: Dict[str, Any]) -> bool:
        shots = safe_float(signal.get("shots"), 0.0)
        shots_on_target = safe_float(signal.get("shots_on_target"), 0.0)
        corners = safe_float(signal.get("corners"), 0.0)
        xg = safe_float(signal.get("xg") or signal.get("xG"), 0.0)
        dangerous_attacks = safe_float(signal.get("dangerous_attacks"), 0.0)

        over_volume_profile = signal.get("over_volume_profile")
        if isinstance(over_volume_profile, dict):
            if over_volume_profile.get("strong_volume") or over_volume_profile.get("medium_volume"):
                return True

        return (
            shots >= 10
            or shots_on_target >= 3
            or corners >= 5
            or xg >= 0.85
            or dangerous_attacks >= 15
        )

    def _has_low_stats_warning(self, signal: Dict[str, Any]) -> bool:
        warnings = []
        warnings.extend(signal.get("risk_warnings", []) or [])
        warnings.extend(signal.get("soft_warnings", []) or [])
        warnings.extend(signal.get("logic_warnings", []) or [])

        data_quality = str(signal.get("data_quality") or "").upper()
        scan_phase = str(signal.get("scan_phase") or "").upper()

        warning_text = " ".join(str(x).upper() for x in warnings)

        return (
            "LOW_STATS_DATA" in warning_text
            or "NO_SHOTS_DATA" in warning_text
            or "NO_DANGEROUS_ATTACKS_DATA" in warning_text
            or data_quality == "LOW"
            or scan_phase == "WAITING_LIVE_STATS"
        )

    def _infer_candidate_market(self, signal: Dict[str, Any]) -> str:
        market = normalize_market(
            signal.get("market_direction")
            or signal.get("master_market")
            or signal.get("market")
            or signal.get("suggested_market")
            or signal.get("market_category")
        )

        if market in {"OVER", "UNDER"}:
            return market

        over_candidate_level = str(signal.get("over_candidate_level") or "").upper()
        if over_candidate_level in {"OVER_STRONG_CANDIDATE", "OVER_HIGH_OBSERVATION"}:
            return "OVER"

        over_score = safe_float(signal.get("over_score"), 0.0)
        under_score = safe_float(signal.get("under_score"), 0.0)

        if over_score >= under_score + 5:
            return "OVER"

        if under_score >= over_score + 5:
            return "UNDER"

        return "OTHER"

    def _confidence_label(self, elite_score: float, master_confidence: float) -> str:
        score = max(elite_score, master_confidence)

        if score >= 88:
            return "PREMIUM"

        if score >= 80:
            return "FUERTE"

        if score >= 70:
            return "BUENA"

        if score >= 60:
            return "MEDIA ALTA"

        return "MEDIA"

    def _soft_warning_text(self, signal: Dict[str, Any]) -> str:
        warnings = []
        warnings.extend(signal.get("logic_warnings", []) or [])
        warnings.extend(signal.get("soft_warnings", []) or [])
        warnings.extend(signal.get("risk_warnings", []) or [])

        if warnings:
            return ", ".join(map(str, warnings[:3]))

        if signal.get("what_is_missing"):
            return str(signal.get("what_is_missing"))

        return ""
