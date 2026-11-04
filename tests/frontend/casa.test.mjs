// Versión: 2026.11.10
// Tests de la vista «Casa» (node --test): conversión de formularios y HTML.
process.env.TZ = "Europe/Madrid";

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const RUTA = "../../custom_components/calorplan/frontend/";
const casa = await import(`${RUTA}casa.js`);
const forms = await import(`${RUTA}forms.js`);
const vista = await import(`${RUTA}render_casa.js`);

const datos = JSON.parse(readFileSync(new URL("./overview.fixture.json", import.meta.url), "utf-8"));
const clonar = (o) => JSON.parse(JSON.stringify(o));

const GLOBAL = {
  outdoor_sensors: ["sensor.ext", "sensor.porche"], outdoor_aggregation: "mean", away_mode: true,
  shadow_mode: true, unavailable_policy: "do_not_start", catch_up: "none",
  channels: [
    { id: "telegram", type: "notify", service: "notify.telegram_ejemplo", templates: { on: "Hola {room}" } },
    { id: "movil", type: "notify", service: "notify.mobile_app_ejemplo" },
  ],
  default_notify: { mode: "both", channels: ["telegram"] }, templates: { on: "Enciende {room}" },
};
const CTX = {
  sensores: ["sensor.ext", "sensor.porche"], notify: ["notify.telegram_ejemplo"], climates: ["climate.a"],
  switches: ["switch.b"], canalesIds: ["telegram", "movil"], canalesGuardados: new Set(["telegram", "movil"]),
  variables: ["room", "slot"], plantillasDefecto: { on: "DEFECTO ON", off: "DEFECTO OFF" },
};

// --- forms.js ----------------------------------------------------------------------------------------------
test("parseEntries: uno, varios y marcado", () => {
  const f = forms.parseEntries([["a", "1"], ["b", "x"], ["b", "y"], ["c", "on"]]);
  assert.equal(f.uno("a"), "1");
  assert.equal(f.uno("z", "def"), "def");
  assert.deepEqual(f.varios("b"), ["x", "y"]);
  assert.deepEqual(f.varios("z"), []);
  assert.equal(f.marcado("c"), true);
  assert.equal(f.marcado("z"), false);
});

test("numero y lista", () => {
  assert.equal(forms.numero(""), null);
  assert.equal(forms.numero("  "), null);
  assert.equal(forms.numero("abc"), null);
  assert.equal(forms.numero("20.5"), 20.5);
  assert.equal(forms.numero("0"), 0);
  assert.deepEqual(forms.lista([" a ", "", "  ", "b"]), ["a", "b"]);
});

// --- Opciones desde hass ------------------------------------------------------------------------------------
test("entidades, sensores de temperatura y canales notify", () => {
  const states = {
    "sensor.t1": { attributes: { device_class: "temperature" } },
    "sensor.hum": { attributes: { device_class: "humidity" } },
    "sensor.t0": { attributes: { device_class: "temperature" } },
    "climate.a": { attributes: {} }, "notify.telegram_x": { attributes: {} },
  };
  assert.deepEqual(casa.entidadesDe(states, "climate"), ["climate.a"]);
  assert.deepEqual(casa.sensoresTemperatura(states), ["sensor.t0", "sensor.t1"]);
  const hass = { states, services: { notify: { movil: {}, notify: {} } } };
  assert.deepEqual(casa.canalesNotify(hass), ["notify.movil", "notify.notify", "notify.telegram_x"]);
  assert.deepEqual(casa.canalesNotify({}), []);
});

