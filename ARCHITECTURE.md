# JHONNY ELITE 20 — Arquitectura

```text
                           FRONTEND REACT
                                 |
                                 v
                         FastAPI /v17/*
                                 |
                      DashboardAdapter (read)
                                 |
                  -------------------------------
                  |                             |
             Worker 30 s                  SignalTracker
                  |                             |
                  v                             v
           LiveMatchFetcher              Settlement/History
                  |
          Competition Filter
                  |
        Normalize / Data Fusion
                  |
       ClockGuard + DataTruthAI
                  |
       Temporal Memory 5/10/15
                  |
     Context + Tactical + Risk AI
                  |
          Candidate Scoring
                  |
          candidate? ---- no ---> OBSERVATION/NO_BET
                  |
                 yes
                  |
     Prematch + Odds (Economy budget)
                  |
      Advanced Probability Engine
         HT / FT / 5 / 10 / 15
                  |
       Contradiction Judge Master
                  |
          Consensus 4 of 5
                  |
          MASTER DECISION AI 20
                  |
        -------------------------
        |                       |
 CONFIRMED_SIGNAL          NO_BET/BLOCKED
        |
       Track
        |
 WIN / LOSS / VOID / INVALIDATED
        |
 Performance + Calibration + Shadow comparison
```

## Boundaries

### MasterDecisionAI20
Solo este componente escribe el contrato oficial. Los demás producen evidencia.

### Frontend
No calcula señales ni confianza. Consume `official_*` y datos explicativos.

### Providers
Toda fuente externa debe convertirse al modelo normalizado antes de las capas AI. `DataFusionEngine` debe registrar contradicciones; nunca fusionarlas silenciosamente.

### Economy
Economy controla **enriquecimientos**, no el ciclo maestro. El loop sigue a 30 s. Prepartido/cuotas no se descargan globalmente.

### Tracking
Solo `official_can_publish=true` puede ingresar al historial oficial. Una señal activa con igual `match+market+line` se actualiza, no se duplica.
