import os

# CONFIGURACIÓN MAESTRA JHONNY_ELITE V16
class Config:
    # Credenciales (Asegúrate de tener estas variables de entorno o cámbialas aquí)
    API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY", "TU_KEY_AQUI")
    THE_ODDS_API_KEY = os.getenv("THE_ODDS_API_KEY", "TU_KEY_AQUI")
    
    # Rango Operativo de Cuotas (Regla #14)
    CUOTA_MINIMA = 1.50
    CUOTA_MAXIMA = 2.10
    
    # Umbrales de Confianza (Regla #3)
    CONFIANZA_MINIMA = 75.0 # Porcentaje
    EDGE_MINIMO = 0.05      # 5% de ventaja matemática
    
    # Ventanas de Operación (Regla #13)
    VENTANAS_PRIORITARIAS = [(25, 45), (60, 75)]
    
    # Modo de Operación
    SHADOW_MODE = False  # Regla #23
