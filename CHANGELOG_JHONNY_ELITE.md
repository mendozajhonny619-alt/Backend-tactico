# CHANGELOG — JHONNY ELITE 20

## 20.0 — Master Protocol

### Autoridad y seguridad lógica
- `MasterDecisionAI20` es la única fuente de campos `official_*`.
- Cuota, línea, edge y EV son obligatorios para señal oficial O/U.
- Consenso mínimo 4/5 antes de publicar.
- Contradicciones críticas bloquean.
- Máximo 6 señales simultáneas.

### Datos
- Nuevo `DataTruthAI` con regla anti-datos-vacíos.
- Nuevo modelo normalizado y `DataFusionEngine` con conflictos explícitos.
- Adaptadores de proveedor para API-Football y contratos opcionales para Flashscore, Prematch y Odds.
- No se incluye scraping de Flashscore.

### Lectura live
- Memoria temporal 5/10/15 min.
- Deltas de tiros, SOT, ataques peligrosos, córners y xG.
- UNDER necesita confirmación temporal; un snapshot pobre no basta.

### Matemática
- Motor 20.0 con horizontes independientes HT, FT, Next 5, Next 10 y Next 15.
- Distribución completa de marcadores conservada para cálculo.
- Probabilidad de estabilidad/cambio de marcador.

### Tracking
- Identidad `match + market + line`.
- `signal_id` UUID por publicación.
- Revisiones lifecycle 5/10/15/20 min.
- Invalidación por colapso crítico de datos/reloj.
- Historial oficial solo de señales publicadas.

### Performance
- ROI con cuotas válidas.
- Average odds, edge y confidence.
- Brier Score, Log Loss y Calibration Error.
- Segmentación por liga, línea, riesgo, calidad y rango de minuto.

### Shadow Mode
- Registro separado en `shadow_decisions.jsonl`.
- `SHADOW_MODE=true` impide publicar picks productivos.

### Panel
- Identidad V20.
- DataTruth, consenso, EV y horizontes 5/10/15 en detalle.
- Métricas de calibración y ROI en Sistema.

### Economy
- Se conserva candidate-first enrichment.
- 1 ficha prepartido nueva/ciclo y 8/hora por defecto.
- Lotes/caché/filtro top-2/copa.
- El detalle visual sigue leyendo memoria sin gasto adicional.
