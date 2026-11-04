// Versión: 2026.11.17
// Lógica pura de la vista «Casa»: opciones desde Home Assistant y conversión de formularios.

import { lista, numero, parseEntries } from "./forms.js?v=2026.11.17";
import { CASA } from "./textos_casa.js?v=2026.11.17";

// --- Opciones (autocompletado) a partir de `hass` ----------------------------------------------
/** Ids de entidades de un dominio, ordenados. */
export function entidadesDe(estados, dominio) {
  return Object.keys(estados ?? {}).filter((id) => id.startsWith(`${dominio}.`)).sort();
}

/** Sensores de temperatura (device_class = temperature). */
export function sensoresTemperatura(estados) {
  return entidadesDe(estados, "sensor").filter((id) => estados[id]?.attributes?.device_class === "temperature");
}

/** Servicios `notify.*` y entidades `notify.*` utilizables como canal. */
export function canalesNotify(hass) {
  const servicios = Object.keys(hass?.services?.notify ?? {}).map((n) => `notify.${n}`);
  const entidades = entidadesDe(hass?.states, "notify");
  return [...new Set([...servicios, ...entidades])].sort();
}

// --- Ajustes globales ------------------------------------------------------------------------------
/** Convierte el formulario global en el diccionario que espera el servidor. */
export function formToGlobal(entries, base) {
  const f = parseEntries(entries);
  const ids = f.varios("ch_id");
  const servicios = f.varios("ch_service");
  const canales = ids.map((id, i) => ({ id: id.trim(), service: (servicios[i] ?? "").trim() }))
    .filter((c) => c.id || c.service)
    .map((c) => {
      const previo = (base.channels ?? []).find((x) => x.id === c.id);
      return { ...c, type: previo?.type ?? "notify", ...(previo?.templates ? { templates: previo.templates } : {}) };
    });
  const idsCanales = canales.map((c) => c.id);
  const plantillas = {};
  for (const accion of Object.keys(CASA.plantillaAcciones)) {
    const texto = f.uno(`tpl_${accion}`).trim();
    if (texto) plantillas[accion] = texto;
  }
  return {
    outdoor_sensors: lista(f.varios("sensor")),
    outdoor_aggregation: f.uno("outdoorAgg", "min"),
    away_mode: base.away_mode ?? false,
    shadow_mode: f.marcado("shadow"),
    unavailable_policy: f.uno("policy", "do_not_start"),
    catch_up: f.uno("catchUp", "none"),
    reevaluate_minutes: numero(f.uno("reevaluate")) ?? 0,
    startup_delay_seconds: numero(f.uno("startupDelay")) ?? CASA.defectos.esperaArranque,
    channels: canales,
    default_notify: {
      mode: f.uno("dnMode", "none"),
      channels: f.varios("dnChannel").filter((c) => idsCanales.includes(c)),
    },
    templates: plantillas,
  };
}

// --- Habitaciones ------------------------------------------------------------------------------------
/** Habitación vacía para el alta. */
export function habitacionVacia() {
  return {
    name: "",
    enabled: true,
    indoor_aggregation: CASA.defectos.agregacion,
    sensors: [""],
    notify: null,
    actuator: {
      type: CASA.defectos.tipo, entity_id: "", child_lock_switch: null,
      child_lock_on_start: CASA.defectos.bloqueoEncender, child_lock_on_end: CASA.defectos.bloqueoApagar,
      off_only_if_heating: true, verify_attempts: CASA.defectos.intentos, hvac_mode_on: CASA.defectos.hvacModoEncendido,
    },
  };
}

/** Convierte el formulario de habitación en el diccionario del servidor (sin id ni tramos). */
export function formToRoom(entries, base) {
  const f = parseEntries(entries);
  const tipo = f.uno("actuatorType", CASA.defectos.tipo);
  const modo = f.uno("notifyMode", CASA.defectos.modoAviso);
  return {
    name: f.uno("name").trim(),
    enabled: f.marcado("enabled"),
    indoor_aggregation: f.uno("agg", CASA.defectos.agregacion),
    sensors: lista(f.varios("sensor")),
    notify: modo === "inherit" ? null : { mode: modo, channels: f.varios("notifyChannel") },
    actuator: {
      type: tipo,
      entity_id: f.uno("entity").trim(),
      child_lock_switch: tipo === "climate" ? (f.uno("lockSwitch").trim() || null) : null,
      child_lock_on_start: f.uno("lockStart", CASA.defectos.bloqueoEncender),
      child_lock_on_end: f.uno("lockEnd", CASA.defectos.bloqueoApagar),
      off_only_if_heating: f.marcado("offOnlyHeating"),
      verify_attempts: numero(f.uno("verify")) ?? CASA.defectos.intentos,
      hvac_mode_on: base?.actuator?.hvac_mode_on ?? CASA.defectos.hvacModoEncendido,
    },
  };
}

// --- Utilidades ----------------------------------------------------------------------------------------
const dos = (n) => String(n).padStart(2, "0");

/** Fecha ISO → «dd/mm HH:MM» en hora local. */
export function fmtFecha(iso) {
  const d = new Date(iso);
  return `${dos(d.getDate())}/${dos(d.getMonth() + 1)} ${dos(d.getHours())}:${dos(d.getMinutes())}`;
}

/** Copia profunda de un objeto JSON. */
export const clonar = (obj) => JSON.parse(JSON.stringify(obj));
