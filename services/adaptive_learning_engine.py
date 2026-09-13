from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List


class AdaptiveLearningEngine:
    """
    Motor de aprendizaje adaptativo.

    Lee historial real y detecta:
    - ligas peligrosas
    - mercados débiles
    - patrones ganadores
    - patrones perdedores
    - señales falsas
    - ajustes de confianza

    No crea señales.
    No reemplaza decisiones.
    Solo entrega aprendizaje contextual.
    """

    def analyze(
        self,
        history: List[Dict[str, Any]] | None = None,
        match: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:

        history = history or []
        match = match or {}

        valid_history = [
            item for item in history
            if isinstance(item, dict)
        ]

        league = str(
            match.get("league")
            or match.get("liga")
            or "UNKNOWN"
        ).upper()

        market = str(
            match.get("market")
            or match.get("recommended_market")
            or "UNKNOWN"
        ).upper()

        league_profile = self._profile_by_field(
            history=valid_history,
            field="league",
            target=league,
        )

        market_profile = self._profile_by_field(
            history=valid_history,
            field="market",
            target=market,
        )

        global_profile = self._global_profile(valid_history)

        adjustment = self._confidence_adjustment(
            league_profile=league_profile,
            market_profile=market_profile,
            global_profile=global_profile,
        )

        warning_flags = self._warning_flags(
            league_profile=league_profile,
            market_profile=market_profile,
            adjustment=adjustment,
        )

        return {
            "adaptive_learning_enabled": True,
            "adaptive_confidence_adjustment": adjustment,
            "adaptive_warning_flags": warning_flags,
            "adaptive_league_profile": league_profile,
            "adaptive_market_profile": market_profile,
            "adaptive_global_profile": global_profile,
            "adaptive_learning_summary": self._summary(
                adjustment=adjustment,
                warning_flags=warning_flags,
                league_profile=league_profile,
                market_profile=market_profile,
            ),
        }

    def _profile_by_field(
        self,
        history: List[Dict[str, Any]],
        field: str,
        target: str,
    ) -> Dict[str, Any]:

        items = []

        for item in history:
            value = str(item.get(field) or "UNKNOWN").upper()

            if target == "UNKNOWN":
                continue

            if value == target or target in value or value in target:
                items.append(item)

        return self._build_profile(items)

    def _global_profile(
        self,
        history: List[Dict[str, Any]],
    ) -> Dict[str, Any]:

        return self._build_profile(history)

    def _build_profile(
        self,
        items: List[Dict[str, Any]],
    ) -> Dict[str, Any]:

        total = len(items)

        if total == 0:
            return {
                "sample": 0,
                "wins": 0,
                "losses": 0,
                "voids": 0,
                "pending": 0,
                "winrate": 0.0,
                "lossrate": 0.0,
                "roi": 0.0,
                "risk_level": "UNKNOWN",
            }

        wins = 0
        losses = 0
        voids = 0
        pending = 0
        profit_units = 0.0
        staked = 0.0

        for item in items:
            result = str(
                item.get("resultado")
                or item.get("status")
                or ""
            ).upper()

            stake = self._safe_float(item.get("stake") or 1.0)
            profit = self._safe_float(item.get("profit_units"))

            if result == "WIN":
                wins += 1
                staked += stake
                profit_units += profit

            elif result == "LOSS":
                losses += 1
                staked += stake
                profit_units += profit

            elif result in {"VOID", "PUSH"}:
                voids += 1

            else:
                pending += 1

        decided = wins + losses

        winrate = (wins / decided * 100) if decided else 0.0
        lossrate = (losses / decided * 100) if decided else 0.0
        roi = (profit_units / staked * 100) if staked > 0 else 0.0

        risk_level = self._risk_level(
            sample=total,
            winrate=winrate,
            roi=roi,
            lossrate=lossrate,
        )

        return {
            "sample": total,
            "wins": wins,
            "losses": losses,
            "voids": voids,
            "pending": pending,
            "winrate": round(winrate, 2),
            "lossrate": round(lossrate, 2),
            "roi": round(roi, 2),
            "profit_units": round(profit_units, 2),
            "risk_level": risk_level,
        }

    def _risk_level(
        self,
        sample: int,
        winrate: float,
        roi: float,
        lossrate: float,
    ) -> str:

        if sample < 5:
            return "LOW_SAMPLE"

        if roi <= -20 or lossrate >= 65:
            return "DANGER"

        if roi < 0 or winrate < 45:
            return "WEAK"

        if roi >= 15 and winrate >= 58:
            return "STRONG"

        return "NORMAL"

    def _confidence_adjustment(
        self,
        league_profile: Dict[str, Any],
        market_profile: Dict[str, Any],
        global_profile: Dict[str, Any],
    ) -> float:

        adjustment = 0.0

        for profile, weight in [
            (league_profile, 0.45),
            (market_profile, 0.35),
            (global_profile, 0.20),
        ]:
            risk = str(profile.get("risk_level") or "").upper()
            sample = self._safe_float(profile.get("sample"))
            roi = self._safe_float(profile.get("roi"))
            winrate = self._safe_float(profile.get("winrate"))

            if sample < 5:
                continue

            if risk == "DANGER":
                adjustment -= 14 * weight

            elif risk == "WEAK":
                adjustment -= 8 * weight

            elif risk == "STRONG":
                adjustment += 8 * weight

            elif risk == "NORMAL":
                if roi > 0 and winrate >= 52:
                    adjustment += 3 * weight

        return round(max(-20.0, min(12.0, adjustment)), 2)

    def _warning_flags(
        self,
        league_profile: Dict[str, Any],
        market_profile: Dict[str, Any],
        adjustment: float,
    ) -> List[str]:

        flags: List[str] = []

        if str(league_profile.get("risk_level")).upper() == "DANGER":
            flags.append("LEAGUE_HISTORY_DANGER")

        if str(league_profile.get("risk_level")).upper() == "WEAK":
            flags.append("LEAGUE_HISTORY_WEAK")

        if str(market_profile.get("risk_level")).upper() == "DANGER":
            flags.append("MARKET_HISTORY_DANGER")

        if str(market_profile.get("risk_level")).upper() == "WEAK":
            flags.append("MARKET_HISTORY_WEAK")

        if adjustment <= -10:
            flags.append("CONFIDENCE_REDUCTION_STRONG")

        elif adjustment < 0:
            flags.append("CONFIDENCE_REDUCTION_LIGHT")

        if adjustment > 5:
            flags.append("CONFIDENCE_SUPPORT")

        return flags

    def _summary(
        self,
        adjustment: float,
        warning_flags: List[str],
        league_profile: Dict[str, Any],
        market_profile: Dict[str, Any],
    ) -> str:

        if not warning_flags:
            return (
                f"Aprendizaje adaptativo estable. "
                f"Ajuste confianza: {adjustment}."
            )

        return (
            f"Aprendizaje adaptativo detecta riesgo histórico. "
            f"Ajuste confianza: {adjustment}. "
            f"Liga WR={league_profile.get('winrate')}%, "
            f"Mercado WR={market_profile.get('winrate')}%. "
            f"Alertas: {', '.join(warning_flags)}."
        )

    def _safe_float(self, value: Any) -> float:
        try:
            return float(value or 0)
        except Exception:
            return 0.0
