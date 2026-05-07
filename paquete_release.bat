@echo off
setlocal
cd /d "%~dp0"

set "DIST_DIR=dist_liviano"
set "ZIP_FILE=dist_liviano.zip"

echo ==============================================
echo Generando paquete liviano
echo ==============================================
echo.

if exist "%DIST_DIR%" (
  echo Limpiando carpeta anterior: %DIST_DIR%
  rmdir /s /q "%DIST_DIR%"
)

if exist "%ZIP_FILE%" (
  echo Eliminando ZIP anterior: %ZIP_FILE%
  del /q "%ZIP_FILE%"
)

mkdir "%DIST_DIR%"
if errorlevel 1 (
  echo ERROR: No se pudo crear la carpeta %DIST_DIR%.
  pause
  exit /b 1
)

echo Copiando archivos principales...
for %%F in (
  copilot_usage_monitor.py
  requirements.txt
  README.md
  DEPENDENCIAS_USUARIO.md
  monitor_config.ini
  iniciar_monitor_github.bat
  configurar_autoarranque_windows.bat
  agregar_cuenta_copilot.bat
  quitar_cuenta_copilot.bat
  setup_entorno.bat
) do (
  if exist "%%F" (
    copy /y "%%F" "%DIST_DIR%\" >nul
  )
)

if exist "assets" (
  echo Copiando assets...
  robocopy "assets" "%DIST_DIR%\assets" /E /NFL /NDL /NJH /NJS /NC /NS >nul
)

echo Generando ZIP...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path '%DIST_DIR%\*' -DestinationPath '%ZIP_FILE%' -CompressionLevel Optimal"
if errorlevel 1 (
  echo ERROR: No se pudo generar %ZIP_FILE%.
  pause
  exit /b 1
)

echo.
echo Paquete generado en: %CD%\%DIST_DIR%
echo ZIP generado en: %CD%\%ZIP_FILE%
echo.
echo Incluye solo lo necesario para distribuir.
echo NO incluye .venv, .auth, __pycache__ ni logs.
echo.
pause
exit /b 0
