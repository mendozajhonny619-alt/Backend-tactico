from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any, Dict, Iterable, List, Optional, Tuple


class MatchNormalizer:
    """
    Normaliza nombres de equipos y partidos para mejorar matching entre:
    - feed live
    - odds
    - mercados
    - fuentes externas

    Objetivos:
    - quitar ruido textual
    - quitar acentos
    - normalizar alias
    - producir claves comparables
    """

    NOISE_WORDS = {
        "fc", "cf", "sc", "club", "deportivo", "de", "ac", "cd", "sd", "ud",
        "the", "team", "fk", "if", "bk", "jk", "u19", "u20", "u21", "reserves",
        "reserve", "women", "w", "femenino", "feminino", "ladies"
    }

    TEAM_ALIASES = {
        "man utd": "manchester united",
        "man united": "manchester united",
        "man city": "manchester city",
        "psg": "paris saint germain",
        "inter": "internazionale",
        "atleti": "atletico madrid",
        "atletico": "atletico madrid",
        "bayern munich": "bayern",
        "bayern munchen": "bayern",
        "juve": "juventus",
    }

    SEPARATORS_PATTERN = re.compile(r"\s+(vs|v|versus|-)\s+", re.IGNORECASE)
    MULTISPACE_PATTERN = re.compile(r"\s+")
    NON_ALNUM_PATTERN = re.compile(r"[^a-z0-9\s]")

    def normalize_team_name(self, name: Any) -> str:
        if not name:
            return ""

        text = str(name).strip().lower()
        text = self._strip_accents(text)
        text = text.replace("&", " and ")
        text = self.NON_ALNUM_PATTERN.sub(" ", text)
        text = self.MULTISPACE_PATTERN.sub(" ", text).strip()

        # alias directo antes de tokenizar
        text = self.TEAM_ALIASES.get(text, text)

        tokens = [t for t in text.split() if t and t not in self.NOISE_WORDS]

        normalized = " ".join(tokens).strip()

        # alias otra vez por si al limpiar quedó exactamente en alias conocido
        normalized = self.TEAM_ALIASES.get(normalized, normalized)

        return normalized

    def normalize_match_name(self, match_name: Any) -> str:
        if not match_name:
            return ""

        text = str(match_name).strip()
        text = self._strip_accents(text.lower())
        parts = self.SEPARATORS_PATTERN.split(text)

        # Si no se puede dividir claramente, limpiar como bloque
        if len(parts) < 3:
            return self.normalize_team_name(text)

        # split produce [home, sep, away, ...]
        home = self.normalize_team_name(parts[0])
        away = self.normalize_team_name(parts[2])

        ordered = sorted([home, away])
        return " vs ".join(ordered)

    def build_match_key(
        self,
        home_team: Any = None,
        away_team: Any = None,
        match_name: Any = None,
    ) -> str:
        if match_name:
            normalized_match = self.normalize_match_name(match_name)
            if normalized_match:
                return normalized_match

        home = self.normalize_team_name(home_team)
        away = self.normalize_team_name(away_team)

        if not home and not away:
            return ""

        ordered = sorted([home, away])
        return " vs ".join([x for x in ordered if x])

    def similarity(self, a: Any, b: Any) -> float:
        na = self.normalize_team_name(a)
        nb = self.normalize_team_name(b)

        if not na or not nb:
            return 0.0

        if na == nb:
            return 1.0

        return SequenceMatcher(None, na, nb).ratio()

    def match_keys_similarity(self, key_a: Any, key_b: Any) -> float:
        a = str(key_a or "").strip().lower()
        b = str(key_b or "").strip().lower()

        if not a or not b:
            return 0.0

        if a == b:
            return 1.0

        return SequenceMatcher(None, a, b).ratio()

    def find_best_match(
        self,
        target_match: Dict[str, Any],
        candidates: Iterable[Dict[str, Any]],
        threshold: float = 0.82,
    ) -> Optional[Dict[str, Any]]:
        """
        Busca el mejor candidato para un partido objetivo.
        """
        target_key = self.build_match_key(
            home_team=target_match.get("home_name") or target_match.get("home_team"),
            away_team=target_match.get("away_name") or target_match.get("away_team"),
            match_name=target_match.get("match_name"),
        )

        if not target_key:
            return None

        best_candidate = None
        best_score = 0.0

        for candidate in candidates:
            candidate_key = self.build_match_key(
                home_team=candidate.get("home_name") or candidate.get("home_team"),
                away_team=candidate.get("away_name") or candidate.get("away_team"),
                match_name=candidate.get("match_name"),
            )

            score = self.match_keys_similarity(target_key, candidate_key)

            # pequeño boost si país/league coinciden
            score += self._context_boost(target_match, candidate)

            if score > best_score:
                best_score = score
                best_candidate = candidate

        if best_score >= threshold:
            return best_candidate

        return None

    def find_best_match_with_score(
        self,
        target_match: Dict[str, Any],
        candidates: Iterable[Dict[str, Any]],
        threshold: float = 0.82,
    ) -> Tuple[Optional[Dict[str, Any]], float]:
        best = self.find_best_match(target_match=target_match, candidates=candidates, threshold=0.0)
        if not best:
            return None, 0.0

        target_key = self.build_match_key(
            home_team=target_match.get("home_name") or target_match.get("home_team"),
            away_team=target_match.get("away_name") or target_match.get("away_team"),
            match_name=target_match.get("match_name"),
        )
        candidate_key = self.build_match_key(
            home_team=best.get("home_name") or best.get("home_team"),
            away_team=best.get("away_name") or best.get("away_team"),
            match_name=best.get("match_name"),
        )

        score = self.match_keys_similarity(target_key, candidate_key) + self._context_boost(target_match, best)

        if score >= threshold:
            return best, round(min(score, 1.0), 4)

        return None, round(min(score, 1.0), 4)

    def normalize_market_label(self, label: Any) -> str:
        if not label:
            return ""

        text = self._strip_accents(str(label).lower().strip())
        text = self.NON_ALNUM_PATTERN.sub(" ", text)
        text = self.MULTISPACE_PATTERN.sub(" ", text).strip()

        if "over" in text:
            return "OVER"
        if "under" in text:
            return "UNDER"

        return text.upper()

    def normalize_line(self, line: Any) -> Optional[str]:
        if line is None:
            return None

        try:
            value = float(line)
            text = f"{value:.2f}".rstrip("0").rstrip(".")
            return text
        except (TypeError, ValueError):
            text = str(line).strip()
            return text or None

    def _context_boost(self, target: Dict[str, Any], candidate: Dict[str, Any]) -> float:
        boost = 0.0

        target_league = self._norm_meta(target.get("league") or target.get("competition"))
        candidate_league = self._norm_meta(candidate.get("league") or candidate.get("competition"))

        if target_league and candidate_league and target_league == candidate_league:
            boost += 0.03

        target_country = self._norm_meta(target.get("country"))
        candidate_country = self._norm_meta(candidate.get("country"))

        if target_country and candidate_country and target_country == candidate_country:
            boost += 0.02

        return boost

    def _norm_meta(self, value: Any) -> str:
        if not value:
            return ""
        text = self._strip_accents(str(value).lower().strip())
        text = self.NON_ALNUM_PATTERN.sub(" ", text)
        return self.MULTISPACE_PATTERN.sub(" ", text).strip()

    def _strip_accents(self, text: str) -> str:
        return "".join(
            ch for ch in unicodedata.normalize("NFKD", text)
            if not unicodedata.combining(ch)
        )
