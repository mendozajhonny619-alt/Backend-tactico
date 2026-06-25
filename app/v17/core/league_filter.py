from __future__ import annotations

import unicodedata
from typing import Any, Dict, List


ALLOWED_LEAGUE_KEYWORDS: List[str] = [
    "WORLD CUP",
    "FIFA WORLD CUP",
    "FIFA WORLD CUP 2026",
    "COPA MUNDIAL",
    "MUNDIAL",
    "WORLD CUP QUALIFIERS",
    "FIFA WORLD CUP QUALIFIERS",
    "CONMEBOL WORLD CUP QUALIFIERS",
    "UEFA WORLD CUP QUALIFIERS",
    "CONCACAF WORLD CUP QUALIFIERS",
    "CAF WORLD CUP QUALIFIERS",
    "AFC WORLD CUP QUALIFIERS",

    "EURO",
    "UEFA EURO",
    "COPA AMERICA",
    "COPA AMÉRICA",
    "AFRICA CUP",
    "AFRICAN CUP OF NATIONS",
    "ASIAN CUP",
    "CONCACAF",
    "CONCACAF GOLD CUP",

    "INTERNATIONAL FRIENDLIES",
    "INTERNATIONAL FRIENDLY",
    "NATIONAL TEAM FRIENDLY",
    "FIFA FRIENDLY",

    "UEFA CHAMPIONS LEAGUE",
    "CHAMPIONS LEAGUE",
    "UEFA EUROPA LEAGUE",
    "EUROPA LEAGUE",
    "UEFA CONFERENCE LEAGUE",
    "CONFERENCE LEAGUE",
    "COPA LIBERTADORES",
    "LIBERTADORES",
    "COPA SUDAMERICANA",
    "SUDAMERICANA",
    "RECOPA",

    "PREMIER LEAGUE",
    "CHAMPIONSHIP",
    "EFL CHAMPIONSHIP",

    "LA LIGA",
    "LALIGA",
    "PRIMERA DIVISION SPAIN",
    "PRIMERA DIVISIÓN SPAIN",
    "SEGUNDA DIVISION",
    "SEGUNDA DIVISIÓN",
    "LALIGA 2",
    "LA LIGA 2",

    "SERIE A",
    "SERIE B",

    "BUNDESLIGA",
    "2. BUNDESLIGA",
    "ZWEITE BUNDESLIGA",

    "LIGUE 1",
    "LIGUE 2",

    "PRIMEIRA LIGA",
    "LIGA PORTUGAL",
    "LIGA PORTUGAL 2",
    "SEGUNDA LIGA",

    "EREDIVISIE",
    "EERSTE DIVISIE",
    "JUPILER PRO LEAGUE",
    "CHALLENGER PRO LEAGUE",

    "MLS",
    "MAJOR LEAGUE SOCCER",
    "USL CHAMPIONSHIP",
    "LIGA MX",
    "EXPANSION MX",
    "EXPANSIÓN MX",

    "BRASILEIRO SERIE A",
    "BRASILEIRAO SERIE A",
    "BRASILEIRÃO SÉRIE A",
    "BRASILEIRO SERIE B",
    "BRASILEIRAO SERIE B",
    "BRASILEIRÃO SÉRIE B",
    "SERIE A BRAZIL",
    "SERIE B BRAZIL",

    "LIGA PROFESIONAL",
    "PRIMERA DIVISION ARGENTINA",
    "PRIMERA DIVISIÓN ARGENTINA",
    "PRIMERA NACIONAL",

    "DIVISION PROFESIONAL",
    "DIVISIÓN PROFESIONAL",
    "NACIONAL B",

    "PRIMERA DIVISION CHILE",
    "PRIMERA DIVISIÓN CHILE",
    "PRIMERA B CHILE",

    "PRIMERA A",
    "PRIMERA B",
    "CATEGORIA PRIMERA A",
    "CATEGORÍA PRIMERA A",
    "CATEGORIA PRIMERA B",
    "CATEGORÍA PRIMERA B",

    "LIGA 1",
    "LIGA 2",

    "LIGA PRO",
    "SERIE A ECUADOR",
    "SERIE B ECUADOR",

    "DIVISION PROFESIONAL PARAGUAY",
    "DIVISIÓN PROFESIONAL PARAGUAY",
    "INTERMEDIA",

    "PRIMERA DIVISION URUGUAY",
    "PRIMERA DIVISIÓN URUGUAY",
    "SEGUNDA DIVISION URUGUAY",
    "SEGUNDA DIVISIÓN URUGUAY",

    "ALLSVENSKAN",
    "SUPERETTAN",
    "ELITESERIEN",
    "OBOS-LIGAEN",
    "OBOS LIGAEN",
    "1. DIVISION NORWAY",
    "1ST DIVISION NORWAY",
    "SUPERLIGA",
    "DANISH SUPERLIGA",
    "1ST DIVISION DENMARK",
    "1. DIVISION DENMARK",
    "VEIKKAUSLIIGA",
    "YKKONEN",
    "YKKÖNEN",
    "SUPER LEAGUE SWITZERLAND",
    "SWISS SUPER LEAGUE",
    "CHALLENGE LEAGUE",
    "SWISS CHALLENGE LEAGUE",
    "BUNDESLIGA AUSTRIA",
    "AUSTRIAN BUNDESLIGA",
    "2. LIGA AUSTRIA",
    "2. LIGA",
    "PREMIERSHIP",
    "SCOTTISH PREMIERSHIP",
    "CHAMPIONSHIP SCOTLAND",
    "SCOTTISH CHAMPIONSHIP",
    "SUPER LIG",
    "SÜPER LIG",
    "1. LIG TURKEY",
    "TFF 1. LIG",
    "SUPER LEAGUE GREECE",
    "SUPER LEAGUE 1",
    "SUPER LEAGUE 2",
    "EKSTRAKLASA",
    "I LIGA",
    "CZECH LIGA",
    "FORTUNA LIGA",
    "FNL",
    "HNL",
    "PRVA HNL",
    "SUPER LIGA SERBIA",
    "SUPERLIGA SERBIA",
    "LIGA I",
    "LIGA 1 ROMANIA",
    "J1 LEAGUE",
    "J2 LEAGUE",
    "K LEAGUE 1",
    "K LEAGUE 2",
    "CHINESE SUPER LEAGUE",
    "CHINA LEAGUE ONE",
    "A-LEAGUE",
    "A LEAGUE",
]


