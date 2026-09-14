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
    SCAN_INTERVAL_SECONDS = int(os.getenv("SCAN_INTERVAL_SECONDS", 30))
    LIVE_BASE_CACHE_TTL_SECONDS = max(30, int(os.getenv("LIVE_BASE_CACHE_TTL_SECONDS", 60)))
    POST_GOAL_RESCAN_SECONDS = max(15, int(os.getenv("POST_GOAL_RESCAN_SECONDS", 15)))
    WORKER_ENABLED = os.getenv("WORKER_ENABLED", "true").lower() == "true"
    WORKER_SINGLE_PROCESS_ONLY = os.getenv("WORKER_SINGLE_PROCESS_ONLY", "true").lower() == "true"
    GLOBAL_SENIOR_SCOPE = os.getenv("GLOBAL_SENIOR_SCOPE", "false").lower() == "true"
    STRICT_COMPETITION_SCOPE = os.getenv("STRICT_COMPETITION_SCOPE", "true").lower() == "true"
    ENFORCE_ALLOWED_LEAGUE_IDS = os.getenv("ENFORCE_ALLOWED_LEAGUE_IDS", "false").lower() == "true"
    API_ECONOMY_MODE = os.getenv("API_ECONOMY_MODE", "true").lower() == "true"
    API_DAILY_RESERVE = max(0, int(os.getenv("API_DAILY_RESERVE", 300)))
    API_THROTTLE_USED_PERCENT = float(os.getenv("API_THROTTLE_USED_PERCENT", 82.0))
    API_CRITICAL_USED_PERCENT = float(os.getenv("API_CRITICAL_USED_PERCENT", 92.0))

    # Escaneo live profundo por lotes. API-Football soporta hasta 20 ids por petición.
    LIVE_DETAILS_BATCH_SIZE = max(1, min(20, int(os.getenv("LIVE_DETAILS_BATCH_SIZE", 20))))
    LIVE_DETAILS_MAX_MATCHES = max(20, int(os.getenv("LIVE_DETAILS_MAX_MATCHES", 40)))
    LIVE_DETAILS_CACHE_TTL_SECONDS = max(60, int(os.getenv("LIVE_DETAILS_CACHE_TTL_SECONDS", 120)))
    LIVE_FALLBACK_DEEP_MATCHES = max(0, int(os.getenv("LIVE_FALLBACK_DEEP_MATCHES", 2)))
    LIVE_PLAYER_STATS_ENABLED = os.getenv("LIVE_PLAYER_STATS_ENABLED", "false").lower() == "true"

    # Protocolo JHONNY ELITE: OVER puede aparecer en cualquier tramo si la evidencia
    # madura; UNDER se publica tarde por defecto.
    UNDER_MINUTE_MIN = int(os.getenv("UNDER_MINUTE_MIN", 60))
    UNDER_PREFERRED_MINUTE = int(os.getenv("UNDER_PREFERRED_MINUTE", 65))
    CANDIDATE_PREMATCH_MIN_CONFIDENCE = float(os.getenv("CANDIDATE_PREMATCH_MIN_CONFIDENCE", 72.0))
    PUBLISH_MIN_CONFIDENCE = float(os.getenv("PUBLISH_MIN_CONFIDENCE", 82.0))
    STRONG_SIGNAL_CONFIDENCE = float(os.getenv("STRONG_SIGNAL_CONFIDENCE", 89.0))
    PREMIUM_SIGNAL_CONFIDENCE = float(os.getenv("PREMIUM_SIGNAL_CONFIDENCE", 94.0))

    # Las cuotas enriquecen solo candidatos para ahorrar cuota y latencia.
    CANDIDATE_ODDS_ENABLED = os.getenv("CANDIDATE_ODDS_ENABLED", "true").lower() == "true"
    VALUE_REQUIRED_FOR_PREMIUM = os.getenv("VALUE_REQUIRED_FOR_PREMIUM", "true").lower() == "true"
    MAX_PREMATCH_ENRICHMENTS_PER_CYCLE = max(1, int(os.getenv("MAX_PREMATCH_ENRICHMENTS_PER_CYCLE", 1)))
    MAX_PUBLISHED_SIGNALS_PER_CYCLE = max(1, min(6, int(os.getenv("MAX_PUBLISHED_SIGNALS_PER_CYCLE", 6))))
    ODDS_CACHE_TTL_SECONDS = max(60, int(os.getenv("ODDS_CACHE_TTL_SECONDS", 180)))
    ODDS_MIN_CANDIDATE_SCORE = float(os.getenv("ODDS_MIN_CANDIDATE_SCORE", 78.0))
    PREMATCH_ECONOMY_MODE = os.getenv("PREMATCH_ECONOMY_MODE", "true").lower() == "true"
    PREMATCH_MAX_NEW_PACKAGES_PER_HOUR = max(1, int(os.getenv("PREMATCH_MAX_NEW_PACKAGES_PER_HOUR", 8)))
    PREMATCH_PROVIDER_PREDICTION_ENABLED = os.getenv("PREMATCH_PROVIDER_PREDICTION_ENABLED", "false").lower() == "true"
    PREMATCH_LEAGUE_SAMPLE_ENABLED = os.getenv("PREMATCH_LEAGUE_SAMPLE_ENABLED", "false").lower() == "true"

    # =========================
    # 🧠 MASTER PROTOCOL 20
    # =========================
    MASTER_PROTOCOL_ENABLED = os.getenv("MASTER_PROTOCOL_ENABLED", "true").lower() == "true"
    MASTER_MIN_CONSENSUS = max(4, min(5, int(os.getenv("MASTER_MIN_CONSENSUS", 4))))
    OBSERVATION_MIN_SCORE = float(os.getenv("OBSERVATION_MIN_SCORE", 45.0))
    EDGE_MIN_PERCENT = float(os.getenv("EDGE_MIN_PERCENT", 4.0))
    MAX_LIVE_DATA_AGE_SECONDS = max(30, int(os.getenv("MAX_LIVE_DATA_AGE_SECONDS", 150)))
    MAX_ODDS_AGE_SECONDS = max(30, int(os.getenv("MAX_ODDS_AGE_SECONDS", 180)))
    PUBLISH_MIN_CONFIDENCE = float(os.getenv("PUBLISH_MIN_CONFIDENCE", 84.0))
    SHADOW_MODE = os.getenv("SHADOW_MODE", "false").lower() == "true"
    SIGNAL_MAX_SIMULTANEOUS = max(1, min(6, int(os.getenv("SIGNAL_MAX_SIMULTANEOUS", 6))))
    REENTRY_COOLDOWN_SECONDS = max(60, int(os.getenv("REENTRY_COOLDOWN_SECONDS", 300)))
    SIGNAL_REVIEW_5_MIN = max(1, int(os.getenv("SIGNAL_REVIEW_5_MIN", 5)))
    SIGNAL_REVIEW_10_MIN = max(5, int(os.getenv("SIGNAL_REVIEW_10_MIN", 10)))
    SIGNAL_REVIEW_15_MIN = max(10, int(os.getenv("SIGNAL_REVIEW_15_MIN", 15)))
    SIGNAL_REVIEW_20_MIN = max(15, int(os.getenv("SIGNAL_REVIEW_20_MIN", 20)))
    BANKROLL_STAKE_MIN_PCT = float(os.getenv("BANKROLL_STAKE_MIN_PCT", 1.0))
    BANKROLL_STAKE_MAX_PCT = float(os.getenv("BANKROLL_STAKE_MAX_PCT", 3.0))
    BANKROLL_PREMIUM_MAX_PCT = float(os.getenv("BANKROLL_PREMIUM_MAX_PCT", 5.0))
    BANKROLL_DAILY_LIMIT_PCT = float(os.getenv("BANKROLL_DAILY_LIMIT_PCT", 10.0))

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
