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
                tactica = TacticalEngine.analizar_momentum(match)
                predictor = TacticalEngine.predictor_gol_inminente(match)
                riesgo = RiskEngine.evaluar_riesgo(
                    match,
                    match.get("market", "OVER_MATCH_DYNAMIC")
                )
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

                # REGLA 1: ventanas operativas
                minuto = match.get("minute", 0)
                en_ventana = (
                    (25 <= minuto <= 45)
                    or (60 <= minuto <= 75)
                    or (15 <= minuto <= 24 and tactica.get("match_state") in ["CALIENTE", "EXPLOSIVO"])
                    or (76 <= minuto <= 85 and riesgo.get("risk_score", 0) <= 4)
                )

                # REGLA 2: NO BET premium
                if not en_ventana:
                    continue

                # REGLA 3: filtros duros
                if riesgo.get("is_blocked", True):
                    continue

                if not mercado.get("valid", False):
                    continue

                if confidence < Config.CONFIANZA_MINIMA:
                    continue

                if valor.get("status") != "OK":
                    continue

                if tactica.get("match_state") in ["MUERTO", "CAOS PELIGROSO"]:
                    continue

                # REGLA 4: consenso interno simple
                consenso = 0

                if tactica.get("match_state") in ["CALIENTE", "EXPLOSIVO"]:
                    consenso += 1

                if predictor.get("gol_inminente"):
                    consenso += 1

                if valor.get("status") == "OK":
                    consenso += 1

                if mercado.get("valid"):
                    consenso += 1

                if not riesgo.get("is_blocked", True) and riesgo.get("risk_score", 99) <= 6:
                    consenso += 1

                if consenso < 4:
                    continue

                signal_score = self._calcular_signal_score(
                    confidence=confidence,
                    edge=valor.get("edge", 0),
                    risk_score=riesgo.get("risk_score", 0),
                    match_state=tactica.get("match_state"),
                    gol_inminente=predictor.get("gol_inminente", False),
                    consenso=consenso
                )

                # Solo señales buenas de verdad
                if signal_score < 70:
                    continue

                signal_rank = self._clasificar_signal_rank(signal_score)

                match_data = match.copy()
                match_data.update({
                    "market": match.get("market", "OVER_MATCH_DYNAMIC"),
                    "selection": match.get("selection", "Over"),
                    "line": match.get("line", "Auto"),
                    "risk_score": riesgo.get("risk_score", 0),
                    "cuota": mercado.get("cuota"),
                    "recomendacion_final": signal_rank,
                    "signal_score": signal_score,
                    "signal_rank": signal_rank,
                    "publish_ready": True,
                    "reason": f"Consenso {consenso}/5 + {tactica.get('match_state')} + edge {valor.get('edge', 0)}"
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

        # Ordenar de más fuerte a más débil
        candidatas.sort(
            key=lambda x: x["match"].get("signal_score", 0),
            reverse=True
        )

        # Máximo 6 mejores del momento
        return candidatas[:6]

    def _calcular_signal_score(self, confidence, edge, risk_score, match_state, gol_inminente, consenso):
        score = 0

        # confianza: 0-35
        score += min(max(confidence, 0), 100) * 0.35

        # edge: 0-25
        if edge >= 0.15:
            score += 25
        elif edge >= 0.10:
            score += 20
        elif edge >= 0.05:
            score += 15

        # táctica: 0-15
        if match_state == "EXPLOSIVO":
            score += 15
        elif match_state == "CALIENTE":
            score += 10
        elif match_state == "CONTROLADO":
            score += 5

        # gol inminente: 0-10
        if gol_inminente:
            score += 10

        # consenso: 0-10
        score += consenso * 2

        # riesgo: resta hasta 15
        score -= min(risk_score * 2, 15)

        return round(max(score, 0), 2)

    def _clasificar_signal_rank(self, signal_score):
        if signal_score >= 90:
            return "PREMIUM"
        elif signal_score >= 80:
            return "FUERTE"
        else:
            return "NORMAL"
