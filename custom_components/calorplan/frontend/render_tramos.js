// Versión: 2026.11.13
// HTML de la vista «Tramos» (funciones puras): tabla por habitación y editor de tramo.

import { CONFIG, TEXTOS } from "./config.js?v=2026.11.13";
import { daysLabel, esc, fmtMin, fmtNum } from "./logic.js?v=2026.11.13";
import { CASA } from "./textos_casa.js?v=2026.11.13";

const E = TEXTOS.editor;

const campo = (etiqueta, control) => `<label class="campo"><span>${esc(etiqueta)}</span>${control}</label>`;
const casilla = (nombre, texto, marcado, valor = "on") =>
  `<label class="casilla"><input type="checkbox" name="${nombre}" value="${esc(valor)}"${marcado ? " checked" : ""}> ${esc(texto)}</label>`;
const opciones = (mapa, actual) => Object.entries(mapa)
  .map(([v, t]) => `<option value="${esc(v)}"${v === actual ? " selected" : ""}>${esc(t)}</option>`).join("");

/** Horario legible: «06:00–07:00». */
export function horario(slot) {
  const [h, m] = slot.start.split(":").map(Number);
  const fin = (h * 60 + m + slot.duration_minutes) % CONFIG.minutosDia;
  return `${slot.start}–${fmtMin(fin)}`;
}

/** Resumen de condiciones: «ext < 15 · int < 16». */
export function condiciones(slot) {
  const partes = [];
  if (slot.outdoor_below !== null) partes.push(`${TEXTOS.tramo.exterior} ${fmtNum(slot.outdoor_below)}`);
  if (slot.indoor_below !== null) partes.push(`${TEXTOS.tramo.interior} ${fmtNum(slot.indoor_below)}`);
  return partes.length ? partes.join(" · ") : TEXTOS.nada;
}

/** Tabla de tramos de una habitación, ordenados por hora de inicio. */
function renderTabla(room) {
  if (!room.slots.length) return `<div class="mensaje">${TEXTOS.sinTramos}</div>`;
  const filas = [...room.slots].sort((a, b) => a.start.localeCompare(b.start)).map((s) => {
    const objetivo = s.setpoint === null ? TEXTOS.nada : `${fmtNum(s.setpoint)} ${TEXTOS.unidades.grados}`;
    const alterna = s.enabled ? TEXTOS.deshabilitar : TEXTOS.habilitar;
    const data = `data-room="${esc(room.id)}" data-slot="${esc(s.id)}"`;
    return `<tr class="${s.enabled ? "" : "tramo-off"}">
      <td>${esc(s.name)}</td><td>${esc(daysLabel(s.days))}</td><td>${esc(horario(s))}</td>
      <td>${esc(objetivo)}</td><td>${esc(condiciones(s))}</td>
      <td class="${s.enabled ? "ok" : "muted"}">${s.enabled ? TEXTOS.habilitado : TEXTOS.inhabilitado}</td>
      <td class="acciones"><button data-accion="editar-tramo" ${data}>${TEXTOS.editar}</button>
      <button data-accion="duplicar-tramo" ${data}>${TEXTOS.duplicar}</button>
      <button data-accion="alternar-tramo" ${data}>${alterna}</button>
      <button data-accion="borrar-tramo" ${data}>${TEXTOS.borrar}</button></td></tr>`;
  }).join("");
  const cab = TEXTOS.columnasTramos.map((c) => `<th>${c}</th>`).join("");
  return `<table><thead><tr>${cab}</tr></thead><tbody>${filas}</tbody></table>`;
}

/** Vista de tramos: una tarjeta por habitación. */
export function renderTramos(datos) {
  if (!datos.rooms.length) return `<div class="tarjeta mensaje">${TEXTOS.sinHabitaciones}</div>`;
  return datos.rooms.map((room) => `<div class="tarjeta"><div class="titulo-tarjeta">
      <h2>${esc(room.name)}${room.enabled ? "" : ` <span class="muted">(${TEXTOS.deshabilitada})</span>`}</h2>
      <button data-accion="nuevo-tramo" data-room="${esc(room.id)}">+ ${TEXTOS.anadir}</button></div>
      ${renderTabla(room)}</div>`).join("");
}

