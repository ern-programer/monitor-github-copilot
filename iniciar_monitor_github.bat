@echo off
setlocal
cd /d "%~dp0"

set "SILENT=0"
if /I "%~1"=="--silent" set "SILENT=1"

set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
set "PYTHONW_EXE=%~dp0.venv\Scripts\pythonw.exe"
set "STATE_FILE=%~dp0.auth\github_storage_state.json"

if not exist "%PYTHON_EXE%" (
    if "%SILENT%"=="0" (
        echo No se encontro Python del entorno virtual en .venv\Scripts\python.exe
        echo Crea el entorno y dependencias primero.
        pause
    )
    exit /b 1
)

rem Asegura Chromium de Playwright (si ya existe, termina rapido).
if "%SILENT%"=="0" (
    echo Verificando navegador de Playwright...
)
"%PYTHON_EXE%" -m playwright install chromium >nul 2>&1
if errorlevel 1 (
    if "%SILENT%"=="0" (
        echo No se pudo instalar/verificar Chromium de Playwright.
        echo Ejecuta manualmente: .venv\Scripts\python.exe -m playwright install chromium
        pause
    )
    exit /b 1
)

if not exist "%STATE_FILE%" (
    if "%SILENT%"=="0" (
        echo Primera ejecucion detectada: se abrira el login de GitHub.
        echo Completa login y 2FA en el navegador.
        echo La sesion se guarda automaticamente al entrar en Copilot Features.
    )
    "%PYTHON_EXE%" copilot_usage_monitor.py --login
    if errorlevel 1 (
        if "%SILENT%"=="0" (
            echo Fallo el login inicial.
            pause
        )
        exit /b 1
    )
)

start "Copilot Usage Bar" "%PYTHONW_EXE%" copilot_usage_monitor.py --gui
exit /b 0
