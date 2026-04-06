import os

class Config:
    API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY", "").strip()
    THE_ODDS_API_KEY = os.getenv("THE_ODDS_API_KEY", "").strip()

    CUOTA_MINIMA = 1.50
    CUOTA_MAXIMA = 2.10

    CONFIANZA_MINIMA = 75.0
    EDGE_MINIMO = 0.05

    VENTANAS_PRIORITARIAS = [(25, 45), (60, 75)]

    SHADOW_MODE = False
