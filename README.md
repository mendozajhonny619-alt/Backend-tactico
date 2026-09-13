# JHONNY ELITE 19

Sistema de inteligencia de fútbol en vivo orientado a **descubrir oportunidades selectivas**, reforzarlas con información prepartido solo cuando existe un candidato real y seguir cada señal hasta su resolución.

> **Importante:** JHONNY ELITE no promete resultados garantizados. El fútbol es estocástico. El objetivo del sistema es ser selectivo, calibrar probabilidades, reducir falsos positivos, medir el rendimiento real y abstenerse cuando la ventaja no es suficiente.

## Protocolo operativo

```text
TODOS LOS PARTIDOS LIVE ELEGIBLES
            |
            v
  normalización + reloj + calidad
            |
            v
 contexto + táctica + riesgo + dinámica reciente
            |
            v
       ¿hay candidato?
          /      \
        no        sí
        |          |
        v          v
 seguir live   PREPARTIDO SOLO AQUÍ
                   + últimos partidos
                   + local/visitante
                   + estadísticas de temporada
                   + H2H
                   + tabla/contexto
                   + predicción del proveedor
                   + cuota live/valor si existe
                   |
                   v
            hazard + Poisson
                   |
                   v
             MASTER DECISION
            /      |       \
         ENTER  OBSERVE   NO_BET
            |
            v
      TRACKER WIN/LOSS/VOID
```

### OVER
- Puede aparecer en cualquier minuto si la lectura live ya tiene suficiente evidencia.
- Usa ritmo, presión, volumen ofensivo, tiros, tiros al arco, ataques peligrosos, xG cuando existe, necesidad de gol, riesgo, cambios recientes entre escaneos y modelo matemático.
- Si pasa la puerta de candidato, recién entonces se consulta el prepartido y las cuotas.
- Después de un gol, el marcador crea una nueva época de señal y el partido puede generar otra oportunidad sin duplicar la anterior.

### UNDER
- Se habilita para publicación desde `UNDER_MINUTE_MIN` (75 por defecto).
- Busca conservación del marcador, caída de ritmo, transición al cierre y baja amenaza restante.
- Si la ventana reciente se abre o aumenta la inestabilidad, el UNDER pierde fuerza aunque los acumulados históricos parezcan favorables.
- El resultado principal se calcula probabilísticamente; resultados alternativos solo aparecen cuando la inestabilidad lo justifica.

## Lectura dinámica entre escaneos

`app/jhonny_elite/live_dynamics.py` guarda una memoria corta por fixture y compara el escaneo actual con el anterior. Calcula:

- cambios recientes de tiros y tiros al arco;
- cambios de ataques peligrosos y córners;
- cambio de xG cuando el proveedor lo entrega;
- amenaza reciente total y por equipo;
- equipo que está empujando;
- tendencia `RISING/HIGH/STABLE/FALLING/LOW`;
- estado `OPENING/OPEN/BALANCED/CLOSING/CLOSED`;
- inestabilidad dinámica;
- reanálisis post-gol.

Esto evita confundir un partido que acumuló actividad hace 30 minutos con uno que **se está abriendo ahora**.

## Prepartido bajo demanda

El sistema **no descarga prepartido de todos los partidos**. Solo se activa al superar el umbral de candidato live. El paquete puede incluir, según cobertura del proveedor:

- últimos 5 de ambos equipos;
- últimos 5 del local como local y del visitante como visitante;
- H2H reciente;
- goles a favor/en contra;
- clean sheets / partidos sin marcar;
- estadísticas de temporada;
- clasificación/contexto de tabla;
- predicción del proveedor;
- perfil reciente de la competición.

Si falta una fuente no crítica, la señal no muere automáticamente: la ausencia se trata como neutral y baja la calidad de evidencia disponible. Los bloqueos duros siguen siendo datos inválidos, reloj no confiable u otros riesgos críticos.

## Alcance de competiciones

Con `GLOBAL_SENIOR_SCOPE=true`, JHONNY ELITE admite competiciones senior profesionales y aplica un filtro para excluir categorías conocidas como juveniles, reservas, femenino, regionales, amateur y divisiones inferiores conocidas. Las principales primeras/segundas divisiones y torneos internacionales tienen clasificación explícita.

La cobertura real siempre depende de los partidos y estadísticas que entregue tu plan/proveedor de datos. Ningún software puede analizar una competición que la API no exponga o para la que no entregue estadísticas live suficientes.

## Panel visual

El frontend React/Vite está en `src/v17`, pero la interfaz se presenta como **JHONNY ELITE 19**. Está diseñada para escritorio y celular:

- barra superior fija;
- navegación inferior móvil tipo app deportiva;
- tarjetas horizontales de partidos live en móvil;
- señales OVER/UNDER con confianza, riesgo, cuota/valor y probabilidades;
- lectura dinámica del partido (`Abriéndose`, `Cerrándose`, etc.);
- amenaza reciente y equipo que empuja;
- resultado principal y alternativos;
- prepartido validado/no disponible;
- historial de señales y precisión observada.

## Instalación del backend

