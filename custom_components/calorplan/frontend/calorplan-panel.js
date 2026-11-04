// Versión: 2026.11.11
// Panel lateral de Calorplan (web component sin dependencias ni compilación).
// Vistas: «Resumen» (solo lectura) y «Casa» (ajustes globales y habitaciones).

import {
  canalesNotify, clonar, entidadesDe, fmtFecha, formToGlobal, formToRoom, habitacionVacia, sensoresTemperatura,
} from "./casa.js?v=2026.11.11";
import { CONFIG, TEXTOS } from "./config.js?v=2026.11.11";
import { esc } from "./logic.js?v=2026.11.11";
import { renderFormTramo, renderTramos, renderValidacionTramo } from "./render_tramos.js?v=2026.11.11";
import { duplicarTramo, formToSlot, tramoVacio } from "./tramos.js?v=2026.11.11";
import { formToPause, pausaVacia } from "./pausas.js?v=2026.11.11";
import { renderFormPausa, renderPausas } from "./render_pausas.js?v=2026.11.11";
import { PAUSAS } from "./textos_pausas.js?v=2026.11.11";
import { renderCabecera, renderPanel } from "./render.js?v=2026.11.11";
import {
  renderCasa, renderFormHabitacion, renderHistorial, renderModal, renderValidacion, renderVistas,
} from "./render_casa.js?v=2026.11.11";
import { ESTILOS } from "./styles.js?v=2026.11.11";
import { ESTILOS_CASA } from "./styles_casa.js?v=2026.11.11";
import { CASA } from "./textos_casa.js?v=2026.11.11";

class CalorplanPanel extends HTMLElement {
  constructor() {
    super();
    this._hass = null;
    this._datos = null; // resumen del servidor
    this._dia = null;
    this._error = null;
    this._vista = "resumen";
    this._global = null; // {original, draft, defaults, variables, validacion}
    this._modal = null; // {tipo, ...}
    this._temporizador = null;
    this._espera = null;
    this._raiz = this.attachShadow({ mode: "open" });
    this._raiz.innerHTML = `<style>${ESTILOS}${ESTILOS_CASA}</style><div id="contenido"></div><div id="modal"></div>`;
    this._raiz.addEventListener("click", (e) => this._alPulsar(e));
    this._raiz.addEventListener("input", (e) => this._alEditar(e, false));
    this._raiz.addEventListener("change", (e) => this._alEditar(e, true));
  }

  /** Home Assistant asigna `hass` en cada cambio de estado; se carga solo la primera vez. */
  set hass(hass) {
    const primera = this._hass === null;
    this._hass = hass;
    if (primera) this._cargar();
  }

  connectedCallback() {
    this._temporizador = setInterval(() => this._cargar(), CONFIG.refrescoSegundos * 1000);
    this._pintar();
  }

  disconnectedCallback() {
    clearInterval(this._temporizador);
    this._temporizador = null;
  }

  // --- Comunicación -------------------------------------------------------------------------------
  _ws(mensaje) {
    return this._hass.callWS(mensaje);
  }

  async _cargar() {
    if (!this._hass) return;
    try {
      this._datos = await this._ws({ type: CONFIG.comandoWs });
      this._error = null;
      if (this._dia === null) this._dia = this._datos.weekday;
    } catch (err) {
      this._error = err?.message ?? String(err);
    }
    // En «Casa» no se repinta: se perdería lo que se está editando.
    if (this._vista === "resumen") this._pintar();
    else if (this._error) this._pintar();
  }

  async _cargarGlobal() {
    const r = await this._ws({ type: "calorplan/get_global" });
    this._global = {
      original: r.global, draft: clonar(r.global), defaults: r.template_defaults,
      variables: r.template_variables, validacion: null,
    };
    this._pintar();
    this._validarGlobal();
  }

