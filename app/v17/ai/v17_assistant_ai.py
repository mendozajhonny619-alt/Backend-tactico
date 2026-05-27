from __future__ import annotations

import os
from typing import Any, Dict, List, Optional


def safe_text(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback

    text = str(value).strip()
    return text if text else fallback


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


def normalize_text(value: Any) -> str:
    return str(value or "").strip().upper()


class V17AssistantAI:
    """
    Asistente conversacional interno de JHONNY ELITE V17.

    Esta primera versión:
    - Lee el snapshot del dashboard V17.
    - Resume señales top, candidatos, observaciones, bloqueados y no bet.
    - Responde preguntas del usuario sobre el sistema.
    - No inventa datos externos.
    - Si no hay OPENAI_API_KEY, responde con una lógica local básica.
    """

    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.model = os.getenv("OPENAI_MODEL", "gpt-5.5").strip()
        self.deep_model = os.getenv("OPENAI_DEEP_MODEL", self.model).strip()

    def answer(
        self,
        question: str,
        dashboard_snapshot: Optional[Dict[str, Any]] = None,
        selected_match: Optional[Dict[str, Any]] = None,
        mode: str = "quick",
        conversation: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        clean_question = safe_text(question)

        if not clean_question:
            return {
                "ok": False,
                "mode": mode,
                "answer": "Necesito que escribas una pregunta para poder analizar el sistema V17.",
                "model": None,
                "used_openai": False,
                "context_summary": {},
            }

        snapshot = dashboard_snapshot if isinstance(dashboard_snapshot, dict) else {}
        match = selected_match if isinstance(selected_match, dict) else None
        context_summary = self._build_context_summary(snapshot=snapshot, selected_match=match)

        if not self.api_key:
            return {
                "ok": True,
                "mode": mode,
                "answer": self._local_answer(question=clean_question, context=context_summary),
                "model": "LOCAL_FALLBACK",
                "used_openai": False,
                "context_summary": context_summary,
            }

        try:
            answer = self._ask_openai(
                question=clean_question,
                context_summary=context_summary,
                mode=mode,
                conversation=conversation or [],
            )

            return {
                "ok": True,
                "mode": mode,
                "answer": answer,
                "model": self._select_model(mode),
                "used_openai": True,
                "context_summary": context_summary,
            }

        except Exception as exc:
            return {
                "ok": True,
                "mode": mode,
                "answer": (
                    "No pude conectar con la IA externa en este momento. "
                    "Te doy una lectura local básica del sistema V17:\n\n"
                    + self._local_answer(question=clean_question, context=context_summary)
                ),
                "model": "LOCAL_FALLBACK_AFTER_ERROR",
                "used_openai": False,
                "error": str(exc),
                "context_summary": context_summary,
            }

    def _select_model(self, mode: str) -> str:
        selected_mode = normalize_text(mode)

        if selected_mode in {"DEEP", "ANALYSIS", "AUDIT", "PROFUNDO", "AUDITORIA"}:
            return self.deep_model

        return self.model

    def _ask_openai(
        self,
        question: str,
        context_summary: Dict[str, Any],
        mode: str,
        conversation: List[Dict[str, Any]],
    ) -> str:
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key)
        model = self._select_model(mode)

        system_prompt = self._system_prompt(mode)
        user_prompt = self._user_prompt(
            question=question,
            context_summary=context_summary,
            conversation=conversation,
        )

        response = client.responses.create(
            model=model,
            input=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
        )

        output_text = getattr(response, "output_text", None)
        if output_text:
            return str(output_text).strip()

        try:
            texts: List[str] = []
            for item in getattr(response, "output", []) or []:
                for content in getattr(item, "content", []) or []:
                    text = getattr(content, "text", None)
                    if text:
                        texts.append(str(text))
            if texts:
                return "\n".join(texts).strip()
        except Exception:
            pass

        return "La IA respondió, pero no pude extraer el texto de salida."

    def _system_prompt(self, mode: str) -> str:
        return """
Eres JHONNY ELITE ASSISTANT V17, un analista deportivo conversacional conectado al sistema JHONNY ELITE V17.

Tu trabajo es explicar el panel, interpretar señales, comparar partidos y ayudar al usuario a entender qué está viendo el sistema.

Reglas obligatorias:
- No inventes datos que no estén en el contexto.
- No prometas ganancias ni aciertos seguros.
- No digas "apuesta sí o sí".
- Usa lenguaje claro, directo y técnico.
- Diferencia entre señal lista, candidato fuerte, observación, no bet y bloqueo.
- Si falta información, dilo claramente.
- Si una señal está bloqueada por reloj, datos viejos o riesgo extremo, no la recomiendes.
- Si una señal es candidato fuerte pero entry_window es WAIT, aclara que todavía no es entrada directa.
- Siempre explica la razón futbolística y la razón operativa.
- Prioriza seguridad lógica sobre emoción del mercado.
- Responde en español.
- No uses párrafos demasiado largos.
"""

    def _user_prompt(
        self,
        question: str,
        context_summary: Dict[str, Any],
        conversation: List[Dict[str, Any]],
    ) -> str:
        short_conversation = conversation[-6:] if isinstance(conversation, list) else []

        return f"""
Pregunta del usuario:
{question}

Resumen actual del sistema V17:
{context_summary}

Conversación reciente:
{short_conversation}

Responde como analista interno de JHONNY ELITE V17.
"""

    def _build_context_summary(
        self,
        snapshot: Dict[str, Any],
        selected_match: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        top_signals = self._summarize_items(snapshot.get("top_signals", []), limit=6)
        observe = self._summarize_items(snapshot.get("observe", []), limit=8)
        no_bet = self._summarize_items(snapshot.get("no_bet", []), limit=5)
        blocked = self._summarize_items(snapshot.get("blocked", []), limit=8)
        all_analyzed = self._summarize_items(snapshot.get("all_analyzed", []), limit=10)

        summary = snapshot.get("summary", {}) if isinstance(snapshot.get("summary"), dict) else {}

        context = {
            "system_version": snapshot.get("version", "V17"),
            "updated_at": snapshot.get("updated_at"),
            "message": snapshot.get("message"),
            "summary": summary,
            "counts": {
                "top_signals": len(snapshot.get("top_signals", []) or []),
                "observe": len(snapshot.get("observe", []) or []),
                "no_bet": len(snapshot.get("no_bet", []) or []),
                "blocked": len(snapshot.get("blocked", []) or []),
                "all_analyzed": len(snapshot.get("all_analyzed", []) or []),
            },
            "top_signals": top_signals,
            "observe": observe,
            "no_bet": no_bet,
            "blocked": blocked,
            "all_analyzed_sample": all_analyzed,
        }

        if selected_match:
            context["selected_match"] = self._summarize_match(selected_match)

        return context

    def _summarize_items(self, items: Any, limit: int = 6) -> List[Dict[str, Any]]:
        if not isinstance(items, list):
            return []

        return [self._summarize_match(item) for item in items[:limit] if isinstance(item, dict)]

    def _summarize_match(self, item: Dict[str, Any]) -> Dict[str, Any]:
        home = safe_text(item.get("home_team"), "Local")
        away = safe_text(item.get("away_team"), "Visitante")

        return {
            "match_id": item.get("match_id") or item.get("fixture_id"),
            "match": f"{home} vs {away}",
            "league": item.get("league"),
            "country": item.get("country"),
            "minute": item.get("api_minute") or item.get("display_minute") or item.get("estimated_minute"),
            "score": item.get("current_score") or item.get("scoreline"),
            "panel_label": item.get("panel_label"),
            "panel_section": item.get("panel_section"),
            "panel_market": item.get("panel_market"),
            "market": item.get("market") or item.get("suggested_market") or item.get("master_market"),
            "master_status": item.get("master_status"),
            "master_action": item.get("master_action"),
            "master_rank": item.get("master_rank"),
            "entry_window": item.get("entry_window"),
            "entry_timing_label": item.get("entry_timing_label"),
            "entry_permission": item.get("entry_permission"),
            "entry_reason": item.get("entry_reason"),
            "clock_status": item.get("clock_status"),
            "clock_action": item.get("clock_action"),
            "data_age_seconds": item.get("data_age_seconds"),
            "clock_frozen": item.get("clock_frozen"),
            "data_quality": item.get("data_quality"),
            "risk_status": item.get("risk_status"),
            "risk_score": item.get("risk_score"),
            "over_score": item.get("over_score"),
            "under_score": item.get("under_score"),
            "football_game_phase": item.get("football_game_phase"),
            "football_game_state": item.get("football_game_state"),
            "football_dominant_reading": item.get("football_dominant_reading"),
            "football_alternative_reading": item.get("football_alternative_reading"),
            "football_confidence": item.get("football_confidence"),
            "football_story": item.get("football_story"),
            "football_pressure_type": item.get("football_pressure_type"),
            "over_candidate_level": item.get("over_candidate_level"),
            "over_candidate_active": item.get("over_candidate_active"),
            "over_support_ratio": item.get("over_support_ratio"),
            "candidate_level": item.get("candidate_level"),
            "majority_support": item.get("majority_support"),
            "support_ratio": item.get("support_ratio"),
            "why_selected": item.get("why_selected"),
            "what_is_missing": item.get("what_is_missing"),
            "hard_blockers": item.get("hard_blockers", []),
            "soft_warnings": item.get("soft_warnings", []),
            "logic_warnings": item.get("logic_warnings", []),
        }

    def _local_answer(self, question: str, context: Dict[str, Any]) -> str:
        counts = context.get("counts", {}) if isinstance(context.get("counts"), dict) else {}

        top_count = safe_int(counts.get("top_signals"), 0)
        observe_count = safe_int(counts.get("observe"), 0)
        blocked_count = safe_int(counts.get("blocked"), 0)
        no_bet_count = safe_int(counts.get("no_bet"), 0)

        top_signals = context.get("top_signals", []) or []
        observe = context.get("observe", []) or []
        blocked = context.get("blocked", []) or []
        selected = context.get("selected_match")

        if selected:
            return self._local_match_answer(selected)

        if top_count > 0:
            best = top_signals[0]
            return (
                f"Ahora mismo el sistema tiene {top_count} señal(es) TOP. "
                f"La primera lectura destacada es {best.get('match')} con mercado "
                f"{best.get('panel_market') or best.get('market')} y estado "
                f"{best.get('entry_timing_label') or best.get('entry_window')}. "
                f"Antes de considerarla, revisa reloj {best.get('clock_status')} y riesgo {best.get('risk_status')}."
            )

        if observe_count > 0:
            candidate = observe[0]
            return (
                f"No hay señales TOP, pero sí hay {observe_count} partido(s) en observación. "
                f"El candidato más visible es {candidate.get('match')}. "
                f"Lectura dominante: {candidate.get('football_dominant_reading') or candidate.get('market')}. "
                f"Estado: {candidate.get('entry_timing_label') or candidate.get('entry_window')}. "
                f"Esto significa que todavía necesita confirmación antes de considerarse entrada."
            )

        if blocked_count > 0:
            item = blocked[0]
            return (
                f"No hay señales operables. Hay {blocked_count} partido(s) bloqueado(s). "
                f"Ejemplo: {item.get('match')} está bloqueado por {item.get('hard_blockers') or item.get('clock_status')}. "
                f"Cuando el sistema bloquea por reloj, datos viejos o riesgo extremo, no conviene forzar lectura."
            )

        if no_bet_count > 0:
            return (
                f"El sistema tiene {no_bet_count} partido(s) como NO BET. "
                "Eso indica que no encontró ventaja suficiente o que la lectura futbolística todavía es débil."
            )

        return (
            "El sistema no muestra señales claras en este momento. "
            "La recomendación local es esperar nuevos escaneos y no forzar entradas."
        )

    def _local_match_answer(self, match: Dict[str, Any]) -> str:
        name = match.get("match", "el partido")
        dominant = match.get("football_dominant_reading") or match.get("market") or "OBSERVE"
        entry = match.get("entry_timing_label") or match.get("entry_window") or "ESPERAR"
        clock = match.get("clock_status") or "SIN_RELOJ"
        risk = match.get("risk_status") or "SIN_RIESGO"
        reason = match.get("entry_reason") or match.get("what_is_missing") or match.get("football_story")

        return (
            f"Para {name}, la lectura dominante es {dominant}. "
            f"El control de entrada indica: {entry}. "
            f"Reloj: {clock}. Riesgo: {risk}. "
            f"Razón principal: {reason or 'el sistema aún necesita más confirmación'}."
      )
