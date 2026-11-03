# Registro de cambios

Formato de versión: `AAAA.MM.V` (la versión vuelve a `.1` al empezar cada mes).

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