  // --- Contexto para los formularios -------------------------------------------------------------------
  _ctx() {
    const estados = this._hass?.states ?? {};
    return {
      sensores: sensoresTemperatura(estados),
      notify: canalesNotify(this._hass),
      climates: entidadesDe(estados, "climate"),
      switches: entidadesDe(estados, "switch"),
      canalesIds: this._datos?.channels ?? [],
      canalesGuardados: new Set((this._global?.original.channels ?? []).map((c) => c.id)),
      variables: this._global?.variables ?? [],
      plantillasDefecto: this._global?.defaults ?? {},
    };
  }

  // --- Pintado ------------------------------------------------------------------------------------------
  _pintar() {
    const cont = this._raiz.getElementById("contenido");
    if (this._error) {
      cont.innerHTML = `<div class="tarjeta mensaje error">${TEXTOS.error}: ${esc(this._error)}</div>`;
    } else if (!this._datos) {
      cont.innerHTML = `<div class="mensaje">${TEXTOS.cargando}</div>`;
    } else if (this._vista === "pausas") {
      cont.innerHTML = `${renderCabecera(this._datos, this._hora())}${renderVistas("pausas")}${renderPausas(this._datos)}`;
    } else if (this._vista === "tramos") {
      cont.innerHTML = `${renderCabecera(this._datos, this._hora())}${renderVistas("tramos")}${renderTramos(this._datos)}`;
    } else if (this._vista === "casa" && this._global) {
      const ahora = new Date();
      const cabecera = renderCabecera(this._datos, `${String(ahora.getHours()).padStart(2, "0")}:${String(ahora.getMinutes()).padStart(2, "0")}`);
      cont.innerHTML = `${cabecera}${renderVistas("casa")}${renderCasa(this._datos, this._global.draft, this._ctx(), this._global.validacion)}`;
    } else {
      cont.innerHTML = renderPanel(this._datos, this._dia ?? this._datos.weekday, new Date(), renderVistas(this._vista));
    }
    this._pintarModal();
  }

  _pintarModal() {
    const cont = this._raiz.getElementById("modal");
    const m = this._modal;
    if (!m) {
      cont.innerHTML = "";
    } else if (m.tipo === "habitacion") {
      const titulo = m.roomId ? CASA.editor.editar : CASA.editor.nueva;
      cont.innerHTML = renderModal(titulo, renderFormHabitacion(m.draft, this._ctx(), m.validacion));
    } else if (m.tipo === "pausa") {
      const sala = m.roomId ? this._datos.rooms.find((r) => r.id === m.roomId) : null;
      const ambito = sala ? sala.name : PAUSAS.editor.ambitoCasa;
      const titulo = m.pauseId ? PAUSAS.editor.editar : PAUSAS.editor.nueva;
      cont.innerHTML = renderModal(titulo, renderFormPausa(m.draft, ambito, m.validacion));
    } else if (m.tipo === "tramo") {
      const sala = this._datos.rooms.find((r) => r.id === m.roomId);
      const titulo = `${m.slotId ? TEXTOS.editor.editar : TEXTOS.editor.nuevo} · ${sala.name}`;
      cont.innerHTML = renderModal(titulo, renderFormTramo(m.draft, sala, this._ctx(), m.validacion));
    } else if (m.tipo === "historial") {
      cont.innerHTML = renderModal(TEXTOS.hist.titulo, renderHistorial(m.lista, fmtFecha));
    }
  }

  /** Actualiza solo el área de validación y el botón de guardar (sin perder el foco). */
  _pintarValidacion(validacion, accionGuardar, zonaId) {
    const zona = this._raiz.querySelector(`#${zonaId}`);
    if (zona) zona.innerHTML = renderValidacion(validacion);
    const boton = this._raiz.querySelector(`[data-accion="${accionGuardar}"]`);
    if (boton) boton.disabled = !validacion?.ok;
  }

  // --- Eventos ------------------------------------------------------------------------------------------
  _formulario(tipo) {
    return this._raiz.querySelector(`form[data-form="${tipo}"]`);
  }

