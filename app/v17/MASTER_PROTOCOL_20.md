# JHONNY ELITE 20 — MASTER PROTOCOL

Esta versión convierte el protocolo maestro definido por el propietario del sistema en reglas de arquitectura y ejecución.

## Principios inmutables

- **CALIDAD > CANTIDAD**.
- **NO BET > señal dudosa**.
- **VALOR REAL > probabilidad aislada**.
- `MasterDecisionAI20` es la única autoridad que crea campos `official_*`.
- El frontend muestra decisiones; no recalcula confianza, riesgo, prioridad ni señal.
- El ciclo maestro corre cada 30 s; el reescaneo post-gol puede adelantarse a 15 s.
- Máximo 6 señales simultáneas. Nunca se rellenan slots artificialmente.
- Observaciones, candidatos, bloqueos y NO_BET no forman parte del historial oficial de picks.

## Pipeline productivo

```text
LIVE ELIGIBLE
  -> normalización proveedor
  -> DataFusion / conflictos
  -> ClockGuard
  -> DataTruthAI
  -> memoria temporal 5/10/15
  -> contexto + táctica + momentum
  -> candidate scoring
  -> prepartido solo si candidato
  -> cuota/línea solo si candidato avanzado
  -> Poisson/xG/hazard + horizontes HT/FT/5/10/15
  -> ContradictionJudgeMaster
  -> consenso interno 4/5
  -> MasterDecisionAI20
  -> CONFIRMED_SIGNAL / CANDIDATE / OBSERVATION / NO_BET / BLOCKED
  -> tracking + settlement + performance
```

## Contrato oficial

Solo `MasterDecisionAI20` puede producir:

- `official_status`
- `official_market`
- `official_line`
- `official_odds`
- `official_confidence`
- `official_risk`
- `official_can_publish`
- `official_reason`
- `official_predicted_score`
- `official_next_goal_team`
- `official_next_goal_probability`
- `official_no_change_probability`
- `official_value_edge`
- `official_expected_value`
- `official_implied_probability`
- `official_consensus`
- `official_recommended_stake_pct`

## Datos y verdad

`DataTruthAI` evalúa completitud, frescura, consistencia y evidencia interpretable. Un partido con tiros, SOT, ataques peligrosos y xG en cero/no disponibles no se convierte automáticamente en UNDER. Tras los primeros minutos se considera ausencia de evidencia y puede bloquear la publicación.

Estados: `EXCELLENT`, `HIGH`, `MEDIUM`, `LOW`, `INSUFFICIENT`. Los estados críticos bloquean publicación.

## Reloj

`ClockGuard` controla minuto efectivo, timestamp, edad, congelamiento y lag. Datos obsoletos o reloj congelado bloquean entrada. La ausencia de timestamp puede tolerarse solo cuando hay estadísticas live confirmadas y coherentes.

## Memoria temporal

`TemporalMatchMemory` conserva snapshots y publica ventanas:

- `window_5`
- `window_10`
- `window_15`

Cada ventana contiene deltas de tiros, SOT, ataques peligrosos, córners, xG, goles y threat score. El objetivo es detectar aceleración real, cierre, reapertura y cambios de momentum, no depender de acumulados.

## Multifuente

`app/jhonny_elite/data_fusion.py` define el contrato normalizado y adaptadores:

- `ApiFootballProvider`
- `FlashscoreProvider`
- `PrematchProvider`
- `OddsProvider`
- `DataFusionEngine`

API-Football es la fuente activa incluida. Flashscore queda como interfaz opcional para una integración autorizada: esta distribución **no incluye scraping** ni simula datos inexistentes.

DataFusion detecta al menos: `SCORE_CONFLICT`, `CLOCK_CONFLICT`, `STATS_CONFLICT`, `STALE_SOURCE`.

## Predicción matemática

`AdvancedProbabilityEngine` calcula una distribución de marcadores y no solo un resultado puntual. Incluye:

- HT específico.
- FT específico.
- probabilidad de gol próximos 5/10/15 minutos.
- próximo gol total y por equipo.
- score stability/change.
- distribución completa de escenarios para cálculo y Top 10 solo para visualización.

## Mercados productivos

Especialización principal:

- `OVER_MATCH_DYNAMIC`
- `OVER_NEXT_15_DYNAMIC` (la infraestructura temporal ya está disponible; la promoción independiente debe mantenerse estricta)
- `UNDER_MATCH_DYNAMIC`

Toda señal oficial OVER/UNDER exige línea concreta, cuota real, probabilidad implícita, edge positivo y expected value positivo.

Rango preferente de cuota: 1.50–2.10, configurable.

## UNDER

Evaluación seria desde 60+, preferencia 65+. En el primer snapshot el UNDER no puede convertirse en candidato fuerte por simple baja actividad: necesita confirmación temporal. Ritmo acelerado, amenaza alta, contradicción crítica, datos vacíos o línea frágil degradan/bloquean.

## Consenso

Cinco capas:

1. Táctica.
2. Contexto.
3. Gol/ritmo.
4. Value.
5. Mercado.

Publicación requiere 4/5 como mínimo, además de calidad, riesgo y ausencia de contradicción crítica.

## Señales y ciclo de vida

Identidad estable: `match_id + market + line`.

El tracker conserva un `signal_id` UUID por publicación para auditoría histórica. Una señal activa de la misma línea se actualiza en lugar de duplicarse. Tras cerrarse puede existir una nueva publicación si el contexto vuelve a justificarla.

Revisiones de ciclo de vida: 5, 10, 15 y 20 minutos. Señales resueltas salen inmediatamente de pendientes.

Settlement utiliza mercado, línea, marcador de entrada y marcador final. Las líneas enteras permiten `VOID` cuando corresponde.

## Shadow Mode

`SHADOW_MODE=true` permite evaluar/guardar decisiones pero impide que se publiquen como picks oficiales. Los registros se escriben separadamente en `shadow_decisions.jsonl` dentro de `JHONNY_DATA_DIR`.

## Performance y calibración

Nativamente se calculan:

- wins, losses, voids, hit rate.
- ROI solo con cuotas válidas.
- average odds, edge y confidence.
- Brier Score.
- Log Loss.
- Calibration Error.
- segmentación por mercado, liga, línea, riesgo, calidad y rango de minuto.

El aprendizaje productivo debe seguir: historial -> evaluación -> propuesta -> shadow -> comparación -> aprobación -> producción. No se permite modificar reglas productivas automáticamente por un único resultado.

## Economy

El ahorro de créditos no cambia la filosofía de análisis:

- descubrimiento live global dentro del alcance competitivo;
- filtro top-2/copa antes del enriquecimiento profundo;
- detalle por lotes y caché;
- prepartido únicamente tras candidato;
- máximo 1 paquete nuevo prepartido por ciclo y 8/hora por defecto;
- odds solo para candidato avanzado;
- abrir detalles desde el panel usa memoria interna y no dispara una consulta nueva al proveedor.

## Alcance competitivo

Producción prioriza primera/segunda división senior y copas importantes UEFA/CONMEBOL/CONCACAF/nacionales configuradas. Juveniles, reservas, amateur, regionales y divisiones inferiores quedan fuera del alcance por defecto.