/** Validación del editor de tramos: error, tramos en conflicto o «válido». */
export function renderValidacionTramo(res, room) {
  if (!res) return `<div class="validacion muted">${E.validando}</div>`;
  if (res.ok) return `<div class="validacion ok">${E.valido}</div>`;
  const nombres = (res.conflicts ?? []).map((id) => room.slots.find((s) => s.id === id)?.name ?? id);
  const solape = nombres.length ? `<div>${E.solapa}: ${esc(nombres.join(", "))}</div>` : "";
  return `<div class="validacion error">${esc(res.error)}${solape}</div>`;
}

/** Formulario del editor de tramo (sin el marco del diálogo). */
export function renderFormTramo(t, room, ctx, validacion) {
  const climate = room.actuator.type === "climate";
  const dias = CONFIG.diasLargos.map((nombre, i) => casilla("days", nombre, t.days.includes(i), String(i))).join("");
  const porDuracion = t.duration_minutes !== undefined && t.duration_minutes !== null;
  const radios = `<label class="casilla"><input type="radio" name="endMode" value="end" data-estructural="1"${porDuracion ? "" : " checked"}> ${E.fin}</label>
    <label class="casilla"><input type="radio" name="endMode" value="duration" data-estructural="1"${porDuracion ? " checked" : ""}> ${E.duracion}</label>`;
  const fin = porDuracion
    ? `<input type="number" name="duration" min="1" max="${CONFIG.minutosMaxDuracion}" value="${esc(t.duration_minutes)}">`
    : `<input type="time" name="end" value="${esc(t.end ?? "")}">`;
  const modo = t.notify ? t.notify.mode : "inherit";
  const canales = ctx.canalesIds.map((id) => casilla("notifyChannel", id, t.notify?.channels?.includes(id), id)).join("");
  const modos = Object.fromEntries(CONFIG.modosAviso.map((m) => [m, E.modoAviso[m]]));
  return `<form data-form="tramo">
    ${campo(E.nombre, `<input name="name" value="${esc(t.name)}">`)}
    <div class="campo"><span>${E.dias}</span><div class="casillas">${dias}</div></div>
    ${campo(E.inicio, `<input type="time" name="start" value="${esc(t.start)}">`)}
    <div class="campo"><span>${E.fin} / ${E.duracion}</span><div class="casillas">${radios}</div>${fin}</div>
    ${climate ? campo(E.objetivo, `<input type="number" step="0.5" name="setpoint" value="${esc(t.setpoint ?? "")}">`) : ""}
    ${campo(E.exterior, `<input type="number" step="0.5" name="outdoor" value="${esc(t.conditions?.outdoor_below ?? "")}">`)}
    ${campo(E.interior, `<input type="number" step="0.5" name="indoor" value="${esc(t.conditions?.indoor_below ?? "")}">`)}
    ${campo(E.reintento, `<input type="number" min="0" max="${CONFIG.minutosMaxDuracion}" name="retry" value="${esc(t.retry_off_minutes)}">`)}
    <h3>${E.avisos}</h3>
    ${campo(CASA.global.modo, `<select name="notifyMode" data-estructural="1">${opciones(modos, modo)}</select>`)}
    ${modo === "inherit" ? "" : `<div class="casillas">${canales}</div>`}
    ${casilla("notifySkip", E.avisarOmision, t.notify_on_skip)}
    ${casilla("enabled", E.habilitado, t.enabled)}
    <div id="validacion-tramo">${renderValidacionTramo(validacion, room)}</div>
    <div class="botones"><button type="button" data-accion="cancelar-modal">${E.cancelar}</button>
    <button type="button" class="primario" data-accion="guardar-tramo"${validacion?.ok ? "" : " disabled"}>${E.guardar}</button></div>
  </form>`;
}
