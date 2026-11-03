// Versión: 2026.11.6
// Lógica pura de la edición de tramos: borradores y conversión del formulario.

import { CONFIG, TEXTOS } from "./config.js";
import { numero, parseEntries } from "./forms.js";

/** Tramo vacío para el alta (la consigna solo aplica a termostatos). */
export function tramoVacio(room) {
  const climate = room.actuator.type === "climate";
  return {
    name: "",
    enabled: true,
    days: [...CONFIG.diasLargos.keys()],
    start: CONFIG.inicioPorDefecto,
    end: CONFIG.finPorDefecto,
    setpoint: climate ? CONFIG.consignaPorDefecto : null,
    retry_off_minutes: CONFIG.reintentoPorDefecto,
    conditions: { outdoor_below: null, indoor_below: null },
    notify: null,
    notify_on_skip: false,
  };
}

/** Copia de un tramo para duplicarlo (sin id y con sufijo en el nombre). */
export function duplicarTramo(config) {
  const copia = JSON.parse(JSON.stringify(config));
  delete copia.id;
  copia.name = `${copia.name} ${TEXTOS.copiaSufijo}`.trim();
  return copia;
}

/** Convierte el formulario en el diccionario del servidor (sin id: lo gestiona el servidor). */
export function formToSlot(entries, room) {
  const f = parseEntries(entries);
  const modoFin = f.uno("endMode", "end");
  const modoAviso = f.uno("notifyMode", "inherit");
  const tramo = {
    name: f.uno("name").trim(),
    enabled: f.marcado("enabled"),
    days: f.varios("days").map(Number).sort((a, b) => a - b),
    start: f.uno("start"),
    setpoint: room.actuator.type === "climate" ? numero(f.uno("setpoint")) : null,
    retry_off_minutes: numero(f.uno("retry")) ?? CONFIG.reintentoPorDefecto,
    conditions: { outdoor_below: numero(f.uno("outdoor")), indoor_below: numero(f.uno("indoor")) },
    notify: modoAviso === "inherit" ? null : { mode: modoAviso, channels: f.varios("notifyChannel") },
    notify_on_skip: f.marcado("notifySkip"),
  };
  // Al cambiar de modo, el campo del modo nuevo aún no existe en el formulario: se usa un valor por defecto.
  if (modoFin === "duration") {
    tramo.duration_minutes = f.marcado("duration") ? numero(f.uno("duration")) : CONFIG.duracionPorDefecto;
  } else {
    tramo.end = f.uno("end", CONFIG.finPorDefecto);
  }
  return tramo;
}