  _sincronizarGlobal() {
    const f = this._formulario("global");
    if (f && this._global) this._global.draft = formToGlobal(new FormData(f), this._global.draft);
  }

  _sincronizarHabitacion() {
    const f = this._formulario("habitacion");
    if (f && this._modal?.tipo === "habitacion") {
      this._modal.draft = formToRoom(new FormData(f), this._modal.base);
    }
  }

  _sincronizarPausa() {
    const f = this._formulario("pausa");
    if (f && this._modal?.tipo === "pausa") this._modal.draft = formToPause(new FormData(f));
  }

  async _validarPausa() {
    const m = this._modal;
    if (!m || m.tipo !== "pausa") return;
    try {
      m.validacion = await this._ws({
        type: CONFIG.comandoValidarPausa, pause: m.draft, pause_id: m.pauseId, room_id: m.roomId,
      });
    } catch (err) {
      m.validacion = { ok: false, error: err?.message ?? String(err) };
    }
    this._pintarValidacion(m.validacion, "guardar-pausa", "validacion-pausa");
  }

  _hora() {
    const a = new Date();
    return `${String(a.getHours()).padStart(2, "0")}:${String(a.getMinutes()).padStart(2, "0")}`;
  }

  _salaDelModal() {
    return this._datos.rooms.find((r) => r.id === this._modal.roomId);
  }

  _sincronizarTramo() {
    const f = this._formulario("tramo");
    if (f && this._modal?.tipo === "tramo") {
      this._modal.draft = formToSlot(new FormData(f), this._salaDelModal());
    }
  }

  _alEditar(evento, esChange) {
    const form = evento.target.closest("form");
    if (!form) return;
    const estructural = esChange && evento.target.dataset.estructural;
    if (form.dataset.form === "global") {
      this._sincronizarGlobal();
      if (estructural) this._pintar();
      this._programar(() => this._validarGlobal());
    } else if (form.dataset.form === "pausa") {
      this._sincronizarPausa();
      if (estructural) this._pintarModal();
      this._programar(() => this._validarPausa());
    } else if (form.dataset.form === "tramo") {
      this._sincronizarTramo();
      if (estructural) this._pintarModal();
      this._programar(() => this._validarTramo());
    } else if (form.dataset.form === "habitacion") {
      this._sincronizarHabitacion();
      if (estructural) this._pintarModal();
      this._programar(() => this._validarHabitacion());
    }
  }

  /** Ejecuta la validación tras una breve espera (evita una llamada por tecla). */
  _programar(accion) {
    clearTimeout(this._espera);
    this._espera = setTimeout(accion, CONFIG.esperaValidacionMs);
  }

  async _validarGlobal() {
    if (!this._global) return;
    const g = this._global;
    try {
      g.validacion = await this._ws({ type: "calorplan/validate_global", global: g.draft });
    } catch (err) {
      g.validacion = { ok: false, error: err?.message ?? String(err) };
    }
    this._pintarValidacion(g.validacion, "guardar-global", "validacion-global");
  }

  async _validarHabitacion() {
    const m = this._modal;
    if (!m || m.tipo !== "habitacion") return;
    try {
      m.validacion = await this._ws({ type: "calorplan/validate_room", room: m.draft, room_id: m.roomId });
    } catch (err) {
      m.validacion = { ok: false, error: err?.message ?? String(err) };
    }
    this._pintarValidacion(m.validacion, "guardar-habitacion", "validacion-habitacion");
  }

  _pintarValidacionTramo() {
    const m = this._modal;
    const zona = this._raiz.querySelector("#validacion-tramo");
    if (zona) zona.innerHTML = renderValidacionTramo(m.validacion, this._salaDelModal());
    const boton = this._raiz.querySelector('[data-accion="guardar-tramo"]');
    if (boton) boton.disabled = !m.validacion?.ok;
  }

