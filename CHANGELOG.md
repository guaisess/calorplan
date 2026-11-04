# Registro de cambios

Formato de versión: `AAAA.MM.V` (la versión vuelve a `.1` al empezar cada mes).

## 2026.11.10

**Reinicio seguro**: tras reiniciar Home Assistant, Calorplan ya no toca lo que estaba como estaba.

- **Espera tras arrancar** (ajuste global `startup_delay_seconds`, por defecto 120 s; editable en
  Casa → Comportamiento): ni la puesta al día ni los inicios de tramo que caigan en esa ventana
  actúan hasta que pase, para que las entidades se estabilicen. Los apagados no esperan.
- **Se recuerda lo ya gestionado:** se guarda qué inicio de cada tramo se encendió u omitió, y
  sobrevive al reinicio. Lo ya gestionado **no se vuelve a evaluar**: lo que estaba encendido sigue
  encendido y lo apagado sigue apagado (incluso si lo apagaste tú). Solo se aplica un inicio perdido
  mientras Home Assistant estaba apagado.
- **Nunca se enciende con datos ausentes al arrancar**, aunque la política sea «Encender
  igualmente». Se omite sin dar error ni aviso y se reintenta cada minuto durante 10 minutos hasta
  que los sensores informan. Los inicios programados normales siguen respetando tu política.
- Primer arranque con esta versión: lo que esté activo se considera gestionado (no toca nada).
- **Caché del navegador:** los imports del panel llevan `?v=<versión>` (antes se veían módulos
  antiguos tras actualizar y había que forzar la recarga). Test que impide olvidarlo y
  `tools/estampar_frontend.py` para estamparlo.

## 2026.11.9

- **Reevaluación durante el tramo** (nuevo ajuste global, `reevaluate_minutes`; 0 = desactivado,
  como hasta ahora). Si al inicio de un tramo no se cumplían las condiciones de temperatura (o
  faltaban datos de un sensor), se vuelve a comprobar cada N minutos mientras el tramo siga activo y
  se enciende si pasan a cumplirse. No actúa si el dispositivo ya está encendido (p. ej. a mano), no
  vuelve a encender después de que lo apagues, se detiene al terminar el tramo y respeta ausencia,
  pausas y deshabilitados. Las omisiones repetidas no se registran ni avisan: solo el encendido.
  Editable en Casa → Comportamiento.
- **Motivos más claros:** «Interior 17 °C no es menor que 17 °C» (antes «Interior 17 ≥ 17»).
- El simulador del panel dice «Si empezara ahora, encendería» (antes «Encendería»), porque describe
  qué pasaría si el tramo empezara en este momento, no que vaya a encender.

## 2026.11.8

**Pausas**: periodos en los que no se programan encendidos (vacaciones, visitas, obras...).

- Pausas por **habitación** y de **toda la casa**, con fecha de inicio y de fin (ambos días incluidos)
  o **sin fecha de fin** hasta que se quiten. Se pueden habilitar, deshabilitar y borrar.
- Mientras una pausa está activa se omiten los encendidos; los **apagados y reintentos siguen
  funcionando**, como en el modo ausencia. «Ejecutar tramo» con `force` la ignora.
- Un fin de pausa vacío se rechaza: «sin fecha de fin» debe ser una decisión explícita.
- Nueva vista **Pausas** en el panel, insignias «En pausa» y «Pausa global», y el simulador
  indica «No: en pausa». Nuevo sensor binario `binary_sensor.calorplan_<hab>_en_pausa`.
- Las omisiones por ausencia, pausa o tramo/habitación deshabilitados **nunca avisan**, ni siquiera
  con «avisar también si se omite» (evita avisos diarios sin interés).
- Orden de las pestañas del panel: Resumen, Casa, Tramos y Pausas.
- Comandos WebSocket `validate_pause`, `save_pause` y `delete_pause`. Guardar los ajustes globales
  o editar una habitación conserva sus pausas.

## 2026.11.7

- «Consigna» pasa a llamarse **«Temperatura objetivo»** en todo el panel (tabla de tramos,
  editor, descripciones) y en la documentación. Los nombres técnicos (`setpoint`) no cambian.

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
