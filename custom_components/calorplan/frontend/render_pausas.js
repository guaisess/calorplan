// Versión: 2026.11.19
// HTML de la vista «Pausas» (funciones puras).

import { esc } from "./logic.js?v=2026.11.19";
import { fmtDia, ordenarPausas } from "./pausas.js?v=2026.11.19";
import { renderValidacion } from "./render_casa.js?v=2026.11.19";
import { PAUSAS } from "./textos_pausas.js?v=2026.11.19";

const E = PAUSAS.editor;

/** Tabla de pausas de un propietario (habitación o casa). `sala` vacío = toda la casa. */
function renderTabla(pausas, sala) {
  if (!pausas.length) return `<div class="mensaje">${PAUSAS.vacio}</div>`;
  const filas = ordenarPausas(pausas).map((p) => {
    const data = `data-room="${esc(sala)}" data-pausa="${esc(p.id)}"`;
    const alterna = p.enabled ? PAUSAS.acciones.deshabilitar : PAUSAS.acciones.habilitar;
    return `<tr class="${p.status === "expired" || p.status === "disabled" ? "tramo-off" : ""}">
      <td>${esc(p.reason || PAUSAS.sinMotivo)}</td><td>${esc(fmtDia(p.from))}</td><td>${esc(fmtDia(p.until))}</td>
      <td class="${PAUSAS.tonos[p.status]}">${PAUSAS.estados[p.status]}</td>
      <td class="acciones"><button data-accion="editar-pausa" ${data}>${PAUSAS.acciones.editar}</button>
      <button data-accion="alternar-pausa" ${data}>${alterna}</button>
      <button data-accion="borrar-pausa" ${data}>${PAUSAS.acciones.borrar}</button></td></tr>`;
  }).join("");
  const cab = PAUSAS.columnas.map((c) => `<th>${c}</th>`).join("");
  return `<table><thead><tr>${cab}</tr></thead><tbody>${filas}</tbody></table>`;
}

function tarjeta(titulo, insignia, nota, pausas, sala) {
  return `<div class="tarjeta"><div class="titulo-tarjeta"><h2>${esc(titulo)}${insignia}</h2>
    <button data-accion="nueva-pausa" data-room="${esc(sala)}">+ ${PAUSAS.anadir}</button></div>${nota}${renderTabla(pausas, sala)}</div>`;
}

/** Vista de pausas: una tarjeta para toda la casa y una por habitación. */
export function renderPausas(datos) {
  const global = (datos.global_pauses ?? []);
  const hayGlobal = global.some((p) => p.status === "active");
  const casa = tarjeta(PAUSAS.casa, hayGlobal ? ` <span class="insignia aviso">${PAUSAS.enPausa}</span>` : "", "", global, "");
  const salas = datos.rooms.map((r) => {
    const por = r.paused_by;
    const insignia = por ? ` <span class="insignia aviso">${PAUSAS.enPausa}</span>` : "";
    const nota = por && por.scope === "global"
      ? `<p class="muted">${PAUSAS.afectadaPorCasa} ${esc(por.reason || PAUSAS.sinMotivo)}${por.until ? ` (${esc(fmtDia(por.until))})` : ""}</p>` : "";
    return tarjeta(r.name, insignia, nota, r.pauses ?? [], r.id);
  }).join("");
  return `<div class="tarjeta"><p class="muted">${PAUSAS.ayuda}</p></div>${casa}${salas}`;
}

/** Formulario del editor de pausas (sin el marco del diálogo). */
export function renderFormPausa(p, ambito, validacion) {
  const sinFin = p.until === null || p.until === undefined;
  const sugerencias = `<datalist id="dl-motivos">${E.sugerencias.map((s) => `<option value="${esc(s)}"></option>`).join("")}</datalist>`;
  return `<form data-form="pausa">${sugerencias}
    <p class="muted">${esc(ambito)}</p>
    <label class="campo"><span>${E.motivo}</span><input name="reason" list="dl-motivos" placeholder="${esc(E.motivoPlaceholder)}" value="${esc(p.reason)}"></label>
    <label class="campo"><span>${E.desde}</span><input type="date" name="from" value="${esc(p.from)}"></label>
    <label class="casilla"><input type="checkbox" name="noEnd" value="on" data-estructural="1"${sinFin ? " checked" : ""}> ${E.sinFin}</label>
    ${sinFin
    ? `<p class="avisos">${E.avisoSinFin}</p>`
    : `<label class="campo"><span>${E.hasta}</span><input type="date" name="until" value="${esc(p.until ?? "")}"></label>`}
    <label class="casilla"><input type="checkbox" name="enabled" value="on"${p.enabled ? " checked" : ""}> ${E.habilitada}</label>
    <div id="validacion-pausa">${renderValidacion(validacion)}</div>
    <div class="botones"><button type="button" data-accion="cancelar-modal">${E.cancelar}</button>
    <button type="button" class="primario" data-accion="guardar-pausa"${validacion?.ok ? "" : " disabled"}>${E.guardar}</button></div>
  </form>`;
}
