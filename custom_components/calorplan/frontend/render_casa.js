// Versión: 2026.11.21
// HTML de la vista «Casa» (funciones puras): ajustes globales, habitaciones, editor e historial.

import { TEXTOS } from "./config.js?v=2026.11.21";
import { esc } from "./logic.js?v=2026.11.21";
import { CASA } from "./textos_casa.js?v=2026.11.21";

// --- Piezas comunes ----------------------------------------------------------------------------------
const opciones = (mapa, actual) => Object.entries(mapa)
  .map(([valor, texto]) => `<option value="${esc(valor)}"${valor === actual ? " selected" : ""}>${esc(texto)}</option>`).join("");

const datalist = (id, valores) =>
  `<datalist id="${id}">${valores.map((v) => `<option value="${esc(v)}"></option>`).join("")}</datalist>`;

const campo = (etiqueta, control) => `<label class="campo"><span>${esc(etiqueta)}</span>${control}</label>`;
const casilla = (nombre, texto, marcado, valor = "on") =>
  `<label class="casilla"><input type="checkbox" name="${nombre}" value="${esc(valor)}"${marcado ? " checked" : ""}> ${esc(texto)}</label>`;

/** Fila de sensor con botón de quitar. */
const filaSensor = (valor, i, lista, accion) =>
  `<div class="fila"><input name="sensor" list="${lista}" value="${esc(valor)}" placeholder="${esc(CASA.global.sensorPlaceholder)}">
   <button type="button" data-accion="${accion}" data-i="${i}" title="${CASA.quitar}">✕</button></div>`;

/** Resultado de la validación: error, avisos o «válido». */
export function renderValidacion(res) {
  if (!res) return `<div class="validacion muted">${CASA.validando}</div>`;
  const avisos = (res.warnings ?? []).map((w) => `<li>${esc(w)}</li>`).join("");
  const lista = avisos ? `<ul class="avisos">${avisos}</ul>` : "";
  if (!res.ok) return `<div class="validacion error">${esc(res.error)}</div>`;
  return `<div class="validacion ok">${CASA.valido}</div>${lista}`;
}

/** Marco de un cuadro de diálogo. */
export function renderModal(titulo, cuerpo) {
  return `<div class="modal-fondo"><div class="modal" role="dialog"><h2>${esc(titulo)}</h2>${cuerpo}</div></div>`;
}

// --- Ajustes globales --------------------------------------------------------------------------------
function seccionSensores(g, ctx) {
  const filas = (g.outdoor_sensors.length ? g.outdoor_sensors : [""])
    .map((s, i) => filaSensor(s, i, "dl-temp", "quitar-sensor-global")).join("");
  return `<h3>${CASA.global.sensores}</h3>${filas}
    <button type="button" data-accion="anadir-sensor-global">+ ${CASA.global.anadirSensor}</button>
    ${campo(CASA.global.agregacion, `<select name="outdoorAgg">${opciones(CASA.agregaciones, g.outdoor_aggregation)}</select>`)}`;
}

function seccionCanales(g, ctx) {
  const filas = g.channels.map((c, i) => {
    const guardado = ctx.canalesGuardados.has(c.id);
    const id = guardado
      ? `<input name="ch_id" value="${esc(c.id)}" readonly title="${esc(c.id)}">`
      : `<input name="ch_id" data-estructural="1" value="${esc(c.id)}" placeholder="${CASA.global.canalId}">`;
    const probar = guardado ? `<button type="button" data-accion="probar-canal" data-canal="${esc(c.id)}">${CASA.global.probar}</button>` : "";
    return `<div class="fila"><span class="id-canal">${id}</span>
      <input name="ch_service" list="dl-notify" value="${esc(c.service)}" placeholder="${esc(CASA.global.canalServicioPlaceholder)}">
      ${probar}<button type="button" data-accion="quitar-canal" data-i="${i}" title="${CASA.quitar}">✕</button></div>`;
  }).join("");
  return `<h3>${CASA.global.canales}</h3>${filas}
    <button type="button" data-accion="anadir-canal">+ ${CASA.global.anadirCanal}</button>
    <div id="resultado-prueba" class="muted"></div>`;
}

function seccionAvisoDefecto(g) {
  const canales = g.channels.filter((c) => c.id).map((c) =>
    casilla("dnChannel", c.id, g.default_notify.channels.includes(c.id), c.id)).join("");
  return `<h3>${CASA.global.avisoDefecto}</h3>
    ${campo(CASA.global.modo, `<select name="dnMode">${opciones(CASA.modosAviso, g.default_notify.mode)}</select>`)}
    <div class="campo"><span>${CASA.global.canalesDestino}</span><div class="casillas">${canales}</div></div>`;
}

