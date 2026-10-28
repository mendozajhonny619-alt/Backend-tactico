# JHONNY ELITE V3 — Actualizacion sobre el mismo proyecto

## Identidad y alcance

Archivo de origen: `Backend-tactico-main(3).zip`.
Version de entrada: `3.0-local`; se conservaron los contratos internos de modelos V17/V20 donde siguen siendo necesarios. **No hay construccion de un proyecto distinto** ni reconstruccion de la base de datos.

## Cambios implementados

01. Normalizador LIVE: eliminacion del `NameError` producido por `deep_scan_used`.
02. Inicio Windows: `INICIAR_JHONNY_ELITE.bat` instala dependencias y lanza un servidor unico; intenta recuperar instalaciones interrumpidas.
03. Configuracion Windows: `CONFIGURAR_API.bat` crea/abre `.env`; no se incluyen claves en la entrega.
04. Acceso movil: mismo origen FastAPI, interfaz responsive, enlace LAN e inicio de sesion con contrasena robusta generada localmente.
05. Seguridad local: bloqueo de IP no privada y prohibicion de acceso LAN sin contrasena; no exponer el puerto en Internet.
06. Panel de respaldo integrado sin compilacion Node, y conservacion de React como frontend avanzado opcional.
07. Separacion Shadow/produccion: simulaciones visibles sin transformarlas en señales oficiales ni contar aciertos ficticios.
08. `MasterDecisionAI` se conserva como autoridad de campos oficiales.
09. Publicacion: cupo de seis señales activas globales; observaciones y candidatos adicionales permanecen visibles.
10. Seguimiento: los fallos de fuente/clock suspenden estado operativo sin manipular resultados oficiales historicos; se sigue buscando liquidacion real.
11. Horario de Bolivia: contadores diarios a las 00:00 America/La_Paz, no 23:30.
12. Marcadores con cero: corregida la conversion de `0` como supuesto campo ausente.
13. Matematicas: masa Poisson total normalizada con categoria `OTROS` de ser necesaria; estado de xG real/proxy etiquetado.
14. Comparador de 23 criterios con N/A, evidencia/proxy/inferencia y detalle disponible sin consultas nuevas.
15. Economia API: se respeta saldo conocido, reserva ajustada para planes pequenos y polling de fixtures cerrados espaciado.
16. Worker: un solo arranque, bloqueo de segundo proceso, parada por Event y reevaluacion interna cada ~30 s segun recursos.
17. Fuente React: `fetch` relativo a host actual para que el telefono no apunte a su localhost; se conserva la UI original.
18. Limpieza: credenciales, copias identicas y archivos frontend sueltos retirados; documentacion historica V20 preservada en `docs/legacy/`.
19. `tzdata` anadido como dependencia para zonas horarias Windows.
20. Tests de regresion para todos los arreglos criticos, sin usar creditos externos.

## Evidencia y pruebas de esta entrega

- **44 pruebas Python: PASS** (`python -m pytest -q`, worker deshabilitado, entorno aislado).
- **59 archivos JS/JSX activos: parse OK** con TypeScript, y JS inline del panel: OK.
- **HTTP local Uvicorn real**: `/ready` 200, `/panel` sin auth 401, `/panel` autenticado 200, `/v17/dashboard` 200, `/v17/match/{id}` 200.
- Sintaxis Python AST sin fallos en el proyecto (verificado durante auditoria original); se preservan los 290 originales salvo inicializadores triviales retirados.
- **No se ejecuto una API real** ni se consumieron creditos.

## Que no significa esta entrega

- No se ha ejecutado el sistema en Windows fisico de la HP 245 G6 ni en el telefono del usuario (son pasos de aceptacion a realizar localmente).
- No se ha compilado React aqui: las dependencias de npm no estuvieron accesibles en el laboratorio sin acceso a registro. **El panel web incluido SI funciona sin Node** y fue servido via HTTP.
- No se afirma cumplir los 154 requisitos de extremo a extremo. Permanecen pendientes el catalogo mundial versionado, cobertura de todas las Nations League, conectores alternativos licenciados, reglas especificas NEXT_15, cuotas con frescura real, calibracion estadistica, escalamiento, y ensayos de carga con API real.
- No es una aplicacion Android instalada como APK ni un servicio remoto 24/7.

## Recomendacion operativa

Instalar en Windows con Shadow Mode, copiar la clave privada al `.env` desde la PC, iniciar con `INICIAR_JHONNY_ELITE.bat` y comprobar partidos del proveedor, consumo de API, limites y rendimiento del hardware antes de considerar habilitar publicaciones oficiales. No divulgar la contrasena de LAN.
