// Versión: 2026.11.8
// Tests de la vista «Pausas» (node --test): lógica de fechas, formulario y HTML.
process.env.TZ = "Europe/Madrid";

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const RUTA = "../../custom_components/calorplan/frontend/";
const pausas = await import(`${RUTA}pausas.js`);
const vista = await import(`${RUTA}render_pausas.js`);
const render = await import(`${RUTA}render.js`);
const logica = await import(`${RUTA}logic.js`);
const casa = await import(`${RUTA}render_casa.js`);

const datos = JSON.parse(readFileSync(new URL("./overview.fixture.json", import.meta.url), "utf-8"));
const clonar = (o) => JSON.parse(JSON.stringify(o));
const P = (extra = {}) => ({ id: "vac", reason: "Vacaciones", from: "2026-11-10", until: "2026-11-15", enabled: true, status: "active", ...extra });

// --- Fechas -------------------------------------------------------------------------------------------------
test("sumarDias: meses, años y bisiestos", () => {
  assert.equal(pausas.sumarDias("2026-11-02", 7), "2026-11-09");
  assert.equal(pausas.sumarDias("2026-12-28", 7), "2027-01-04");
  assert.equal(pausas.sumarDias("2028-02-28", 1), "2028-02-29");
  assert.equal(pausas.sumarDias("2027-02-28", 1), "2027-03-01");
  assert.equal(pausas.sumarDias("2026-03-01", -1), "2026-02-28");
});

test("fmtDia", () => {
  assert.equal(pausas.fmtDia("2026-12-20"), "20/12/2026");
  assert.equal(pausas.fmtDia(null), "sin fecha de fin");
});

test("pausaVacia empieza hoy y dura una semana", () => {
  assert.deepEqual(pausas.pausaVacia("2026-11-02"), { reason: "", from: "2026-11-02", until: "2026-11-09", enabled: true });
});

// --- Formulario --------------------------------------------------------------------------------------------------
test("formToPause: con fecha de fin", () => {
  const p = pausas.formToPause([["reason", " Visita "], ["from", "2026-12-20"], ["until", "2026-12-27"], ["enabled", "on"]]);
  assert.deepEqual(p, { reason: "Visita", from: "2026-12-20", until: "2026-12-27", enabled: true });
});

test("formToPause: «sin fecha de fin» es explícito (null) y el resto de casos no", () => {
  const sinFin = pausas.formToPause([["reason", "x"], ["from", "2026-12-20"], ["noEnd", "on"], ["until", "2026-12-27"], ["enabled", "on"]]);
  assert.equal(sinFin.until, null);
  // Un fin vacío NO se convierte en «sin fin»: llega vacío y el servidor lo rechaza
  const vacio = pausas.formToPause([["reason", "x"], ["from", "2026-12-20"], ["until", ""]]);
  assert.equal(vacio.until, "");
  assert.equal(vacio.enabled, false); // casilla sin marcar
});

test("ordenarPausas: activas, próximas, deshabilitadas, caducadas", () => {
  const orden = pausas.ordenarPausas([
    P({ id: "e", status: "expired", from: "2026-01-01" }), P({ id: "d", status: "disabled" }),
    P({ id: "u2", status: "upcoming", from: "2027-01-01" }), P({ id: "u1", status: "upcoming", from: "2026-12-01" }),
    P({ id: "a", status: "active" }),
  ]).map((p) => p.id);
  assert.deepEqual(orden, ["a", "u1", "u2", "d", "e"]);
});

// --- HTML -----------------------------------------------------------------------------------------------------------
test("renderPausas: tarjeta de la casa y una por habitación, con ayuda", () => {
  const html = vista.renderPausas(datos);
  assert.equal((html.match(/data-accion="nueva-pausa"/g) || []).length, 4); // casa + 3 habitaciones
  assert.match(html, /data-accion="nueva-pausa" data-room=""/); // la de la casa va sin habitación
  assert.match(html, /data-accion="nueva-pausa" data-room="dormitorio"/);
  assert.match(html, /Toda la casa/);
  assert.match(html, /Sin pausas\./);
  assert.match(html, /los apagados siguen funcionando/);
});

