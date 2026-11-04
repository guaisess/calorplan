// Versión: 2026.11.15
// Generación del HTML del panel a partir de los datos (función pura, sin DOM).

import { CONFIG, TEXTOS } from "./config.js?v=2026.11.16";
import {
  barStyle, describeLast, describeNext, describeSimulation, esc, fmtMin, fmtNum, segState, slotTitle,
} from "./logic.js?v=2026.11.16";

/** Cabecera: título, versión, avisos de modo y temperatura exterior. */
export function renderCabecera(datos, actualizadoEn) {
  const insignias = [`<span class="insignia">v${esc(datos.version)}</span>`];
  if (datos.shadow_mode) insignias.push(`<span class="insignia aviso">${TEXTOS.sombra}</span>`);
  if (datos.away_mode) insignias.push(`<span class="insignia aviso">${TEXTOS.ausencia}</span>`);
  if ((datos.global_pauses ?? []).some((p) => p.status === "active")) {
    insignias.push(`<span class="insignia aviso">${TEXTOS.pausaGlobal}</span>`);
  }
  if (datos.outdoor !== null) {
    insignias.push(`<span class="insignia">${TEXTOS.exterior} ${fmtNum(datos.outdoor)} ${TEXTOS.unidades.grados}</span>`);
  }
  return `<div class="cabecera"><h1>${TEXTOS.titulo}</h1>${insignias.join("")}<span class="espacio"></span>
    <span class="muted">${TEXTOS.actualizado} ${esc(actualizadoEn)}</span>
    <button data-accion="actualizar">${TEXTOS.actualizar}</button></div>`;
}

/** Pestañas de los días de la semana. */
export function renderPestanas(dia, hoy) {
  const botones = CONFIG.diasLargos.map((nombre, i) =>
    `<button data-dia="${i}" class="${i === dia ? "sel" : ""} ${i === hoy ? "hoy" : ""}">${nombre}</button>`);
  return `<div class="pestanas">${botones.join("")}</div>`;
}

/** Barra de un segmento dentro de la pista. */
function renderBarra(room, seg, dia, datos) {
  const slot = room.slots.find((s) => s.id === seg.slot_id);
  const { left, width } = barStyle(seg);
  const estado = segState(room, slot, dia, datos.weekday, datos.minute, seg);
  const clases = ["barra", estado, seg.continued_from_prev ? "cont-izq" : "", seg.continues_next ? "cont-der" : ""];
  let texto = "";
  if (width >= CONFIG.anchoRangoCompleto) texto = `${fmtMin(seg.start)}–${fmtMin(seg.end)}`;
  else if (width >= CONFIG.anchoSoloInicio) texto = fmtMin(seg.start);
  return `<div class="${clases.join(" ")}" style="left:${left.toFixed(3)}%;width:${width.toFixed(3)}%" title="${esc(slot ? slotTitle(slot) : seg.slot_id)}">${texto}</div>`;
}

/** Línea de tiempo del día seleccionado: una fila por habitación. */
export function renderGantt(datos, dia) {
  const marcas = CONFIG.marcasHoras.map((h) => (h / 24) * 100);
  const eje = CONFIG.marcasHoras.map((h, i) => `<span style="left:${marcas[i]}%">${h}</span>`).join("");
  const lineas = marcas.map((m) => `<div class="marca" style="left:${m}%"></div>`).join("");
  const ahora = dia === datos.weekday
    ? `<div class="ahora" style="left:${((datos.minute / CONFIG.minutosDia) * 100).toFixed(3)}%"></div>` : "";
  const filas = datos.rooms.map((room) => {
    const barras = room.week[dia].map((seg) => renderBarra(room, seg, dia, datos)).join("");
    const estado = room.actuator.state ?? TEXTOS.nada;
    const nombre = esc(room.name) + (room.enabled ? "" : ` (${TEXTOS.deshabilitada})`);
    return `<div class="etiqueta">${nombre}<small>${esc(estado)}</small></div>
      <div class="pista">${lineas}${barras}${ahora}</div>`;
  });
  return `<div class="gantt"><div></div><div class="eje">${eje}</div>${filas.join("")}</div>`;
}

/** Tabla «Estado ahora» con simulación y última acción. */
export function renderEstado(datos, ahora) {
  const cabecera = TEXTOS.columnas.map((c) => `<th>${c}</th>`).join("");
  const filas = datos.rooms.map((room) => {
    const activo = room.slots.find((s) => s.id === room.active_slot);
    const sim = describeSimulation(room.simulation);
    const ultima = describeLast(room.last);
    return `<tr>
      <td>${esc(room.name)}</td>
      <td>${esc(room.actuator.state ?? TEXTOS.nada)}</td>
      <td>${activo ? esc(activo.name) : TEXTOS.nada}</td>
      <td>${esc(describeNext(room.next, room, ahora))}</td>
      <td class="${sim.tone}">${esc(sim.text)}</td>
      <td class="${ultima.tone}" title="${esc(ultima.title ?? "")}">${esc(ultima.text)}</td></tr>`;
  });
  return `<table><thead><tr>${cabecera}</tr></thead><tbody>${filas.join("")}</tbody></table>`;
}

/** Documento completo del panel. */
export function renderPanel(datos, dia, ahora, extra = "") {
  const actualizado = fmtMin(ahora.getHours() * 60 + ahora.getMinutes());
  if (!datos.rooms.length) {
    return `${renderCabecera(datos, actualizado)}${extra}<div class="tarjeta mensaje">${TEXTOS.sinHabitaciones}</div>`;
  }
  return `${renderCabecera(datos, actualizado)}${extra}
    <div class="tarjeta"><h2>${TEXTOS.lineaTiempo}</h2>${renderPestanas(dia, datos.weekday)}${renderGantt(datos, dia)}</div>
    <div class="tarjeta"><h2>${TEXTOS.estadoAhora}</h2>${renderEstado(datos, ahora)}</div>`;
}
