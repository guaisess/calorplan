// Versión: 2026.11.21
// Generación del HTML de la tarjeta (funciones puras: datos → texto).

import { CONFIG_TARJETA as C, TEXTOS_TARJETA as T } from "./textos_card.js?v=2026.11.21";
import { accionesHabitacion, estadoHabitacion, filtrarHabitaciones, hhmm, posicion, textoEstado, textoProximo } from "./card_logic.js?v=2026.11.21";

/** Escapa texto para insertarlo en HTML. */
export function esc(valor) {
  return String(valor ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

/** Cabecera con insignias (sombra, ausencia, pausa global, exterior) y atajo de ausencia. */
export function renderCabecera(resumen, config) {
  const ins = [];
  if (resumen.shadow_mode) ins.push(`<span class="insignia aviso">${esc(T.sombra)}</span>`);
  if (resumen.away_mode) ins.push(`<span class="insignia aviso">${esc(T.ausencia)}</span>`);
  if (resumen.global_pause) ins.push(`<span class="insignia aviso">${esc(T.pausaGlobal)}</span>`);
  if (resumen.outdoor != null) ins.push(`<span class="insignia">${esc(T.exterior)} ${esc(resumen.outdoor)} °C</span>`);
  const away = config.actions.includes("away")
    ? `<button data-accion="away">${esc(resumen.away_mode ? T.acciones.away.desactivar : T.acciones.away.activar)}</button>` : "";
  return `<div class="cabecera"><span class="titulo">${esc(config.title)}</span>${ins.join("")}<span class="espacio"></span>${away}</div>`;
}

/** Mini línea de tiempo de hoy con la hora actual. */
export function renderLinea(h, minuto) {
  const barras = h.today.map((s) => {
    const p = posicion(s);
    const cls = ["barra", s.enabled ? "" : "disabled", s.start <= minuto && minuto < s.end && s.enabled ? "active" : ""].join(" ");
    return `<div class="${cls}" style="left:${p.left}%;width:${p.width}%" title="${esc(s.name)} ${hhmm(s.start)}–${hhmm(s.end)}"></div>`;
  }).join("");
  const marcas = C.marcasHoras.map((m) => `<span style="left:${(m * 60 / C.minutosDia) * 100}%">${m}</span>`).join("");
  return `<div class="pista">${barras}<div class="ahora" style="left:${(minuto / C.minutosDia) * 100}%"></div></div><div class="eje">${marcas}</div>`;
}

/** Botones de atajo de una habitación. */
export function renderAcciones(h, config) {
  return accionesHabitacion(h, config).map((a) => {
    const texto = a.id === "run" ? T.acciones.run : (a.activa ? T.acciones[a.id].desactivar : T.acciones[a.id].activar);
    return `<button data-accion="${a.id}" data-sala="${esc(h.id)}">${esc(texto)}</button>`;
  }).join("");
}

/** Bloque de una habitación. */
export function renderHabitacion(h, resumen, config) {
  const estado = estadoHabitacion(h);
  const linea = config.show_timeline ? renderLinea(h, resumen.minute) : "";
  const botones = renderAcciones(h, config);
  return `<div class="sala ${estado}"><div class="fila"><span class="nombre">${esc(h.name)}</span>
    <span class="estado">${esc(textoEstado(h))}</span></div>
    <div class="detalle">${esc(textoProximo(h))}</div>${linea}
    ${botones ? `<div class="botones">${botones}</div>` : ""}</div>`;
}

/** Contenido completo de la tarjeta. */
export function renderTarjeta(resumen, config) {
  const salas = filtrarHabitaciones(resumen, config);
  const cuerpo = salas.length ? salas.map((h) => renderHabitacion(h, resumen, config)).join("")
    : `<div class="vacio">${esc(T.sinHabitaciones)}</div>`;
  return `${renderCabecera(resumen, config)}${cuerpo}`;
}