HARD_BLOCKED_LEAGUE_KEYWORDS: List[str] = [
    "U20", "U21", "U23", "U19", "U18", "U17",
    "UNDER 20", "UNDER 21", "UNDER 23", "UNDER 19", "UNDER 18", "UNDER 17",
    "RESERVE", "RESERVES", "RESERVA", "RESERVAS",
    "YOUTH", "JUNIOR", "JUNIORS", "JUVENIL", "ACADEMY",
    "WOMEN", "WOMEN'S", "FEMENINO", "FEMENINA", "FEMALE",
    "TERCERA", "TERCERA DIVISION", "TERCERA DIVISIÓN", "THIRD DIVISION",
    "CUARTA", "CUARTA DIVISION", "CUARTA DIVISIÓN", "FOURTH DIVISION",
    "5TH", "FIFTH", "REGIONAL", "AMATEUR", "LOCAL LEAGUE", "DISTRICT", "COUNTY",
    "UNIVERSITY", "UNIVERSITARIO", "COLLEGE", "SCHOOL",
]


SOFT_BLOCKED_LEAGUE_KEYWORDS: List[str] = [
    "FRIENDLY",
    "FRIENDLIES",
    "CLUB FRIENDLIES",
    "AMISTOSO",
    "AMISTOSOS",
]


COUNTRY_ALLOWED_HINTS: List[str] = [
    "ENGLAND", "SPAIN", "ITALY", "GERMANY", "FRANCE", "PORTUGAL",
    "NETHERLANDS", "BELGIUM", "USA", "UNITED STATES", "MEXICO",
    "BRAZIL", "BRASIL", "ARGENTINA", "BOLIVIA", "CHILE", "COLOMBIA",
    "PERU", "ECUADOR", "PARAGUAY", "URUGUAY", "SWEDEN", "SUECIA",
    "NORWAY", "NORUEGA", "DENMARK", "DINAMARCA", "FINLAND", "FINLANDIA",
    "SWITZERLAND", "SUIZA", "AUSTRIA", "SCOTLAND", "ESCOCIA",
    "TURKEY", "TURQUIA", "TURQUÍA", "GREECE", "GRECIA", "POLAND",
    "POLONIA", "CZECH REPUBLIC", "CZECHIA", "CROATIA", "SERBIA",
    "ROMANIA", "JAPAN", "KOREA", "SOUTH KOREA", "CHINA", "AUSTRALIA",
]


