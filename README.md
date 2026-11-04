# Calorplan

Programador de calefacción **por habitación** para Home Assistant, instalable con HACS.

Cada habitación tiene **tramos** horarios con sus propias condiciones (temperatura exterior e interior, días de la semana). Un único motor interno los ejecuta: no necesitas una automatización por habitación.

> **Estado: Fase 1 (núcleo).** Aún no hay panel visual; la configuración se importa desde un JSON. Empieza siempre con `shadow_mode: true` (modo sombra) para comprobar lo que haría sin que actúe.

## Qué hace

- Tramos con hora de inicio y fin **o** duración (útil para toalleros eléctricos), días y temperatura objetivo.
- Condiciones por tramo: enciende solo si `exterior < X` e `interior < Y`. Los sensores de cada grupo se agregan por el **mínimo** y los no disponibles se ignoran.
- Actuadores `climate` (modo `heat` + temperatura objetivo) y `switch` (enchufes, toalleros).
- **Bloqueo infantil** opcional (switch asociado) configurable al encender y al apagar: `lock`, `unlock` o `none`.
- **Apagado verificado**: espera a que el dispositivo esté disponible, apaga, comprueba el estado y reintenta; si falla, avisa siempre.
- Reintento de apagado a los N minutos (se ignora si hay otro tramo activo).
- **Modo ausencia**: omite los encendidos; los apagados siguen funcionando.
- **Modo sombra**: no ejecuta nada ni avisa; solo registra lo que habría hecho.
- Avisos por tramo (ninguno / encendido / apagado / ambos), con canales y plantillas configurables, heredados tramo → habitación → global.
- Evento `calorplan_action` en el bus en cada decisión, para tus automatizaciones.

## Instalación (HACS)

1. HACS → ⋮ → *Repositorios personalizados* → añade `https://github.com/guaisess/calorplan` con categoría *Integración*.
2. Instala **Calorplan** y reinicia Home Assistant.
3. *Ajustes → Dispositivos y servicios → Añadir integración → Calorplan*.
4. Copia tu configuración a `/config/calorplan.json` (parte de [`examples/config_ejemplo.json`](examples/config_ejemplo.json)) y llama al servicio:

```yaml
action: calorplan.import_config
data:
  path: /config/calorplan.json
```

La ruta puede ser relativa a la carpeta de configuración o absoluta dentro de ella; fuera de ahí debe estar en `allowlist_external_dirs`.

## Configuración

Ejemplo mínimo (la referencia completa está en [`docs/DISENO.md`](docs/DISENO.md)):

```json
{
  "version": 1,
  "global": {
    "outdoor_sensors": ["sensor.temperatura_exterior"],
    "shadow_mode": true,
    "channels": [{ "id": "telegram", "type": "notify", "service": "notify.telegram_ejemplo" }],
    "default_notify": { "mode": "both", "channels": ["telegram"] }
  },
  "rooms": [{
    "id": "dormitorio",
    "name": "Dormitorio",
    "actuator": {
      "type": "climate",
      "entity_id": "climate.calefaccion_dormitorio",
      "child_lock_switch": "switch.calefaccion_dormitorio_bloqueo_infantil",
      "child_lock_on_start": "lock",
      "child_lock_on_end": "none"
    },
    "sensors": ["sensor.dormitorio_temperatura"],
    "slots": [{
      "id": "madrugada", "name": "Madrugada", "days": [0, 1, 2, 3, 4],
      "start": "06:00", "end": "07:00", "setpoint": 20,
      "conditions": { "outdoor_below": 10, "indoor_below": 16 }
    }]
  }]
}
```

**Reinicio seguro.** Tras reiniciar Home Assistant, Calorplan espera `global.startup_delay_seconds` (por defecto 120 s) antes de actuar. Recuerda qué inicio de cada tramo ya gestionó (se guarda en disco): lo ya gestionado no se vuelve a evaluar, así que lo encendido sigue encendido y lo apagado sigue apagado; solo se aplica un inicio perdido mientras Home Assistant estaba apagado, y nunca con datos de sensores ausentes (se reintenta cada minuto durante 10 minutos).

**Reevaluación durante el tramo.** Por defecto las condiciones se comprueban solo al inicio de cada tramo. Con `global.reevaluate_minutes` (por ejemplo `15`) se vuelven a comprobar cada N minutos si el inicio se omitió por condiciones, y se enciende si pasan a cumplirse mientras el tramo sigue activo. No actúa si ya está encendido ni después de que lo apagues tú, y las omisiones repetidas no se registran ni avisan.

