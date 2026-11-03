// Versión: 2026.11.6
// Tests de la edición de tramos (node --test): borradores, formulario y HTML.
process.env.TZ = "Europe/Madrid";

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const RUTA = "../../custom_components/calorplan/frontend/";
const tramos = await import(`${RUTA}tramos.js`);
const vista = await import(`${RUTA}render_tramos.js`);
const casa = await import(`${RUTA}render_casa.js`);

const datos = JSON.parse(readFileSync(new URL("./overview.fixture.json", import.meta.url), "utf-8"));
const clonar = (o) => JSON.parse(JSON.stringify(o));
const [dormitorio, despacho, toallero] = datos.rooms;
const CTX = { canalesIds: ["telegram", "movil"] };

// --- Borradores ---------------------------------------------------------------------------------------------
test("tramoVacio: la consigna solo aplica a termostatos", () => {
  const t = tramos.tramoVacio(dormitorio);
  assert.equal(t.setpoint, 20);
  assert.deepEqual(t.days, [0, 1, 2, 3, 4, 5, 6]);
  assert.equal(t.start, "08:00");
  assert.equal(t.end, "09:00");
  assert.equal(t.notify, null);
  assert.equal(tramos.tramoVacio(despacho).setpoint, null);
});

test("duplicarTramo quita el id y marca el nombre", () => {
  const original = dormitorio.slots[0].config;
  const copia = tramos.duplicarTramo(original);
  assert.equal(copia.id, undefined);
  assert.equal(copia.name, "Madrugada (copia)");
  assert.equal(original.id, "madrugada"); // el original no cambia
  copia.days.push(5);
  assert.deepEqual(original.days, [0, 1, 2, 3, 4]);
});

// --- formToSlot -----------------------------------------------------------------------------------------------
test("formToSlot: tramo con hora de fin en un termostato", () => {
  const t = tramos.formToSlot([
    ["name", " Noche "], ["days", "4"], ["days", "0"], ["days", "2"], ["start", "21:00"], ["endMode", "end"], ["end", "23:30"],
    ["setpoint", "21.5"], ["outdoor", "12"], ["indoor", ""], ["retry", "10"], ["notifyMode", "inherit"], ["enabled", "on"],
  ], dormitorio);
  assert.deepEqual(t, {
    name: "Noche", enabled: true, days: [0, 2, 4], start: "21:00", setpoint: 21.5, retry_off_minutes: 10,
    conditions: { outdoor_below: 12, indoor_below: null }, notify: null, notify_on_skip: false, end: "23:30",
  });
});

test("formToSlot: duración, switch sin consigna, aviso propio y avisar al omitir", () => {
  const t = tramos.formToSlot([
    ["name", "Toallero"], ["days", "0"], ["start", "05:50"], ["endMode", "duration"], ["duration", "105"],
    ["setpoint", "22"], ["notifyMode", "both"], ["notifyChannel", "telegram"], ["notifySkip", "on"],
  ], toallero);
  assert.equal(t.duration_minutes, 105);
  assert.equal("end" in t, false);
  assert.equal(t.setpoint, null); // un switch no tiene consigna
  assert.deepEqual(t.notify, { mode: "both", channels: ["telegram"] });
  assert.equal(t.notify_on_skip, true);
  assert.equal(t.enabled, false); // casilla sin marcar
  assert.equal(t.retry_off_minutes, 5); // valor por defecto si está vacío
});

test("formToSlot: al cambiar de modo se usan valores por defecto del campo que aún no existe", () => {
  const aDuracion = tramos.formToSlot([["name", "x"], ["start", "08:00"], ["endMode", "duration"], ["end", "09:00"]], despacho);
  assert.equal(aDuracion.duration_minutes, 60);
  const aFin = tramos.formToSlot([["name", "x"], ["start", "08:00"], ["endMode", "end"], ["duration", "30"]], despacho);
  assert.equal(aFin.end, "09:00");
  assert.equal("duration_minutes" in aFin, false);
});

test("formToSlot: una duración vacía llega como null para que el servidor la rechace", () => {
  const t = tramos.formToSlot([["name", "x"], ["start", "08:00"], ["endMode", "duration"], ["duration", ""]], despacho);
  assert.equal(t.duration_minutes, null);
});

// --- HTML -------------------------------------------------------------------------------------------------------
test("horario y condiciones", () => {
  assert.equal(vista.horario({ start: "06:00", duration_minutes: 60 }), "06:00–07:00");
  assert.equal(vista.horario({ start: "23:00", duration_minutes: 120 }), "23:00–01:00");
  assert.equal(vista.horario(toallero.slots[0]), "05:50–07:35");
  assert.equal(vista.condiciones({ outdoor_below: 15, indoor_below: 16 }), "ext < 15 · int < 16");
  assert.equal(vista.condiciones({ outdoor_below: null, indoor_below: 18.5 }), "int < 18.5");
  assert.equal(vista.condiciones({ outdoor_below: null, indoor_below: null }), "—");
});

