@echo off
setlocal
cd /d "%~dp0"
title JHONNY ELITE V3 - Windows + Telefono
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
if exist ".venv\Scripts\python.exe" goto check

echo ============================================================
echo     JHONNY ELITE V3 - INSTALACION INICIAL EN WINDOWS
echo ============================================================
echo.
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 -c "import sys; assert sys.version_info >= (3,11)" >nul 2>nul
    if %errorlevel%==0 (
        py -3 -m venv .venv
        goto check
    )
)
where python >nul 2>nul
if %errorlevel%==0 (
    python -c "import sys; assert sys.version_info >= (3,11)" >nul 2>nul
    if %errorlevel%==0 (
        python -m venv .venv
        goto check
    )
)
echo ERROR: Instala Python 3.11-3.13 oficial, marca "Add Python to PATH".
echo Despues ejecuta otra vez este archivo.
pause
exit /b 1

:check
".venv\Scripts\python.exe" -c "import fastapi,uvicorn,dotenv,requests,numpy,sklearn" >nul 2>nul
if %errorlevel%==0 goto run

:install
if not exist ".venv\Scripts\python.exe" (
    echo ERROR: No fue posible crear el entorno de Python.
    pause
    exit /b 1
)
echo Instalando dependencias. Se necesita Internet la primera vez.
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
    echo ERROR: Dependencias incompletas. Revisa conexion y memoria.
    pause
    exit /b 1
)

:run
".venv\Scripts\python.exe" scripts\start_local.py
if errorlevel 1 (
    echo.
    echo ERROR: El servidor no pudo arrancar. Revisa el mensaje anterior.
)
echo.
pause
endlocal