// --- formToGlobal ---------------------------------------------------------------------------------------------
test("formToGlobal conserva lo no editable y filtra lo vacío", () => {
  const g = casa.formToGlobal([
    ["sensor", " sensor.ext "], ["sensor", ""], ["outdoorAgg", "max"],
    ["ch_id", "telegram"], ["ch_service", "notify.t2"], ["ch_id", "nuevo"], ["ch_service", "notify.n"],
    ["ch_id", ""], ["ch_service", ""],
    ["dnMode", "on"], ["dnChannel", "telegram"], ["dnChannel", "fantasma"],
    ["tpl_on", "  Hola {room} "], ["tpl_off", ""], ["policy", "start_anyway"], ["catchUp", "evaluate"], ["shadow", "on"],
  ], GLOBAL);
  assert.deepEqual(g.outdoor_sensors, ["sensor.ext"]);
  assert.equal(g.outdoor_aggregation, "max");
  assert.equal(g.away_mode, true); // se conserva (tiene su propio interruptor)
  assert.equal(g.shadow_mode, true);
  assert.deepEqual(g.channels.map((c) => c.id), ["telegram", "nuevo"]);
  assert.equal(g.channels[0].service, "notify.t2");
  assert.deepEqual(g.channels[0].templates, { on: "Hola {room}" }); // plantilla del canal conservada
  assert.equal(g.channels[1].type, "notify");
  assert.deepEqual(g.default_notify, { mode: "on", channels: ["telegram"] }); // «fantasma» se descarta
  assert.deepEqual(g.templates, { on: "Hola {room}" }); // vacíos fuera
  assert.equal(g.unavailable_policy, "start_anyway");
  assert.equal(g.catch_up, "evaluate");
});

test("formToGlobal: sin casilla de sombra, el modo sombra queda desactivado", () => {
  assert.equal(casa.formToGlobal([["dnMode", "none"]], GLOBAL).shadow_mode, false);
});

// --- formToRoom -----------------------------------------------------------------------------------------------
test("formToRoom: climate con bloqueo y aviso propio", () => {
  const h = casa.formToRoom([
    ["name", " Cocina "], ["actuatorType", "climate"], ["entity", "climate.cocina"], ["lockSwitch", "switch.bloqueo"],
    ["lockStart", "lock"], ["lockEnd", "unlock"], ["offOnlyHeating", "on"], ["verify", "4"],
    ["sensor", "sensor.a"], ["sensor", " "], ["sensor", "sensor.b"], ["agg", "mean"],
    ["notifyMode", "both"], ["notifyChannel", "telegram"], ["enabled", "on"],
  ], { actuator: { hvac_mode_on: "heat_cool" } });
  assert.equal(h.name, "Cocina");
  assert.deepEqual(h.sensors, ["sensor.a", "sensor.b"]);
  assert.equal(h.indoor_aggregation, "mean");
  assert.deepEqual(h.notify, { mode: "both", channels: ["telegram"] });
  assert.equal(h.enabled, true);
  assert.deepEqual(h.actuator, {
    type: "climate", entity_id: "climate.cocina", child_lock_switch: "switch.bloqueo",
    child_lock_on_start: "lock", child_lock_on_end: "unlock", off_only_if_heating: true,
    verify_attempts: 4, hvac_mode_on: "heat_cool",
  });
});

test("formToRoom: un switch no lleva bloqueo infantil y 'heredar' deja notify en null", () => {
  const h = casa.formToRoom([
    ["name", "Toallero"], ["actuatorType", "switch"], ["entity", "switch.t"], ["lockSwitch", "switch.x"],
    ["notifyMode", "inherit"], ["verify", ""],
  ], null);
  assert.equal(h.actuator.child_lock_switch, null);
  assert.equal(h.notify, null);
  assert.equal(h.enabled, false); // casilla sin marcar
  assert.equal(h.actuator.off_only_if_heating, false);
  assert.equal(h.actuator.verify_attempts, 3); // valor por defecto
  assert.equal(h.actuator.hvac_mode_on, "heat");
});

test("habitacionVacia es una plantilla válida para el alta", () => {
  const h = casa.habitacionVacia();
  assert.equal(h.actuator.type, "climate");
  assert.deepEqual(h.sensors, [""]);
  assert.equal(h.enabled, true);
});

test("fmtFecha y clonar", () => {
  assert.equal(casa.fmtFecha("2026-11-03T16:49:45+01:00"), "03/11 16:49");
  const o = { a: [1] };
  const c = casa.clonar(o);
  c.a.push(2);
  assert.deepEqual(o.a, [1]);
});

// --- HTML ----------------------------------------------------------------------------------------------------------
test("renderValidacion", () => {
  assert.match(vista.renderValidacion(null), /Validando/);
  assert.match(vista.renderValidacion({ ok: true, warnings: ["Aviso <1>"] }), /✓ Válido.*Aviso &lt;1&gt;/s);
  const mal = vista.renderValidacion({ ok: false, error: "Plantilla mala" });
  assert.match(mal, /class="validacion error">Plantilla mala/);
});

