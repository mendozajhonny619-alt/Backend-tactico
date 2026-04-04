# app/services/scan_service.py
from app.engines.tactical_engine import TacticalEngine
from app.engines.value_engine import ValueEngine
from app.engines.risk_engine import RiskEngine
from app.engines.market_engine import MarketEngine
from app.config.config import Config

class ScanService:
    """
    JHONNY_ELITE V16 - Servicio de Escaneo y Filtrado en Vivo
    Implementa la orquestación total de la cadena de decisión.
    """

    def __init__(self):
        self.market_engine = MarketEngine()

    def escanear_partidos(self, live_matches, odds_data):
        """
        Procesa una lista de partidos y devuelve solo señales válidas (Punto 26).
        """
        senales_detectadas = []

        for match in live_matches:
            # 1. EVALUACIÓN TÁCTICA (M2, M3, M4)
            tactica = TacticalEngine.analizar_momentum(match)
            
            # 2. EVALUACIÓN DE RIESGO (M6, M8)
            riesgo = RiskEngine.evaluar_riesgo(match, match.get('market', 'OVER'))
            
            # 3. VALIDACIÓN DE MERCADO (M9, M10)
            mercado = self.market_engine.validar_mercado(match, odds_data)

            # 4. EVALUACIÓN DE VALOR (M5)
            if mercado['valid']:
                valor = ValueEngine.calcular_edge(match, mercado['cuota'])
            else:
                valor = {"status": "LOW_VALUE", "edge": 0}

            # 5. APLICACIÓN DE LA REGLA #16 (CONSENSO OBLIGATORIO)
            # Solo publicamos si: No está bloqueado + Mercado Válido + Confianza > 75%
            if not riesgo['is_blocked'] and mercado['valid'] and match['confidence'] >= Config.CONFIANZA_MINIMA:
                
                # Armamos el paquete de datos para la señal
                motores_data = {
                    "tactica": tactica,
                    "riesgo": riesgo,
                    "mercado": mercado,
                    "value": valor
                }
                
                # Inyectamos datos de motores al objeto match para el formato final
                match.update({
                    "risk_score": riesgo['risk_score'],
                    "cuota": mercado['cuota'],
                    "recomendacion_final": "PREMIUM" if valor['edge'] > 0.15 else "ESTÁNDAR"
                })

                senales_detectadas.append({
                    "match": match,
                    "motores": motores_data
                })

        return senales_detectadas
