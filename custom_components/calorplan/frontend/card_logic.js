// Versión: 2026.11.20
// Lógica pura de la tarjeta (sin DOM): configuración, filtrado, texto de estado y servicios.

import { CONFIG_TARJETA as C, TEXTOS_TARJETA as T } from "./textos_card.js?v=2026.11.20";

/** Normaliza la configuración del usuario aplicando los valores por defecto. */
export function normalizarConfig(cfg = {}) {
  const base = C.porDefecto;
  const lista = (v) => (Array.isArray(v) ? v : typeof v === "string" ? v.split(",") : []);
  return {
    ...cfg,
    title: cfg.title ?? base.title,
    show_timeline: cfg.show_timeline ?? base.show_timeline,
    actions: lista(cfg.actions ?? base.actions).filter((a) => C.accionesDisponibles.includes(a)),
    rooms: lista(cfg.rooms ?? base.rooms).map((r) => String(r).trim()).filter(Boolean),
  };
}

/** Habitaciones a mostrar según la lista configurada (vacía = todas), respetando su orden. */
export function filtrarHabitaciones(resumen, config) {
  const todas = resumen.rooms ?? [];
  if (!config.rooms.length) return todas;
  return config.rooms.map((id) => todas.find((h) => h.id === id)).filter(Boolean);
}

/** Minutos desde las 00:00 → «HH:MM». */
export function hhmm(min) {
  return `${String(Math.floor(min / 60)).padStart(2, "0")}:${String(Math.round(min % 60)).padStart(2, "0")}`;
}

/** Hora local «HH:MM» de una fecha ISO. */
export function horaDeIso(iso) {
  const d = new Date(iso);
  return hhmm(d.getHours() * 60 + d.getMinutes());
}

/** Posición y anchura (%) de un segmento en la barra de 24 h. */
export function posicion(seg) {
  return { left: (seg.start / C.minutosDia) * 100, width: ((seg.end - seg.start) / C.minutosDia) * 100 };
}

/** Estado de una habitación para pintar: disabled | paused | active | idle. */
export function estadoHabitacion(h) {
  if (!h.enabled) return "disabled";
  if (h.paused_by) return "paused";
  return h.active ? "active" : "idle";
}

/** Texto principal de estado de una habitación. */
export function textoEstado(h) {
  const e = estadoHabitacion(h);
  if (e === "disabled") return T.deshabilitada;
  if (e === "paused") return `${T.enPausa}${h.paused_by.until ? ` ${T.hasta} ${h.paused_by.until}` : ""}`;
  if (e === "active") return `${T.tramoActivo}: ${h.active.name}${h.active.end != null ? ` ${T.hastaHora} ${hhmm(h.active.end)}` : ""}`;
  return T.sinTramoActivo;
}

/** Texto del próximo evento («Próximo: inicio Mañana · 06:30»). */
export function textoProximo(h) {
  if (!h.next) return `${T.proximo}: ${T.nada}`;
  return `${T.proximo}: ${T.eventos[h.next.kind] ?? h.next.kind} ${h.next.slot_name} · ${horaDeIso(h.next.time)}`;
}

/** Acciones que se ofrecen para una habitación según la configuración y su estado. */
export function accionesHabitacion(h, config) {
  const lista = [];
  for (const a of config.actions) {
    if (a === "pause") lista.push({ id: "pause", activa: h.quick_pause });
    // «activa» = el estado que el botón desharía: habitación habilitada → se ofrece «Deshabilitar»
    else if (a === "enable") lista.push({ id: "enable", activa: h.enabled });
    else if (a === "run" && h.enabled && h.active) lista.push({ id: "run", activa: false });
  }
  return lista;
}

/** Llamada de servicio {servicio, datos} para una acción; `null` si no procede. */
export function llamadaServicio(accion, h, resumen) {
  const S = C.servicios;
  switch (accion) {
    case "pause":
      return h.quick_pause
        ? { servicio: S.quitarPausa, datos: { room_id: h.id, reason: resumen.quick_pause_reason } }
        : { servicio: S.pausa, datos: { room_id: h.id, reason: resumen.quick_pause_reason, from: resumen.today, until: resumen.today } };
    case "enable":
      return { servicio: S.habitacion, datos: { room_id: h.id, enabled: !h.enabled } };
    case "run":
      return h.active ? { servicio: S.tramo, datos: { room_id: h.id, slot_id: h.active.id, force: true } } : null;
    default:
      return null;
  }
}

/** Llamada de servicio del modo ausencia. */
export function llamadaAusencia(resumen) {
  return { servicio: C.servicios.ausencia, datos: { away: !resumen.away_mode } };
}

/** Texto de confirmación de «Ejecutar tramo ahora». */
export function textoConfirmacion(h) {
  return T.confirmarEjecutar.replace("{tramo}", h.active?.name ?? "").replace("{habitacion}", h.name);
}
