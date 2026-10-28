# Registro de limpieza controlada — JHONNY ELITE V3

Este documento compara el ZIP original con la carpeta **actualizada**. No se destruyo el ZIP fuente.

- Archivo fuente: `Backend-tactico-main(3).zip`.
- Archivos originales enumerados: **482**.
- Rutas originales preservadas: **400**.
- Rutas originales cambiadas: **26** (incluidas dentro de las preservadas).
- Rutas originales trasladadas a documentacion historica: **5**.
- Rutas originales retiradas del paquete de trabajo: **77**.
- Los datos canonicos conservados no se eliminaron; unicamente se retiraron copias byte a byte identicas cuando se verificaron.

## Conteo por motivo

| Motivo | Cantidad |
|---|---:|
| Raiz/frontend suelto (no incorporado a src activo) | 67 |
| Duplicado nombrado, no modulo cargado | 6 |
| Credenciales no distribuidas | 2 |
| Copia duplicada con original identico en app/v17/storage | 2 |

## Rutas trasladadas a docs/legacy

- `CHANGELOG_JHONNY_ELITE.md` → `docs/legacy/CHANGELOG_JHONNY_ELITE.md`
- `DEPLOY_RENDER_20.md` → `docs/legacy/DEPLOY_RENDER_20.md`
- `MASTER_PROTOCOL_20.md` → `docs/legacy/MASTER_PROTOCOL_20.md`
- `PATCH_JHONNY_ELITE_20_1.md` → `docs/legacy/PATCH_JHONNY_ELITE_20_1.md`
- `VALIDATION_20.md` → `docs/legacy/VALIDATION_20.md`

## Archivos retirados (rutas originales, numerados)

001. `. env`
002. `.env`
003. `AIBrainPanel.jsx`
004. `AICommandCenter.jsx`
005. `AIConfidenceMeter.jsx`
006. `AILearningPanel.jsx`
007. `AILiveBrain.jsx`
008. `AITacticalInsights.jsx`
009. `AIWarningPanel.jsx`
010. `AdvancedMomentumPanel.jsx`
011. `App.jsx`
012. `ChatAssistantV17.jsx`
013. `ClockStatusBadge.jsx`
014. `Dashboard.css`
015. `Dashboard.jsx`
016. `DashboardV17.jsx`
017. `DashboardV17Test.jsx`
018. `DeepAnalysisPanel.jsx`
019. `EliteAnalyticsPanel.jsx`
020. `EliteDashboardPro.jsx`
021. `EliteHeader.jsx`
022. `EliteMatchDetailPro.jsx`
023. `EliteMetricCard.jsx`
024. `EliteSidebar.jsx`
025. `HistoryPanelV17.jsx`
026. `JhonnyEliteDashboard.jsx`
027. `LiveMatchCard.jsx`
028. `LiveMatches.jsx`
029. `LiveSignalFeed.jsx`
030. `MainLayout.jsx`
031. `MatchDetailModal.jsx`
032. `MatchDetailModalV17.jsx`
033. `MatchDetailPage.jsx`
034. `MatchHeroPanel.jsx`
035. `MatchMomentumChart.jsx`
036. `MatchProPanel.jsx`
037. `MatchStatsGrid.jsx`
038. `MatchView.jsx`
039. `MomentumHeatPanel.jsx`
040. `OpportunityCard.jsx`
041. `ResponsiveGrid.jsx`
042. `ResultsTable.jsx`
043. `RiskMeter.jsx`
044. `SectionPanelV17.jsx`
045. `SignalCardV17.jsx`
046. `SignalRadar.jsx`
047. `SignalResults.jsx`
048. `StatCardV17.jsx`
049. `SystemStatusWidget.jsx`
050. `TacticalWindowCard.jsx`
051. `TeamIdentityV17.jsx`
052. `XGChart.jsx`
053. `animations.css`
054. `api.js`
055. `apiV17.js`
056. `app/__init__ (1).py`
057. `app/__init__ (2).py`
058. `app/__init__ (3).py`
059. `app/__init__ (4).py`
060. `app/__init__ (5).py`
061. `app/__init__ (6).py`
062. `app/prediction_features.db`
063. `app/prematch_cache.json`
064. `components.css`
065. `dataMapper.js`
066. `elite-champions-panel.css`
067. `elite-mobile-pro.css`
068. `elite-pro.css`
069. `main.jsx`
070. `styles.css`
071. `useLiveData.js`
072. `useMomentum.js`
073. `useResponsive.js`
074. `useSignalFeed.js`
075. `useV17LiveData.js`
076. `v17-dashboard.css`
077. `variables.css`

## Precauciones

- **No** borrar `app/v17/storage` ni registros de historial.
- No borrar automaticamente los modulos Python duplicados por contenido: hay imports dinamicos y compatibilidad historica por comprobar.
- Si un archivo de codigo no esta referenciado por `src/main.jsx` pero se necesita para una tarea futura, recuperarlo desde el ZIP original.
- `.env` con claves reales no debe redistribuirse; el usuario configura claves nuevas desde su propia PC.
