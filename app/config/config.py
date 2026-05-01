import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """
    Configuración central del sistema.
    Toda variable sensible o ajustable debe vivir aquí.
    """

    # =========================
    # 🔑 API KEYS
    # =========================
    API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY", "").strip()
    FOOTBALL_DATA_KEY = os.getenv("FOOTBALL_DATA_KEY", "").strip()
    ODDS_API_KEY = os.getenv("ODDS_API_KEY", "").strip()
    API_FOOTBALL_ALLOWED_LEAGUES = [
    # 🌍 EUROPA TOP - Primera división
    39,   # Premier League
    140,  # La Liga
    135,  # Serie A
    78,   # Bundesliga
    61,   # Ligue 1

    # 🌍 EUROPA - Segunda división fuerte
    40,   # England Championship
    141,  # Spain Segunda División
    136,  # Italy Serie B
    79,   # Germany 2. Bundesliga
    62,   # France Ligue 2

    # 🌍 EUROPA - Ligas primera división recomendadas
    94,   # Portugal Primeira Liga
    88,   # Netherlands Eredivisie
    203,  # Turkey Super Lig
    119,  # Denmark Superliga
    113,  # Sweden Allsvenskan
    103,  # Norway Eliteserien
    144,  # Belgium Pro League
    179,  # Scotland Premiership
    235,  # Russia Premier League
    207,  # Switzerland Super League
    218,  # Austria Bundesliga
    286,  # Serbia SuperLiga

    # 🌍 UEFA / Europa competiciones fuertes
    2,    # UEFA Champions League
    3,    # UEFA Europa League
    848,  # UEFA Conference League
    4,    # Euro Championship

    # 🌎 CONMEBOL - Torneos fuertes
    13,   # Copa Libertadores
    11,   # Copa Sudamericana

    # 🌎 CONMEBOL - Primera y segunda confiables
    71,   # Brazil Serie A
    72,   # Brazil Serie B
    128,  # Argentina Liga Profesional
    129,  # Argentina Primera Nacional
    239,  # Colombia Primera A
    265,  # Chile Primera División
    281,  # Peru Liga 1

    # 🌐 CONCACAF - Principales
    262,  # MLS
    253,  # Liga MX

    # 🌍 EXTRA primera división útil
    307,  # Saudi Pro League
]
    # =========================
    # 💰 MERCADO
    # =========================
    CUOTA_MINIMA = float(os.getenv("CUOTA_MINIMA", 1.50))
    CUOTA_MAXIMA = float(os.getenv("CUOTA_MAXIMA", 2.10))
    EDGE_MINIMO = float(os.getenv("EDGE_MINIMO", 0.05))

    # =========================
    # 🎯 CONFIANZA / FILTROS
    # =========================
    CONFIANZA_MINIMA = float(os.getenv("CONFIANZA_MINIMA", 75.0))

    # =========================
    # ⏱️ VENTANAS
    # =========================
    VENTANAS_PRIORITARIAS = [
        (25, 45),
        (60, 75),
    ]

    # =========================
    # ⚙️ SISTEMA
    # =========================
    SHADOW_MODE = os.getenv("SHADOW_MODE", "false").lower() == "true"
    SCAN_INTERVAL_SECONDS = int(os.getenv("SCAN_INTERVAL_SECONDS", 15))

    # =========================
    # 🧪 DEBUG
    # =========================
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"

    @classmethod
    def validate(cls):
        """
        Verifica configuración crítica al iniciar.
        """
        warnings = []

        if not cls.API_FOOTBALL_KEY:
            warnings.append("⚠️ API_FOOTBALL_KEY no configurada")

        if not cls.FOOTBALL_DATA_KEY:
            warnings.append("⚠️ FOOTBALL_DATA_KEY no configurada")

        if not cls.ODDS_API_KEY:
            warnings.append("⚠️ ODDS_API_KEY no configurada")

        for w in warnings:
            print(w)

        return warnings
