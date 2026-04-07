from app.engines.tactical_engine import TacticalEngine
from app.engines.value_engine import ValueEngine
from app.engines.risk_engine import RiskEngine
from app.engines.market_engine import MarketEngine
from app.config.config import Config

class ScanService:
    def __init__(self):
        self.market_engine = MarketEngine()

    def escanear_partidos(self, live_matches, odds_data):
        candidatas = []

        for match in live_matches:
            try:
                market = match.get("market", "OVER_MATCH_DYNAMIC")

                tactica = TacticalEngine.analizar_momentum(match)
                predictor = TacticalEngine.predictor_gol_inminente(match)
                riesgo = RiskEngine.evaluar_riesgo(match, market)
                mercado = self.market_engine.validar_mercado(match, odds_data)

                if mercado.get("valid"):
                    enriched_match = {**match, **tactica, **predictor}
                    valor = ValueEngine.calcular_edge(enriched_match, mercado["cuota"])
                else:
                    valor = {
                        "status": "LOW_VALUE",
                        "edge": 0,
                        "value_category": "SIN_VALOR",
                        "prob_real": match.get("prob_real", 0.5),
                        "prob_implicita": 0
                    }

                confidence = match.get("confidence", 0)
                minuto = match.get("minute", 0)
                shots_on_target = match.get("shots_on_target", 0)
                dangerous_attacks = match.get("dangerous_attacks", 0)
                edge = valor.get("edge", 0)
                mercado_valido = mercado.get("valid", False)

                # 1. BLOQUEOS DUROS
                if riesgo.get("is_blocked", False):
                    continue

                if tactica.get("match_state") in ["MUERTO", "CAOS PELIGROSO"]:
                    continue

                if confidence < 60:
                    continue

                # 2. VENTANAS OPERATIVAS FLEXIBLES
                en_ventana = (
                    (25 <= minuto <= 45)
                    or (60 <= minuto <= 75)
                    or (15 <= minuto <= 24 and tactica.get("match_state") in ["CALIENTE", "EXPLOSIVO"])
                    or (76 <= minuto <= 85 and riesgo.get("risk_score", 0) <= 4)
                )

                if not en_ventana:
                    continue

                # 3. VALUE MÍNIMO FLEXIBLE
                if edge < 0.01:
                    continue

                # 4. CONSENSO FLEXIBLE
                consenso = 0

                if tactica.get("match_state") in ["CONTROLADO", "CALIENTE", "EXPLOSIVO"]:
                    consenso += 1

                if predictor.get("gol_inminente"):
                    consenso += 1

                if edge >= 0.05:
                    consenso += 1

                if mercado_valido:
                    consenso += 1

                if riesgo.get("risk_score", 99) <= 5:
                    consenso += 1

                if consenso < 2:
                    continue

                # 5. SCORE FINAL
                signal_score = self._calcular_signal_score(
                    confidence=confidence,
                    edge=edge,
                    risk_score=riesgo.get("risk_score", 0),
                    match_state=tactica.get("match_state"),
                    gol_inminente=predictor.get("gol_inminente", False),
                    consenso=consenso,
                    mercado_valido=mercado_valido,
                    shots_on_target=shots_on_target,
                    dangerous_attacks=dangerous_attacks
                )

                # 6. SCORE MÍNIMO PARA COMPETIR EN EL TOP
                if signal_score < 55:
                    continue

                signal_rank = self._clasificar_signal_rank(signal_score)

                match_data = match.copy()
                match_data.update({
                    "market": market,
                    "selection": match.get("selection", "Over"),
                    "line": match.get("line", "Auto"),
                    "risk_score": riesgo.get("risk_score", 0),
                    "cuota": mercado.get("cuota", 1.80),
                    "recomendacion_final": signal_rank,
                    "signal_score": signal_score,
                    "signal_rank": signal_rank,
                    "publish_ready": True,
                    "reason": (
                        f"Consenso {consenso}/5 | "
                        f"Estado {tactica.get('match_state')} | "
                        f"Edge {round(edge, 4)} | "
                        f"Riesgo {riesgo.get('risk_score', 0)}"
                    )
                })

                motores_data = {
                    "tactica": tactica,
                    "predictor": predictor,
                    "riesgo": riesgo,
                    "mercado": mercado,
                    "value": valor
                }

                candidatas.append({
                    "match": match_data,
                    "motores": motores_data
                })

            except Exception as e:
                print(f"ERROR en escanear_partidos: {e}")
                continue

        # Ordenar de la más fuerte a la más débil
        candidatas.sort(
            key=lambda x: x["match"].get("signal_score", 0),
            reverse=True
        )

        # Máximo 6 señales
        return candidatas[:6]

    def _calcular_signal_score(
        self,
        confidence,
        edge,
        risk_score,
        match_state,
        gol_inminente,
        consenso,
        mercado_valido,
        shots_on_target,
        dangerous_attacks
    ):
        score = 0

        # Confianza: hasta 30 puntos
        score += min(max(confidence, 0), 100) * 0.30

        # Edge: hasta 20 puntos
        if edge >= 0.15:
            score += 20
        elif edge >= 0.10:
            score += 16
        elif edge >= 0.05:
            score += 12
        elif edge >= 0.02:
            score += 8
        elif edge >= 0.01:
            score += 4

        # Estado táctico: hasta 15 puntos
        if match_state == "EXPLOSIVO":
            score += 15
        elif match_state == "CALIENTE":
            score += 12
        elif match_state == "CONTROLADO":
            score += 7

        # Gol inminente: hasta 8 puntos
        if gol_inminente:
            score += 8

        # Consenso: hasta 10 puntos
        score += consenso * 2

        # Mercado válido: bono o castigo
        if mercado_valido:
            score += 7
        else:
            score -= 5

        # Remates a puerta
        if shots_on_target >= 3:
            score += 5
        elif shots_on_target >= 1:
            score += 2

        # Ataques peligrosos
        if dangerous_attacks >= 25:
            score += 5
        elif dangerous_attacks >= 15:
            score += 2

        # Riesgo: castigo
        score -= min(risk_score * 2, 15)

        return round(max(score, 0), 2)

    def _clasificar_signal_rank(self, signal_score):
        if signal_score >= 88:
            return "PREMIUM"
        elif signal_score >= 78:
            return "FUERTE"
        elif signal_score >= 70:
            return "BUENA"
        else:
            return "ACEPTABLE"
