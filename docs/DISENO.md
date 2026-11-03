# Calorplan — Diseño técnico

**Versión del documento:** 2026.11.2
**Estado:** borrador para aprobación
**Autor:** Alfredo Fernández Badía
**Nombre de trabajo:** `calorplan` (dominio de la integración; se puede renombrar antes de crear el repositorio)

## 1. Objetivo

Programador de calefacción por habitación para Home Assistant, distribuido como **integración personalizada vía HACS (repositorio público)**.

- Cada habitación tiene **tramos** horarios y cada tramo tiene sus **condiciones** (temperatura exterior, temperatura interior, días).
- Un único motor interno ejecuta los tramos; no hay automatizaciones por habitación.
- **Avisos configurables** por tramo: ninguno, solo encendido, solo apagado o ambos, con elección de canales.
- **Edición visual** (panel en la barra lateral + tarjeta Lovelace). Sin tocar YAML.
- Replica la lógica actual (ver sección 4) para poder migrar sin perder funciones.

Fuera de alcance de la primera versión: refrigeración, aprendizaje adaptativo (precalentamiento), multi-zona con prioridades.

## 2. Decisiones ya tomadas

| Tema | Decisión |
|---|---|
| Distribución | Repositorio HACS público (`hacs.json`, README, traducciones, tests, CI desde el inicio). |
| Edición | Panel visual + tarjeta, en una segunda fase. |
| Alcance | Replicar lo actual: bloqueo infantil, mínimo de varios sensores, reintentos de apagado, modo ausencia. |
| Convenciones | Código comentado en español, orientado a objetos, ficheros pequeños, sin valores fijos en el código (todo en configuración), versión `AAAA.MM.V`. |

## 3. Arquitectura

```
┌──────────────── Frontend (panel + tarjeta) ───────────────┐
│  Editor de tramos · línea de tiempo · simulador           │
└───────────────┬───────────────────────────────────────────┘
                │ WebSocket API (calorplan/*)
┌───────────────▼───────────────────────────────────────────┐
│ Integración Python                                         │
│  Almacén (Store)  ←→  Modelos  ←→  Motor                   │
│                                     ├─ Planificador (disparos)
│                                     ├─ Evaluador (condiciones)
│                                     ├─ Ejecutor (acciones + verificación)
│                                     └─ Notificador (canales)
│  Entidades: switch · sensor · binary_sensor                │
│  Servicios · Eventos del bus                               │
└────────────────────────────────────────────────────────────┘
```

Principios:

- **Una única fuente de verdad**: el almacén (`.storage/calorplan`). El frontend solo lo modifica por la API WebSocket.
- **El motor no conoce marcas**: habla con `climate.*` y `switch.*` a través de la capa "actuador".
- **Todo es observable**: cada decisión (encendió, no encendió y por qué) queda como atributo y como evento.

## 4. Lógica actual que se replica

Extraída de `automations.yaml` y `scripts.yaml`:

| Función actual | Cómo se cubre |
|---|---|
| Mínimo de varios sensores por habitación (`float(99)` si falla) | Agregación `min` de la lista de sensores; **no disponibles se ignoran**. Si todos fallan, política configurable (por defecto: no encender, como ahora). |
| Exterior = mínimo entre exterior y porche | Lista de sensores exteriores global, misma agregación. |
| Encender solo si `Ext < X` y `T < Y` | Condiciones por tramo. |
| `climate.set_hvac_mode heat` + `set_temperature` + bloqueo infantil + aviso | Actuador `climate` con `child_lock_switch` opcional. |
| Apagado solo si el climate está en `heat` | Comportamiento `off_only_if_heating` (activo por defecto). |
| Reintento de apagado a +5 min | `retry_off_minutes` por tramo. |
| Apagado de toalleros: espera disponibilidad, hasta 5 intentos, aviso si falla | **Verificación de apagado** en el ejecutor (`verify_attempts`, `verify_timeout`) con aviso de fallo siempre activo. |
| Toalleros: encender y apagar tras 1 h 30 / 1 h 45 | Tramo con `duration_minutes` en lugar de hora de fin. |
| 5 automatizaciones «Anular encendido…» | Un único interruptor global **modo ausencia** (y uno por habitación). |
| Avisos de Telegram | Canales de aviso configurables (ver sección 7). |

## 5. Modelo de datos