  async _validarTramo() {
    const m = this._modal;
    if (!m || m.tipo !== "tramo") return;
    try {
      m.validacion = await this._ws({
        type: CONFIG.comandoValidar, room_id: m.roomId, slot: m.draft, slot_id: m.slotId,
      });
    } catch (err) {
      m.validacion = { ok: false, error: err?.message ?? String(err), conflicts: [] };
    }
    this._pintarValidacionTramo();
  }

  async _alPulsar(evento) {
    const boton = evento.target.closest("button");
    if (!boton) return;
    const d = boton.dataset;
    try {
      if (d.vista) await this._cambiarVista(d.vista);
      else if (d.dia !== undefined) { this._dia = Number(d.dia); this._pintar(); }
      else if (d.accion) await this._accion(d.accion, d);
    } catch (err) {
      this._error = err?.message ?? String(err);
      this._pintar();
    }
  }

  async _cambiarVista(vista) {
    this._vista = vista;
    this._modal = null;
    if (vista === "casa") await this._cargarGlobal();
    else this._pintar();
  }

  async _accion(accion, d) {
    const g = this._global;
    switch (accion) {
      case "actualizar": return this._cargar();
      // --- Ajustes globales: estructura
      case "anadir-sensor-global": this._sincronizarGlobal(); g.draft.outdoor_sensors.push(""); return this._pintar();
      case "quitar-sensor-global": this._sincronizarGlobal(); g.draft.outdoor_sensors.splice(Number(d.i), 1); return this._pintar();
      case "anadir-canal": this._sincronizarGlobal(); g.draft.channels.push({ id: "", service: "", type: "notify" }); return this._pintar();
      case "quitar-canal": return this._quitarCanal(Number(d.i));
      case "probar-canal": return this._probarCanal(d.canal);
      case "descartar-global": g.draft = clonar(g.original); this._pintar(); return this._validarGlobal();
      case "guardar-global": return this._guardarGlobal();
      // --- Habitaciones
      case "nueva-habitacion": return this._abrirHabitacion(null);
      case "editar-habitacion": return this._abrirHabitacion(d.room);
      case "borrar-habitacion": return this._borrarHabitacion(d.room);
      case "anadir-sensor-habitacion": this._sincronizarHabitacion(); this._modal.draft.sensors.push(""); return this._pintarModal();
      case "quitar-sensor-habitacion": this._sincronizarHabitacion(); this._modal.draft.sensors.splice(Number(d.i), 1); return this._pintarModal();
      case "guardar-habitacion": return this._guardarHabitacion();
      // --- Pausas
      case "nueva-pausa": return this._abrirPausa(d.room, null);
      case "editar-pausa": return this._abrirPausa(d.room, d.pausa);
      case "alternar-pausa": return this._alternarPausa(d.room, d.pausa);
      case "borrar-pausa": return this._borrarPausa(d.room, d.pausa);
      case "guardar-pausa": return this._guardarPausa();
      // --- Tramos
      case "nuevo-tramo": return this._abrirTramo(d.room, null, null);
      case "editar-tramo": return this._abrirTramo(d.room, d.slot, "editar");
      case "duplicar-tramo": return this._abrirTramo(d.room, d.slot, "duplicar");
      case "alternar-tramo": return this._alternarTramo(d.room, d.slot);
      case "borrar-tramo": return this._borrarTramo(d.room, d.slot);
      case "guardar-tramo": return this._guardarTramo();
      // --- Historial y diálogos
      case "historial": return this._abrirHistorial();
      case "restaurar": return this._restaurar(Number(d.i));
      case "cancelar-modal": this._modal = null; return this._pintarModal();
      default: return undefined;
    }
  }

  // --- Ajustes globales ------------------------------------------------------------------------------------
  _quitarCanal(i) {
    this._sincronizarGlobal();
    const g = this._global.draft;
    const [quitado] = g.channels.splice(i, 1);
    g.default_notify.channels = g.default_notify.channels.filter((c) => c !== quitado.id);
    this._pintar();
    this._programar(() => this._validarGlobal());
  }

