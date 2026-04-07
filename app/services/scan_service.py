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

                # 1. BLOQUEOS DUROS
                if riesgo.get("is_blocked", False):
                    continue

                if tactica.get("match_state") in ["MUERTO", "CAOS PELIGROSO"]:
                    continue

                if confidence < 60:
                    continue

                # 2. VENTANAS FLEXIBLES
                en_ventana = (
                    (25 <= minuto <= 45)
                    or (60 <= minuto <= 75)
                    or (15 <= minuto <= 24 and tactica.get("match_state") in ["CALIENTE", "EXPLOSIVO"])
                    or (76 <= minuto <= 85 and riesgo.get("risk_score", 0) <= 4)
                )

                if not en_ventana:
                    continue

                # 3. MERCADO
                # Si hay odds reales válidas, mejor.
                # Si no, permitimos competir a la señal, pero con castigo en score.
                mercado_valido = mercado.get("valid", False)

                # 4. VALUE FLEXIBLE
                edge = valor.get("edge", 0)
                if edge < 0.02:
                    continue

                # 5. CONSENSO FLEXIBLE
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

                if consenso < 3:
                    continue

                # 6. SCORE FINAL
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

                # mínimo flexible para entrar al top
                if signal_score < 62:
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

        # ordenar por score, de más fuerte a más débil
        candidatas.sort(
            key=lambda x: x["match"].get("signal_score", 0),
            reverse=True
        )

        # devolver máximo 6
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

        # confianza: hasta 30
        score += min(max(confidence, 0), 100) * 0.30

        # edge: hasta 20
        if edge >= 0.15:
            score += 20
        elif edge >= 0.10:
            score += 16
        elif edge >= 0.05:
            score += 12
        elif edge >= 0.02:
            score += 8

        # táctica: hasta 15
        if match_state == "EXPLOSIVO":
            score += 15
        elif match_state == "CALIENTE":
            score += 12
        elif match_state == "CONTROLADO":
            score += 7

        # predictor de gol: hasta 8
        if gol_inminente:
            score += 8

        # consenso: hasta 10
        score += consenso * 2

        # mercado: bono pequeño
        if mercado_valido:
            score += 7
        else:
            score -= 5

        # presión real
        if shots_on_target >= 3:
            score += 5
        elif shots_on_target >= 1:
            score += 2

        if dangerous_attacks >= 25:
            score += 5
        elif dangerous_attacks >= 15:
            score += 2

        # riesgo: castigo
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
