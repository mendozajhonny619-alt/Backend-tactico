from app.engines.tactical_engine import TacticalEngine
from app.engines.value_engine import ValueEngine
from app.engines.risk_engine import RiskEngine
from app.engines.market_engine import MarketEngine
from app.config.config import Config

class ScanService:
    def __init__(self):
        self.market_engine = MarketEngine()

    def escanear_partidos(self, live_matches, odds_data):
        senales_detectadas = []

        for match in live_matches:
            try:
                tactica = TacticalEngine.analizar_momentum(match)
                riesgo = RiskEngine.evaluar_riesgo(
                    match,
                    match.get("market", "OVER_MATCH_DYNAMIC")
                )
                mercado = self.market_engine.validar_mercado(match, odds_data)

                if mercado.get("valid"):
                    enriched_match = {**match, **tactica}
                    valor = ValueEngine.calcular_edge(enriched_match, mercado["cuota"])
                else:
                    valor = {
                        "status": "LOW_VALUE",
                        "edge": 0,
                        "value_category": "SIN_VALOR"
                    }

                confidence = match.get("confidence", 0)

                if (
                    not riesgo.get("is_blocked", True)
                    and mercado.get("valid", False)
                    and confidence >= Config.CONFIANZA_MINIMA
                    and valor.get("status") == "OK"
                ):
                    match_data = match.copy()
                    match_data.update({
                        "market": match.get("market", "OVER_MATCH_DYNAMIC"),
                        "selection": match.get("selection", "Over"),
                        "line": match.get("line", "Auto"),
                        "risk_score": riesgo.get("risk_score", 0),
                        "cuota": mercado.get("cuota"),
                        "recomendacion_final": (
                            "PREMIUM" if valor.get("edge", 0) > 0.15 else "ESTÁNDAR"
                        )
                    })

                    motores_data = {
                        "tactica": tactica,
                        "riesgo": riesgo,
                        "mercado": mercado,
                        "value": valor
                    }

                    senales_detectadas.append({
                        "match": match_data,
                        "motores": motores_data
                    })

            except Exception as e:
                print(f"ERROR en escanear_partidos: {e}")
                continue

        return senales_detectadas
