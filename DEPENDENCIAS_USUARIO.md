# Dependencias del Programa

## Requisitos base

- Windows 10/11
- Python 3.10 o superior
- Conexion a internet (solo para instalacion inicial)

## Dependencias Python

Las dependencias tecnicas instaladas por `requirements.txt` son:

- `playwright>=1.53.0`
- `pystray>=0.19.5`
- `Pillow>=10.4.0`

## Dependencia de navegador

Ademas se instala Chromium para Playwright con:

- `python -m playwright install chromium`

## Instalacion recomendada para usuarios finales

Usar el instalador automatico:

- `setup_entorno.bat`

Este archivo:

1. Crea `.venv` si no existe.
2. Instala dependencias Python.
3. Instala Chromium de Playwright.

## Que NO distribuir

Para reducir peso del paquete, no distribuir:

- `.venv/`
- `__pycache__/`
- `.auth/` (sesiones locales)
- `single_instance_events.txt`

Se recomienda distribuir solo codigo y scripts `.bat`, y luego ejecutar `setup_entorno.bat` en la maquina destino.
