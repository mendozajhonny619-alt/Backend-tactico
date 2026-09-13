# Cambios principales de la reconstrucción JHONNY ELITE 19

- Eliminación de secretos reales del repositorio y creación de `.env.example` / `.gitignore`.
- Restauración de `PredictionFeatureBuilder` y `ResultResolver`, que estaban sobrescritos por clases incorrectas.
- Activación real de endpoints `/v17/*` en `main.py`.
- Cadena de análisis unificada: live -> candidato -> prepartido/cuota -> matemática -> decisión -> tracker.
- Prepartido bajo demanda, no precarga global.
- Cuotas bajo demanda y manejo de rate limit.
- Detalle de fixtures por lotes y alcance senior global configurable.
- Dinámica entre escaneos para detectar apertura/cierre reciente del partido.
- Reanálisis post-gol y reentrada por nueva época de marcador.
- Corrección de minuto efectivo con tiempo añadido.
- Resolución de señales al finalizar fixtures que desaparecen del feed live.
- `VOID` para push en líneas asiáticas enteras.
- RAW debugging apagado por defecto.
- Centralización de `JHONNY_DATA_DIR`.
- Worker único protegido contra duplicación por múltiples procesos.
- Panel React/Vite reconstruido y responsive para PC/celular.
- Panel muestra amenaza reciente, estado dinámico y reanálisis post-gol.
- Suite de pruebas de integración del protocolo.