```jsonc
{
  "version": 1,
  "global": {
    "outdoor_sensors": ["sensor.temperatura_exterior_temperatura", "sensor.tmp_porche_temperature"],
    "away_mode": false,
    "unavailable_policy": "do_not_start",       // do_not_start | start_anyway
    "channels": [
      { "id": "telegram", "type": "notify", "service": "notify.telegram_ejemplo" },
      { "id": "movil",    "type": "notify", "service": "notify.mobile_app_ejemplo" }
    ],
    "default_notify": { "mode": "both", "channels": ["telegram"] }
  },
  "rooms": [
    {
      "id": "alba",
      "name": "Alba",
      "enabled": true,
      "actuator": {
        "type": "climate",                       // climate | switch
        "entity_id": "climate.calefaccion_alba",
        "child_lock_switch": "switch.calefaccion_alba_bloque_infantil",
        "off_only_if_heating": true,
        "verify_attempts": 3
      },
      "sensors": [
        "sensor.tmp_alba_temperature",
        "sensor.dormitorio_alba_digital_temperature"
      ],
      "notify": null,                            // null = hereda de global
      "slots": [
        {
          "id": "manana",
          "name": "Madrugada",
          "enabled": true,
          "days": [0, 1, 2, 3, 4],               // 0 = lunes
          "start": "06:00",
          "end": "07:00",                        // o "duration_minutes": 90
          "setpoint": 20,
          "retry_off_minutes": 5,
          "conditions": { "outdoor_below": 10, "indoor_below": 16 },
          "notify": { "mode": "both", "channels": ["telegram", "movil"] }
        }
      ]
    }
  ]
}
```

Reglas de validación (al guardar, en el servidor):

- Tramos de una misma habitación **no se solapan** (se admite cruzar medianoche).
- `end` o `duration_minutes`, nunca los dos.
- Las entidades deben existir; los sensores deben ser de temperatura.
- Cualquier cambio de esquema incrementa `version` y tiene migración.

## 6. Semántica del motor

1. **Planificación**: por cada tramo se programa el inicio y el fin con `async_track_time_change`. Se recalcula al guardar cambios y al cambiar la hora del sistema.
2. **Inicio de tramo** (si la habitación y el tramo están habilitados y no hay modo ausencia):
   1. Evalúa las condiciones (`outdoor_below` y `indoor_below` con los valores en ese instante).
   2. Si se cumplen: ejecuta el actuador (`heat`, temperatura objetivo, bloqueo infantil) y envía el aviso de encendido.
   3. Si no: registra el motivo ("exterior 17 ≥ 15") y **no** avisa, salvo que el tramo tenga activado «avisar también si se omite».
3. **Fin de tramo**: apaga con `off_only_if_heating`, verifica el estado con reintentos y envía el aviso de apagado. Programa el reintento a `retry_off_minutes`.
4. **Arranque de Home Assistant dentro de un tramo**: política `catch_up` configurable (`none` por defecto; `evaluate` aplica el tramo activo si las condiciones se cumplen).
5. **Modo ausencia**: los inicios se omiten. Los finales y reintentos de apagado **siguen funcionando** (nunca deja algo encendido).
6. **Fallos**: actuador no disponible, apagado no verificado o sensor sin datos generan un aviso de error independiente de la configuración de avisos.

## 7. Avisos

- Modo por tramo: `none` · `on` · `off` · `both`. Se hereda: tramo → habitación → global.
- Canales: tipo `notify` (cualquier servicio `notify.*`: Telegram, móvil, etc.). Cada tramo elige qué canales usa.
- Plantilla de mensaje con variables: `{room}`, `{slot}`, `{action}`, `{setpoint}`, `{outdoor}`, `{indoor}`, `{reason}`, `{time}`. Una plantilla global editable y una opcional por canal.
- Evento del bus `calorplan_action` en cada acción (para automatizaciones externas).
- Servicio `calorplan.test_notification` para probar un canal desde el panel.

## 8. Entidades, servicios y eventos

Entidades:

| Plataforma | Entidad | Contenido |
|---|---|---|
| `switch` | `switch.calorplan_<hab>` | Habilita o deshabilita la habitación. |
| `switch` | `switch.calorplan_modo_ausencia` | Modo ausencia global. |
| `sensor` | `sensor.calorplan_<hab>_proximo` | Próximo evento (marca de tiempo); atributos: tramo, acción, condiciones. |
| `sensor` | `sensor.calorplan_<hab>_ultima_accion` | Última decisión y su motivo. |
| `binary_sensor` | `binary_sensor.calorplan_<hab>_tramo_activo` | `on` dentro de un tramo habilitado. |

