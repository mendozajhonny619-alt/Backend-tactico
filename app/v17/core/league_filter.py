from __future__ import annotations

from typing import Any, Dict, List


ALLOWED_LEAGUE_KEYWORDS: List[str] = [
    # Internacionales principales
    "WORLD CUP",
    "EURO",
    "COPA AMERICA",
    "AFRICA CUP",
    "ASIAN CUP",
    "CONCACAF",
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

    # Inglaterra
    "PREMIER LEAGUE",
    "CHAMPIONSHIP",

    # España
    "LA LIGA",
    "LALIGA",
    "SEGUNDA DIVISION",
    "SEGUNDA DIVISIÓN",

    # Italia
    "SERIE A",
    "SERIE B",

    # Alemania
    "BUNDESLIGA",
    "2. BUNDESLIGA",
    "ZWEITE BUNDESLIGA",

    # Francia
    "LIGUE 1",
    "LIGUE 2",

    # Portugal / Holanda / Bélgica
    "PRIMEIRA LIGA",
    "LIGA PORTUGAL",
    "EREDIVISIE",
    "EERSTE DIVISIE",
    "JUPILER PRO LEAGUE",

    # Estados Unidos / México
    "MLS",
    "MAJOR LEAGUE SOCCER",
    "LIGA MX",
    "EXPANSION MX",
    "EXPANSIÓN MX",

    # Brasil
    "BRASILEIRO SERIE A",
    "BRASILEIRAO SERIE A",
    "BRASILEIRÃO SÉRIE A",
    "BRASILEIRO SERIE B",
    "BRASILEIRAO SERIE B",
    "BRASILEIRÃO SÉRIE B",
    "SERIE A BRAZIL",
    "SERIE B BRAZIL",

    # Argentina
    "LIGA PROFESIONAL",
    "PRIMERA DIVISION",
    "PRIMERA DIVISIÓN",
    "PRIMERA NACIONAL",

    # Bolivia
    "DIVISION PROFESIONAL",
    "DIVISIÓN PROFESIONAL",
    "NACIONAL B",

    # Chile
    "PRIMERA DIVISION CHILE",
    "PRIMERA DIVISIÓN CHILE",
    "PRIMERA B CHILE",

    # Colombia
    "PRIMERA A",
    "PRIMERA B",

    # Perú
    "LIGA 1",
    "LIGA 2",

    # Ecuador
    "LIGA PRO",
    "SERIE A ECUADOR",
    "SERIE B ECUADOR",

    # Paraguay
    "DIVISION PROFESIONAL PARAGUAY",
    "DIVISIÓN PROFESIONAL PARAGUAY",
    "INTERMEDIA",

    # Uruguay
    "PRIMERA DIVISION URUGUAY",
    "PRIMERA DIVISIÓN URUGUAY",
    "SEGUNDA DIVISION URUGUAY",
    "SEGUNDA DIVISIÓN URUGUAY",
]


BLOCKED_LEAGUE_KEYWORDS: List[str] = [
    # Juveniles / reservas
    "U20",
    "U21",
    "U23",
    "U19",
    "U18",
    "U17",
    "UNDER 20",
    "UNDER 21",
    "UNDER 23",
    "RESERVE",
    "RESERVES",
    "RESERVA",
    "RESERVAS",
    "YOUTH",
    "JUNIOR",
    "JUVENIL",
    "ACADEMY",

    # Femenino, si no se trabajará ese mercado
    "WOMEN",
    "WOMEN'S",
    "FEMENINO",
    "FEMENINA",

    # Divisiones inferiores
    "TERCERA",
    "TERCERA DIVISION",
    "TERCERA DIVISIÓN",
    "THIRD",
    "THIRD DIVISION",
    "CUARTA",
    "FOURTH",
    "4TH",
    "3.",
    "4.",
    "REGIONAL",
    "AMATEUR",
    "LOCAL LEAGUE",

    # Amistosos menores
    "FRIENDLY",
    "FRIENDLIES",
    "CLUB FRIENDLIES",
    "AMISTOSO",
    "AMISTOSOS",

    # Torneos no prioritarios
    "UNIVERSITY",
    "UNIVERSITARIO",
    "COLLEGE",
    "SCHOOL",
]


