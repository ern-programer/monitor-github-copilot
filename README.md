# Barra Visual de Uso de GitHub Copilot (Python)

Este proyecto muestra una barra flotante y movible en Windows con el porcentaje de uso mensual de Premium requests de GitHub Copilot.

## Que muestra

- Porcentaje actual de uso mensual
- Barra de progreso visual angosta
- Ventana movible (arrastrando con click) y always-on-top
- Datos de ritmo en el mismo renglon de "Copilot Premium"
- Modo mini opcional
- Opacidad configurable
- Ancho auto-adaptable al contenido
- Modo dock superior opcional
- Opcion de "siempre por encima" configurable
- Modo compacto tipo taskbar (150x30, solo barra y porcentaje)
- Variante mini taskbar (70x30, para pantallas chicas)
- Variante intermedia taskbar (100x30)
- Modo multi-cuenta en una misma ventana (barras apiladas)
- Estado del plan (cuando la pagina lo expone)
- Nota de reinicio mensual (si aparece)
- Ritmo de consumo vs avance del mes
- Proyeccion al cierre de mes (si mantienes el ritmo actual)

## Requisitos

- Python 3.10+
- Cuenta de GitHub con acceso a Copilot

## Instalacion

Recomendada para usuarios finales (doble clic):

```bash
setup_entorno.bat
```

Este script crea `.venv`, instala dependencias y descarga Chromium para Playwright.

Instalacion manual:

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

Consulta el detalle en `DEPENDENCIAS_USUARIO.md`.

## Uso

Primera vez (guardar sesion):

```bash
python copilot_usage_monitor.py --login
```

No hace falta presionar ENTER: cuando completes login y abras Copilot Features,
la sesion se guarda automaticamente.

Iniciar barra visual:

```bash
python copilot_usage_monitor.py --gui --interval 60
```

Override rapido por linea de comando:

```bash
python copilot_usage_monitor.py --gui --mini --opacity 0.85
```

Ejemplos nuevos:

```bash
python copilot_usage_monitor.py --gui --dock-top --auto-width
python copilot_usage_monitor.py --gui --free-dock --fixed-width --width 520
python copilot_usage_monitor.py --gui --not-always-on-top
python copilot_usage_monitor.py --gui --taskbar-compact
python copilot_usage_monitor.py --gui --taskbar-compact --taskbar-compact-70
python copilot_usage_monitor.py --gui --taskbar-compact --taskbar-compact-100
python copilot_usage_monitor.py --gui --extra-state-files ".auth\\cuenta2.json;.auth\\cuenta3.json"
```

En multi-cuenta:

- Vista normal: una barra por cuenta (apiladas)
- Modo taskbar compacto: carrusel de cuentas
- Clic simple en mini taskbar: rota a la siguiente cuenta
- Doble clic en mini taskbar: restaura la vista normal

Asistente para agregar cuentas extra:

```bash
python copilot_usage_monitor.py --add-account cuenta2
python copilot_usage_monitor.py --remove-account cuenta2
python copilot_usage_monitor.py --remove-account cuenta2 --delete-state-file
python copilot_usage_monitor.py --list-accounts
```

Tambien puedes usar el asistente por doble clic:

```bash
agregar_cuenta_copilot.bat
quitar_cuenta_copilot.bat
```

Nota: al quitar una cuenta, por defecto solo se elimina de `extra_state_files` en la configuracion.
Si agregas `--delete-state-file`, tambien se borra el archivo `.auth\\alias.json`.

Arranque con doble clic en Windows:

```bash
iniciar_monitor_github.bat
```

Nota: si falta Chromium de Playwright, el .bat lo instala automaticamente.

Atajo rapido dentro de la barra:

- Click derecho: actualizar ahora, rehacer login, salir
- Click derecho: opcion "Minimizar a bandeja"
- Click derecho: opcion "Alternar siempre visible"
- Click derecho: opcion "Alternar modo compacto taskbar"
- Click derecho: opcion "Usar mini taskbar 70px"
- Click derecho: opcion "Usar taskbar intermedio 100px"
- Click derecho: opcion "Usar taskbar normal 150px"
- Click derecho: opcion "Alternar dock superior"
- Click derecho: menu "Configuracion" para cambiar intervalo, opacidad, auto-width, ancho fijo y autoarranque
- Click derecho: menu "Configuracion > Cuentas" para listar/agregar/quitar cuentas sin editar archivos
- Click derecho: "Configuracion > Reiniciar barra ahora" para aplicar cambios inmediatamente
- Boton "_" en la cabecera: minimiza a bandeja
- Desde bandeja: Restaurar, Actualizar, Salir
- Tecla Escape: cerrar barra

## Configuracion persistente

Edita el archivo `monitor_config.ini`:

Tambien puedes manejar estos ajustes desde la UI en `click derecho > Configuracion`.

- `interval_seconds`: cada cuantos segundos refresca
- `mini_mode`: `true` o `false`
- `opacity`: de `0.35` a `1.0`
- `auto_width`: `true` o `false`
- `dock_top`: `true` o `false`
- `window_width`: ancho base en pixeles
- `always_on_top`: `true` o `false`
- `taskbar_compact_mode`: `true` o `false`
- `taskbar_compact_width`: `70`, `100` o `150`
- `extra_state_files`: lista separada por `;` con sesiones adicionales
- `auto_start_enabled`: `true` o `false` para inicio con Windows

Nota: el modo compacto taskbar no se minimiza como boton de aplicacion; se muestra como mini-widget flotante (150x30) anclado sobre la barra de tareas, cerca de la zona de notificacion.

## Autoarranque con Windows

Comandos:

```bash
configurar_autoarranque_windows.bat on
configurar_autoarranque_windows.bat off
configurar_autoarranque_windows.bat status
configurar_autoarranque_windows.bat apply
```

`apply` toma el valor de `auto_start_enabled` en `monitor_config.ini` y lo aplica al registro de usuario actual.

## Paquete Liviano Para Distribuir

Para generar una carpeta lista para compartir sin `.venv`:

```bash
paquete_release.bat
```

Esto crea `dist_liviano` con solo los archivos necesarios para el usuario final.
Tambien genera `dist_liviano.zip` listo para compartir.

## Notas importantes

- Para cuentas personales, GitHub no publica un endpoint oficial y estable para este dato en tiempo real, por eso el script lee la pagina de ajustes autenticada.
- Si caduca la sesion, ejecuta de nuevo con `--login` o usa click derecho > Rehacer login.
- Si cambian textos/selectores en GitHub, puede ser necesario ajustar las expresiones de extraccion.
