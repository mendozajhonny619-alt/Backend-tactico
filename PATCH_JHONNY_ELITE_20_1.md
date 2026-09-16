# JHONNY ELITE 20.1 — PATCH PRECISION + ODDS + HISTORY

Este ZIP NO es el sistema completo. Contiene únicamente los archivos modificados respecto a JHONNY ELITE 20.
Copie/reemplace respetando exactamente la misma estructura de carpetas.

## 1. UNDER objetivo 75'

- Preanalisis UNDER desde minuto 68 para que prepartido/cuota ya esten disponibles antes de la decision.
- Entrada tecnica permitida desde 72 solo si toda la evidencia es excepcional.
- Ventana objetivo: 75–79.
- Desde 80: penalizacion de entrada tardia y exigencia PREMIUM.
- Desde 84: no se crea una nueva señal UNDER.
- El paso del tiempo por si solo NO aumenta la confianza.
- El modelo matematico 20.1 pondera la actividad reciente 5/10/15 min para distinguir un partido que realmente se enfrio de uno que solo parece Under por el acumulado.

## 2. Cuota real obligatoria

Cadena de proveedores para candidatos:

1. API-Football `/odds/live?fixture=...`
2. API-Football `/odds?fixture=...`
3. The Odds API (ODDS_API_KEY), solo como fallback de la liga compatible y con cache.
4. Cuota ya adjunta al match, si es real.

No se fabrica una cuota. Sin mercado real -> NO_BET / OBSERVATION.

Publicacion exige por defecto:

- Cuota 1.50–2.10
- Edge >= 5 puntos porcentuales
- EV >= 0.03
- DataTruth >= 72
- OVER math support >= 72
- UNDER math support >= 70
- Riesgo <= 45
- Prepartido disponible
- UNDER: consenso interno 5/5
- Confianza OVER >= 88
- Confianza UNDER >= 90

## 3. Historial oficial persistente

Los resultados oficiales se guardan en `official_results_archive.json` y, si `DATABASE_URL` apunta a PostgreSQL, tambien se guardan en una tabla durable.

Corte diario:

- Zona horaria: America/La_Paz
- Los resultados del dia siguen como HOY hasta 23:30.
- A partir de 23:30 pasan a AYER.
- El panel agrupa: HOY, AYER, HACE_N_DIAS, HACE_1_SEMANA, HACE_2_SEMANAS y fechas anteriores.
- Retencion por defecto: 365 dias / 5000 resultados oficiales.

IMPORTANTE EN RENDER:
Si el servicio usa filesystem efimero, configure `DATABASE_URL` de PostgreSQL o monte `JHONNY_DATA_DIR` sobre almacenamiento persistente. Sin una de esas dos opciones, ningun archivo JSON puede garantizar supervivencia ante un redeploy/reinicio del host.

## 4. Variables recomendadas en Render

```
UNDER_PREP_MINUTE=68
UNDER_MINUTE_MIN=72
UNDER_PREFERRED_MINUTE=75
UNDER_TARGET_WINDOW_END=79
UNDER_LATE_ENTRY_MINUTE=80
UNDER_HARD_CUTOFF_MINUTE=84
UNDER_CANDIDATE_MIN_CONFIDENCE=66
UNDER_ODDS_PREFETCH_MIN_SCORE=66

PUBLISH_MIN_CONFIDENCE=88
OVER_PUBLISH_MIN_CONFIDENCE=88
UNDER_PUBLISH_MIN_CONFIDENCE=90
STRONG_SIGNAL_CONFIDENCE=92
PREMIUM_SIGNAL_CONFIDENCE=95

CANDIDATE_ODDS_ENABLED=true
ODDS_MIN_CANDIDATE_SCORE=76
ODDS_CACHE_TTL_SECONDS=300
THE_ODDS_FALLBACK_ENABLED=true
THE_ODDS_REGION=eu

EDGE_MIN_PERCENT=5
MIN_EXPECTED_VALUE=0.03
MIN_DATA_TRUTH_SCORE=72
MAX_SIGNAL_RISK_SCORE=45
MIN_MATH_SUPPORT_OVER=72
MIN_MATH_SUPPORT_UNDER=70
REQUIRE_PREMATCH_FOR_OFFICIAL=true

RESULTS_TIMEZONE=America/La_Paz
RESULTS_CUTOFF_HOUR=23
RESULTS_CUTOFF_MINUTE=30
RESULTS_RETENTION_DAYS=365
OFFICIAL_RESULTS_LIMIT=5000
```

Mantenga sus claves existentes:

- API_FOOTBALL_KEY
- ODDS_API_KEY
- FOOTBALL_DATA_KEY (si la usa)

Para persistencia durable entre deploys, configure ademas:

```
DATABASE_URL=<PostgreSQL URL>
```

o use un `JHONNY_DATA_DIR` montado en almacenamiento persistente.

## 5. Panel

- ACIERTOS/FALLOS principales muestran el dia operativo actual.
- Esos contadores permanecen hasta 23:30 Bolivia.
- Historial muestra resultados anteriores agrupados por dia/semana.
- Cada resultado conserva marcador de entrada, marcador final/actual, mercado, linea y cuota cuando existen.
- Detalle muestra tambien fuente/proveedor de la cuota.

## 6. Precision

Este parche prioriza selectividad:

- sube umbrales de publicacion;
- exige mercado real y EV positivo;
- UNDER usa consenso 5/5;
- exige DataTruth, prematch y soporte matematico;
- penaliza riesgo y entradas tardias;
- usa hazard reciente 5/10/15, no solo estadisticas acumuladas.

Esto busca reducir falsos positivos. No constituye garantia de acierto: la precision real debe medirse con las señales oficiales guardadas.

## 7. Validacion local

- pytest: 28/28
- compileall: OK
- imports `app`: 52 modulos, 0 errores
