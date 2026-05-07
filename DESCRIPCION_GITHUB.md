# Monitor GitHub Copilot

Monitor visual de uso mensual de GitHub Copilot (Premium requests), pensado para tener siempre a la vista el consumo de una o varias cuentas.

## Que es este proyecto

Es una aplicacion en Python que lee la pagina autenticada de GitHub Copilot Features y muestra una barra flotante con:

- porcentaje de uso actual
- progreso visual
- ritmo de consumo y proyeccion mensual
- estado del plan y nota de reinicio (cuando GitHub lo informa)

## Para que sirve

- evitar sorpresas por consumo alto a fin de mes
- monitorear varias cuentas desde una sola ventana
- tener un indicador liviano tipo taskbar sin abrir el navegador

## Funcionalidades principales

- interfaz flotante movible, opacidad configurable y always-on-top
- modo compacto tipo taskbar (70, 100 y 150 px)
- bandeja del sistema (restaurar, actualizar, salir)
- soporte multi-cuenta
- login asistido con sesion persistente
- instancia unica con bring-to-front
- configuracion persistente por archivo INI y menu en la UI

## Plataformas

- Windows: soporte completo
- Linux: version separada en monitor_github_linux

## Privacidad y alcance

El proyecto no usa un endpoint publico oficial para este dato. Toma la informacion desde la pagina de configuracion autenticada del usuario en GitHub. La sesion se guarda localmente en archivos de estado para evitar relogin continuo.

## Inicio rapido

1. Ejecutar setup_entorno.bat
2. Ejecutar iniciar_monitor_github.bat
3. Si es la primera vez, completar login cuando lo solicite

## Estado de version

Version visual actual: v1.3
