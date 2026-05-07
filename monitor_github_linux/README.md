# monitor_github_linux

Adaptacion Linux separada del monitor de Windows.

## Estado

- Carpeta aislada para no mezclar con los scripts de Windows.
- Base funcional: lectura de uso + GUI + login + refresco.
- Nota: funciones especificas de Windows (registro, BAT, posicion taskbar Win32) no aplican en Linux.

## Instalacion

```bash
cd monitor_github_linux
chmod +x setup_linux.sh iniciar_monitor_github.sh
./setup_linux.sh
```

## Uso

Primera vez (guardar sesion):

```bash
./.venv/bin/python copilot_usage_monitor_linux.py --login
```

Iniciar monitor:

```bash
./iniciar_monitor_github.sh
```

## Dependencias

Ver `requirements_linux.txt`.

## Importante

- Esta carpeta NO incluye entorno virtual.
- En Linux se recomienda iniciar siempre desde esta carpeta para que `.auth/` y `monitor_config.ini` queden locales.
