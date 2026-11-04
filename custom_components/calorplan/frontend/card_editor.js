// Versión: 2026.11.16
// Editor visual sencillo de la tarjeta (inputs nativos, evento `config-changed`).

import { CONFIG_TARJETA as C, TEXTOS_TARJETA as T } from "./textos_card.js?v=2026.11.16";
import { normalizarConfig } from "./card_logic.js?v=2026.11.16";
import { esc } from "./render_card.js?v=2026.11.16";
import { ESTILOS_TARJETA } from "./styles_card.js?v=2026.11.16";

export class CalorplanCardEditor extends HTMLElement {
  constructor() {
    super();
    this._config = normalizarConfig();
    this.attachShadow({ mode: "open" });
  }

  setConfig(config) {
    this._config = normalizarConfig(config);
    this._pintar();
  }

  _pintar() {
    const E = T.editor;
    const cfg = this._config;
    const acciones = C.accionesDisponibles.map((a) =>
      `<label><input type="checkbox" data-accion="${a}" ${cfg.actions.includes(a) ? "checked" : ""}> ${esc(E.etiquetasAcciones[a])}</label>`).join("");
    this.shadowRoot.innerHTML = `<style>${ESTILOS_TARJETA}</style><div class="editor">
      <label>${esc(E.titulo)}</label><input type="text" id="titulo" value="${esc(cfg.title)}">
      <label>${esc(E.habitaciones)}</label><input type="text" id="salas" value="${esc(cfg.rooms.join(", "))}">
      <label><input type="checkbox" id="linea" ${cfg.show_timeline ? "checked" : ""}> ${esc(E.lineaTiempo)}</label>
      <label><b>${esc(E.acciones)}</b></label>${acciones}</div>`;
    this.shadowRoot.querySelectorAll("input").forEach((i) => i.addEventListener("change", () => this._cambio()));
  }

  /** Lee el formulario y avisa a Lovelace. */
  _cambio() {
    const r = this.shadowRoot;
    const config = {
      ...this._config,
      title: r.getElementById("titulo").value,
      rooms: r.getElementById("salas").value.split(",").map((x) => x.trim()).filter(Boolean),
      show_timeline: r.getElementById("linea").checked,
      actions: [...r.querySelectorAll("input[data-accion]")].filter((i) => i.checked).map((i) => i.dataset.accion),
    };
    this._config = normalizarConfig(config);
    this.dispatchEvent(new CustomEvent("config-changed", { detail: { config }, bubbles: true, composed: true }));
  }
}

if (!customElements.get(C.nombreEditor)) customElements.define(C.nombreEditor, CalorplanCardEditor);