test("renderPausas: filas, estados, fechas y acciones", () => {
  const d = clonar(datos);
  d.rooms[0].pauses = [P(), P({ id: "f", reason: "", from: "2027-01-02", until: null, status: "upcoming" }), P({ id: "c", status: "expired" })];
  const html = vista.renderPausas(d);
  assert.match(html, /Vacaciones<\/td><td>10\/11\/2026<\/td><td>15\/11\/2026<\/td>\s*<td class="ok">Activa/);
  assert.match(html, /\(sin motivo\)<\/td><td>02\/01\/2027<\/td><td>sin fecha de fin<\/td>\s*<td class="muted">Próxima/);
  assert.match(html, /Caducada/);
  assert.match(html, /data-accion="editar-pausa" data-room="dormitorio" data-pausa="vac"/);
  assert.match(html, /data-accion="alternar-pausa"[^>]*>Deshabilitar/);
  assert.match(html, /class="tramo-off"/); // la caducada se atenúa
  assert.ok(html.indexOf("Activa") < html.indexOf("Próxima") && html.indexOf("Próxima") < html.indexOf("Caducada"));
});

test("renderPausas: insignia «En pausa» y nota cuando la afecta la pausa de la casa", () => {
  const d = clonar(datos);
  d.global_pauses = [P({ id: "g", reason: "Viaje", until: null })];
  d.rooms[0].paused_by = { scope: "global", id: "g", reason: "Viaje", until: null };
  d.rooms[1].paused_by = { scope: "room", id: "x", reason: "Obras", until: "2026-11-20" };
  d.rooms[1].pauses = [P({ id: "x", reason: "Obras", until: "2026-11-20" })];
  const html = vista.renderPausas(d);
  assert.equal((html.match(/En pausa<\/span>/g) || []).length, 3); // casa + 2 habitaciones
  assert.match(html, /Afectada por la pausa de toda la casa: Viaje/);
  assert.doesNotMatch(html, /Afectada por la pausa de toda la casa: Obras/); // la propia no lleva nota
});

test("renderFormPausa: con fecha de fin", () => {
  const html = vista.renderFormPausa({ reason: "Visita", from: "2026-12-20", until: "2026-12-27", enabled: true }, "Dormitorio", { ok: true });
  assert.match(html, /name="from" value="2026-12-20"/);
  assert.match(html, /name="until" value="2026-12-27"/);
  assert.doesNotMatch(html, /name="noEnd"[^>]*checked/);
  assert.match(html, /list="dl-motivos"/);
  assert.match(html, /<option value="Vacaciones">/);
  assert.match(html, /name="enabled" value="on" checked/);
  assert.match(html, /id="validacion-pausa"/);
  assert.doesNotMatch(html, /data-accion="guardar-pausa" disabled/);
});

test("renderFormPausa: sin fecha de fin oculta el campo y avisa", () => {
  const html = vista.renderFormPausa({ reason: "", from: "2026-12-20", until: null, enabled: true }, "Toda la casa", { ok: true });
  assert.match(html, /name="noEnd" value="on" data-estructural="1" checked/);
  assert.doesNotMatch(html, /name="until"/);
  assert.match(html, /hasta que borres o deshabilites la pausa/);
});

test("renderFormPausa: guardar deshabilitado sin validar y se muestra el error", () => {
  const p = { reason: "", from: "2026-12-20", until: "2026-12-01", enabled: true };
  assert.match(vista.renderFormPausa(p, "x", null), /data-accion="guardar-pausa" disabled/);
  const mal = vista.renderFormPausa(p, "x", { ok: false, error: "la fecha final no puede ser anterior" });
  assert.match(mal, /la fecha final no puede ser anterior/);
  assert.match(mal, /data-accion="guardar-pausa" disabled/);
});

test("renderFormPausa escapa el motivo", () => {
  const html = vista.renderFormPausa({ reason: '"><script>x</script>', from: "2026-12-20", until: null, enabled: true }, "x", { ok: true });
  assert.doesNotMatch(html, /<script>/);
});

test("la cabecera muestra «Pausa global» solo si hay una activa", () => {
  const d = clonar(datos);
  assert.doesNotMatch(render.renderCabecera(d, "10:00"), /Pausa global/);
  d.global_pauses = [P({ status: "upcoming" })];
  assert.doesNotMatch(render.renderCabecera(d, "10:00"), /Pausa global/);
  d.global_pauses = [P()];
  assert.match(render.renderCabecera(d, "10:00"), /Pausa global/);
});

test("el simulador explica la pausa", () => {
  const r = logica.describeSimulation({ would_start: false, active: true, slot: "Tarde", code: "paused", reason: "x" });
  assert.equal(r.text, "No: en pausa · Tarde");
  assert.equal(r.tone, "warn");
});

test("las pestañas: Resumen, Casa, Tramos, Pausas", () => {
  const html = casa.renderVistas("pausas");
  const orden = ["resumen", "casa", "tramos", "pausas"].map((v) => html.indexOf(`data-vista="${v}"`));
  assert.deepEqual([...orden].sort((a, b) => a - b), orden);
  assert.match(html, /data-vista="pausas" class="sel"/);
});