  async _probarCanal(canal) {
    const zona = this._raiz.querySelector("#resultado-prueba");
    try {
      await this._hass.callService("calorplan", "test_notification", { channel: canal });
      zona.innerHTML = `<span class="ok">${esc(CASA.global.probado)}: ${esc(canal)}</span>`;
    } catch (err) {
      zona.innerHTML = `<span class="error">${esc(CASA.global.errorProbar)}: ${esc(err?.message ?? err)}</span>`;
    }
  }

  async _guardarGlobal() {
    this._sincronizarGlobal();
    const g = this._global;
    if (g.original.shadow_mode && !g.draft.shadow_mode && !confirm(CASA.global.confirmarSombra)) return;
    try {
      const r = await this._ws({ type: "calorplan/save_global", global: g.draft });
      g.original = r.global;
      g.draft = clonar(r.global);
      this._datos = r.overview;
      g.validacion = { ok: true, warnings: [] };
      this._pintar();
      this._raiz.querySelector("#validacion-global").insertAdjacentHTML("beforeend", `<div class="ok">${CASA.guardado}</div>`);
    } catch (err) {
      g.validacion = { ok: false, error: `${CASA.errorGuardar}: ${err?.message ?? err}` };
      this._pintarValidacion(g.validacion, "guardar-global", "validacion-global");
    }
  }

  // --- Habitaciones ----------------------------------------------------------------------------------------
  async _abrirHabitacion(roomId) {
    const sala = roomId ? this._datos.rooms.find((r) => r.id === roomId) : null;
    this._modal = {
      tipo: "habitacion", roomId, base: sala ? clonar(sala.config) : null,
      draft: sala ? clonar(sala.config) : habitacionVacia(), validacion: null,
    };
    this._pintarModal();
    await this._validarHabitacion();
  }

  async _guardarHabitacion() {
    this._sincronizarHabitacion();
    const m = this._modal;
    try {
      const r = await this._ws({ type: "calorplan/save_room", room: m.draft, room_id: m.roomId });
      this._datos = r.overview;
      this._modal = null;
      this._pintar();
    } catch (err) {
      m.validacion = { ok: false, error: `${CASA.errorGuardar}: ${err?.message ?? err}` };
      this._pintarValidacion(m.validacion, "guardar-habitacion", "validacion-habitacion");
    }
  }

  async _borrarHabitacion(roomId) {
    const sala = this._datos.rooms.find((r) => r.id === roomId);
    const texto = CASA.habitaciones.confirmarBorrar.replace("{habitacion}", sala.name).replace("{tramos}", sala.slots.length);
    if (!confirm(texto)) return;
    const r = await this._ws({ type: "calorplan/delete_room", room_id: roomId });
    this._datos = r.overview;
    this._pintar();
  }

  // --- Tramos ---------------------------------------------------------------------------------------------
  _tramo(roomId, slotId) {
    const sala = this._datos.rooms.find((r) => r.id === roomId);
    return { sala, slot: slotId ? sala.slots.find((t) => t.id === slotId) : null };
  }

  async _abrirTramo(roomId, slotId, modo) {
    const { sala, slot } = this._tramo(roomId, slotId);
    let draft = tramoVacio(sala);
    let idEditado = null;
    if (slot && modo === "duplicar") {
      draft = duplicarTramo(slot.config);
    } else if (slot) {
      draft = clonar(slot.config);
      idEditado = slot.id;
    }
    delete draft.id; // el identificador lo gestiona el servidor
    this._modal = { tipo: "tramo", roomId, slotId: idEditado, draft, validacion: null };
    this._pintarModal();
    await this._validarTramo();
  }

  async _guardarTramo() {
    this._sincronizarTramo();
    const m = this._modal;
    try {
      const r = await this._ws({ type: CONFIG.comandoGuardar, room_id: m.roomId, slot: m.draft, slot_id: m.slotId });
      this._datos = r.overview;
      this._modal = null;
      this._pintar();
    } catch (err) {
      m.validacion = { ok: false, error: `${CASA.errorGuardar}: ${err?.message ?? err}`, conflicts: [] };
      this._pintarValidacionTramo();
    }
  }

