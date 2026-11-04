// Versión: 2026.11.9
// Tests del frontend (node --test): lógica pura y generación de HTML.
process.env.TZ = "Europe/Madrid";

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import * as logica from "../../custom_components/calorplan/frontend/logic.js";
import * as render from "../../custom_components/calorplan/frontend/render.js";

const datos = JSON.parse(readFileSync(new URL("./overview.fixture.json", import.meta.url), "utf-8"));
const clonar = (o) => JSON.parse(JSON.stringify(o));
const AHORA = new Date("2026-11-02T06:30:00+01:00");

test("fmtMin y fmtNum", () => {
  assert.equal(logica.fmtMin(0), "00:00");
  assert.equal(logica.fmtMin(390), "06:30");
  assert.equal(logica.fmtMin(1440), "24:00");
  assert.equal(logica.fmtNum(20), "20");
  assert.equal(logica.fmtNum(14.34), "14.3");
  assert.equal(logica.fmtNum(null), "—");
});

test("daysLabel resume los días, también cruzando la semana", () => {
  assert.equal(logica.daysLabel([0, 1, 2, 3, 4, 5, 6]), "Diario");
  assert.equal(logica.daysLabel([0, 1, 2, 3, 4]), "L–V");
  assert.equal(logica.daysLabel([6, 0, 1, 2, 3, 4]), "D–V");
  assert.equal(logica.daysLabel([5, 6]), "S, D");
  assert.equal(logica.daysLabel([0, 2]), "L, X");
  assert.equal(logica.daysLabel([6, 0]), "D, L");
});

test("barStyle calcula porcentajes sobre 24 h", () => {
  const { left, width } = logica.barStyle({ start: 360, end: 420 });
  assert.equal(left, 25);
  assert.ok(Math.abs(width - 100 / 24) < 1e-9);
});

test("segState: activo solo hoy y dentro del tramo; deshabilitado manda", () => {
  const sala = { enabled: true };
  const tramo = { enabled: true };
  const seg = { start: 360, end: 420 };
  assert.equal(logica.segState(sala, tramo, 0, 0, 390, seg), "active");
  assert.equal(logica.segState(sala, tramo, 0, 0, 420, seg), "normal");
  assert.equal(logica.segState(sala, tramo, 1, 0, 390, seg), "normal");
  assert.equal(logica.segState(sala, { enabled: false }, 0, 0, 390, seg), "disabled");
  assert.equal(logica.segState({ enabled: false }, tramo, 0, 0, 390, seg), "disabled");
});

test("describeSimulation", () => {
  assert.deepEqual(logica.describeSimulation(null), { text: "Sin tramos", tone: "muted" });
  const ok = logica.describeSimulation({ would_start: true, active: true, slot: "Tarde", code: "ok" });
  assert.equal(ok.tone, "ok");
  assert.match(ok.text, /^Si empezara ahora, encendería · Tarde$/);
  const futuro = logica.describeSimulation({ would_start: true, active: false, slot: "Tarde", code: "ok" });
  assert.match(futuro.text, /\(próximo tramo\)/);
  const alto = logica.describeSimulation({ would_start: false, active: true, slot: "T", code: "outdoor_too_warm", reason: "Exterior 20 ≥ 10" });
  assert.equal(alto.text, "Exterior 20 ≥ 10 · T");
  assert.equal(alto.tone, "warn");
  const sinDato = logica.describeSimulation({ would_start: false, active: true, slot: "T", code: "indoor_unavailable", reason: "x" });
  assert.equal(sinDato.tone, "error");
  assert.match(logica.describeSimulation({ would_start: false, active: true, slot: "T", code: "away" }).text, /ausencia/);
});

test("describeNext y describeLast", () => {
  const sala = datos.rooms[0];
  assert.match(logica.describeNext(sala.next, sala, AHORA), /^Fin Madrugada · 07:00 \(en 30 min\)$/);
  assert.equal(logica.describeNext(null, sala, AHORA), "—");
  const ultima = logica.describeLast(sala.last);
  assert.equal(ultima.tone, "ok");
  assert.match(ultima.text, /^Encendió \(simulado\) · Madrugada 06:00$/);
  assert.equal(logica.describeLast(null).text, "—");
});

test("esc evita inyección de HTML", () => {
  assert.equal(logica.esc('<img src=x onerror="a">'), "&lt;img src=x onerror=&quot;a&quot;&gt;");
});

test("renderGantt: una fila por habitación, barras y línea de ahora", () => {
  const html = render.renderGantt(datos, 0);
  assert.equal((html.match(/class="pista"/g) || []).length, 3);
  assert.match(html, /left:25\.000%;width:4\.167%/); // madrugada 06:00–07:00
  assert.match(html, /barra active/); // a las 06:30 el tramo está activo
  assert.match(html, /class="ahora" style="left:27\.083%"/);
  assert.equal(render.renderGantt(datos, 1).includes('class="ahora"'), false);
});

test("renderGantt: tramo que cruza la medianoche marca los extremos", () => {
  const d = clonar(datos);
  d.rooms[0].week[4] = [{ slot_id: "madrugada", start: 1380, end: 1440, continued_from_prev: false, continues_next: true }];
  d.rooms[0].week[5] = [{ slot_id: "madrugada", start: 0, end: 60, continued_from_prev: true, continues_next: false }];
  assert.match(render.renderGantt(d, 4), /cont-der/);
  assert.match(render.renderGantt(d, 5), /cont-izq/);
});

test("renderGantt: habitación o tramo deshabilitado se marca", () => {
  const d = clonar(datos);
  d.rooms[0].enabled = false;
  const html = render.renderGantt(d, 0);
  assert.match(html, /\(deshabilitada\)/);
  assert.match(html, /barra disabled/);
});

test("renderPanel: cabecera, tabla y escape del nombre", () => {
  const d = clonar(datos);
  d.rooms[1].name = "<script>alert(1)</script>";
  const html = render.renderPanel(d, 0, AHORA);
  assert.match(html, /Modo sombra/);
  assert.match(html, /v2026\.\d+\.\d+/);
  assert.match(html, /Exterior 8 °C/);
  assert.match(html, /Si empezara ahora, encendería/);
  assert.equal(html.includes("<script>"), false);
  assert.match(html, /&lt;script&gt;/);
});

test("renderPanel: sin habitaciones muestra ayuda", () => {
  const d = clonar(datos);
  d.rooms = [];
  assert.match(render.renderPanel(d, 0, AHORA), /calorplan\.import_config/);
});

test("renderPestanas marca el día seleccionado y hoy", () => {
  const html = render.renderPestanas(2, 0);
  assert.match(html, /data-dia="2" class="sel /);
  assert.match(html, /data-dia="0" class=" hoy"/);
});

test("las barras estrechas muestran solo el inicio y las muy estrechas, nada", () => {
  const d = clonar(datos);
  const sala = d.rooms[0];
  sala.week[0] = [{ slot_id: "madrugada", start: 360, end: 420, continued_from_prev: false, continues_next: false }];
  assert.match(render.renderGantt(d, 0), />06:00<\/div>/); // 4,17 %: solo inicio
  sala.week[0] = [{ slot_id: "madrugada", start: 360, end: 380, continued_from_prev: false, continues_next: false }];
  assert.match(render.renderGantt(d, 0), /><\/div>/); // 1,4 %: sin texto
  sala.week[0] = [{ slot_id: "madrugada", start: 360, end: 540, continued_from_prev: false, continues_next: false }];
  assert.match(render.renderGantt(d, 0), />06:00–09:00<\/div>/); // 12,5 %: rango completo
});
