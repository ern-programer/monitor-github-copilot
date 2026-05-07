@echo off
setlocal
cd /d "%~dp0"

echo ==============================================
echo Configuracion inicial - Copilot Usage Monitor
echo ==============================================
echo.

if exist ".venv\Scripts\python.exe" (
  set "PYTHON_EXE=.venv\Scripts\python.exe"
  echo Entorno virtual detectado: .venv
) else (
  echo No existe .venv. Creando entorno virtual...

  where py >nul 2>&1
  if %errorlevel%==0 (
    py -3 -m venv .venv
  ) else (
    where python >nul 2>&1
    if %errorlevel%==0 (
      python -m venv .venv
    ) else (
      echo ERROR: No se encontro Python en PATH.
      echo Instala Python 3.10+ y vuelve a ejecutar este archivo.
      pause
      exit /b 1
    )
  )

  if not exist ".venv\Scripts\python.exe" (
    echo ERROR: No se pudo crear .venv correctamente.
    pause
    exit /b 1
  )

  set "PYTHON_EXE=.venv\Scripts\python.exe"
)

echo.
echo Instalando dependencias Python...
"%PYTHON_EXE%" -m pip install --upgrade pip
if errorlevel 1 (
  echo ERROR: Fallo la actualizacion de pip.
  pause
  exit /b 1
)

"%PYTHON_EXE%" -m pip install -r requirements.txt
if errorlevel 1 (
  echo ERROR: Fallo la instalacion de requirements.txt
  pause
  exit /b 1
)

echo.
echo Instalando navegador Chromium para Playwright...
"%PYTHON_EXE%" -m playwright install chromium
if errorlevel 1 (
  echo ERROR: Fallo la instalacion de Chromium.
  pause
  exit /b 1
)

echo.
echo Listo. Entorno configurado correctamente.
echo Ahora puedes iniciar con: iniciar_monitor_github.bat
pause
exit /b 0