function seccionPlantillas(g, ctx) {
  const vars = ctx.variables.map((v) => `<code>{${esc(v)}}</code>`).join(" ");
  const areas = Object.entries(CASA.plantillaAcciones).map(([accion, nombre]) =>
    campo(nombre, `<textarea name="tpl_${accion}" rows="3" placeholder="${esc(ctx.plantillasDefecto[accion] ?? "")}">${esc(g.templates?.[accion] ?? "")}</textarea>`)).join("");
  return `<h3>${CASA.global.plantillas}</h3><p class="muted">${CASA.global.plantillasAyuda} ${vars}</p>${areas}`;
}

function seccionComportamiento(g) {
  return `<h3>${CASA.global.comportamiento}</h3>
    ${campo(CASA.global.politica, `<select name="policy">${opciones(CASA.politicas, g.unavailable_policy)}</select>`)}
    ${campo(CASA.global.catchUp, `<select name="catchUp">${opciones(CASA.catchUps, g.catch_up)}</select>`)}
    ${campo(CASA.global.reevaluar, `<input type="number" name="reevaluate" min="0" max="1440" value="${esc(g.reevaluate_minutes ?? 0)}">`)}
    <p class="muted">${CASA.global.reevaluarAyuda}</p>
    ${campo(CASA.global.esperaArranque, `<input type="number" name="startupDelay" min="0" max="3600" value="${esc(g.startup_delay_seconds ?? 120)}">`)}
    <p class="muted">${CASA.global.esperaArranqueAyuda}</p>
    ${casilla("shadow", CASA.global.sombra, g.shadow_mode)}`;
}

/** Formulario de ajustes globales. `g` es el borrador; `ctx` trae listas y valores por defecto. */
export function renderGlobal(g, ctx, validacion) {
  return `<form data-form="global">
    ${datalist("dl-temp", ctx.sensores)}${datalist("dl-notify", ctx.notify)}
    ${seccionSensores(g, ctx)}${seccionCanales(g, ctx)}${seccionAvisoDefecto(g)}
    ${seccionPlantillas(g, ctx)}${seccionComportamiento(g)}
    <div id="validacion-global">${renderValidacion(validacion)}</div>
    <div class="botones"><button type="button" data-accion="descartar-global">${CASA.descartar}</button>
    <button type="button" class="primario" data-accion="guardar-global"${validacion?.ok ? "" : " disabled"}>${CASA.guardar}</button></div>
  </form>`;
}

// --- Habitaciones -------------------------------------------------------------------------------------
/** Tabla de habitaciones con acciones. */
export function renderHabitaciones(datos) {
  const H = CASA.habitaciones;
  if (!datos.rooms.length) return `<div class="mensaje">${H.vacio}</div>`;
  const filas = datos.rooms.map((r) => {
    const nombre = esc(r.name) + (r.enabled ? "" : ` <span class="muted">(${H.deshabilitada})</span>`);
    const n = r.config.sensors.length;
    return `<tr><td>${nombre}</td>
      <td>${esc(r.actuator.type)} · ${esc(r.actuator.entity_id)}</td>
      <td>${esc(H.sensoresN.replace("{n}", n))}</td>
      <td>${esc(CASA.agregaciones[r.indoor_aggregation] ?? r.indoor_aggregation)}</td>
      <td>${r.slots.length}</td>
      <td class="acciones"><button data-accion="editar-habitacion" data-room="${esc(r.id)}">${H.editar}</button>
      <button data-accion="borrar-habitacion" data-room="${esc(r.id)}">${H.borrar}</button></td></tr>`;
  }).join("");
  const cab = H.columnas.map((c) => `<th>${c}</th>`).join("");
  return `<table><thead><tr>${cab}</tr></thead><tbody>${filas}</tbody></table>`;
}