test("renderGlobal: sensores, canales guardados y nuevos, aviso por defecto y plantillas", () => {
  const g = clonar(GLOBAL);
  g.channels.push({ id: "", service: "", type: "notify" });
  const html = vista.renderGlobal(g, CTX, { ok: true });
  assert.equal((html.match(/name="sensor"/g) || []).length, 2);
  assert.equal((html.match(/name="ch_id"/g) || []).length, 3);
  assert.equal((html.match(/readonly/g) || []).length, 2); // los guardados no se renombran
  assert.equal((html.match(/data-accion="probar-canal"/g) || []).length, 2); // el nuevo no se puede probar
  assert.match(html, /name="ch_id" data-estructural="1"/);
  assert.match(html, /name="dnChannel" value="telegram" checked/);
  assert.doesNotMatch(html, /name="dnChannel" value="movil" checked/);
  assert.match(html, /<option value="mean" selected>/);
  assert.match(html, /placeholder="DEFECTO ON">Enciende {room}<\/textarea>/);
  assert.match(html, /placeholder="DEFECTO OFF"><\/textarea>/);
  assert.match(html, /name="shadow" value="on" checked/);
  assert.match(html, /<code>{room}<\/code>/);
  assert.doesNotMatch(html, /data-accion="guardar-global" disabled/);
});

test("renderGlobal: el botón de guardar está deshabilitado hasta validar", () => {
  assert.match(vista.renderGlobal(clonar(GLOBAL), CTX, null), /data-accion="guardar-global" disabled/);
  assert.match(vista.renderGlobal(clonar(GLOBAL), CTX, { ok: false, error: "x" }), /data-accion="guardar-global" disabled/);
});

test("renderGlobal escapa los valores", () => {
  const g = clonar(GLOBAL);
  g.outdoor_sensors = ['"><script>x</script>'];
  const html = vista.renderGlobal(g, CTX, { ok: true });
  assert.doesNotMatch(html, /<script>/);
});

test("renderHabitaciones muestra una fila por habitación con sus acciones", () => {
  const html = vista.renderHabitaciones(datos);
  assert.equal((html.match(/data-accion="editar-habitacion"/g) || []).length, 3);
  assert.match(html, /climate · climate\.calefaccion_dormitorio/);
  assert.match(html, /2 sensor\(es\)/);
  assert.match(html, /El más frío \(mínimo\)/);
  const d = clonar(datos);
  d.rooms[0].enabled = false;
  assert.match(vista.renderHabitaciones(d), /\(deshabilitada\)/);
  assert.match(vista.renderHabitaciones({ rooms: [] }), /No hay habitaciones/);
});

test("renderFormHabitacion: climate muestra bloqueo; switch no", () => {
  const sala = clonar(datos.rooms[0].config);
  const html = vista.renderFormHabitacion(sala, CTX, { ok: true });
  assert.match(html, /name="lockSwitch"/);
  assert.match(html, /name="entity" list="dl-climate" value="climate\.calefaccion_dormitorio"/);
  assert.equal((html.match(/name="sensor"/g) || []).length, 2);
  assert.doesNotMatch(html, /name="notifyChannel"/); // hereda: no hay canales propios
  const sw = clonar(datos.rooms[1].config);
  const htmlSw = vista.renderFormHabitacion(sw, CTX, { ok: true });
  assert.doesNotMatch(htmlSw, /name="lockSwitch"/);
  assert.match(htmlSw, /list="dl-switch"/);
});

test("renderFormHabitacion: aviso propio muestra los canales marcados", () => {
  const sala = clonar(datos.rooms[0].config);
  sala.notify = { mode: "both", channels: ["movil"] };
  const html = vista.renderFormHabitacion(sala, CTX, { ok: true });
  assert.match(html, /name="notifyChannel" value="movil" checked/);
  assert.doesNotMatch(html, /name="notifyChannel" value="telegram" checked/);
  assert.match(html, /<option value="both" selected>/);
});

test("renderFormHabitacion: alta nueva con la plantilla vacía y guardar deshabilitado", () => {
  const html = vista.renderFormHabitacion(casa.habitacionVacia(), CTX, null);
  assert.match(html, /data-accion="guardar-habitacion" disabled/);
  assert.match(html, /name="actuatorType" data-estructural="1"/);
});

