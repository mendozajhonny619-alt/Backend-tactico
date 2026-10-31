# JHONNY ELITE V3.5 - Motor, calibracion y verificacion

## Que cambia

- `app/jhonny_elite/master_protocol.py`: las ventanas temporales 5/10/15 minutos ahora se calculan exclusivamente con muestras dentro de cada intervalo. Se rechaza una ventana sin cobertura real y se diferencia cero del valor no publicado. Se reinicia la referencia ante revisiones incompatibles de reloj/marcador. `MasterDecisionAI` exige comprobacion completa de una cuota LIVE de goles FT y estado de modelo VALIDATED_OUT_OF_SAMPLE antes de autorizar una senal oficial. Shadow Mode conserva su bloqueo.
- `app/jhonny_elite/engine.py`: conserva separadamente la probabilidad matematica del evento de mercado exacto (si existe) para auditoria, sin convertir candidate_score en probabilidad.
- `app/v17/dashboard/dashboard_adapter.py`: no utiliza indices heuristicos de Over/Under como sustitutos de probabilidades de gol.
- `app/v17/ai/calibration_lab.py`: utilitario offline para examinar un conjunto de predicciones con resultados certificados. Separa entrenamiento y evaluacion cronologicamente y por fixture, evita usar partidos cuyo resultado aun no se conocia, informa Brier, Log Loss, ECE y baseline, y propone un candidato de calibracion monotonica sin activarlo en produccion.
- `app/v17/tests/test_v35_reliability.py` y `test_v35_calibration_lab.py`: regresiones nuevas, sin red ni claves.

## Lo que NO es calibracion validada

Las predicciones y los registros Shadow actuales no demuestran calibracion fuera de muestra. La calibracion requiere un conjunto suficientemente grande y representativo de pronosticos emitidos y guardados ANTES de cada resultado, con identificacion exacta de partido, mercado, linea, hora, version del modelo, resultado, regla de liquidacion y fuente verificable. No se puede recuperar retrospectivamente un pronostico no guardado. No extrapoles el porcentaje de candidate_score como probabilidad de gol.

Por eso este parche **no habilita** senales oficiales ni modifica deliberadamente el valor NOT_VALIDATED_OUT_OF_SAMPLE. El umbral por defecto del laboratorio (200 fixtures distintos de entrenamiento y 100 de prueba) es un minimo tecnico inicial para un diagnostico, **no una garantia estadistica de buen rendimiento**. Revisar el sesgo por competencia, linea, minuto, odds, calidad de datos y mercado antes de cualquier despliegue.

## Formato de entrada JSONL (una linea por pronostico)

Ejemplo FICTICIO solo ilustrativo; **no utilizar para aprobar el modelo**:

```json
{"fixture_id":"EJEMPLO-1","episode_id":"min65","market":"OVER_MATCH_DYNAMIC","period":"FT","line":2.5,"model_version":"MODEL_A","predicted_at":"2026-10-25T19:05:00+00:00","resolved_at":"2026-10-25T19:55:00+00:00","model_probability":0.64,"label_source":"FINAL_SCORE","result_status":"WON","final_home_score":2,"final_away_score":1}
```

`model_probability` debe ser la probabilidad del evento EXACTO (ej. Over 2.5 FT); admite rango 0..1 o porcentaje 0..100. Nunca usar confianza de calidad, puntaje candidato o porcentaje generico de gol siguiente.

`label_source=FINAL_SCORE` exige `final_home_score` y `final_away_score` y comprueba que el estado WON/LOST concuerde con la linea. Las ventanas NEXT_15 requieren `label_source=OFFICIAL_SETTLEMENT`, `settlement_rule_id`, y `verified_window_goals`, porque el resultado final no demuestra los goles de la ventana.

## Ejecutar en PowerShell (en la raiz Backend-tactico-main)

```powershell
.\.venv\Scripts\python.exe -m app.v17.ai.calibration_lab .\app\v17\storage\pronosticos_resueltos.jsonl --out .\app\v17\storage\reporte_calibracion.json
```

Solo ejecutar ese comando cuando el archivo JSONL de pronosticos RESUELTOS exista y cumpla los requisitos. Si no lo tienes, no inventes registros ni declares calibracion. El utilitario no consume API ni activa produccion.

Pruebas locales sin lanzar el worker:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests app/v17/tests
```

## Tareas siguientes pendientes

1. Conectar el cierre de pronosticos Shadow con resultados oficiales verificados para construir datos etiquetados sin informacion futura.
2. Reorganizar la investigacion profunda en una cola acotada que no bloquee el escaneo global.
3. Completar perfiles de alineaciones/bajas y separar estadisticas verificadas de estimaciones.
4. Validar resultados sobre partidos posteriores y segmentos por liga/mercado; comparar con baseline y cuotas vigentes.
5. Probar en una HP 245 G6 de 4GB (RAM, CPU, coste API y acceso LAN) antes de activar nuevas funciones.

**No se cambiaron claves, .env, limites de creditos, la configuracion de shadow, ni bases de datos de usuario.**
