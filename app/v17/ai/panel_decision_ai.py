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

    Regla clave:
    - La lectura dominante manda sobre la alternativa.
    - Si UNDER domina claramente, OVER WATCH no puede ser título principal.
    - Si OVER domina claramente, UNDER queda como riesgo o alternativa.
    - OVER HIGH OBSERVATION solo sube como principal cuando no hay un UNDER dominante fuerte.
    """

    def evaluate(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(signal, dict):
            return self._empty()


        official_market = normalize_market(
            signal.get("official_market")
        )
        official_status = str(
            signal.get("official_status")
            or signal.get("master_status")
            or ""
        ).upper()

        official_confidence_raw = signal.get("official_confidence")
        official_confidence = safe_float(
            official_confidence_raw
            if official_confidence_raw is not None
            else signal.get("master_confidence"),
            0.0,
        )

        if "official_can_publish" in signal:
            official_can_publish = bool(
                signal.get("official_can_publish")
            )
        else:
            official_can_publish = bool(signal.get("can_publish"))

        official_market = normalize_market(signal.get("official_market"))
        market = (
            official_market
            if official_market in {"OVER", "UNDER"}
            else normalize_market(
                signal.get("market_direction")
                or signal.get("master_market")
                or signal.get("market")
                or signal.get("suggested_market")
                or signal.get("market_category")
            )
        )

        football_dominant = normalize_market(signal.get("football_dominant_reading"))

        over_score = safe_float(signal.get("over_score"), 0.0)
        under_score = safe_float(signal.get("under_score"), 0.0)
        market_gap = over_score - under_score

        master_status = official_status
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

        can_publish = official_can_publish
        should_observe = bool(signal.get("should_observe"))
        should_block = bool(signal.get("should_block"))

        risk_score = safe_float(signal.get("risk_score"), 0.0)
        elite_score = safe_float(signal.get("elite_score"), 0.0)
        master_confidence = official_confidence

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

        # Si MasterDecisionAI no autoriza publicación, el panel no debe
        # promocionar lecturas auxiliares como decisión principal.
        if not can_publish and official_status in {
            "OBSERVE",
            "WAIT_CONFIRMATION",
            "NO_BET",
            "BLOCKED",
            "NO_REENTRY",
        }:
            if official_status in {"BLOCKED", "NO_REENTRY"}:
                return self._blocked(signal)
            if official_status == "NO_BET":
                return self._no_bet(signal)
            return self._normal_observation(signal)

        dominant_under = self._is_dominant_under(
            signal=signal,
            market=market,
            football_dominant=football_dominant,
            under_score=under_score,
            over_score=over_score,
            candidate_level=candidate_level,
            majority_support=majority_support,
        )

        dominant_over = self._is_dominant_over(
            signal=signal,
            market=market,
            football_dominant=football_dominant,
            under_score=under_score,
            over_score=over_score,
            real_offensive_volume=real_offensive_volume,
            majority_support=majority_support,
        )

        if dominant_under:
            payload = self._panel_for_main_under(
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
            return self._apply_conflict_downgrade(payload, signal)

        if dominant_over:
            payload = self._panel_for_main_over(
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
            return self._apply_conflict_downgrade(payload, signal)

        if market == "UNDER":
            payload = self._panel_for_main_under(
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
            return self._apply_conflict_downgrade(payload, signal)

        if market == "OVER":
            payload = self._panel_for_main_over(
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
            return self._apply_conflict_downgrade(payload, signal)

        if over_candidate_active or over_candidate_level in {
            "OVER_STRONG_CANDIDATE",
            "OVER_HIGH_OBSERVATION",
        }:
            payload = self._panel_for_alternative_over(
                signal=signal,
                over_candidate_level=over_candidate_level,
                over_support_ratio=over_support_ratio,
                over_support_score=over_support_score,
                over_blockers=over_blockers,
                risk_status=risk_status,
                risk_score=risk_score,
                real_offensive_volume=real_offensive_volume,
                under_score=under_score,
                over_score=over_score,
            )
            return self._apply_conflict_downgrade(payload, signal)

        if candidate_level in {"STRONG_CANDIDATE", "HIGH_OBSERVATION"}:
            inferred_market = self._infer_candidate_market(signal)

            if inferred_market == "UNDER":
                return self._apply_conflict_downgrade(self._under_candidate(signal), signal)

            if inferred_market == "OVER":
                return self._apply_conflict_downgrade(self._over_candidate(signal), signal)

            return self._apply_conflict_downgrade(self._high_observation(signal), signal)

        if should_observe or master_status in {"OBSERVE", "WAIT_CONFIRMATION"}:
            return self._normal_observation(signal)

        return self._no_bet(signal)

    def _is_dominant_under(
        self,
        signal: Dict[str, Any],
        market: str,
        football_dominant: str,
        under_score: float,
        over_score: float,
        candidate_level: str,
        majority_support: bool,
    ) -> bool:
        context_category = str(signal.get("context_category") or "").upper()
        market_category = str(signal.get("market_category") or "").upper()
        why_selected = str(signal.get("why_selected") or "").upper()
        recommended_panel_message = str(signal.get("recommended_panel_message") or "").upper()

        if football_dominant == "UNDER":
            return True

        if market == "UNDER" and under_score >= over_score + 8:
            return True

        if under_score >= over_score + 15:
            return True

        if "UNDER" in context_category and under_score >= over_score + 8:
            return True

        if "UNDER" in market_category and under_score >= over_score + 8:
            return True

        if candidate_level == "STRONG_CANDIDATE" and majority_support:
            if "UNDER" in why_selected or "UNDER" in recommended_panel_message:
                return True

        return False

    def _is_dominant_over(
        self,
        signal: Dict[str, Any],
        market: str,
        football_dominant: str,
        under_score: float,
        over_score: float,
        real_offensive_volume: bool,
        majority_support: bool,
    ) -> bool:
        over_candidate_level = str(signal.get("over_candidate_level") or "").upper()

        if football_dominant == "OVER" and over_score >= under_score - 5:
            return True

        if market == "OVER" and over_score >= under_score + 5 and real_offensive_volume:
            return True

        if over_score >= under_score + 10 and real_offensive_volume:
            return True

        if (
            over_candidate_level == "OVER_STRONG_CANDIDATE"
            and real_offensive_volume
            and over_score >= under_score - 5
            and majority_support
        ):
            return True

        return False

    def _alternative_over_payload(
        self,
        signal: Dict[str, Any],
    ) -> Dict[str, Any]:
        over_candidate_level = str(signal.get("over_candidate_level") or "").upper()
        over_candidate_active = bool(signal.get("over_candidate_active"))
        over_support_ratio = safe_float(signal.get("over_support_ratio"), 0.0)
        over_support_score = safe_int(signal.get("over_support_score"), 0)

        if over_candidate_level == "OVER_STRONG_CANDIDATE":
            return {
                "alternative_market": "OVER",
                "alternative_label": "OVER CANDIDATO FUERTE",
                "alternative_reason": signal.get("why_over_candidate")
                or f"OVER tiene soporte ofensivo alternativo con puntaje {over_support_score}.",
                "alternative_priority": 78,
                "alternative_badge": "OVER WATCH",
            }

        if over_candidate_level == "OVER_HIGH_OBSERVATION" or over_candidate_active or over_support_ratio >= 0.55:
            return {
                "alternative_market": "OVER",
                "alternative_label": "OVER WATCH",
                "alternative_reason": signal.get("why_over_candidate")
                or "OVER queda visible como alternativa, pero no domina la lectura principal.",
                "alternative_priority": 65,
                "alternative_badge": "OVER WATCH",
            }

        return {
            "alternative_market": "NONE",
            "alternative_label": "SIN ALTERNATIVA FUERTE",
            "alternative_reason": "",
            "alternative_priority": 0,
            "alternative_badge": "",
        }

    def _alternative_under_payload(
        self,
        signal: Dict[str, Any],
    ) -> Dict[str, Any]:
        under_score = safe_float(signal.get("under_score"), 0.0)
        over_score = safe_float(signal.get("over_score"), 0.0)

        if under_score >= over_score + 8:
            return {
                "alternative_market": "UNDER",
                "alternative_label": "UNDER RIESGO",
                "alternative_reason": "UNDER sigue teniendo lectura de conservación como riesgo alternativo.",
                "alternative_priority": 60,
                "alternative_badge": "UNDER WATCH",
            }

        return {
            "alternative_market": "NONE",
            "alternative_label": "SIN ALTERNATIVA FUERTE",
            "alternative_reason": "",
            "alternative_priority": 0,
            "alternative_badge": "",
        }

    def _with_alternative_over(self, payload: Dict[str, Any], signal: Dict[str, Any]) -> Dict[str, Any]:
        return {
            **payload,
            **self._alternative_over_payload(signal),
        }

    def _with_alternative_under(self, payload: Dict[str, Any], signal: Dict[str, Any]) -> Dict[str, Any]:
        return {
            **payload,
            **self._alternative_under_payload(signal),
        }

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
            return self._with_alternative_under(
                {
                    "panel_decision_version": "V17_PANEL_DECISION_3_CONFLICT_AWARE",
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
                },
                signal,
            )

        if majority_support and support_ratio >= 0.62 and real_offensive_volume:
            return self._with_alternative_under(
                {
                    "panel_decision_version": "V17_PANEL_DECISION_3_CONFLICT_AWARE",
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
                },
                signal,
            )

        return self._with_alternative_under(self._over_candidate(signal), signal)

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
            return self._with_alternative_over(
                {
                    "panel_decision_version": "V17_PANEL_DECISION_3_CONFLICT_AWARE",
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
                },
                signal,
            )

        if (
            candidate_level == "STRONG_CANDIDATE"
            or majority_support
            or support_ratio >= 0.60
        ):
            if non_critical_missing_count <= 3 and risk_status not in {"HIGH_RISK", "EXTREME_RISK"}:
                return self._with_alternative_over(
                    {
                        "panel_decision_version": "V17_PANEL_DECISION_3_CONFLICT_AWARE",
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
                    },
                    signal,
                )

        return self._with_alternative_over(self._under_candidate(signal), signal)

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
        under_score: float,
        over_score: float,
    ) -> Dict[str, Any]:
        if over_blockers:
            return self._normal_observation(signal)

        if under_score >= over_score + 12:
            return self._with_alternative_over(self._under_candidate(signal), signal)

        if over_candidate_level == "OVER_STRONG_CANDIDATE":
            return {
                "panel_decision_version": "V17_PANEL_DECISION_3_CONFLICT_AWARE",
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
                **self._alternative_under_payload(signal),
            }

        if over_candidate_level == "OVER_HIGH_OBSERVATION":
            return {
                "panel_decision_version": "V17_PANEL_DECISION_3_CONFLICT_AWARE",
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
                **self._alternative_under_payload(signal),
            }

        if over_support_ratio >= 0.58 and real_offensive_volume:
            return self._with_alternative_under(self._over_candidate(signal), signal)

        return self._normal_observation(signal)

    def _over_candidate(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "panel_decision_version": "V17_PANEL_DECISION_3_CONFLICT_AWARE",
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
            "panel_decision_version": "V17_PANEL_DECISION_3_CONFLICT_AWARE",
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
            "panel_decision_version": "V17_PANEL_DECISION_3_CONFLICT_AWARE",
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
            "panel_decision_version": "V17_PANEL_DECISION_3_CONFLICT_AWARE",
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
            "panel_decision_version": "V17_PANEL_DECISION_3_CONFLICT_AWARE",
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
            "panel_decision_version": "V17_PANEL_DECISION_3_CONFLICT_AWARE",
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
            "alternative_market": "NONE",
            "alternative_label": "SIN ALTERNATIVA",
            "alternative_reason": "",
            "alternative_priority": 0,
            "alternative_badge": "",
        }

    def _empty(self) -> Dict[str, Any]:
        return {
            "panel_decision_version": "V17_PANEL_DECISION_3_CONFLICT_AWARE",
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
            "alternative_market": "NONE",
            "alternative_label": "SIN ALTERNATIVA",
            "alternative_reason": "",
            "alternative_priority": 0,
            "alternative_badge": "",
        }


    def _apply_conflict_downgrade(self, payload: Dict[str, Any], signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ajuste visual V17 Elite.

        El panel no debe mostrar una tarjeta como SEÑAL o CANDIDATO FUERTE
        cuando el propio sistema avisa conflicto predictivo, reloj en alerta,
        espera de confirmación o revalidación pendiente.

        No bloquea la señal ni cambia el mercado; solo traduce mejor el estado
        visual para evitar contradicciones como:
        "UNDER CANDIDATO FUERTE 100%" + "OBSERVAR POR CONFLICTO".
        """
        if not isinstance(payload, dict):
            return payload

        if payload.get("panel_signal_type") in {"TECHNICAL_BLOCK", "NO_BET", "NO_DATA"}:
            return payload

        conflict = self._panel_conflict_profile(signal)
        if not conflict.get("active"):
            return payload

        is_signal = bool(payload.get("panel_show_as_signal"))
        is_candidate = bool(payload.get("panel_show_as_candidate"))
        signal_type = str(payload.get("panel_signal_type") or "").upper()
        label = str(payload.get("panel_label") or "").upper()

        should_downgrade = (
            is_signal
            or is_candidate
            or "CANDIDATO FUERTE" in label
            or "STRONG" in signal_type
            or "TOP_" in signal_type
        )

        if not should_downgrade:
            return {
                **payload,
                "panel_conflict_active": True,
                "panel_conflict_level": conflict.get("level"),
                "panel_conflict_reason": conflict.get("reason"),
            }

        market = normalize_market(payload.get("panel_market") or self._infer_candidate_market(signal))
        if market not in {"OVER", "UNDER"}:
            market = self._infer_candidate_market(signal)

        level = conflict.get("level") or "SOFT_CONFLICT"
        if level == "CLOCK_ALERT":
            new_label = f"{market} EN ALERTA DE RELOJ" if market in {"OVER", "UNDER"} else "RELOJ EN ALERTA"
            permission = "ESPERAR_REVALIDACION"
            priority_cap = 64
            confidence_label = "MEDIA"
        elif level == "PREDICTIVE_CONFLICT":
            new_label = f"{market} EN OBSERVACIÓN POR CONFLICTO" if market in {"OVER", "UNDER"} else "OBSERVACIÓN POR CONFLICTO"
            permission = "ESPERAR_CONFIRMACION"
            priority_cap = 66
            confidence_label = "MEDIA"
        elif level == "MURITY_OR_REVALIDATION":
            new_label = f"{market} EN REVALIDACIÓN" if market in {"OVER", "UNDER"} else "EN REVALIDACIÓN"
            permission = "ESPERAR_REVALIDACION"
            priority_cap = 68
            confidence_label = "MEDIA ALTA"
        else:
            new_label = f"{market} EN OBSERVACIÓN CONTROLADA" if market in {"OVER", "UNDER"} else "OBSERVACIÓN CONTROLADA"
            permission = "ESPERAR_CONFIRMACION"
            priority_cap = 70
            confidence_label = "MEDIA ALTA"

        return {
            **payload,
            "panel_label": new_label,
            "panel_decision": "MOSTRAR_OBSERVACION_CONTROLADA",
            "panel_signal_type": f"{market}_CONTROLLED_OBSERVATION" if market in {"OVER", "UNDER"} else "CONTROLLED_OBSERVATION",
            "panel_priority": min(safe_int(payload.get("panel_priority"), 50), priority_cap),
            "panel_confidence_label": confidence_label,
            "panel_entry_permission": permission,
            "panel_color_hint": "orange" if level in {"CLOCK_ALERT", "PREDICTIVE_CONFLICT"} else "yellow",
            "panel_reason": conflict.get("reason") or payload.get("panel_reason"),
            "panel_warning": conflict.get("warning") or payload.get("panel_warning"),
            "panel_show_as_signal": False,
            "panel_show_as_candidate": True,
            "panel_show_as_observation": True,
            "panel_conflict_active": True,
            "panel_conflict_level": level,
            "panel_conflict_reason": conflict.get("reason"),
            "panel_confidence_cap": priority_cap,
        }

    def _panel_conflict_profile(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        warnings: List[Any] = []
        warnings.extend(signal.get("logic_warnings", []) or [])
        warnings.extend(signal.get("soft_warnings", []) or [])
        warnings.extend(signal.get("risk_warnings", []) or [])
        warnings.extend(signal.get("hard_blockers", []) or [])

        fields = [
            signal.get("master_status"),
            signal.get("master_action"),
            signal.get("master_reason"),
            signal.get("recommended_panel_message"),
            signal.get("what_is_missing"),
            signal.get("logic_status"),
            signal.get("clock_status"),
            signal.get("clock_action"),
            signal.get("entry_timing_status"),
            signal.get("entry_timing_action"),
            signal.get("prediction_market_alignment"),
            signal.get("prediction_conflict"),
            signal.get("conflict_level"),
            signal.get("risk_status"),
        ]

        text = " ".join(str(x or "") for x in fields + warnings).upper()

        clock_terms = {
            "RELOJ EN ALERTA",
            "CLOCK_WARNING",
            "CLOCK_STALE",
            "STALE",
            "CLOCK_GUARD_NO_ENTER",
            "WAIT_CLOCK",
            "ESPERAR_RELOJ",
            "DATA_TOO_OLD",
            "MINUTE_LAG",
            "REVALIDAR RELOJ",
        }
        predictive_terms = {
            "OBSERVAR POR CONFLICTO",
            "PREDICTIVE_CONFLICT",
            "SCENARIO_CONFLICT",
            "CONFLICT",
            "CONFLICTO",
            "CONTRADICT",
            "NO TOMAR COMO SEÑAL PRINCIPAL",
            "RISK_NOT_ALIGNED",
        }
        maturity_terms = {
            "WAIT_CONFIRMATION",
            "ESPERAR_CONFIRMACION",
            "ESPERAR CONFIRMACION",
            "REVALIDATION",
            "REVALIDACIÓN",
            "MATCH_MATURITY_GUARD",
            "MaturityAI".upper(),
            "NO_REENTRY",
        }

        if any(term in text for term in clock_terms):
            return {
                "active": True,
                "level": "CLOCK_ALERT",
                "reason": "La lectura existe, pero el reloj o la sincronía requieren revalidación antes de operar.",
                "warning": self._soft_warning_text(signal) or "Reloj en alerta: esperar confirmación.",
            }

        if any(term in text for term in predictive_terms):
            return {
                "active": True,
                "level": "PREDICTIVE_CONFLICT",
                "reason": "La lectura tiene soporte, pero existe conflicto entre predicción, mercado, riesgo o escenario probable.",
                "warning": self._soft_warning_text(signal) or "Conflicto predictivo activo: no tomar como señal principal.",
            }

        if any(term in text for term in maturity_terms):
            return {
                "active": True,
                "level": "MURITY_OR_REVALIDATION",
                "reason": "La oportunidad está en fase de maduración o revalidación; debe esperar confirmación final.",
                "warning": self._soft_warning_text(signal) or "Requiere confirmación final.",
            }

        # Conflicto suave por baja calidad de datos: visible, pero no bloqueo.
        if self._has_low_stats_warning(signal):
            return {
                "active": True,
                "level": "LOW_DATA_CAUTION",
                "reason": "La lectura es utilizable, pero la cobertura estadística es parcial; se muestra con cautela.",
                "warning": self._soft_warning_text(signal) or "Datos live parciales.",
            }

        return {"active": False}

    def _has_critical_block(
        self,
        critical_block: bool,
        should_block: bool,
        hard_blockers: List[Any],
        risk_status: str,
        clock_status: str,
    ) -> bool:
        """
        Determina si el panel debe mostrar bloqueo crítico.

        Ajuste V17 Elite:
        - No todo hard_blocker debe matar la señal visualmente.
        - CLOCK_GUARD_NO_ENTER, HALFTIME_WAIT y advertencias de reloj deben quedar
          como espera/observación cuando la lectura tiene mayoría suficiente.
        - Solo se bloquea visualmente ante fallas técnicas realmente críticas.
        """

        hard_text = " ".join(str(x or "").upper() for x in hard_blockers or [])

        real_critical_blockers = {
            "INVALID_MINUTE",
            "DATA_TOO_OLD",
            "CLOCK_FROZEN",
            "BLOCKED_CLOCK",
            "MATCH_ENDED",
            "MATCH_FINISHED",
            "CORRUPTED_DATA",
            "CRITICAL_CONTRADICTION",
            "EXTREME_RISK",
            "RED_CARD_CRITICAL",
        }

        soft_clock_blockers = {
            "CLOCK_GUARD_NO_ENTER",
            "EL RELOJ NO AUTORIZA ENTRADA",
            "CLOCK_WARNING",
            "HALFTIME_WAIT",
            "POSSIBLE_HALFTIME_PAUSE",
            "DATA_TIMESTAMP_MISSING",
            "DATA_TIMESTAMP_MISSING_BUT_STATS_CONFIRMED",
            "CLOCK_STALE_WARNING",
            "CLOCK_CONFIRMED_BY_STATS",
        }

        if risk_status == "EXTREME_RISK":
            return True

        if clock_status in {"BLOCKED_CLOCK", "CLOCK_FROZEN"}:
            return True

        for blocker in real_critical_blockers:
            if blocker in hard_text:
                return True

        if critical_block:
            return True

        if should_block:
            # Si el único bloqueo proviene de reloj/espera técnica no crítica,
            # no convertirlo en bloqueo visual. El resto del sistema puede mantener
            # la señal en observación o revalidación.
            if hard_text:
                has_real_critical = any(
                    blocker in hard_text for blocker in real_critical_blockers
                )
                has_only_soft_clock = any(
                    blocker in hard_text for blocker in soft_clock_blockers
                ) and not has_real_critical

                if has_only_soft_clock:
                    return False

            return True

        if hard_text:
            has_real_critical = any(
                blocker in hard_text for blocker in real_critical_blockers
            )
            if has_real_critical:
                return True

            # Hard blockers suaves de reloj no deben borrar candidatos coherentes.
            if any(blocker in hard_text for blocker in soft_clock_blockers):
                return False

            # Si llega un hard blocker desconocido, se mantiene prudencia.
            return True

        return False

    def _has_real_offensive_volume(self, signal: Dict[str, Any]) -> bool:
        shots = safe_float(signal.get("shots"), 0.0)
        shots_on_target = safe_float(signal.get("shots_on_target"), 0.0)
        shots_inside_box = safe_float(signal.get("shots_inside_box"), 0.0)
        blocked_shots = safe_float(signal.get("blocked_shots"), 0.0)
        goalkeeper_saves = safe_float(signal.get("goalkeeper_saves"), 0.0)
        corners = safe_float(signal.get("corners"), 0.0)
        xg = safe_float(signal.get("xg") or signal.get("xG"), 0.0)
        dangerous_attacks = safe_float(signal.get("dangerous_attacks"), 0.0)
        goal_evidence_score = safe_float(signal.get("goal_evidence_score"), 0.0)
        attack_quality_score = safe_float(signal.get("attack_quality_score"), 0.0)
        box_pressure_score = safe_float(signal.get("box_pressure_score"), 0.0)

        over_volume_profile = signal.get("over_volume_profile")
        if isinstance(over_volume_profile, dict):
            if over_volume_profile.get("strong_volume") or over_volume_profile.get("medium_volume"):
                return True

        return (
            shots >= 10
            or shots_on_target >= 3
            or shots_inside_box >= 3
            or blocked_shots >= 4
            or goalkeeper_saves >= 3
            or corners >= 5
            or xg >= 0.85
            or dangerous_attacks >= 15
            or goal_evidence_score >= 45
            or attack_quality_score >= 55
            or box_pressure_score >= 45
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
        # Si MasterDecisionAI decidió no tomar mercado operativo, no caer
        # a lecturas auxiliares de promoción/activación/predicción.
        official_market_raw = str(signal.get("official_market") or "").upper()

        if official_market_raw in {
            "OBSERVE",
            "WAIT_CONFIRMATION",
            "NO_BET",
            "BLOCKED",
            "NO_REENTRY",
        }:
            return "OTHER"

        football_dominant = normalize_market(signal.get("football_dominant_reading"))

        if football_dominant in {"OVER", "UNDER"}:
            return football_dominant

        official_market = normalize_market(signal.get("official_market"))
        market = (
            official_market
            if official_market in {"OVER", "UNDER"}
            else normalize_market(
                signal.get("market_direction")
                or signal.get("master_market")
                or signal.get("market")
                or signal.get("suggested_market")
                or signal.get("market_category")
            )
        )

        if market in {"OVER", "UNDER"}:
            return market

        over_score = safe_float(signal.get("over_score"), 0.0)
        under_score = safe_float(signal.get("under_score"), 0.0)

        if under_score >= over_score + 5:
            return "UNDER"

        if over_score >= under_score + 5:
            return "OVER"

        over_candidate_level = str(signal.get("over_candidate_level") or "").upper()
        if over_candidate_level in {"OVER_STRONG_CANDIDATE", "OVER_HIGH_OBSERVATION"}:
            return "OVER"

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
