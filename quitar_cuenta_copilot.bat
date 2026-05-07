@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" (
  echo No se encontro Python en .venv\Scripts\python.exe
  pause
  exit /b 1
)

set /p ACCOUNT_ALIAS=Alias o ruta de la cuenta a quitar (ej: cuenta2): 
if "%ACCOUNT_ALIAS%"=="" (
  echo Valor vacio. Operacion cancelada.
  pause
  exit /b 1
)

set "DELETE_FLAG="
set /p DELETE_FILE=Tambien borrar archivo de sesion .json? (s/N): 
if /i "%DELETE_FILE%"=="s" set "DELETE_FLAG=--delete-state-file"
if /i "%DELETE_FILE%"=="si" set "DELETE_FLAG=--delete-state-file"

"%PYTHON_EXE%" copilot_usage_monitor.py --remove-account "%ACCOUNT_ALIAS%" %DELETE_FLAG%
if errorlevel 1 (
  echo Error al quitar la cuenta.
  pause
  exit /b 1
)

echo Cuenta quitada de la configuracion.
pause
exit /b 0