test("renderTramos: una tarjeta por habitación, ordenado por hora y con acciones", () => {
  const html = vista.renderTramos(datos);
  assert.equal((html.match(/data-accion="nuevo-tramo"/g) || []).length, 3);
  assert.equal((html.match(/data-accion="editar-tramo"/g) || []).length, 6); // 3 + 2 + 1
  assert.ok(html.indexOf("Madrugada") < html.indexOf("Tarde") && html.indexOf("Tarde") < html.indexOf("Noche"));
  assert.match(html, /L–V/);
  assert.match(html, /20 °C/);
  assert.match(html, /ext &lt; 10 · int &lt; 16|ext < 10 · int < 16/);
  assert.match(html, /data-accion="alternar-tramo" data-room="dormitorio" data-slot="madrugada">Deshabilitar/);
});

test("renderTramos: un tramo deshabilitado se marca y ofrece habilitar; sin tramos, ayuda", () => {
  const d = clonar(datos);
  d.rooms[0].slots[0].enabled = false;
  const html = vista.renderTramos(d);
  assert.match(html, /class="tramo-off"/);
  assert.match(html, />Habilitar</);
  d.rooms[2].slots = [];
  assert.match(vista.renderTramos(d), /No hay tramos en esta habitación/);
  assert.match(vista.renderTramos({ rooms: [] }), /No hay habitaciones/);
});

test("renderFormTramo: climate con hora de fin", () => {
  const html = vista.renderFormTramo(clonar(dormitorio.slots[0].config), dormitorio, CTX, { ok: true, conflicts: [] });
  assert.match(html, /name="days" value="0" checked/);
  assert.doesNotMatch(html, /name="days" value="5" checked/);
  assert.match(html, /name="setpoint"/);
  assert.match(html, /name="end" value="07:00"/);
  assert.doesNotMatch(html, /name="duration"/);
  assert.match(html, /name="endMode" value="end" data-estructural="1" checked/);
  assert.doesNotMatch(html, /name="notifyChannel"/); // hereda
  assert.doesNotMatch(html, /data-accion="guardar-tramo" disabled/);
});

test("renderFormTramo: switch con duración, sin consigna", () => {
  const html = vista.renderFormTramo(clonar(toallero.slots[0].config), toallero, CTX, null);
  assert.match(html, /name="duration"[^>]*value="105"/);
  assert.doesNotMatch(html, /name="end"/);
  assert.doesNotMatch(html, /name="setpoint"/);
  assert.match(html, /name="endMode" value="duration" data-estructural="1" checked/);
  assert.match(html, /data-accion="guardar-tramo" disabled/);
});

test("renderFormTramo: aviso propio con canales marcados", () => {
  const t = clonar(dormitorio.slots[0].config);
  t.notify = { mode: "on", channels: ["movil"] };
  t.notify_on_skip = true;
  const html = vista.renderFormTramo(t, dormitorio, CTX, { ok: true });
  assert.match(html, /name="notifyChannel" value="movil" checked/);
  assert.doesNotMatch(html, /name="notifyChannel" value="telegram" checked/);
  assert.match(html, /name="notifySkip" value="on" checked/);
});

test("renderFormTramo escapa el nombre", () => {
  const t = tramos.tramoVacio(dormitorio);
  t.name = '"><script>x</script>';
  assert.doesNotMatch(vista.renderFormTramo(t, dormitorio, CTX, { ok: true }), /<script>/);
});

test("renderValidacionTramo: conflictos por nombre", () => {
  assert.match(vista.renderValidacionTramo(null, dormitorio), /Validando/);
  assert.match(vista.renderValidacionTramo({ ok: true }, dormitorio), /✓ Válido/);
  const mal = vista.renderValidacionTramo({ ok: false, error: "los tramos se solapan", conflicts: ["tarde", "x"] }, dormitorio);
  assert.match(mal, /los tramos se solapan/);
  assert.match(mal, /Se solapa con: Tarde, x/);
  assert.doesNotMatch(vista.renderValidacionTramo({ ok: false, error: "e", conflicts: [] }, dormitorio), /Se solapa/);
});

test("las pestañas incluyen Tramos entre Resumen y Casa", () => {
  const html = casa.renderVistas("tramos");
  assert.ok(html.indexOf("resumen") < html.indexOf("tramos") && html.indexOf("tramos") < html.indexOf('data-vista="casa"'));
  assert.match(html, /data-vista="tramos" class="sel"/);
});
