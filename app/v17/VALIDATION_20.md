# Validación — JHONNY ELITE 20

Fecha de construcción: 2026-09-13

## Validaciones ejecutadas

- `pytest -q`: **22 passed**.
- `python -m compileall -q app main.py worker.py`: OK.
- Importación programática: **132 módulos, 0 errores**.
- FastAPI TestClient: `/`, `/ready`, `/v17/health`, `/v17/dashboard`, `/v17/live`, `/v17/signals`, `/v17/history`, `/v17/stats` -> HTTP 200.
- `/v17/dashboard` reporta `JHONNY_ELITE_20.0`.
- TypeScript compiler usado como parser de JSX/JS (`--noEmit`): OK.
- Búsqueda local de asignaciones de claves API incrustadas: sin hallazgos; `.env.example` contiene placeholders.

## Suite V20 añadida

- DataTruth bloquea evidencia live vacía.
- Memoria temporal publica ventanas 5/10/15.
- Master exige línea, cuota y value.
- Master confirma con consenso >=4/5 cuando el resto de guardias pasa.
- Contradicción crítica bloquea publicación.
- Identidad de señal = match + market + line.
- Métricas Brier / Log Loss / Calibration Error.

## Limitaciones declaradas

- API-Football es la fuente live integrada actualmente.
- `FlashscoreProvider` es un contrato de adaptación para una fuente autorizada; no incluye scraping ni credenciales.
- No se ejecutó `npm run build` porque `npm install` agotó el tiempo de red disponible durante esta sesión. La sintaxis JSX/JS sí fue validada con `tsc --noEmit`.
- La precisión real no se garantiza desde el código; debe medirse con picks oficiales resueltos.
- El tracker sigue usando persistencia de archivo local. Para Render, configura un disco persistente mediante `JHONNY_DATA_DIR` si quieres conservar historial entre reinicios.
