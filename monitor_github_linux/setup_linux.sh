#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "=============================================="
echo "Configuracion inicial - monitor_github_linux"
echo "=============================================="

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 no esta instalado en el sistema."
  exit 1
fi

if [ ! -d ".venv" ]; then
  echo "Creando entorno virtual (.venv)..."
  python3 -m venv .venv
fi

VENV_PY=".venv/bin/python"

"$VENV_PY" -m pip install --upgrade pip
"$VENV_PY" -m pip install -r requirements_linux.txt
"$VENV_PY" -m playwright install chromium

echo
echo "Entorno listo."
echo "Ejecuta: ./iniciar_monitor_github.sh"