/** Contenido del editor de habitación (sin el marco del diálogo). */
export function renderFormHabitacion(h, ctx, validacion) {
  const E = CASA.editor;
  const a = h.actuator;
  const climate = a.type === "climate";
  const sensores = (h.sensors.length ? h.sensors : [""])
    .map((s, i) => filaSensor(s, i, "dl-temp", "quitar-sensor-habitacion")).join("");
  const bloqueo = climate ? `
    ${campo(E.bloqueo, `<input name="lockSwitch" list="dl-switch" value="${esc(a.child_lock_switch ?? "")}">`)}
    ${campo(E.bloqueoEncender, `<select name="lockStart">${opciones(E.bloqueoOpciones, a.child_lock_on_start)}</select>`)}
    ${campo(E.bloqueoApagar, `<select name="lockEnd">${opciones(E.bloqueoOpciones, a.child_lock_on_end)}</select>`)}` : "";
  const modo = h.notify ? h.notify.mode : "inherit";
  const canales = ctx.canalesIds.map((id) => casilla("notifyChannel", id, h.notify?.channels?.includes(id), id)).join("");
  const modos = { inherit: E.avisoHeredar, ...CASA.modosAviso };
  return `<form data-form="habitacion">
    ${datalist("dl-temp", ctx.sensores)}${datalist("dl-climate", ctx.climates)}${datalist("dl-switch", ctx.switches)}
    ${campo(E.nombre, `<input name="name" value="${esc(h.name)}">`)}
    ${campo(E.tipo, `<select name="actuatorType" data-estructural="1">${opciones(E.tipos, a.type)}</select>`)}
    ${campo(E.entidad, `<input name="entity" list="${climate ? "dl-climate" : "dl-switch"}" value="${esc(a.entity_id)}">`)}
    ${bloqueo}
    ${casilla("offOnlyHeating", E.soloSiEncendido, a.off_only_if_heating)}
    ${campo(E.intentos, `<input type="number" name="verify" min="${CASA.limites.intentosMin}" max="${CASA.limites.intentosMax}" value="${esc(a.verify_attempts)}">`)}
    <h3>${E.sensores}</h3>${sensores}
    <button type="button" data-accion="anadir-sensor-habitacion">+ ${E.anadirSensor}</button>
    ${campo(E.agregacion, `<select name="agg">${opciones(CASA.agregaciones, h.indoor_aggregation)}</select>`)}
    <h3>${E.avisoPropio}</h3>
    ${campo(CASA.global.modo, `<select name="notifyMode" data-estructural="1">${opciones(modos, modo)}</select>`)}
    ${modo === "inherit" ? "" : `<div class="casillas">${canales}</div>`}
    ${casilla("enabled", E.habilitada, h.enabled)}
    <div id="validacion-habitacion">${renderValidacion(validacion)}</div>
    <div class="botones"><button type="button" data-accion="cancelar-modal">${CASA.cancelar}</button>
    <button type="button" class="primario" data-accion="guardar-habitacion"${validacion?.ok ? "" : " disabled"}>${CASA.guardar}</button></div>
  </form>`;
}

/** Historial de versiones del plan. */
export function renderHistorial(lista, formatearFecha) {
  const T = TEXTOS.hist;
  const cuerpo = lista.length
    ? `<table><tbody>${lista.map((e) => `<tr><td>${esc(formatearFecha(e.time))}</td><td>${esc(T.antesDe)} ${esc(e.reason)}</td>
        <td class="muted">${esc(T.resumen.replace("{habitaciones}", e.rooms).replace("{tramos}", e.slots))}</td>
        <td><button data-accion="restaurar" data-i="${e.index}">${T.restaurar}</button></td></tr>`).join("")}</tbody></table>`
    : `<div class="mensaje">${T.vacio}</div>`;
  return `${cuerpo}<div class="botones"><button type="button" data-accion="cancelar-modal">${T.cerrar}</button></div>`;
}

// --- Vista completa --------------------------------------------------------------------------------------
export function renderCasa(datos, g, ctx, validacion) {
  return `<div class="tarjeta"><div class="titulo-tarjeta"><h2>${CASA.global.titulo}</h2>
      <button data-accion="historial">${TEXTOS.historial}</button></div>${renderGlobal(g, ctx, validacion)}</div>
    <div class="tarjeta"><div class="titulo-tarjeta"><h2>${CASA.habitaciones.titulo}</h2>
      <button data-accion="nueva-habitacion">+ ${CASA.habitaciones.anadir}</button></div>${renderHabitaciones(datos)}</div>`;
}

/** Pestañas de vista: Resumen | Casa. */
export function renderVistas(vista) {
  return `<div class="pestanas vistas">${Object.entries(CASA.vistas).map(([clave, texto]) =>
    `<button data-vista="${clave}" class="${clave === vista ? "sel" : ""}">${texto}</button>`).join("")}</div>`;
}
