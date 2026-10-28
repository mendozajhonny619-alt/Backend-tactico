@echo off
setlocal
cd /d "%~dp0"
where node >nul 2>nul
if errorlevel 1 (
    echo Node.js 20.19+ no encontrado. Instala una version soportada si deseas compilar React.
    echo El panel local incluido funciona sin Node.js.
    pause
    exit /b 1
)
where npm >nul 2>nul
if errorlevel 1 (
    echo npm no encontrado.
    pause
    exit /b 1
)
echo Instalando dependencias de React y compilando panel completo...
call npm ci --no-audit --no-fund
if errorlevel 1 (
    echo ERROR durante npm ci
    pause
    exit /b 1
)
call npm run build
if errorlevel 1 (
    echo ERROR durante npm run build
    pause
    exit /b 1
)
echo Panel React compilado. Cierra y vuelve a iniciar JHONNY ELITE V3.
pause
endlocal
