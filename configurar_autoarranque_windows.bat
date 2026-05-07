@echo off
setlocal
cd /d "%~dp0"

set "RUN_KEY=HKCU\Software\Microsoft\Windows\CurrentVersion\Run"
set "RUN_NAME=CopilotUsageBar"
set "START_COMMAND=\"%~dp0iniciar_monitor_github.bat\" --silent"
set "CONFIG_FILE=%~dp0monitor_config.ini"

if /I "%~1"=="on" goto :enable
if /I "%~1"=="off" goto :disable
if /I "%~1"=="status" goto :status
if /I "%~1"=="apply" goto :apply

echo.
echo Uso:
echo   configurar_autoarranque_windows.bat on
echo   configurar_autoarranque_windows.bat off
echo   configurar_autoarranque_windows.bat status
echo   configurar_autoarranque_windows.bat apply
echo.
echo apply lee monitor_config.ini y activa/desactiva segun auto_start_enabled.
goto :eof

:enable
reg add "%RUN_KEY%" /v "%RUN_NAME%" /t REG_SZ /d "%START_COMMAND%" /f >nul
if errorlevel 1 (
    echo No se pudo activar el autoarranque.
    exit /b 1
)
echo Autoarranque ACTIVADO.
goto :eof

:disable
reg delete "%RUN_KEY%" /v "%RUN_NAME%" /f >nul 2>&1
echo Autoarranque DESACTIVADO.
goto :eof

:status
reg query "%RUN_KEY%" /v "%RUN_NAME%" >nul 2>&1
if errorlevel 1 (
    echo Estado: DESACTIVADO
) else (
    echo Estado: ACTIVADO
)
goto :eof

:apply
set "AUTO_START=false"
if exist "%CONFIG_FILE%" (
    for /f "tokens=1,* delims==" %%A in ('findstr /R /I "^auto_start_enabled=" "%CONFIG_FILE%"') do (
        set "AUTO_START=%%B"
    )
)

set "AUTO_START=%AUTO_START: =%"
if /I "%AUTO_START%"=="true" goto :enable
if /I "%AUTO_START%"=="1" goto :enable
goto :disable
