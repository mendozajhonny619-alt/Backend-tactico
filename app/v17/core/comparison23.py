"""Comparador V3 de 23 criterios con procedencia y ausencia explicita.

No convierte posesion, ataques o proxies en notas inventadas 1..10.
Solo utiliza datos que aparecen realmente en el snapshot y conserva N/A.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

CRITERIA = [
    "Posesion util", "Dominio territorial", "Presion alta", "Presion ofensiva",
    "Robo y recuperacion", "Presion en area rival", "Volumen de remates",
    "Remates a porteria", "Calidad de ocasiones", "Peligrosidad dentro del area",
    "Ataques por bandas", "Definicion", "Contraataque", "Transicion ofensiva",
    "Transicion defensiva", "Solidez defensiva", "Vulnerabilidad a espacios",
    "Balon parado", "Ritmo reciente", "Momentum", "Intensidad tardia estimada",
    "Impacto de alineaciones", "Urgencia contextual",
]

# Raw values are only legitimate when the original provider published the field.
FIELDS = {
    "shots": "Total Shots",
    "shots_on_target": "Shots on Goal",
    "shots_inside_box": "Shots insidebox",
    "corners": "Corner Kicks",
    "possession": "Ball Possession",
    "xG": "expected_goals",
}


def _number(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(str(value).replace('%','').strip())
    except (ValueError, TypeError):
        return None


def _stat(stats: Dict[str, Any], key: str) -> Optional[float]:
    available = set(stats.get("stats_available_fields") or [])
    # `stats_available_fields` is the provider evidence flag, not an estimate.
    if FIELDS.get(key) not in available:
        return None
    return _number(stats.get(key))


def build_comparison23(match: Dict[str, Any]) -> Dict[str, Any]:
    home = match.get("home_stats") if isinstance(match.get("home_stats"), dict) else {}
    away = match.get("away_stats") if isinstance(match.get("away_stats"), dict) else {}
    if not match.get("has_live_stats"):
        home, away = {}, {}

    rows: List[Dict[str, Any]] = []
    mapping = {
        6: ("shots_inside_box", "PROXY: tiros desde dentro del area"),
        7: ("shots", "HECHO: remates acumulados"),
        8: ("shots_on_target", "HECHO: tiros al arco"),
        9: ("xG", "HECHO: xG publicado por proveedor"),
        10: ("shots_inside_box", "PROXY: tiros desde dentro del area"),
        18: ("corners", "PROXY: corners, no incluye calidad de faltas"),
    }
    for index, name in enumerate(CRITERIA, start=1):
        row: Dict[str, Any] = {
            "number": index, "name": name,
            "home_value": None, "away_value": None,
            "score_home": None, "score_away": None,
            "status": "N/A", "source": None,
            "evidence": "Datos insuficientes para este criterio; no se inventa nota",
        }
        if index in mapping:
            key, description = mapping[index]
            hv, av = _stat(home, key), _stat(away, key)
            if hv is not None or av is not None:
                row.update(home_value=hv, away_value=av,
                           source=match.get("stats_source") or "api_football_fixture_statistics",
                           status="AVAILABLE" if hv is not None and av is not None else "PARTIAL",
                           evidence=description)
        elif index == 12:
            # Conversion is descriptive only: never a reliable finishing skill
            # estimate based on a single live game.
            hs,as_ = _stat(home, "shots"),_stat(away,"shots")
            hgoals,agoals=_number(match.get("home_score")),_number(match.get("away_score"))
            if hs and as_ and hgoals is not None and agoals is not None:
                row.update(home_value=round(100*hgoals/hs,1),away_value=round(100*agoals/as_,1),
                           status="PROXY",evidence="Conversion goles/remates %; muestra limitada; no es habilidad de definicion",
                           source="marcador + remates")
        elif index == 16:
            hs,as_ = _stat(home,"shots_on_target"),_stat(away,"shots_on_target")
            if hs is not None and as_ is not None:
                row.update(home_value=as_,away_value=hs,status="PROXY",
                           evidence="Tiros al arco concedidos (menos no siempre significa defensa mejor)",
                           source="api_football_fixture_statistics")
        elif index == 20 and match.get("temporal_memory_ready"):
            hv=match.get("home_momentum")
            av=match.get("away_momentum")
            if hv is not None or av is not None:
                row.update(home_value=hv,away_value=av,status="INFERENCE",
                           evidence="Tendencia derivada de snapshots temporales, no hecho independiente",
                           source="TemporalMatchMemory")
        elif index == 23:
            minute=_number(match.get("api_minute") if match.get("api_minute") is not None else match.get("minute"))
            hg=_number(match.get("home_score"))
            ag=_number(match.get("away_score"))
            if minute is not None and hg is not None and ag is not None:
                row.update(home_value="PIERDE" if hg < ag else "EMPATA" if hg == ag else "GANA",
                           away_value="PIERDE" if ag < hg else "EMPATA" if ag == hg else "GANA",
                           status="INFERENCE",source="marcador + minuto",
                           evidence=f"Situacion de marcador al minuto {minute:g}; no asegura urgencia tactica")
        rows.append(row)
    return {"version": "COMPARISON23_V3_1", "count": len(rows),
            "available": sum(x["status"] != "N/A" for x in rows),
            "scoring_method": "NO_UNSUPPORTED_SCORES", "criteria": rows}
