@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" (
  echo No se encontro Python en .venv\Scripts\python.exe
  pause
  exit /b 1
)

set /p ACCOUNT_ALIAS=Alias de la cuenta (ej: cuenta2): 
if "%ACCOUNT_ALIAS%"=="" (
  echo Alias vacio. Operacion cancelada.
  pause
  exit /b 1
)

"%PYTHON_EXE%" copilot_usage_monitor.py --add-account "%ACCOUNT_ALIAS%"
if errorlevel 1 (
  echo Error al agregar la cuenta.
  pause
  exit /b 1
)

echo Cuenta agregada correctamente.
pause
exit /b 0
