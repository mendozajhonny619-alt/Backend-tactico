# JHONNY ELITE V3 — ELITE LIVE INTELLIGENCE

**Mismo proyecto original actualizado; Python + FastAPI + escáner LIVE + motor JHONNY + almacenamiento existente + React.**

**Estado de esta entrega:** actualización local orientada a Windows y acceso móvil por Wi-Fi privado. Primero **Shadow Mode / simulación**. No hay apuestas automáticas, promesa de acierto ni garantía de cumplimiento íntegro de los 154 requisitos del Protocolo Maestro.

## Arranque recomendado en Windows

1. Descomprime la carpeta `Backend-tactico-main` **completa** en `Documentos` o en otra carpeta local. No ejecutes nada dentro del ZIP.
2. Instala Python 3.11 a 3.13 de fuente oficial; durante la instalación marca `Add Python to PATH`. Se necesita Internet inicialmente para instalar las bibliotecas.
3. Abre **`CONFIGURAR_API.bat`**, coloca la clave de tu cuenta autorizada en `API_FOOTBALL_KEY=...` y guarda el archivo `.env` **solo en tu PC**. No envíes ese archivo al chat.
4. Haz doble clic en **`INICIAR_JHONNY_ELITE.bat`**. En el primer inicio se crea `.venv` y se instalan dependencias. Si falta una dependencia, el siguiente inicio intenta reinstalarla.
5. Abre `http://127.0.0.1:8000/panel` en tu PC. La consola muestra usuario `jhonny` y una contraseña única generada en `.env`.
6. Desde el teléfono, conectado a **la misma red Wi-Fi privada**, abre el enlace `http://IP_DE_LA_PC:8000/panel` que aparece en la consola. Configura el firewall de Windows **solo para redes privadas** si hace falta. **No publiques el puerto 8000 en Internet.**

**Para cerrar el software:** Ctrl+C en la consola. El escáner se ejecuta dentro del proceso FastAPI; no se debe arrancar `worker.py` aparte ni ejecutar Uvicorn con `--workers 2` o `--reload`.

Consulta **`PRIMEROS_PASOS_WINDOWS_Y_TELEFONO.txt`** para pasos y resolución de problemas.

## El panel para teléfono y computadora

- `web_local/index.html` es un **panel móvil/escritorio listo para usar sin Node ni Internet para compilarlo**. Se sirve automáticamente desde `/panel` y muestra LIVE, oportunidades, Shadow, bloqueos, historial y detalle de 23 criterios.
- `src/` conserva el **frontend React original** y sus mejoras V3. Si tienes Node.js compatible, ejecuta `COMPILAR_PANEL_REACT.bat`, reinicia el backend y se utilizará el panel React compilado desde `dist/`.
- Ambos paneles utilizan **el mismo backend y la misma fuente de datos**, sin segundo escáner ni consumo de API al refrescar la pantalla.
- El teléfono es un **panel web responsive**, no un APK nativo ni un escáner autónomo. La PC debe estar encendida para usarlo por Wi-Fi. Acceso desde fuera de la red requiere una solución segura con HTTPS/VPN o servidor remoto, aún no incluida.

## Arquitectura que se conservó

```text
API-Football (según proveedor, plan, cobertura y presupuesto)
    -> LiveMatchFetcher -> filtro/catálogo actual -> DataTruth/Clock
    -> lecturas/contexto/memoria -> oportunidad
    -> investigación prepartido y cuotas bajo demanda
    -> motor matemático -> riesgo/contradicciones -> MasterDecisionAI
    -> SHADOW visible; producción solo tras validación habilitada
    -> SignalTracker -> historial y performance
    -> FastAPI /v17/* -> panel PC/teléfono
```

El backend conserva los módulos históricos `app/v17/` y `app/jhonny_elite/`, incluidas referencias internas a V20. **No se reentrenaron los modelos, ni se alteró el historial oficial, ni se sustituyó MasterDecisionAI**. La versión de la aplicación local/entrada es V3; los identificadores heredados del motor se mantienen para compatibilidad y trazabilidad hasta completar una migración de contratos probada.

### Lo actualizado

- Fallo de normalización LIVE corregido; respuesta vacía no produce `NameError`.
- Candidatos Shadow visibles y separados del historial/las señales oficiales.
- Inicio seguro en Shadow Mode, bloqueo de worker duplicado y parada ordenada.
- Distribución de resultados sin pérdida de cola y distinción entre xG provisto y proxy.
- Resultados diarios filtrados a las **00:00 America/La_Paz** y marcador 0 preservado.
- Comparación de **23 criterios**, con hechos, proxies, inferencias y N/A; ninguna nota sin respaldo.
- Seis señales activas como máximo para el tracker; las suspendidas por falta de datos no se liquidan artificialmente como VOID ni desaparecen del historial pendiente.
- Panel responsive local y acceso desde teléfono con usuario/contraseña en red privada.
- Caché/batching existente conservados, límite adaptado a la cuota conocida y menos consultas repetidas de estado final.
- Limpieza documentada de archivos sin uso verificado y de secretos que venían en el ZIP.

### Requisitos todavía pendientes / no certificados

La cobertura mundial por ID de todas las primeras/segundas divisiones, los torneos Nations League y sus temporadas, la disponibilidad/licencia de cuotas en vivo, la calibración histórica de probabilidades, las definiciones contractuales de OVER_NEXT_15, toda la máquina de estados oficial y la validación de cientos de encuentros simultáneos **no quedan demostrados solamente por instalar esta actualización**. Algunas funciones históricas existen de forma parcial; requieren pruebas con credenciales y datos reales y, en ciertos casos, desarrollo adicional.

No se ejecutó ningún consumo de API-Football durante la preparación ni se verificó directamente esta instalación en Windows físico, debido a que la revisión se realizó en un entorno aislado Linux. **El comportamiento Windows/teléfono debe validarse en la HP.**

## Pruebas offline

Para desarrolladores, desde la carpeta raíz:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Las pruebas no verifican la conexión a API-Football ni el build React; las dependencias de Node requieren descarga para compilar el frontend original.

## Seguridad y confidencialidad

- `.env` **no se entrega** en el ZIP; solo se incluye `.env.example` sin valores secretos. El iniciador crea `.env` en la PC.
- Usa API keys exclusivamente en backend; no copies claves al frontend ni compartas `.env`.
- HTTP Basic por Wi-Fi **no cifra** contraseñas. Empléalo únicamente en una Wi-Fi privada de confianza; no uses Wi-Fi pública, port forwarding ni redes abiertas.
- Las bases/historial local existentes se preservaron salvo duplicados idénticos especificados en `ARCHIVOS_RETIRADOS_V3.md`.

## Documentos

- `CAMBIOS_JHONNY_ELITE_V3.md`: lista de cambios, pruebas, limitaciones.
- `ARCHIVOS_RETIRADOS_V3.md`: listado verificable de eliminaciones y traslados.
- `docs/legacy/`: documentación V20 histórica, **no** las instrucciones vigentes.
- `PRIMEROS_PASOS_WINDOWS_Y_TELEFONO.txt`: guía breve para usuario final.

**Lema:** OBSERVAR · COMPARAR · ANTICIPAR · VALIDAR · MONITOREAR · APRENDER.
