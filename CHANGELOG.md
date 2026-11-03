# Registro de cambios

Formato de versión: `AAAA.MM.V` (la versión vuelve a `.1` al empezar cada mes).

## 2026.11.5

- Panel lateral **Calorplan** (solo administradores, solo lectura): línea de tiempo por día con
  barras por habitación y línea de «ahora», estado actual, próximo evento, última acción y
  simulador «¿qué haría ahora?» (evalúa las condiciones con los valores actuales sin ejecutar nada).
- API WebSocket `calorplan/overview` y cálculo de línea de tiempo y simulador en el núcleo (probado).
- Frontend sin dependencias ni compilación (módulos ES), con 14 tests de Node y test de contrato
  contra el formato real de la API.

## 2026.11.4

- Corrección: los avisos funcionan también con entidades `notify.*` (Telegram moderno), enviadas con `notify.send_message`. Antes solo se admitían servicios `notify.<nombre>`.

## 2026.11.3

- Corrección: `import_config` rechazaba rutas dentro de `/config` («Ruta no permitida»). Ahora se admite cualquier ruta dentro de la carpeta de configuración (además de las permitidas por Home Assistant).

## 2026.11.2

Primera versión con código (Fase 1: núcleo).

- Núcleo puro Python (`core/`): modelos con validación, evaluador de condiciones,
  planificador, notificador y ejecutor con verificación de apagado.
- Bloqueo infantil configurable al encender y al apagar (bloquear, desbloquear o nada).
- Modo ausencia, modo sombra (no actúa; solo registra), política de sensores sin datos
  y `catch_up` al arrancar.
- Capa de Home Assistant: almacén, adaptadores, controlador con un único temporizador,
  entidades `switch`, `sensor` y `binary_sensor`, servicios `import_config`, `run_slot`,
  `set_away`, `test_notification` y `reload`, traducciones es/en.
- Tests del núcleo (81) y CI (hassfest, validación HACS, pytest).

## 2026.11.1

- Diseño técnico y traspaso (`docs/`).