Servicios: `run_slot` (ejecutar ahora), `skip_next` (saltar el próximo inicio), `set_away`, `test_notification`, `reload`.
La creación y edición de tramos va por la API WebSocket del panel (con validación), no por servicios.

## 9. Frontend

- **Panel lateral** (`calorplan-panel`): lista de habitaciones, editor de tramos (hora, días, temperatura objetivo, condiciones, avisos), ajustes globales y canales.
- **Línea de tiempo** del día/semana con barras por habitación (el diagrama tipo Gantt que ya usamos en la vista actual).
- **Simulador** «¿qué haría ahora?»: evalúa los tramos con los valores actuales y muestra el resultado sin ejecutar nada.
- **Tarjeta Lovelace** (`calorplan-card`): resumen de una o varias habitaciones con próximo evento y atajos (saltar, ausencia).
- Tecnología: componentes web con Lit, compilados con esbuild y el resultado versionado en el repositorio (sin necesidad de compilar al instalar vía HACS).

## 10. Estructura del repositorio

```
calorplan/
├─ custom_components/calorplan/
│  ├─ __init__.py            # puesta en marcha e integración con HA
│  ├─ manifest.json          # version "AAAA.MM.V"
│  ├─ settings.py            # TODOS los valores por defecto y constantes
│  ├─ config_flow.py         # alta inicial (sensores exteriores, canales)
│  ├─ storage.py             # almacén y migraciones de esquema
│  ├─ models/                # room.py · slot.py · actuator.py · notify.py
│  ├─ engine/                # planner.py · evaluator.py · executor.py · notifier.py
│  ├─ entities/              # switch.py · sensor.py · binary_sensor.py
│  ├─ services.py · services.yaml
│  ├─ websocket_api.py       # CRUD para el frontend
│  ├─ frontend/              # panel y tarjeta (dist/)
│  └─ translations/          # es.json · en.json
├─ frontend-src/             # código fuente Lit (no se instala)
├─ tests/                    # pytest + pytest-homeassistant-custom-component
├─ docs/                     # este diseño, guía de uso, migración
├─ .github/workflows/        # hassfest · HACS validate · pytest · build frontend
├─ hacs.json · README.md · CHANGELOG.md · LICENSE (MIT)
```

## 11. Calidad y versionado

- Versión `AAAA.MM.V` en `manifest.json`, en cada fichero modificado y en `CHANGELOG.md`. Empieza en `AAAA.MM.1` cada mes.
- Tests unitarios del evaluador y el planificador con tiempo simulado; tests de integración con entidades falsas; validación `hassfest` y `HACS` en CI.
- Todas las cadenas visibles en `translations/` (español e inglés).

## 12. Fases y criterios de aceptación

| Fase | Contenido | Se da por terminada cuando |
|---|---|---|
| **1. Núcleo** | Modelos, almacén, motor, actuadores (`climate` y `switch`), avisos, entidades, servicios. Configuración inicial por JSON. | Los 5 climas y 2 toalleros pasan los tests con los horarios actuales. |
| **2. Modo sombra** | Corre en paralelo a la automatización actual **sin actuar**: solo registra lo que habría hecho. | Una semana sin diferencias frente a la automatización actual. |
| **3. Panel visual** | Editor de tramos, línea de tiempo, simulador, tarjeta. | Se puede crear, editar y borrar un tramo sin tocar ficheros. |
| **4. Corte** | Se desactiva la automatización antigua, se retiran las «Anular encendido…» y se activa el motor. | Una semana operando, con copias de seguridad de lo anterior. |
| **5. Publicación** | README, capturas, CI verde, versión inicial en HACS. | `hassfest` y `HACS validate` en verde. |

## 13. Riesgos y decisiones abiertas

- **Nombre**: `calorplan` es provisional. Hay que comprobar que no choca con otro proyecto antes de crear el repositorio.
- **Bloqueo infantil**: hoy se activa junto con el encendido. Se mantiene igual; falta confirmar si debe desbloquearse al apagar.
- **Marcas de dispositivo**: el motor solo asume `climate.set_hvac_mode`, `climate.set_temperature` y `switch.turn_on/off`. Si algún termostato necesita algo distinto, se resuelve con un tipo de actuador nuevo.
- **Mantenimiento a largo plazo**: al ser público, hay que asumir compatibilidad con versiones futuras de Home Assistant y soporte básico a otros usuarios.