**Varios sensores.** Tanto los sensores exteriores (`global.outdoor_aggregation`) como los de cada habitación (`indoor_aggregation`) se combinan con `min` (por defecto: el más frío), `max` (el más cálido; el más conservador) o `mean` (media). Los sensores sin datos se ignoran.

Notas: `days` usa 0 = lunes … 6 = domingo; el día de un tramo es el de su inicio (un tramo que cruza la medianoche termina al día siguiente); los tramos de una misma habitación no pueden solaparse.

**Tus datos personales** (servicios `notify`, identificadores de Telegram) no deben subirse al repositorio: guárdalos en tu configuración local de Home Assistant. La carpeta `local/` de este repositorio está ignorada por git.

En `channels`, `service` puede ser un servicio `notify.<nombre>` o una entidad `notify.*` (por ejemplo Telegram en versiones recientes de Home Assistant).

## Panel

Tras importar la configuración aparece **Calorplan** en la barra lateral (solo administradores) con cuatro vistas: Resumen, Casa, Tramos y Pausas.

**Resumen** (solo lectura)
- **Línea de tiempo** por día de la semana: una fila por habitación, barras por tramo (verde = activo ahora, gris = deshabilitado) y marca de la hora actual.
- **Estado ahora**: estado del actuador, tramo activo, próximo evento, última acción (indica si fue simulada) y el simulador **«¿qué haría ahora?»**, que evalúa las condiciones con los valores actuales sin ejecutar nada.

**Pausas** (edición)
- Periodos sin programación: **vacaciones, visitas, obras**... Una pausa puede ser de una habitación o de **toda la casa**, con fecha de inicio y de fin (ambos incluidos) o **sin fecha de fin** hasta que la quites.
- Mientras está activa no se programan encendidos; los **apagados siguen funcionando** para que nunca quede nada encendido. Se puede habilitar, deshabilitar o borrar en cualquier momento.
- El sensor `binary_sensor.calorplan_<habitación>_en_pausa` indica si una habitación está en pausa (por su propia pausa o por la de la casa).

**Tramos** (edición)
- Una tarjeta por habitación con sus tramos. Alta, edición, **duplicado**, habilitar/deshabilitar y borrado.
- El editor admite hora de fin **o** duración, temperatura objetivo (solo termostatos), condiciones de temperatura exterior e interior, reintento de apagado y avisos propios. Indica con qué tramos se solapa antes de guardar.

**Casa** (edición)
- **Ajustes globales**: sensores exteriores y cómo se combinan (más frío, más cálido o media), canales de aviso (con botón *Probar*), aviso por defecto, mensajes, política si falta un sensor, comportamiento al arrancar y **modo sombra**.
- **Habitaciones**: alta, edición y baja con su `climate` o `switch`, bloqueo infantil, sensores y agregación.
- Cada cambio se **valida en el servidor** antes de guardar y se conserva una **copia de las últimas 10 versiones**, que se pueden restaurar desde *Historial*.

## Entidades

| Entidad | Contenido |
|---|---|
| `switch.calorplan_<habitación>` | Habilita o deshabilita la habitación |
| `switch.calorplan_modo_ausencia` | Modo ausencia global |
| `sensor.calorplan_<habitación>_proximo` | Próximo evento (marca de tiempo) |
| `sensor.calorplan_<habitación>_ultima_accion` | Última decisión y su motivo (atributos) |
| `binary_sensor.calorplan_<habitación>_tramo_activo` | `on` dentro de un tramo habilitado |

## Servicios

| Servicio | Para qué |
|---|---|
| `calorplan.import_config` | Sustituye el plan por un JSON (`path` o `config`) |
| `calorplan.run_slot` | Ejecuta ahora el inicio de un tramo (`force` ignora condiciones) |
| `calorplan.set_away` | Activa o desactiva el modo ausencia |
| `calorplan.test_notification` | Envía un aviso de prueba a un canal |
| `calorplan.reload` | Recarga la integración |

## Desarrollo y tests

El núcleo (`custom_components/calorplan/core`) es Python puro y se prueba sin Home Assistant:

```bash
pip install -r requirements_test.txt
python -m pytest
node --test tests/frontend/*.test.mjs
```

Si cambia el formato de la API del panel, regenera el fixture del frontend con `python tests/frontend/generar_fixture.py`.

La capa `ha/` y las plataformas necesitan Home Assistant; se validan en CI con `hassfest` y la validación de HACS.

## Convenciones

Código comentado en español, orientado a objetos, ficheros pequeños, valores en `core/settings.py` y versión `AAAA.MM.V` (ver [CHANGELOG](CHANGELOG.md)).

## Licencia

MIT — ver [LICENSE](LICENSE).
