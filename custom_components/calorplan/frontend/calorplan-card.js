// Versión: 2026.11.17
// Tarjeta Lovelace «calorplan-card»: resumen por habitación + línea de tiempo de hoy + atajos.

import { CONFIG_TARJETA as C, TEXTOS_TARJETA as T } from "./textos_card.js?v=2026.11.17";
import { llamadaAusencia, llamadaServicio, normalizarConfig, textoConfirmacion } from "./card_logic.js?v=2026.11.17";
import { renderTarjeta, esc } from "./render_card.js?v=2026.11.17";
import { ESTILOS_TARJETA } from "./styles_card.js?v=2026.11.17";
import "./card_editor.js?v=2026.11.17";

export class CalorplanCard extends HTMLElement {
  constructor() {
    super();
    this._resumen = null;
    this._error = null;
    this._hass = null;
    this._temporizador = null;
    this._config = normalizarConfig();
    this.attachShadow({ mode: "open" });
  }

  /** Configuración de Lovelace. */
  setConfig(config) {
    this._config = normalizarConfig(config);
    this._pintar();
  }

  /** Home Assistant entrega su objeto en cada cambio; el resumen se pide una sola vez al inicio. */
  set hass(hass) {
    const primera = !this._hass;
    this._hass = hass;
    if (primera) this._cargar();
  }

  getCardSize() {
    return 1 + (this._resumen?.rooms?.length ?? 2);
  }

  static getConfigElement() {
    return document.createElement(C.nombreEditor);
  }

  static getStubConfig() {
    return { ...C.porDefecto };
  }

  connectedCallback() {
    this._temporizador = setInterval(() => this._cargar(), C.refrescoSegundos * 1000);
  }

  disconnectedCallback() {
    clearInterval(this._temporizador);
  }

  /** Pide el resumen al backend (comando accesible a cualquier usuario). */
  async _cargar() {
    if (!this._hass) return;
    try {
      this._resumen = await this._hass.callWS({ type: C.comandoResumen });
      this._error = null;
    } catch (e) {
      this._error = e?.message ?? String(e);
    }
    this._pintar();
  }

  /** Dibuja la tarjeta. */
  _pintar() {
    const cuerpo = this._error ? `<div class="error">${esc(T.error)}: ${esc(this._error)}</div>`
      : this._resumen ? renderTarjeta(this._resumen, this._config) : `<div class="vacio">${esc(T.cargando)}</div>`;
    this.shadowRoot.innerHTML = `<style>${ESTILOS_TARJETA}</style><ha-card>${cuerpo}</ha-card>`;
    this.shadowRoot.querySelectorAll("button[data-accion]").forEach((b) =>
      b.addEventListener("click", () => this._accion(b.dataset.accion, b.dataset.sala)));
  }

  /** Ejecuta un atajo; «Ejecutar tramo ahora» pide confirmación. */
  async _accion(accion, salaId) {
    const r = this._resumen;
    const h = r.rooms.find((x) => x.id === salaId);
    const llamada = accion === "away" ? llamadaAusencia(r) : h ? llamadaServicio(accion, h, r) : null;
    if (!llamada) return;
    if (accion === "run" && !window.confirm(textoConfirmacion(h))) return;
    try {
      await this._hass.callService(C.dominio, llamada.servicio, llamada.datos);
    } catch (e) {
      window.alert(`${T.fallo}: ${e?.message ?? e}`);
    }
    await this._cargar();
  }
}

if (!customElements.get(C.nombreElemento)) customElements.define(C.nombreElemento, CalorplanCard);
window.customCards = window.customCards || [];
if (!window.customCards.some((t) => t.type === C.nombreElemento)) {
  window.customCards.push({ type: C.nombreElemento, name: "Calorplan", description: T.descripcionSelector, preview: false });
}
