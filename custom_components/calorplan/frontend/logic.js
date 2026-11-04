// Versión: 2026.11.19
// Lógica pura del panel (sin DOM): formatos, posiciones de barras y descripciones.

import { CONFIG, TEXTOS } from "./config.js?v=2026.11.19";

/** Escapa texto para insertarlo en HTML. */
export function esc(valor) {
  return String(valor ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

/** Minutos desde las 00:00 → «HH:MM» (1440 → «24:00»). */
export function fmtMin(min) {
  const h = Math.floor(min / 60);
  const m = Math.round(min % 60);
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

/** Número sin ceros sobrantes (null → «—»). */
export function fmtNum(valor) {
  return valor === null || valor === undefined ? TEXTOS.nada : String(Number(valor.toFixed?.(1) ?? valor));
}

/** Posición y anchura (en %) de un segmento en la barra de 24 h. */
export function barStyle(seg) {
  const dia = CONFIG.minutosDia;
  return { left: (seg.start / dia) * 100, width: ((seg.end - seg.start) / dia) * 100 };
}

/** Estado visual de un segmento: active | disabled | normal. */
export function segState(room, slot, diaSeg, hoy, minutoActual, seg) {
  if (!room.enabled || !slot || !slot.enabled) return "disabled";
  const esHoy = diaSeg === hoy && seg.start <= minutoActual && minutoActual < seg.end;
  return esHoy ? "active" : "normal";
}

/** Resume los días de un tramo: «Diario», «L–V», «D–V», «S–D», «L, X». */
export function daysLabel(days) {
  const set = new Set(days);
  if (set.size === 7) return TEXTOS.diario;
  const nombres = CONFIG.diasCortos;
  // Empieza en un día incluido cuyo anterior no lo está (semana circular).
  const inicios = [...set].filter((d) => !set.has((d + 6) % 7)).sort((a, b) => a - b);
  const grupos = inicios.map((i) => {
    let fin = i;
    while (set.has((fin + 1) % 7) && (fin + 1) % 7 !== i) fin = (fin + 1) % 7;
    const largo = ((fin - i + 7) % 7) + 1;
    if (largo === 1) return nombres[i];
    if (largo === 2) return `${nombres[i]}, ${nombres[fin]}`;
    return `${nombres[i]}–${nombres[fin]}`;
  });
  return grupos.join(", ");
}

/** Texto de ayuda (tooltip) de un tramo. */
export function slotTitle(slot) {
  const [h, m] = slot.start.split(":").map(Number);
  const fin = (h * 60 + m + slot.duration_minutes) % CONFIG.minutosDia;
  const partes = [`${slot.name} ${slot.start}–${fmtMin(fin)}`, daysLabel(slot.days)];
  if (slot.setpoint !== null && slot.setpoint !== undefined) {
    partes.push(`${TEXTOS.tramo.objetivo} ${fmtNum(slot.setpoint)} ${TEXTOS.unidades.grados}`);
  }
  if (slot.outdoor_below !== null) partes.push(`${TEXTOS.tramo.exterior} ${fmtNum(slot.outdoor_below)}`);
  if (slot.indoor_below !== null) partes.push(`${TEXTOS.tramo.interior} ${fmtNum(slot.indoor_below)}`);
  if (!slot.enabled) partes.push(TEXTOS.deshabilitada);
  return partes.join(" · ");
}

/** Describe la simulación «¿qué haría ahora?» → {text, tone}. */
export function describeSimulation(sim) {
  if (!sim) return { text: TEXTOS.simulacion.sinTramos, tone: "muted" };
  const sufijo = sim.active ? "" : ` ${TEXTOS.simulacion.proximo}`;
  const nombre = `${sim.slot}${sufijo}`;
  if (sim.would_start) return { text: `${TEXTOS.simulacion.encenderia} · ${nombre}`, tone: "ok" };
  const conocido = TEXTOS.simulacion[sim.code];
  const motivo = conocido ?? sim.reason;
  const tono = ["outdoor_unavailable", "indoor_unavailable"].includes(sim.code) ? "error" : "warn";
  return { text: `${motivo} · ${nombre}`, tone: tono };
}

/** Texto relativo: «en 25 min», «en 3 h», «en 2 d». */
export function relativo(ms) {
  const min = Math.round(ms / 60000);
  if (min < 1) return "<1 min";
  if (min < 60) return `${min} ${TEXTOS.unidades.minutos}`;
  const horas = Math.round(min / 60);
  if (horas < 48) return `${horas} ${TEXTOS.unidades.horas}`;
  return `${Math.round(horas / 24)} d`;
}

/** Describe el próximo evento de una habitación. */
export function describeNext(next, room, ahora) {
  if (!next) return TEXTOS.nada;
  const cuando = new Date(next.time);
  const slot = room.slots.find((s) => s.id === next.slot_id);
  const hora = fmtMin(cuando.getHours() * 60 + cuando.getMinutes());
  const dia = cuando.toDateString() === ahora.toDateString() ? "" : `${CONFIG.diasLargos[(cuando.getDay() + 6) % 7]} `;
  return `${TEXTOS.eventos[next.kind]} ${slot ? slot.name : next.slot_id} · ${dia}${hora} (${TEXTOS.en} ${relativo(cuando - ahora)})`;
}

/** Describe la última acción registrada. */
export function describeLast(last) {
  if (!last) return { text: TEXTOS.nada, tone: "muted" };
  const accion = TEXTOS.acciones[last.action] ?? last.action;
  const hora = last.time ? fmtMin(new Date(last.time).getHours() * 60 + new Date(last.time).getMinutes()) : "";
  const sim = last.simulated ? ` (${TEXTOS.simulado})` : "";
  const tono = last.action === "error" ? "error" : last.action === "skip" ? "warn" : "ok";
  return { text: `${accion}${sim} · ${last.slot} ${hora}`, tone: tono, title: last.reason };
}
