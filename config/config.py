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

    # =========================
    # 🏆 LIGAS / COMPETICIONES PERMITIDAS
    # =========================
    API_FOOTBALL_ALLOWED_LEAGUES = [
        # =====================================================
        # 🌍 FIFA / SELECCIONES / MUNDIAL
        # =====================================================
        1,     # FIFA World Cup
        26,    # World Cup Qualification
        15,    # FIFA Club World Cup
        5,     # UEFA Nations League
        4,     # Euro Championship
        6,     # Africa Cup of Nations
        7,     # Copa América
        17,    # AFC Asian Cup
        31,    # CONCACAF Gold Cup

        # =====================================================
        # 🌍 UEFA / EUROPA CLUBES
        # =====================================================
        2,     # UEFA Champions League
        3,     # UEFA Europa League
        848,   # UEFA Conference League

        # =====================================================
        # 🌎 CONMEBOL CLUBES
        # =====================================================
        13,    # Copa Libertadores
        11,    # Copa Sudamericana

        # =====================================================
        # 🇬🇧 INGLATERRA
        # =====================================================
        39,    # Premier League
        40,    # Championship

        # =====================================================
        # 🇪🇸 ESPAÑA
        # =====================================================
        140,   # La Liga
        141,   # Segunda División

        # =====================================================
        # 🇮🇹 ITALIA
        # =====================================================
        135,   # Serie A
        136,   # Serie B

        # =====================================================
        # 🇩🇪 ALEMANIA
        # =====================================================
        78,    # Bundesliga
        79,    # 2. Bundesliga

        # =====================================================
        # 🇫🇷 FRANCIA
        # =====================================================
        61,    # Ligue 1
        62,    # Ligue 2

        # =====================================================
        # 🇵🇹 PORTUGAL
        # =====================================================
        94,    # Primeira Liga

        # =====================================================
        # 🇳🇱 / 🇧🇪 / EUROPA MEDIA
        # =====================================================
        88,    # Eredivisie
        144,   # Belgium Pro League
        119,   # Denmark Superliga
        113,   # Sweden Allsvenskan
        103,   # Norway Eliteserien
        207,   # Switzerland Super League
        218,   # Austria Bundesliga
        179,   # Scotland Premiership
        203,   # Turkey Super Lig
        286,   # Serbia SuperLiga
        235,   # Russia Premier League

        # =====================================================
        # 🇧🇷 BRASIL
        # =====================================================
        71,    # Brazil Serie A
        72,    # Brazil Serie B

        # =====================================================
        # 🇦🇷 ARGENTINA
        # =====================================================
        128,   # Liga Profesional
        129,   # Primera Nacional

        # =====================================================
        # 🌎 SUDAMÉRICA
        # =====================================================
        239,   # Colombia Primera A
        265,   # Chile Primera División
        281,   # Perú Liga 1
        242,   # Uruguay Primera División
        250,   # Paraguay División Profesional
        240,   # Ecuador LigaPro

        # OJO: verificar ID real de Bolivia en tu API.
        # Antes estaba 218, pero 218 normalmente corresponde a Austria.
        # Mantengo Bolivia fuera hasta confirmar el ID correcto.

        # =====================================================
        # 🌎 CONCACAF
        # =====================================================
        262,   # MLS
        263,   # USL Championship
        253,   # Liga MX
        254,   # Expansión MX
        162,   # Costa Rica Primera División
        165,   # Honduras Liga Nacional
        266,   # Guatemala Liga Nacional
        479,   # Canadian Premier League

        # =====================================================
        # 🌍 EXTRA
        # =====================================================
        307,   # Saudi Pro League
    ]

    # IDs internacionales que nunca deberían bloquearse por lista cerrada.
    FORCE_ALLOW_INTERNATIONAL_LEAGUE_IDS = [
        1, 26, 15, 5, 4, 6, 7, 17, 31
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
    SCAN_INTERVAL_SECONDS = int(os.getenv("SCAN_INTERVAL_SECONDS", 30))
    LIVE_BASE_CACHE_TTL_SECONDS = max(15, int(os.getenv("LIVE_BASE_CACHE_TTL_SECONDS", 15)))
    POST_GOAL_RESCAN_SECONDS = max(15, int(os.getenv("POST_GOAL_RESCAN_SECONDS", 15)))
    WORKER_ENABLED = os.getenv("WORKER_ENABLED", "true").lower() == "true"
    WORKER_SINGLE_PROCESS_ONLY = os.getenv("WORKER_SINGLE_PROCESS_ONLY", "true").lower() == "true"
    GLOBAL_SENIOR_SCOPE = os.getenv("GLOBAL_SENIOR_SCOPE", "true").lower() == "true"

    # Escaneo live profundo por lotes. API-Football soporta hasta 20 ids por petición.
    LIVE_DETAILS_BATCH_SIZE = max(1, min(20, int(os.getenv("LIVE_DETAILS_BATCH_SIZE", 20))))
    LIVE_DETAILS_MAX_MATCHES = max(20, int(os.getenv("LIVE_DETAILS_MAX_MATCHES", 200)))
    LIVE_DETAILS_CACHE_TTL_SECONDS = max(15, int(os.getenv("LIVE_DETAILS_CACHE_TTL_SECONDS", 15)))

    # Protocolo JHONNY ELITE: OVER puede aparecer en cualquier tramo si la evidencia
    # madura; UNDER se publica tarde por defecto.
    UNDER_MINUTE_MIN = int(os.getenv("UNDER_MINUTE_MIN", 75))
    CANDIDATE_PREMATCH_MIN_CONFIDENCE = float(os.getenv("CANDIDATE_PREMATCH_MIN_CONFIDENCE", 58.0))
    PUBLISH_MIN_CONFIDENCE = float(os.getenv("PUBLISH_MIN_CONFIDENCE", 68.0))
    STRONG_SIGNAL_CONFIDENCE = float(os.getenv("STRONG_SIGNAL_CONFIDENCE", 82.0))
    PREMIUM_SIGNAL_CONFIDENCE = float(os.getenv("PREMIUM_SIGNAL_CONFIDENCE", 88.0))

    # Las cuotas enriquecen solo candidatos para ahorrar cuota y latencia.
    CANDIDATE_ODDS_ENABLED = os.getenv("CANDIDATE_ODDS_ENABLED", "true").lower() == "true"
    VALUE_REQUIRED_FOR_PREMIUM = os.getenv("VALUE_REQUIRED_FOR_PREMIUM", "true").lower() == "true"

    # Seguridad / panel. Separar múltiples orígenes con coma.
    CORS_ORIGINS = [
        x.strip() for x in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",") if x.strip()
    ]

    # Persistencia local del tracker/caches. En hosts efímeros se debe montar
    # DATA_DIR sobre disco persistente. DATABASE_URL queda reservado para una
    # migración futura y no se utiliza como backend del tracker en esta versión.
    DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
    DATA_DIR = os.getenv("JHONNY_DATA_DIR", "app/v17/storage").strip()

    # =========================
    # 🧪 DEBUG
    # =========================
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    API_FOOTBALL_DEBUG_RAW = os.getenv("JHONNY_DEBUG_API_RAW", "0").lower() in {"1", "true", "yes", "on"}
    API_FOOTBALL_DEBUG_RAW_DIR = os.getenv("JHONNY_DEBUG_API_RAW_DIR", "debug_api_football")

    @classmethod
    def validate(cls):
        warnings = []

        if not cls.API_FOOTBALL_KEY:
            warnings.append("⚠️ API_FOOTBALL_KEY no configurada")

        if not cls.FOOTBALL_DATA_KEY:
            warnings.append("⚠️ FOOTBALL_DATA_KEY no configurada")

        if not cls.ODDS_API_KEY:
            warnings.append("⚠️ ODDS_API_KEY no configurada")

        if 1 not in cls.API_FOOTBALL_ALLOWED_LEAGUES:
            warnings.append("⚠️ FIFA World Cup no está en API_FOOTBALL_ALLOWED_LEAGUES")

        for w in warnings:
            print(w)

        return warnings
