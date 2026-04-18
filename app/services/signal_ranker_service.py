from typing import Any, Dict, List


class SignalRankerService:
    """
    Rankea candidatas y oportunidades para decidir cuáles son
    las mejores señales del momento.

    Filosofía:
    - no depender de un solo filtro
    - combinar score + probabilidad + contexto + gate + riesgo
    - priorizar calidad y claridad
    """

    MAX_ACTIVE_SIGNALS = 6

    @staticmethod
    def build_top_signals(
        candidates: List[Dict[str, Any]],
        opportunities_payload: Dict[str, Any] | None = None,
    ) -> List[Dict[str, Any]]:
        ranked: List[Dict[str, Any]] = []

        # =========================
        # 1. CANDIDATAS DIRECTAS DEL SCAN
        # =========================
        for item in candidates or []:
            if not isinstance(item, dict):
                continue

            match = item.get("match", {}) or {}
            motores = item.get("motores", {}) or {}

            if not isinstance(match, dict):
                continue

            ranked_row = SignalRankerService._rank_candidate(match, motores)
            if ranked_row:
                ranked.append(ranked_row)

        # =========================
        # 2. OPORTUNIDADES SECUNDARIAS
        # =========================
        if isinstance(opportunities_payload, dict):
            sections = opportunities_payload.get("sections", {}) or {}

            for row in sections.get("over_candidates", []) or []:
                built = SignalRankerService._rank_opportunity(row, forced_market="OVER_MATCH_DYNAMIC")
                if built:
                    ranked.append(built)

            for row in sections.get("under_candidates", []) or []:
                built = SignalRankerService._rank_opportunity(row, forced_market="UNDER_MATCH_DYNAMIC")
                if built:
                    ranked.append(built)

        # =========================
        # 3. DEDUP POR PARTIDO + MERCADO
        # =========================
        ranked = SignalRankerService._deduplicate(ranked)

        # =========================
        # 4. ORDEN FINAL
        # =========================
        ranked.sort(
            key=lambda x: (
                float(x.get("publication_score", 0) or 0),
                float(x.get("gate_score", 0) or 0),
                float(x.get("signal_score", 0) or 0),
                float(x.get("ai_score", 0) or 0),
                float(x.get("goal_probability", 0) or 0),
                float(x.get("over_probability", 0) or 0),
            ),
            reverse=True,
        )

        # =========================
        # 5. CLASIFICACIÓN FINAL
        # =========================
        final_rows: List[Dict[str, Any]] = []

        for row in ranked[: SignalRankerService.MAX_ACTIVE_SIGNALS]:
            publication_score = float(row.get("publication_score", 0) or 0)

            if publication_score >= 78:
                row["publish_tier"] = "PREMIUM"
                row["publish_ready"] = True
            elif publication_score >= 66:
                row["publish_tier"] = "FUERTE"
                row["publish_ready"] = True
            elif publication_score >= 56:
                row["publish_tier"] = "BUENA"
                row["publish_ready"] = True
            elif publication_score >= 46:
                row["publish_tier"] = "OBSERVE_PRO"
                row["publish_ready"] = False
            else:
                row["publish_tier"] = "OBSERVE"
                row["publish_ready"] = False

            final_rows.append(row)

        return final_rows

    # =========================
    # RANKING DE CANDIDATA REAL
    # =========================
    @staticmethod
    def _rank_candidate(match: Dict[str, Any], motores: Dict[str, Any]) -> Dict[str, Any]:
        market = str(match.get("market", "N/A") or "N/A").upper()
        minute = SignalRankerService._safe_int(match.get("minute"), 0)

        ai_score = SignalRankerService._safe_float(match.get("ai_score"), 0.0)
        signal_score = SignalRankerService._safe_float(match.get("signal_score"), 0.0)
        gate_score = SignalRankerService._safe_float(match.get("gate_score"), 0.0)
        goal_probability = SignalRankerService._safe_float(match.get("goal_probability"), 0.0)
        over_probability = SignalRankerService._safe_float(match.get("over_probability"), 0.0)
        risk_score = SignalRankerService._safe_float(match.get("risk_score"), 0.0)

        match_state = str(match.get("match_state", "CONTROLADO") or "CONTROLADO").upper()
        signal_rank = str(match.get("signal_rank", "ACEPTABLE") or "ACEPTABLE").upper()
        data_quality = str(match.get("data_quality", "LOW") or "LOW").upper()
        window_phase = str(match.get("window_phase", "GENERAL") or "GENERAL").upper()

        predictor = motores.get("predictor", {}) or {}
        tactica = motores.get("tactica", {}) or {}
        gate = motores.get("gate", {}) or {}

        gol_inminente = bool(predictor.get("gol_inminente", False))
        confianza_ventana = SignalRankerService._safe_float(
            predictor.get("confianza_ventana"), 0.0
        )
        intensity_score = SignalRankerService._safe_float(
            tactica.get("intensity_score"), 0.0
        )

        publication_score = 0.0

        # Base principal
        publication_score += min(signal_score * 0.42, 42)
        publication_score += min(gate_score * 0.22, 22)
        publication_score += min(ai_score * 0.18, 18)

        # Probabilidades según mercado
        if "UNDER" in market:
            under_probability = max(100.0 - over_probability, 0.0)
            publication_score += min(under_probability * 0.10, 10)
            publication_score += min((100.0 - goal_probability) * 0.06, 6)
        else:
            publication_score += min(goal_probability * 0.10, 10)
            publication_score += min(over_probability * 0.08, 8)

        # Bonus por ventana y contexto
        if window_phase in [
            "OVER_PREMIUM_WINDOW",
            "LATE_CONTROL_WINDOW",
            "ULTRA_LATE",
            "HALFTIME_CAUTION",
            "EARLY_OBSERVE",
        ]:
            publication_score += 4

        if match_state == "EXPLOSIVO":
            publication_score += 8
        elif match_state == "CALIENTE":
            publication_score += 6
        elif match_state == "ACTIVO":
            publication_score += 4
        elif match_state == "ABIERTO":
            publication_score += 4
        elif match_state == "MUERTO" and "UNDER" in market:
            publication_score += 7
        elif match_state == "MUERTO" and "UNDER" not in market:
            publication_score -= 8

        if gol_inminente and "UNDER" not in market:
            publication_score += 6

        if confianza_ventana >= 70 and "UNDER" not in market:
            publication_score += 4

        if intensity_score >= 30 and "UNDER" not in market:
            publication_score += 3

        # Calidad de datos
        if data_quality == "HIGH":
            publication_score += 6
        elif data_quality == "MEDIUM":
            publication_score += 2
        else:
            if "UNDER" in market and minute >= 60:
                publication_score -= 2
            else:
                publication_score -= 7

        # Riesgo
        publication_score -= min(risk_score * 1.7, 14)

        # Bonus por rank ya asignado
        if signal_rank == "PREMIUM":
            publication_score += 7
        elif signal_rank == "FUERTE":
            publication_score += 5
        elif signal_rank == "BUENA":
            publication_score += 3

        # Bonus si gate ya venía favorable
        if gate.get("publish", False):
            publication_score += 4

        publication_score = round(max(publication_score, 0), 2)

        row = dict(match)
        row["publication_score"] = publication_score
        row["ranking_source"] = "candidate"
        row["ranking_reason"] = SignalRankerService._build_reason(
            market=market,
            publication_score=publication_score,
            signal_score=signal_score,
            gate_score=gate_score,
            ai_score=ai_score,
            goal_probability=goal_probability,
            over_probability=over_probability,
            risk_score=risk_score,
            data_quality=data_quality,
            match_state=match_state,
        )
        return row

    # =========================
    # RANKING DE OPORTUNIDAD
    # =========================
    @staticmethod
    def _rank_opportunity(row: Dict[str, Any], forced_market: str) -> Dict[str, Any]:
        minute = SignalRankerService._safe_int(row.get("minute"), 0)

        ai_score = SignalRankerService._safe_float(row.get("ai_score"), 0.0)
        goal_probability = SignalRankerService._safe_float(row.get("goal_probability"), 0.0)
        over_probability = SignalRankerService._safe_float(row.get("over_probability"), 0.0)
        risk_score = SignalRankerService._safe_float(row.get("risk_score"), 0.0)
        strength = SignalRankerService._safe_float(row.get("opportunity_strength"), 0.0)

        market = str(forced_market or row.get("market") or "N/A").upper()
        data_quality = str(row.get("data_quality", "LOW") or "LOW").upper()
        match_state = str(row.get("match_state", "CONTROLADO") or "CONTROLADO").upper()
        side = str(row.get("opportunity_side", "NONE") or "NONE").upper()

        publication_score = 0.0

        publication_score += min(strength * 0.85, 38)
        publication_score += min(ai_score * 0.20, 20)

        if "UNDER" in market:
            under_probability = max(100.0 - over_probability, 0.0)
            publication_score += min(under_probability * 0.18, 18)
            publication_score += min((100.0 - goal_probability) * 0.10, 10)

            if minute >= 60:
                publication_score += 8
            if match_state in ["MUERTO", "CONTROLADO", "TIBIO"]:
                publication_score += 6
        else:
            publication_score += min(goal_probability * 0.18, 18)
            publication_score += min(over_probability * 0.14, 14)

            if minute >= 25:
                publication_score += 4
            if match_state in ["ACTIVO", "ABIERTO", "CALIENTE", "EXPLOSIVO"]:
                publication_score += 6

        # calidad
        if data_quality == "HIGH":
            publication_score += 5
        elif data_quality == "MEDIUM":
            publication_score += 2
        else:
            if "UNDER" in market and minute >= 60:
                publication_score -= 1
            else:
                publication_score -= 6

        publication_score -= min(risk_score * 1.6, 14)

        if side == "UNDER" and "UNDER" in market:
            publication_score += 3
        if side == "OVER" and "UNDER" not in market:
            publication_score += 3

        publication_score = round(max(publication_score, 0), 2)

        built = {
            "match_id": row.get("match_id"),
            "partido": row.get("partido"),
            "home": row.get("home"),
            "away": row.get("away"),
            "league": row.get("league"),
            "country": row.get("country"),
            "minute": minute,
            "score": row.get("score", "0-0"),
            "market": market,
            "selection": "Under" if "UNDER" in market else "Over",
            "line": row.get("line", "Auto"),
            "ai_score": ai_score,
            "goal_probability": goal_probability,
            "over_probability": over_probability,
            "risk_score": risk_score,
            "signal_score": strength,
            "gate_score": strength,
            "signal_rank": SignalRankerService._classify_rank(publication_score),
            "match_state": match_state,
            "window_phase": row.get("window_phase", "OPPORTUNITY"),
            "window_reason": row.get("window_reason", "Oportunidad detectada por radar"),
            "momentum_label": row.get("momentum_label", "ESTABLE"),
            "dominance": row.get("dominance", "EQUILIBRADO"),
            "risk_level": row.get("risk_level", "MEDIO"),
            "shots": row.get("shots", 0),
            "shots_on_target": row.get("shots_on_target", 0),
            "corners": row.get("corners", 0),
            "dangerous_attacks": row.get("dangerous_attacks", 0),
            "xG": row.get("xG", 0),
            "data_quality": data_quality,
            "publication_score": publication_score,
            "ranking_source": "opportunity",
            "ranking_reason": ", ".join(row.get("opportunity_reasons", []) or []),
            "publish_ready": False,
            "recomendacion_final": SignalRankerService._classify_rank(publication_score),
        }
        return built

    # =========================
    # DEDUPLICACIÓN
    # =========================
    @staticmethod
    def _deduplicate(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        best_map: Dict[str, Dict[str, Any]] = {}

        for row in rows:
            match_id = str(row.get("match_id") or "")
            market = str(row.get("market") or "N/A").upper()

            if not match_id:
                home = str(row.get("home") or "")
                away = str(row.get("away") or "")
                league = str(row.get("league") or "")
                match_id = f"{home}|{away}|{league}"

            key = f"{match_id}|{market}"

            if key not in best_map:
                best_map[key] = row
                continue

            current_score = SignalRankerService._safe_float(
                best_map[key].get("publication_score"), 0.0
            )
            incoming_score = SignalRankerService._safe_float(
                row.get("publication_score"), 0.0
            )

            if incoming_score > current_score:
                best_map[key] = row

        return list(best_map.values())

    # =========================
    # HELPERS
    # =========================
    @staticmethod
    def _classify_rank(publication_score: float) -> str:
        if publication_score >= 82:
            return "PREMIUM"
        if publication_score >= 68:
            return "FUERTE"
        if publication_score >= 56:
            return "BUENA"
        return "ACEPTABLE"

    @staticmethod
    def _build_reason(
        market: str,
        publication_score: float,
        signal_score: float,
        gate_score: float,
        ai_score: float,
        goal_probability: float,
        over_probability: float,
        risk_score: float,
        data_quality: str,
        match_state: str,
    ) -> str:
        if "UNDER" in market:
            return (
                f"UNDER | pub={publication_score} | signal={signal_score} | gate={gate_score} | "
                f"IA={ai_score} | gol={goal_probability}% | over={over_probability}% | "
                f"riesgo={risk_score} | quality={data_quality} | state={match_state}"
            )

        return (
            f"OVER | pub={publication_score} | signal={signal_score} | gate={gate_score} | "
            f"IA={ai_score} | gol={goal_probability}% | over={over_probability}% | "
            f"riesgo={risk_score} | quality={data_quality} | state={match_state}"
        )

    @staticmethod
    def _safe_int(value: Any, default: int = 0) -> int:
        try:
            return int(float(value))
        except Exception:
            return default

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except Exception:
            return default
