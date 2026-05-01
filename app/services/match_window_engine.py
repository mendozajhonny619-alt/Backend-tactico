from __future__ import annotations

from typing import Any, Dict


class MatchWindowEngine:
    """
    Controla ventanas operativas del partido.

    Reglas base:
    - 25–45 y 60–75 => PREMIUM
    - 15–24 y 76–85 => OPERABLE con filtro extra
    - 1–14 => bloqueado
    - 86+ => bloqueado salvo premium real (de momento restringido)

    Devuelve:
    - phase
    - reason
    - allowed
    - allow_over
    - allow_under
    - bias
    - gate_min_score
    """

    PHASE_BLOCKED = "BLOCKED"
    PHASE_RESTRICTED = "RESTRICTED"
    PHASE_OPERABLE = "OPERABLE"
    PHASE_PREMIUM = "PREMIUM"

    def evaluate(self, match: Dict[str, Any]) -> Dict[str, Any]:
        minute = self._extract_minute(match)

        if minute <= 0:
            return self._build_response(
                minute=minute,
                phase=self.PHASE_BLOCKED,
                allowed=False,
                allow_over=False,
                allow_under=False,
                bias="NONE",
                gate_min_score=999,
                reason="WINDOW_INVALID_MINUTE",
            )

        # 1–14 bloqueado
        if 1 <= minute <= 14:
            return self._build_response(
                minute=minute,
                phase=self.PHASE_BLOCKED,
                allowed=False,
                allow_over=False,
                allow_under=False,
                bias="NONE",
                gate_min_score=999,
                reason="WINDOW_TOO_EARLY",
            )

        # 15–24 operable con filtro extra, más sesgo a OVER
        if 15 <= minute <= 24:
            return self._build_response(
                minute=minute,
                phase=self.PHASE_OPERABLE,
                allowed=True,
                allow_over=True,
                allow_under=False,
                bias="OVER",
                gate_min_score=72,
                reason="WINDOW_OPERABLE_FIRST_HALF",
            )

        # 25–45 premium
        if 25 <= minute <= 45:
            return self._build_response(
                minute=minute,
                phase=self.PHASE_PREMIUM,
                allowed=True,
                allow_over=True,
                allow_under=False,
                bias="OVER",
                gate_min_score=68,
                reason="WINDOW_PREMIUM_FIRST_HALF",
            )

        # 46–59 intermedio, operable conservador
        if 46 <= minute <= 59:
            return self._build_response(
                minute=minute,
                phase=self.PHASE_OPERABLE,
                allowed=True,
                allow_over=True,
                allow_under=False,
                bias="OVER",
                gate_min_score=70,
                reason="WINDOW_SECOND_HALF_BUILDUP",
            )

        # 60–75 premium
        if 60 <= minute <= 75:
            return self._build_response(
                minute=minute,
                phase=self.PHASE_PREMIUM,
                allowed=True,
                allow_over=True,
                allow_under=True,
                bias="BALANCED",
                gate_min_score=68,
                reason="WINDOW_PREMIUM_SECOND_HALF",
            )

        # 76–85 operable con filtro extra, sesgo a UNDER
        if 76 <= minute <= 85:
            return self._build_response(
                minute=minute,
                phase=self.PHASE_OPERABLE,
                allowed=True,
                allow_over=False,
                allow_under=True,
                bias="UNDER",
                gate_min_score=74,
                reason="WINDOW_OPERABLE_LATE_GAME",
            )

        # 86–90 restringido: solo UNDER en contextos muy limpios, el resto bloqueado en capas siguientes
        if 86 <= minute <= 90:
            return self._build_response(
                minute=minute,
                phase=self.PHASE_RESTRICTED,
                allowed=True,
                allow_over=False,
                allow_under=True,
                bias="UNDER",
                gate_min_score=80,
                reason="WINDOW_RESTRICTED_LATE_UNDER_ONLY",
            )

        return self._build_response(
            minute=minute,
            phase=self.PHASE_BLOCKED,
            allowed=False,
            allow_over=False,
            allow_under=False,
            bias="NONE",
            gate_min_score=999,
            reason="WINDOW_TOO_LATE",
        )

    def _extract_minute(self, match: Dict[str, Any]) -> int:
        raw = (
            match.get("minute")
            or match.get("current_minute")
            or match.get("match_minute")
            or 0
        )
        try:
            return int(raw)
        except (TypeError, ValueError):
            return 0

    def _build_response(
        self,
        minute: int,
        phase: str,
        allowed: bool,
        allow_over: bool,
        allow_under: bool,
        bias: str,
        gate_min_score: int,
        reason: str,
    ) -> Dict[str, Any]:
        return {
            "minute": minute,
            "phase": phase,
            "allowed": allowed,
            "allow_over": allow_over,
            "allow_under": allow_under,
            "bias": bias,
            "gate_min_score": gate_min_score,
            "reason": reason,
        }
