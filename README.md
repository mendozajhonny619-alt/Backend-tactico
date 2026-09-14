# JHONNY ELITE 20 — MASTER PROTOCOL + ECONOMY

Plataforma de inteligencia futbolística live construida alrededor de una regla central: **publicar menos, justificar mejor y medir todo**.

> JHONNY ELITE no garantiza resultados. El sistema estima probabilidades y valor bajo incertidumbre; `NO_BET` es una decisión válida.

## Arquitectura operativa

```text
LIVE -> NORMALIZE/FUSION -> CLOCK -> DATATRUTH
     -> MEMORY 5/10/15 -> TACTICAL/CONTEXT/MOMENTUM
     -> CANDIDATE -> PREMATCH + ODDS
     -> MATH HT/FT/5/10/15 -> CONTRADICTIONS -> CONSENSUS 4/5
     -> MASTER DECISION AI -> TRACK -> SETTLEMENT -> PERFORMANCE
```

`MasterDecisionAI20` es la **única autoridad final** para los campos `official_*`. React no recalcula decisiones.

El protocolo detallado está en [`MASTER_PROTOCOL_20.md`](MASTER_PROTOCOL_20.md).

## Qué cambia en V20

- DataTruth anti-datos-vacíos: ausencia de estadísticas no equivale a UNDER.
- Memoria temporal real de 5/10/15 min.
- Modelo matemático con horizontes HT, FT y gol en próximos 5/10/15 min.
- Línea, cuota, edge y EV obligatorios para publicación O/U.
- Consenso mínimo 4 de 5 capas.
- Contradiction Judge explícito con bloqueos críticos.
- Máximo 6 picks activos simultáneos.
- Identidad `match + market + line` y `signal_id` UUID por publicación.
- Shadow Mode separado de producción.
- ROI con cuotas reales y métricas Brier/Log Loss/Calibration Error.
- Segmentación por liga, mercado, línea, minuto, riesgo y calidad.
- Panel V20 muestra DataTruth, consenso, EV, horizontes 5/10/15 y memoria temporal.
- Economy conserva filtros top-2/copa, lotes, caché y enriquecimiento solo tras candidato.

## Worker

El ciclo normal es `30s` y el post-gol puede reanalizar a `15s`.

El frontend puede refrescar a 15–30 s, pero **no sustituye** al worker del backend.

## Alcance

Por defecto: primeras y segundas divisiones senior + competiciones prioritarias (UEFA, Libertadores, Sudamericana, CONCACAF, Copa América y copas nacionales configuradas). Se excluyen juveniles, reservas, amateur, regionales y divisiones inferiores.

La cobertura exacta depende del proveedor y de las competiciones disponibles en la cuenta API.

## Multifuente

Se incluye el contrato normalizado y Data Fusion para API-Football, Flashscore, prepartido y odds. API-Football es la fuente activa incluida. Flashscore es un **adaptador opcional**, no un scraper integrado.

## Instalación backend

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --host 0.0.0.0 --port 8000
```

Configura al menos `API_FOOTBALL_KEY`. Para publicar picks con value también necesitas cobertura de cuotas válida.

Rutas:

- `/ready`
- `/v17/health`
- `/v17/dashboard`
- `/v17/live`
- `/v17/signals`
- `/v17/history`
- `/v17/opportunities`
- `/v17/blocked`
- `/v17/stats`
- `/v17/match/{fixture_id}`

## Frontend

```bash
npm install
npm run build
```

Variables:

```env
VITE_API_URL=http://127.0.0.1:8000
VITE_DASHBOARD_POLL_MS=15000
```

## Variables recomendadas de producción

```env
WORKER_ENABLED=true
MASTER_PROTOCOL_ENABLED=true
SCAN_INTERVAL_SECONDS=30
POST_GOAL_RESCAN_SECONDS=15
API_ECONOMY_MODE=true
STRICT_COMPETITION_SCOPE=true
GLOBAL_SENIOR_SCOPE=false
UNDER_MINUTE_MIN=60
UNDER_PREFERRED_MINUTE=65
PUBLISH_MIN_CONFIDENCE=84
MASTER_MIN_CONSENSUS=4
SIGNAL_MAX_SIMULTANEOUS=6
MAX_PREMATCH_ENRICHMENTS_PER_CYCLE=1
PREMATCH_MAX_NEW_PACKAGES_PER_HOUR=8
ODDS_MIN_CANDIDATE_SCORE=78
SHADOW_MODE=false
```

Consulta `.env.example` para la configuración completa.

## Economy

El worker sigue su ciclo de decisión de 30 s. El ahorro proviene de **no profundizar todo**:

1. descubre live;
2. filtra competiciones;
3. reutiliza cache y detalle por lotes;
4. puntúa localmente;
5. solo candidatos consumen prepartido;
6. solo candidatos avanzados consultan cuota;
7. el panel lee memoria y no consume API-Football al abrir un detalle.

## Historial y performance

Solo los picks realmente publicados se registran como oficiales. Observaciones, candidatos, NO_BET y bloqueados pueden analizarse por separado, pero no inflan el hit rate.

El tracker calcula hit rate, ROI, cuota/edge/confianza media, Brier, Log Loss y Calibration Error. El ROI no inventa beneficio cuando falta cuota.

## Persistencia

El estado local usa `JHONNY_DATA_DIR`. En Render u otro host efímero monta un disco persistente si deseas conservar historial entre reinicios.

## Pruebas

```bash
pip install -r requirements-dev.txt
pytest -q
python -m compileall -q app main.py worker.py
```

La suite V20 cubre DataTruth, memoria 5/10/15, autoridad Master, cuota/value obligatorios, contradicciones, identidad de señal, calibración, Economy, settlement y endpoints.

## Render

`render.yaml` mantiene un único proceso Python worker/API y un sitio Vite estático. Para escaneo continuo utiliza una instancia que no se suspenda por inactividad.

No subas claves reales a Git. Usa variables privadas en Render.
