# Deploy JHONNY ELITE 20 en Render

## Backend Web Service

Runtime: Python 3

Build:

```text
pip install -r requirements.txt
```

Start:

```text
gunicorn -w 1 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:$PORT --timeout 120
```

Variables mínimas:

```text
API_FOOTBALL_KEY=<privada>
FOOTBALL_DATA_KEY=<privada si se usa>
ODDS_API_KEY=<privada si se usa>
WORKER_ENABLED=true
WORKER_SINGLE_PROCESS_ONLY=true
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
CORS_ORIGINS=https://TU-PANEL.onrender.com
JHONNY_DEBUG_API_RAW=0
```

Para historial persistente agrega un Persistent Disk y configura, por ejemplo:

```text
JHONNY_DATA_DIR=/var/data/jhonny
```

## Panel Static Site

Build:

```text
npm install && npm run build
```

Publish directory:

```text
dist
```

Variables:

```text
VITE_API_URL=https://TU-BACKEND.onrender.com
VITE_DASHBOARD_POLL_MS=15000
```

`VITE_API_URL` no debe terminar en `/v17` porque el cliente ya añade ese prefijo.

## Comprobación

1. `/ready` -> `ok: true`, versión 20.0.
2. `/v17/health` -> `active: true`, `status: OK`.
3. `/v17/live` -> `count` refleja partidos elegibles live.
4. `/v17/dashboard` -> `version: JHONNY_ELITE_20.0`.
5. Panel -> indicador `LIVE` y sin `Failed to fetch`.

## Free instance

Si la instancia se duerme por inactividad, el worker también se detiene. Para un scanner continuo necesitas una instancia que permanezca activa.
