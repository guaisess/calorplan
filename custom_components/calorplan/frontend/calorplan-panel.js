// Versión: 2026.11.5
// Panel lateral de Calorplan (web component sin dependencias ni compilación).

import { CONFIG, TEXTOS } from "./config.js";
import { renderPanel } from "./render.js";
import { ESTILOS } from "./styles.js";
import { esc } from "./logic.js";

class CalorplanPanel extends HTMLElement {
  constructor() {
    super();
    this._hass = null;
    this._datos = null;
    this._dia = null;
    this._error = null;
    this._temporizador = null;
    this._raiz = this.attachShadow({ mode: "open" });
    this._raiz.addEventListener("click", (e) => this._alPulsar(e));
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

  async _cargar() {
    if (!this._hass) return;
    try {
      this._datos = await this._hass.callWS({ type: CONFIG.comandoWs });
      this._error = null;
      if (this._dia === null) this._dia = this._datos.weekday;
    } catch (err) {
      this._error = err?.message ?? String(err);
    }
    this._pintar();
  }

  _alPulsar(evento) {
    const boton = evento.target.closest("button");
    if (!boton) return;
    if (boton.dataset.dia !== undefined) {
      this._dia = Number(boton.dataset.dia);
      this._pintar();
    } else if (boton.dataset.accion === "actualizar") {
      this._cargar();
    }
  }

  _pintar() {
    let cuerpo;
    if (this._error) cuerpo = `<div class="tarjeta mensaje error">${TEXTOS.error}: ${esc(this._error)}</div>`;
    else if (!this._datos) cuerpo = `<div class="mensaje">${TEXTOS.cargando}</div>`;
    else cuerpo = renderPanel(this._datos, this._dia ?? this._datos.weekday, new Date());
    this._raiz.innerHTML = `<style>${ESTILOS}</style>${cuerpo}`;
  }
}

customElements.define("calorplan-panel", CalorplanPanel);
