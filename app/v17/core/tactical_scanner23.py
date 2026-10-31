"""TacticalScanner23 V3 — SECOND, separate set of 23 tactical indicators.

This module never computes goals, odds, EV or publishes a signal. It reuses
already collected match statistics; no API requests and no invented tracking.
A numeric 1..10 is shown ONLY for interpretable metrics with an explicit,
*experimental* transformation. It is NOT an official statistic, nor a
probability, nor a proven league-relative ranking.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

NAMES = [
    "Dominio de balón / posesión útil", "Precisión de pases",
    "Construcción de juego", "Frecuencia de ataque por bandas",
    "Letalidad y productividad de las bandas", "Llegadas al último tercio",
    "Creación de ocasiones claras", "Tiros totales", "Tiros a puerta",
    "Calidad de ejecución de remates", "Eficacia de finalización",
    "Peligrosidad dentro del área", "Presión territorial sobre el área",
    "Presión ofensiva alta", "Robo y recuperación del balón",
    "Contrapresión tras pérdida", "Velocidad en transición ofensiva",
    "Ataque posicional y ruptura de líneas", "Frecuencia de contragolpes",
    "Letalidad del contragolpe", "Ofensiva peligrosa real",
    "Errores defensivos forzados (proxy de depredación)",
    "Resistencia e intensidad durante 90 minutos",
]
MINI_IDS = (14, 15, 13, 17, 22, 11)

# The only field names accepted as *published* when using API-Football.
FIELDS = {
    'possession': ('Ball Possession',),
    'pass_accuracy': ('Passes %',),
    'passes': ('Total passes',),
    'shots': ('Total Shots',),
    'sot': ('Shots on Goal',),
    'inside': ('Shots insidebox',),
    'xg': ('expected_goals',),
    'corners': ('Corner Kicks',),
}


def _numeric(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        n = float(str(value).strip().rstrip('%'))
        if n != n or n == float('inf') or n == -float('inf'):
            return None
        return n
    except (ValueError, TypeError):
        return None


def _published(stats: Dict[str, Any], key: str) -> Optional[float]:
    fields = set(stats.get('stats_available_fields') or [])
    if not fields.intersection(FIELDS.get(key, ())):
        return None
    return _numeric(stats.get({
        'passes': 'total_passes', 'sot': 'shots_on_target',
        'inside': 'shots_inside_box', 'xg': 'xG',
    }.get(key, key)))


def _score(value: float, benchmark: float) -> float:
    """Transparent descriptive 1..10 scale; benchmark is NOT league mean."""
    return round(min(10.0, max(1.0, 1.0 + 9.0 * max(0.0, value) / benchmark)), 1)


def build_tactical_scanner23(match: Dict[str, Any]) -> Dict[str, Any]:
    home = match.get('home_stats') if isinstance(match.get('home_stats'), dict) else {}
    away = match.get('away_stats') if isinstance(match.get('away_stats'), dict) else {}
    if not match.get('has_live_stats'):
        home, away = {}, {}
    minute = _numeric(match.get('effective_minute') or match.get('api_minute') or match.get('minute')) or 0.0
    valid_minute = minute >= 20.0
    rows: List[Dict[str, Any]] = []

    def both(key: str):
        return _published(home, key), _published(away, key)

    def fill(number: int, *, h: Optional[float], a: Optional[float], note: str,
             source: str, scores: Optional[tuple] = None, label: str = 'R'):
        row = rows[number - 1]
        if h is None or a is None:
            return
        row.update(home_value=round(h, 2), away_value=round(a, 2),
                   quality=label, evidence=note, source=source)
        if scores and scores[0] is not None and scores[1] is not None:
            row.update(score_home=scores[0], score_away=scores[1],
                       difference=round(scores[0] - scores[1], 1),
                       advantage='LOCAL' if scores[0] > scores[1] else 'VISITANTE' if scores[1] > scores[0] else 'IGUAL')
            row['quality'] = 'E'

    for number, title in enumerate(NAMES, 1):
        rows.append({
            'number': number, 'name': title, 'score_home': None,
            'score_away': None, 'difference': None, 'advantage': 'ND',
            'home_value': None, 'away_value': None, 'quality': 'ND',
            'source': None, 'evidence': 'La fuente no aporta la métrica necesaria; no se infiere una nota.',
        })

    # Raw possession is shown as a fact; it does NOT establish *useful* possession.
    ph, pa = both('possession')
    fill(1, h=ph, a=pa, note='Posesión publicada en %. Sin progresión verificable, NO se califica posesión útil.',
         source='API-Football: Ball Possession')
    pass_h, pass_a = both('pass_accuracy')
    if pass_h is not None and pass_a is not None:
        passes_h, passes_a = both('passes')
        scores = (_score(pass_h, 100), _score(pass_a, 100)) if (
            passes_h is not None and passes_a is not None and min(passes_h, passes_a) >= 80) else None
        fill(2, h=pass_h, a=pass_a, scores=scores,
             note='Precisión % observada; índice E = 1 + 9 × precisión/100, con ≥80 pases por equipo.'
                  if scores else 'Precisión % publicada; sin muestra suficiente para nota.',
             source='API-Football: Passes %')

    # The benchmark values are documented exploratory per-90 references, not
    # derived from unpublished league averages. Both sides need ≥20 observed min.
    for number, key, benchmark in ((8, 'shots', 20.0), (9, 'sot', 8.0), (12, 'inside', 12.0)):
        hv, av = both(key)
        if hv is None or av is None:
            continue
        per90_h, per90_a = hv * 90.0 / max(minute, 1), av * 90.0 / max(minute, 1)
        scores = (_score(per90_h, benchmark), _score(per90_a, benchmark)) if valid_minute else None
        fill(number, h=hv, a=av, scores=scores,
             note=(f'HECHO: acumulado. Índice E = 1 + 9 × min(1, (dato/tiempo×90)/{benchmark:g}); no es referencia de liga.'
                   if scores else 'Dato real acumulado; <20 minutos impide extrapolar la tasa a 90.'),
             source=f'API-Football: {FIELDS[key][0]}')

    hs, as_ = both('shots')
    ht, at = both('sot')
    if all(v is not None for v in (hs, as_, ht, at)) and hs and as_:
        ratio_h, ratio_a = min(100.0, ht / hs * 100.0), min(100.0, at / as_ * 100.0)
        scores = (_score(ratio_h, 100), _score(ratio_a, 100)) if min(hs, as_) >= 3 else None
        fill(10, h=ratio_h, a=ratio_a, scores=scores,
             note='Remates a puerta / remates totales. Índice E en escala lineal; no mide xG.',
             source='API-Football: Shots on Goal / Total Shots')

    # Conversion is an observed proportion, never an asserted innate skill.
    gh, ga = _numeric(match.get('home_score')), _numeric(match.get('away_score'))
    if all(v is not None for v in (hs, as_, gh, ga)) and hs and as_:
        cvh, cva = gh / hs * 100.0, ga / as_ * 100.0
        scores = (_score(cvh, 50), _score(cva, 50)) if minute >= 35 and min(hs, as_) >= 5 else None
        fill(11, h=cvh, a=cva, scores=scores,
             note='Conversión goles/remates (%) en ESTE partido; índice E descriptivo, muestra pequeña.',
             source='API-Football: score + Total Shots')

    # Shots within the box can be an explicit *proxy* for area pressure.
    ih, ia = both('inside')
    if ih is not None and ia is not None:
        scores = (_score(ih * 90 / minute, 12), _score(ia * 90 / minute, 12)) if valid_minute else None
        fill(13, h=ih, a=ia, scores=scores,
             note='PROXY: tiros dentro del área (NO toques, entradas ni recuperaciones). Índice E por 90.',
             source='API-Football: Shots insidebox')

    xh, xa = both('xg')
    if xh is not None and xa is not None:
        scores = (_score(xh * 90 / minute, 2.6), _score(xa * 90 / minute, 2.6)) if valid_minute else None
        fill(21, h=xh, a=xa, scores=scores,
             note='xG REAL acumulado (si el proveedor lo publicó); índice E xG/90 (benchmark 2.6), no convierte xG en tiros.',
             source='API-Football: expected_goals')

    # High press, recoveries, wing progressions and fatigue require true
    # location/sequence data. Do NOT fake these from cumulative shots/possession.
    eligible = [r for r in rows if isinstance(r['score_home'], (int, float)) and isinstance(r['score_away'], (int, float))]
    sh = round(sum(r['score_home'] for r in eligible), 1)
    sa = round(sum(r['score_away'] for r in eligible), 1)
    mini = [dict(rows[i-1]) for i in MINI_IDS]
    mini_valid = [r for r in mini if r['score_home'] is not None and r['score_away'] is not None]
    evidence_count = len(eligible)
    if evidence_count < 2:
        verdict = 'DATOS INSUFICIENTES'
    else:
        difference = (sh - sa) / evidence_count
        verdict = 'EQUILIBRADO' if abs(difference) < 0.5 else 'VENTAJA LOCAL' if difference > 0 else 'VENTAJA VISITANTE'
    ranked = sorted(eligible, key=lambda r: abs(r['difference']), reverse=True)
    return {
        'version': 'TACTICAL_SCANNER23_V3_3', 'count': 23,
        'score_kind': 'EXPERIMENTAL_DESCRIPTIVE_NOT_PROBABILITY',
        'evaluated_both': evidence_count, 'maximum_evaluated': evidence_count * 10,
        'score_home_total': sh, 'score_away_total': sa,
        'historical_comparison': 'ND: se calcula solamente cuando exista un perfil previo verificable',
        'verdict': verdict, 'reliability': 'BAJA' if evidence_count < 6 else 'MEDIA',
        'criteria': rows, 'mini_factors': mini,
        'mini_evaluated': len(mini_valid),
        'mini_home_average': round(sum(r['score_home'] for r in mini_valid)/len(mini_valid), 1) if mini_valid else None,
        'mini_away_average': round(sum(r['score_away'] for r in mini_valid)/len(mini_valid), 1) if mini_valid else None,
        'top_differences': ranked[:5],
        'time_windows': [
            {'minutes': w, 'available': bool((match.get(f'window_{w}') or {}).get('available')),
             'note': 'Evento acumulado del partido, sin atribución de equipo' if (match.get(f'window_{w}') or {}).get('available') else 'ND'}
            for w in (5, 10, 15)
        ],
        'disclaimer': 'R=hecho observado; E=índice derivado de datos reales con rúbrica experimental; ND=sin datos. Los índices NO son probabilidades ni notas oficiales.',
    }
