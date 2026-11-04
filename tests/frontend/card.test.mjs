// Versión: 2026.11.19
// Tests de la tarjeta Lovelace: lógica pura y HTML generado.
process.env.TZ = "Europe/Madrid";

import assert from "node:assert/strict";
import { test } from "node:test";

import * as L from "../../custom_components/calorplan/frontend/card_logic.js";
import * as R from "../../custom_components/calorplan/frontend/render_card.js";

const sala = (extra = {}) => ({
  id: "alba", name: "Alba", enabled: true, active: { id: "n", name: "Noche", end: 420 }, next: null,
  paused_by: null, quick_pause: false, today: [{ slot_id: "n", name: "Noche", start: 0, end: 420, enabled: true }], ...extra,
});
const resumen = (extra = {}) => ({ today: "2026-11-02", minute: 390, away_mode: false, shadow_mode: false,
  global_pause: null, outdoor: 8, quick_pause_reason: "Pausa rápida", rooms: [sala()], ...extra });

test("normalizarConfig aplica valores por defecto y limpia acciones", () => {
  const c = L.normalizarConfig({ actions: ["away", "xx"], rooms: "a, b" });
  assert.deepEqual(c.actions, ["away"]);
  assert.deepEqual(c.rooms, ["a", "b"]);
  assert.equal(c.show_timeline, true);
});

test("filtrarHabitaciones respeta la lista y el orden", () => {
  const r = resumen({ rooms: [sala({ id: "a" }), sala({ id: "b" })] });
  assert.equal(L.filtrarHabitaciones(r, L.normalizarConfig({})).length, 2);
  assert.deepEqual(L.filtrarHabitaciones(r, L.normalizarConfig({ rooms: ["b", "zz"] })).map((h) => h.id), ["b"]);
});

test("estado y texto de la habitación", () => {
  assert.equal(L.estadoHabitacion(sala({ enabled: false })), "disabled");
  assert.equal(L.estadoHabitacion(sala({ paused_by: { until: null } })), "paused");
  assert.match(L.textoEstado(sala()), /Noche hasta 07:00/);
});

test("llamadas de servicio de los atajos", () => {
  const r = resumen();
  assert.deepEqual(L.llamadaServicio("pause", sala(), r),
    { servicio: "set_pause", datos: { room_id: "alba", reason: "Pausa rápida", from: "2026-11-02", until: "2026-11-02" } });
  assert.equal(L.llamadaServicio("pause", sala({ quick_pause: true }), r).servicio, "clear_pause");
  assert.deepEqual(L.llamadaServicio("enable", sala(), r).datos, { room_id: "alba", enabled: false });
  assert.equal(L.llamadaServicio("run", sala({ active: null }), r), null);
  assert.equal(L.llamadaServicio("run", sala(), r).datos.force, true);
  assert.deepEqual(L.llamadaAusencia(r).datos, { away: true });
});

test("«Ejecutar» solo se ofrece con tramo activo y habitación habilitada", () => {
  const c = L.normalizarConfig({ actions: ["run"] });
  assert.equal(L.accionesHabitacion(sala(), c).length, 1);
  assert.equal(L.accionesHabitacion(sala({ active: null }), c).length, 0);
});

test("renderTarjeta pinta cabecera, sala, línea y botones; escapa HTML", () => {
  const c = L.normalizarConfig({ title: "<b>x</b>", actions: ["away", "pause", "run"] });
  const html = R.renderTarjeta(resumen({ away_mode: true }), c);
  assert.ok(html.includes("&lt;b&gt;x"));
  assert.ok(html.includes("Desactivar ausencia") && html.includes("Pausar hasta mañana") && html.includes("Ejecutar tramo ahora"));
  assert.ok(html.includes('class="ahora"') && html.includes("Exterior 8"));
  assert.ok(!R.renderTarjeta(resumen(), L.normalizarConfig({ show_timeline: false })).includes('class="ahora"'));
});

test("el botón de habilitar ofrece la acción contraria al estado actual", () => {
  const c = L.normalizarConfig({ actions: ["enable"] });
  assert.ok(R.renderAcciones(sala({ enabled: true }), c).includes("Deshabilitar"));
  assert.ok(R.renderAcciones(sala({ enabled: false }), c).includes("Habilitar"));
  assert.ok(!R.renderAcciones(sala({ enabled: false }), c).includes("Deshabilitar"));
  assert.ok(R.renderAcciones(sala({ quick_pause: true }), L.normalizarConfig({ actions: ["pause"] })).includes("Reanudar"));
});
