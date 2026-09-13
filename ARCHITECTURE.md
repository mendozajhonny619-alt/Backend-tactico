# Arquitectura JHONNY ELITE 19

## Autoridad operativa única

La cadena activa es `JhonnyEliteEngine`. Los módulos legacy permanecen solo cuando todavía son útiles como componentes auxiliares o por compatibilidad de importación, pero el worker no ejecuta dos motores en paralelo.

```text
API-Football live=all
      |
      v
LiveMatchFetcher
  - normaliza marcador/reloj
  - detalle por lotes
  - filtra competiciones senior
      |
      v
JhonnyEliteEngine
  1. LiveDynamicsMemory
  2. ClockGuard
  3. DataQualityGuard
  4. ContextReader
  5. TacticalAI
  6. MarketAI
  7. RiskAI
  8. candidate gate
      |
      +---- no candidate ---> OBSERVE / NO_BET
      |
      v candidate
PreMatchDataService + PreMatchProfileAI
CandidateOddsService
AdvancedProbabilityEngine
      |
      v
Master decision gate
      |
      +---- ENTER ---> SignalTracker ---> ResultResolver
      +---- OBSERVE
      +---- NO_BET/BLOCKED
      |
      v
DashboardAdapter -> DashboardService -> /v17/*
```

## Reentrada tras gol

La clave estable incluye fixture, mercado, línea y época de marcador. Una señal anterior no impide una nueva oportunidad después de que cambia el score. El worker detecta el cambio y acelera el siguiente ciclo con `POST_GOAL_RESCAN_SECONDS`.

## Resolución de señal

Un fixture con señal pendiente puede desaparecer de `live=all` cuando finaliza. El worker identifica únicamente esos fixtures pendientes ausentes y consulta su estado final para resolver `WON`, `LOST` o `VOID`.

## Datos y cuotas

- El escaneo live es global dentro del alcance senior configurado.
- El detalle live se solicita por lotes.
- El prepartido se solicita solo tras detectar candidato.
- La cuota live también se solicita solo tras detectar candidato.
- Si una fuente no crítica falta, el motor conserva la lectura live y añade cautela; un bloqueo duro sí impide publicar.

## Modelo matemático

`AdvancedProbabilityEngine` combina hazard live y Poisson para estimar goles restantes. Produce:

- lambda restante;
- P(próximo gol);
- P(no más goles);
- P(2+ goles restantes);
- reparto de amenaza local/visitante;
- marcador final principal;
- escenarios alternativos condicionados por inestabilidad.

Estas son probabilidades de modelo, no garantías.

## UI

El panel lee estado ya procesado. Las rutas no vuelven a ejecutar el análisis pesado, evitando que una apertura del dashboard consuma cuota de datos o bloquee el scanner.
