# Registro de cambios

Formato de versión: `AAAA.MM.V` (la versión vuelve a `.1` al empezar cada mes).

## 2026.11.6

Edición desde el panel: vistas **Tramos** y **Casa** sobre el backend de edición.

- Vista **Tramos**: tabla por habitación y editor (nombre, días, inicio, hora de fin o duración,
  consigna, condiciones de temperatura exterior e interior, reintento de apagado, avisos propios,
  habilitado). Duplicar, habilitar/deshabilitar y borrar. La validación en vivo indica con qué
  tramos se solapa y no deja guardar hasta resolverlo; cada cambio guarda una copia en el historial.
- Panel con tres vistas: **Resumen**, **Tramos** y **Casa**. En Casa se editan los sensores exteriores y su
  agregación, los canales de aviso (con botón de prueba), el aviso por defecto, los mensajes,
  la política de sensores sin datos, `catch_up` y el modo sombra (pide confirmación al desactivarlo);
  y se crean, editan y borran habitaciones (actuador `climate`/`switch`, bloqueo infantil,
  sensores y agregación). Validación en vivo contra el servidor, con avisos si algo no existe
  en Home Assistant, y diálogo de historial para restaurar versiones anteriores.
- Tests de Node de las vistas Casa y Tramos (49 en total) y prueba de integración manual del panel contra
  el backend real.
- **Agregación de sensores configurable:** `outdoor_aggregation` (global) e `indoor_aggregation`
  (por habitación) aceptan `min` (por defecto, como hasta ahora), `max` o `mean`.
- Validación de plantillas de aviso al guardar: variables desconocidas o formato roto.
- Editor de plan en el núcleo: tramos, habitaciones (actuador, sensores, agregación) y ajustes
  globales, siempre validando el plan completo y sin modificar el original.
- Historial de las últimas 10 versiones del plan (copia automática antes de cada cambio e
  importación) con restauración.
- Comandos WebSocket de escritura solo para administradores: `validate_slot`, `save_slot`,
  `delete_slot`, `validate_room`, `save_room`, `delete_room`, `get_global`, `validate_global`,
  `save_global`, `history`, `restore`. Las validaciones avisan (sin bloquear) si un sensor,
  actuador o canal no existe en Home Assistant.

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