class LeagueFilter:
    """
    Filtro de ligas V17.

    Permite competiciones prioritarias, incluyendo Mundial 2026,
    primeras divisiones, segundas divisiones fuertes y torneos internacionales.
    Bloquea juveniles, reservas, femenino, ligas regionales y amistosos menores.
    """

    def evaluate(self, item: Dict[str, Any]) -> Dict[str, Any]:
        league = self._extract_league_name(item)
        country = self._extract_country_name(item)

        league_text = self._normalize(f"{league} {country}")

        allowed_hits = [x for x in ALLOWED_LEAGUE_KEYWORDS if self._normalize(x) in league_text]
        hard_blocked_hits = [x for x in HARD_BLOCKED_LEAGUE_KEYWORDS if self._normalize(x) in league_text]
        soft_blocked_hits = [x for x in SOFT_BLOCKED_LEAGUE_KEYWORDS if self._normalize(x) in league_text]
        country_hits = [x for x in COUNTRY_ALLOWED_HINTS if self._normalize(x) in league_text]

        competition_tier = self._competition_tier(league_text, allowed_hits)

        if hard_blocked_hits:
            return self._result(
                allowed=False,
                status="BLOCKED_HARD_NON_PRIORITY",
                reason=f"Liga descartada por bloqueo fuerte: {hard_blocked_hits[0]}",
                allowed_hits=allowed_hits,
                blocked_hits=hard_blocked_hits,
                country_hits=country_hits,
                competition_tier="BLOCKED",
                competition_weight=0,
            )

        if allowed_hits:
            return self._result(
                allowed=True,
                status="ALLOWED_PRIORITY_LEAGUE",
                reason=f"Liga permitida: {allowed_hits[0]}",
                allowed_hits=allowed_hits,
                blocked_hits=soft_blocked_hits,
                country_hits=country_hits,
                competition_tier=competition_tier,
                competition_weight=self._competition_weight(competition_tier),
            )

        if soft_blocked_hits:
            return self._result(
                allowed=False,
                status="BLOCKED_FRIENDLY_OR_LOW_PRIORITY",
                reason=f"Liga descartada por palabra bloqueada: {soft_blocked_hits[0]}",
                allowed_hits=allowed_hits,
                blocked_hits=soft_blocked_hits,
                country_hits=country_hits,
                competition_tier="BLOCKED",
                competition_weight=0,
            )

        if country_hits:
            return self._result(
                allowed=True,
                status="ALLOWED_BY_COUNTRY_NEEDS_REVIEW",
                reason="País prioritario detectado, pero liga no clasificada. Se permite con revisión.",
                allowed_hits=allowed_hits,
                blocked_hits=[],
                country_hits=country_hits,
                competition_tier="COUNTRY_REVIEW",
                competition_weight=45,
            )

        return self._result(
            allowed=False,
            status="BLOCKED_UNKNOWN_LOW_PRIORITY",
            reason="Liga no identificada como primera o segunda división prioritaria.",
            allowed_hits=allowed_hits,
            blocked_hits=[],
            country_hits=country_hits,
            competition_tier="UNKNOWN",
            competition_weight=0,
        )

    def filter_matches(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        allowed: List[Dict[str, Any]] = []
        blocked: List[Dict[str, Any]] = []

        for item in items or []:
            if not isinstance(item, dict):
                continue

            result = self.evaluate(item)
            enriched = {**item, **result}

            if result.get("league_allowed"):
                allowed.append(enriched)
            else:
                blocked.append(enriched)

        return {
            "allowed": allowed,
            "blocked_by_league": blocked,
            "summary": {
                "received": len(items or []),
                "allowed": len(allowed),
                "blocked_by_league": len(blocked),
            },
        }

    def _result(
        self,
        allowed: bool,
        status: str,
        reason: str,
        allowed_hits: List[str],
        blocked_hits: List[str],
        country_hits: List[str],
        competition_tier: str,
        competition_weight: int,
    ) -> Dict[str, Any]:
        return {
            "league_allowed": allowed,
            "league_filter_status": status,
            "league_filter_reason": reason,
            "competition_tier": competition_tier,
            "competition_weight": competition_weight,
            "league_filter_hits": {
                "allowed": allowed_hits,
                "blocked": blocked_hits,
                "country": country_hits,
            },
        }

    def _competition_tier(self, league_text: str, allowed_hits: List[str]) -> str:
        if any(x in league_text for x in ["WORLD CUP", "COPA MUNDIAL", "MUNDIAL"]):
            return "WORLD_CUP_ELITE"

        if any(x in league_text for x in ["CHAMPIONS LEAGUE", "EUROPA LEAGUE", "LIBERTADORES", "SUDAMERICANA"]):
            return "INTERNATIONAL_CLUB_ELITE"

        if any(x in league_text for x in ["COPA AMERICA", "EURO", "AFRICA CUP", "ASIAN CUP", "GOLD CUP"]):
            return "NATIONAL_TEAM_ELITE"

        if allowed_hits:
            return "PRIORITY_LEAGUE"

        return "UNKNOWN"

    def _competition_weight(self, tier: str) -> int:
        weights = {
            "WORLD_CUP_ELITE": 100,
            "INTERNATIONAL_CLUB_ELITE": 90,
            "NATIONAL_TEAM_ELITE": 88,
            "PRIORITY_LEAGUE": 75,
            "COUNTRY_REVIEW": 45,
            "UNKNOWN": 0,
            "BLOCKED": 0,
        }
        return weights.get(tier, 0)

    def _extract_league_name(self, item: Dict[str, Any]) -> str:
        league_obj = item.get("league") if isinstance(item.get("league"), dict) else {}

        return self._text(
            item.get("league") if not isinstance(item.get("league"), dict) else None
            or item.get("league_name")
            or item.get("competition")
            or item.get("tournament")
            or league_obj.get("name")
        )

    def _extract_country_name(self, item: Dict[str, Any]) -> str:
        league_obj = item.get("league") if isinstance(item.get("league"), dict) else {}

        return self._text(
            item.get("country")
            or item.get("country_name")
            or item.get("pais")
            or league_obj.get("country")
        )

    def _text(self, value: Any) -> str:
        if value is None:
            return ""

        return str(value).strip()

    def _normalize(self, value: Any) -> str:
        text = str(value or "").strip().upper()
        text = unicodedata.normalize("NFKD", text)
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        return text
