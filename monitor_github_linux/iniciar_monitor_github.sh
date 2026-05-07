#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -x ".venv/bin/python" ]; then
  echo "No se encontro .venv. Ejecuta primero ./setup_linux.sh"
  exit 1
fi

exec ./.venv/bin/python copilot_usage_monitor_linux.py --gui --headless
