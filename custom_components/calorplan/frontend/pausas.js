// Versión: 2026.11.17
// Lógica pura de las pausas: borradores, formulario y formato de fechas.

import { parseEntries } from "./forms.js?v=2026.11.17";
import { PAUSAS } from "./textos_pausas.js?v=2026.11.17";

/** Suma días a una fecha «AAAA-MM-DD» (sin depender de la zona horaria). */
export function sumarDias(iso, dias) {
  const [a, m, d] = iso.split("-").map(Number);
  const fecha = new Date(Date.UTC(a, m - 1, d + dias));
  return fecha.toISOString().slice(0, 10);
}

/** «2026-12-20» → «20/12/2026». */
export function fmtDia(iso) {
  if (!iso) return PAUSAS.sinFin;
  const [a, m, d] = iso.split("-");
  return `${d}/${m}/${a}`;
}

/** Pausa nueva: desde hoy durante unos días (el usuario ajusta las fechas). */
export function pausaVacia(hoy) {
  return {
    reason: "", from: hoy, until: sumarDias(hoy, PAUSAS.defectos.diasDuracion), enabled: true,
  };
}

/** Convierte el formulario en el diccionario del servidor. «Sin fin» es explícito (null). */
export function formToPause(entries) {
  const f = parseEntries(entries);
  return {
    reason: f.uno("reason").trim(),
    from: f.uno("from"),
    until: f.marcado("noEnd") ? null : f.uno("until"),
    enabled: f.marcado("enabled"),
  };
}

/** Orden de las pausas: activas, próximas (por fecha), deshabilitadas y caducadas. */
export function ordenarPausas(pausas) {
  const rango = { active: 0, upcoming: 1, disabled: 2, expired: 3 };
  return [...pausas].sort((a, b) => (rango[a.status] - rango[b.status]) || a.from.localeCompare(b.from));
}