Recomendado: Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate       # Linux/macOS
# .venv\Scripts\activate       # Windows
pip install -r requirements.txt
cp .env.example .env
```

Configura como mínimo:

```env
API_FOOTBALL_KEY=tu_clave_nueva
```

Luego:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Rutas principales:

- `GET /ready`
- `GET /v17/health`
- `GET /v17/dashboard`
- `GET /v17/live`
- `GET /v17/signals`
- `GET /v17/history`
- `GET /v17/opportunities`
- `GET /v17/blocked`
- `GET /v17/stats`
- `POST /v17/chat`

Las rutas `/v17/*` se mantienen por compatibilidad con el panel existente; el motor que las alimenta es JHONNY ELITE 19.

## Instalación del frontend

Vite 8 requiere Node.js 20.19+ (o una rama 22.12+ equivalente). Si el proveedor de despliegue usa una versión antigua, fija/actualiza la versión de Node antes del build.

```bash
npm install
```

Crea `.env.local`:

```env
VITE_API_URL=http://127.0.0.1:8000
VITE_DASHBOARD_POLL_MS=15000
```

Ejecuta:

```bash
npm run dev
```

Producción:

```bash
npm run build
```

El resultado queda en `dist/`.

## Variables importantes

| Variable | Predeterminado | Función |
|---|---:|---|
| `WORKER_ENABLED` | `true` | Activa el scanner live |
| `SCAN_INTERVAL_SECONDS` | `30` | Intervalo normal; el worker fuerza mínimo 15 s |
| `POST_GOAL_RESCAN_SECONDS` | `15` | Próximo ciclo acelerado tras detectar cambio de marcador |
| `LIVE_DETAILS_BATCH_SIZE` | `20` | Fixtures por consulta de detalle |
| `LIVE_DETAILS_MAX_MATCHES` | `200` | Máximo de fixtures live detallados por ciclo |
| `GLOBAL_SENIOR_SCOPE` | `true` | Alcance global senior con exclusiones |
| `UNDER_MINUTE_MIN` | `75` | Inicio de ventana UNDER publicable |
| `CANDIDATE_PREMATCH_MIN_CONFIDENCE` | `58` | Puerta para enriquecer con prepartido/cuota |
| `PUBLISH_MIN_CONFIDENCE` | `68` | Umbral base de publicación |
| `STRONG_SIGNAL_CONFIDENCE` | `82` | Umbral FUERTE |
| `PREMIUM_SIGNAL_CONFIDENCE` | `88` | Umbral superior |
| `CANDIDATE_ODDS_ENABLED` | `true` | Consulta cuota solo para candidatos |
| `JHONNY_DATA_DIR` | `app/v17/storage` | Estado/historial local |
| `JHONNY_DEBUG_API_RAW` | `0` | Dumps raw; mantener apagado en producción |
| `CORS_ORIGINS` | localhost | Orígenes web permitidos |

## Persistencia

El tracker y caches locales usan `JHONNY_DATA_DIR`. En un servidor efímero, usa un **disco persistente** y apunta esa variable al punto de montaje, por ejemplo:

```env
JHONNY_DATA_DIR=/var/data/jhonny
```

`DATABASE_URL` queda reservado para una migración futura a PostgreSQL; esta entrega **no afirma** tener el tracker migrado a PostgreSQL.

## Render / Git

Se incluye `render.yaml` con dos servicios en el mismo repositorio:

1. API FastAPI/Gunicorn.
2. Panel Vite como sitio estático.

En Render debes introducir manualmente las claves marcadas `sync: false`. Para que el escaneo sea realmente continuo, utiliza un tipo de servicio que permanezca activo; si el proveedor/plataforma duerme la instancia, el worker también deja de escanear durante ese tiempo.

Si deseas conservar historial entre redeploys/reinicios, añade un disco persistente al backend y configura `JHONNY_DATA_DIR` a su mount path.

## Pruebas

```bash
pip install -r requirements-dev.txt
pytest -q
python -m compileall -q app main.py worker.py
```

La suite incluida cubre, entre otros:

- prepartido solo después de candidato;
- OVER fuerte activa enriquecimiento;
- UNDER no publicable antes del minuto 75;
- reentrada tras gol;
- resolución OVER/UNDER;
- cierre de una señal cuando el fixture pasa a FT;
- push asiático entero como `VOID`;
- rutas de dashboard montadas;
- detección de apertura reciente entre snapshots.

## Seguridad

El ZIP original auditado contenía claves reales en un archivo `. env`. Esas claves **no están incluidas en esta versión**. Debes **revocar/rotar las claves originales** y usar únicamente variables de entorno nuevas.

Nunca subas `.env` a Git. El repositorio contiene `.env.example` sin secretos y `.gitignore` protege los archivos reales.

## Estructura clave

```text
app/
  jhonny_elite/
    engine.py                 # flujo operativo único
    live_dynamics.py          # memoria/dinámica entre escaneos
  fetchers/
    live_match_fetcher.py     # live + detalle por lotes + cierre FT
  v17/
    ai/
      advanced_probability_engine.py
      pre_match_profile_ai.py
      risk_ai.py
      tactical_ai.py
      market_ai.py
    services/
      pre_match_data_service.py
      candidate_odds_service.py
      prediction_feature_builder.py
    signals/
      result_resolver.py
      signal_tracker.py
    dashboard/
      dashboard_adapter.py
src/v17/                       # panel responsive JHONNY ELITE 19
main.py
worker.py
tests/
```

## Principio de diseño

La métrica importante no es “mostrar muchas apuestas”. Es mantener un registro honesto de:

- señales publicadas;
- aciertos/fallos/voids;
- precisión por mercado y competición;
- disponibilidad de cuotas;
- valor estimado cuando existe cuota;
- condiciones en las que el modelo funciona o falla.

Eso permite ajustar los umbrales con evidencia real en lugar de forzar una supuesta precisión antes de tener suficiente historial.