test("las zonas de validación tienen ids distintos (global y diálogo)", () => {
  const g = vista.renderGlobal(clonar(GLOBAL), CTX, { ok: true });
  const h = vista.renderFormHabitacion(casa.habitacionVacia(), CTX, { ok: true });
  assert.match(g, /id="validacion-global"/);
  assert.match(h, /id="validacion-habitacion"/);
  assert.doesNotMatch(g + h, /id="validacion"/);
});

test("renderHistorial", () => {
  const f = (iso) => `F:${iso}`;
  assert.match(vista.renderHistorial([], f), /Todavía no hay versiones/);
  const html = vista.renderHistorial([{ index: 0, time: "t0", reason: "Guardar tramo a/b", rooms: 3, slots: 7 }], f);
  assert.match(html, /F:t0/);
  assert.match(html, /Antes de: Guardar tramo a\/b/);
  assert.match(html, /3 habitaciones, 7 tramos/);
  assert.match(html, /data-accion="restaurar" data-i="0"/);
});

test("renderCasa y renderVistas", () => {
  const html = vista.renderCasa(datos, clonar(GLOBAL), CTX, { ok: true });
  assert.match(html, /Ajustes globales/);
  assert.match(html, /data-accion="historial"/);
  assert.match(html, /data-accion="nueva-habitacion"/);
  assert.match(vista.renderVistas("casa"), /data-vista="casa" class="sel"/);
  assert.match(vista.renderVistas("casa"), /data-vista="resumen" class=""/);
});

// --- Reevaluación durante el tramo -----------------------------------------------------------------------------
test("formToGlobal: reevaluate_minutes se lee como número, y vacío o ausente es 0", () => {
  assert.equal(casa.formToGlobal([["reevaluate", "15"]], GLOBAL).reevaluate_minutes, 15);
  assert.equal(casa.formToGlobal([["reevaluate", ""]], GLOBAL).reevaluate_minutes, 0);
  assert.equal(casa.formToGlobal([["dnMode", "none"]], GLOBAL).reevaluate_minutes, 0);
  // Un valor inválido llega tal cual para que el servidor lo rechace con su mensaje
  assert.equal(casa.formToGlobal([["reevaluate", "-5"]], GLOBAL).reevaluate_minutes, -5);
});

test("renderGlobal: campo de reevaluación con su ayuda", () => {
  const g = clonar(GLOBAL);
  g.reevaluate_minutes = 15;
  const html = vista.renderGlobal(g, CTX, { ok: true });
  assert.match(html, /name="reevaluate" min="0" max="1440" value="15"/);
  assert.match(html, /Reevaluar durante el tramo cada \(minutos; 0 = solo al inicio\)/);
  assert.match(html, /No actúa si ya está encendido ni después de apagarlo tú/);
  assert.match(vista.renderGlobal(clonar(GLOBAL), CTX, { ok: true }), /name="reevaluate"[^>]*value="0"/); // sin dato: 0
});

// --- Espera tras arrancar ---------------------------------------------------------------------------------------
test("formToGlobal: startup_delay_seconds, y vacío o ausente es el valor por defecto (120)", () => {
  assert.equal(casa.formToGlobal([["startupDelay", "300"]], GLOBAL).startup_delay_seconds, 300);
  assert.equal(casa.formToGlobal([["startupDelay", "0"]], GLOBAL).startup_delay_seconds, 0);
  assert.equal(casa.formToGlobal([["startupDelay", ""]], GLOBAL).startup_delay_seconds, 120);
  assert.equal(casa.formToGlobal([["dnMode", "none"]], GLOBAL).startup_delay_seconds, 120);
});

test("renderGlobal: campo de espera tras arrancar con su ayuda", () => {
  const g = clonar(GLOBAL);
  g.startup_delay_seconds = 300;
  const html = vista.renderGlobal(g, CTX, { ok: true });
  assert.match(html, /name="startupDelay" min="0" max="3600" value="300"/);
  assert.match(html, /Esperar tras arrancar Home Assistant antes de actuar \(segundos\)/);
  assert.match(html, /nunca se enciende con datos ausentes/);
  assert.match(vista.renderGlobal(clonar(GLOBAL), CTX, { ok: true }), /name="startupDelay"[^>]*value="120"/);
});