  async _alternarTramo(roomId, slotId) {
    const { slot } = this._tramo(roomId, slotId);
    const config = clonar(slot.config);
    config.enabled = !config.enabled;
    delete config.id;
    const r = await this._ws({ type: CONFIG.comandoGuardar, room_id: roomId, slot: config, slot_id: slotId });
    this._datos = r.overview;
    this._pintar();
  }

  async _borrarTramo(roomId, slotId) {
    const { sala, slot } = this._tramo(roomId, slotId);
    const texto = TEXTOS.editor.confirmarBorrar.replace("{tramo}", slot.name).replace("{habitacion}", sala.name);
    if (!confirm(texto)) return;
    const r = await this._ws({ type: CONFIG.comandoBorrar, room_id: roomId, slot_id: slotId });
    this._datos = r.overview;
    this._pintar();
  }

  // --- Pausas ---------------------------------------------------------------------------------------------
  _listaPausas(roomId) {
    return roomId ? this._datos.rooms.find((r) => r.id === roomId).pauses : this._datos.global_pauses;
  }

  async _abrirPausa(roomId, pauseId) {
    const existente = pauseId ? this._listaPausas(roomId).find((p) => p.id === pauseId) : null;
    const draft = existente
      ? { reason: existente.reason, from: existente.from, until: existente.until, enabled: existente.enabled }
      : pausaVacia(this._datos.today);
    this._modal = { tipo: "pausa", roomId: roomId || null, pauseId: pauseId || null, draft, validacion: null };
    this._pintarModal();
    await this._validarPausa();
  }

  async _guardarPausa() {
    this._sincronizarPausa();
    const m = this._modal;
    try {
      const r = await this._ws({ type: CONFIG.comandoGuardarPausa, pause: m.draft, pause_id: m.pauseId, room_id: m.roomId });
      this._datos = r.overview;
      this._modal = null;
      this._pintar();
    } catch (err) {
      m.validacion = { ok: false, error: `${CASA.errorGuardar}: ${err?.message ?? err}` };
      this._pintarValidacion(m.validacion, "guardar-pausa", "validacion-pausa");
    }
  }

  async _alternarPausa(roomId, pauseId) {
    const p = this._listaPausas(roomId).find((x) => x.id === pauseId);
    const pause = { reason: p.reason, from: p.from, until: p.until, enabled: !p.enabled };
    const r = await this._ws({ type: CONFIG.comandoGuardarPausa, pause, pause_id: pauseId, room_id: roomId || null });
    this._datos = r.overview;
    this._pintar();
  }

  async _borrarPausa(roomId, pauseId) {
    const p = this._listaPausas(roomId).find((x) => x.id === pauseId);
    const ambito = roomId ? this._datos.rooms.find((r) => r.id === roomId).name : PAUSAS.editor.ambitoCasa;
    const texto = PAUSAS.editor.confirmarBorrar.replace("{pausa}", p.reason || PAUSAS.sinMotivo).replace("{ambito}", ambito);
    if (!confirm(texto)) return;
    const r = await this._ws({ type: CONFIG.comandoBorrarPausa, pause_id: pauseId, room_id: roomId || null });
    this._datos = r.overview;
    this._pintar();
  }

  // --- Historial ----------------------------------------------------------------------------------------------
  async _abrirHistorial() {
    const lista = await this._ws({ type: "calorplan/history" });
    this._modal = { tipo: "historial", lista };
    this._pintarModal();
  }

  async _restaurar(indice) {
    if (!confirm(TEXTOS.hist.confirmar)) return;
    const r = await this._ws({ type: "calorplan/restore", index: indice });
    this._datos = r.overview;
    this._modal = null;
    await this._cargarGlobal();
  }
}

customElements.define("calorplan-panel", CalorplanPanel);