COUNTRY_ALLOWED_HINTS: List[str] = [
    "ENGLAND",
    "SPAIN",
    "ITALY",
    "GERMANY",
    "FRANCE",
    "PORTUGAL",
    "NETHERLANDS",
    "BELGIUM",
    "USA",
    "UNITED STATES",
    "MEXICO",
    "BRAZIL",
    "BRASIL",
    "ARGENTINA",
    "BOLIVIA",
    "CHILE",
    "COLOMBIA",
    "PERU",
    "ECUADOR",
    "PARAGUAY",
    "URUGUAY",
]


class LeagueFilter:
    """
    Filtro de ligas V17.

    Objetivo:
    - Priorizar primera y segunda división.
    - Permitir torneos internacionales principales.
    - Ignorar reservas, juveniles, femenino, amistosos menores y ligas inferiores.
    """

    def evaluate(self, item: Dict[str, Any]) -> Dict[str, Any]:
        league = self._text(
            item.get("league")
            or item.get("league_name")
            or item.get("competition")
            or item.get("tournament")
        )

        country = self._text(
            item.get("country")
            or item.get("country_name")
            or item.get("pais")
        )

        league_text = f"{league} {country}".upper()

        blocked_hits = [x for x in BLOCKED_LEAGUE_KEYWORDS if x in league_text]
        allowed_hits = [x for x in ALLOWED_LEAGUE_KEYWORDS if x in league_text]
        country_hits = [x for x in COUNTRY_ALLOWED_HINTS if x in league_text]

        if blocked_hits:
            return {
                "league_allowed": False,
                "league_filter_status": "BLOCKED_LOWER_OR_NON_PRIORITY",
                "league_filter_reason": f"Liga descartada por palabra bloqueada: {blocked_hits[0]}",
                "league_filter_hits": {
                    "allowed": allowed_hits,
                    "blocked": blocked_hits,
                    "country": country_hits,
                },
            }

        if allowed_hits:
            return {
                "league_allowed": True,
                "league_filter_status": "ALLOWED_PRIORITY_LEAGUE",
                "league_filter_reason": f"Liga permitida: {allowed_hits[0]}",
                "league_filter_hits": {
                    "allowed": allowed_hits,
                    "blocked": blocked_hits,
                    "country": country_hits,
                },
            }

        # Si no se identifica claramente, no se bloquea de forma agresiva al inicio.
        # Se manda como observación para no matar ligas mal nombradas por la API.
        if country_hits:
            return {
                "league_allowed": True,
                "league_filter_status": "ALLOWED_BY_COUNTRY_NEEDS_REVIEW",
                "league_filter_reason": "País prioritario detectado, pero liga no clasificada. Se permite con revisión.",
                "league_filter_hits": {
                    "allowed": allowed_hits,
                    "blocked": blocked_hits,
                    "country": country_hits,
                },
            }

        return {
            "league_allowed": False,
            "league_filter_status": "BLOCKED_UNKNOWN_LOW_PRIORITY",
            "league_filter_reason": "Liga no identificada como primera o segunda división prioritaria.",
            "league_filter_hits": {
                "allowed": allowed_hits,
                "blocked": blocked_hits,
                "country": country_hits,
            },
        }

    def filter_matches(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        allowed: List[Dict[str, Any]] = []
        blocked: List[Dict[str, Any]] = []

        for item in items or []:
            result = self.evaluate(item)
            enriched = {
                **item,
                **result,
            }

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

    def _text(self, value: Any) -> str:
        if value is None:
            return ""

        return str(value).strip()
