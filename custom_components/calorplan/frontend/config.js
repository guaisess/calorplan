// Versión: 2026.11.5
// Configuración del panel: todos los textos y valores ajustables (sin valores fijos en el código).

export const CONFIG = {
  comandoWs: "calorplan/overview",
  refrescoSegundos: 30,
  minutosDia: 1440,
  anchoRangoCompleto: 7.5, // % mínimo de barra para mostrar «HH:MM–HH:MM»
  anchoSoloInicio: 4, // % mínimo para mostrar solo la hora de inicio
  marcasHoras: [0, 3, 6, 9, 12, 15, 18, 21, 24],
  diasCortos: ["L", "M", "X", "J", "V", "S", "D"],
  diasLargos: ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"],
};

export const TEXTOS = {
  titulo: "Calorplan",
  sombra: "Modo sombra",
  ausencia: "Ausencia",
  exterior: "Exterior",
  actualizar: "Actualizar",
  actualizado: "Actualizado",
  cargando: "Cargando…",
  error: "No se pudo cargar Calorplan",
  sinHabitaciones: "No hay habitaciones. Importa una configuración con calorplan.import_config.",
  lineaTiempo: "Línea de tiempo",
  estadoAhora: "Estado ahora",
  columnas: ["Habitación", "Actuador", "Tramo activo", "Próximo evento", "¿Qué haría ahora?", "Última acción"],
  diario: "Diario",
  nada: "—",
  deshabilitada: "deshabilitada",
  eventos: { start: "Inicio", end: "Fin", retry: "Reintento de apagado" },
  acciones: { on: "Encendió", off: "Apagó", skip: "Omitió", error: "Error" },
  simulado: "simulado",
  simulacion: {
    encenderia: "Encendería",
    away: "No: modo ausencia",
    room_disabled: "No: habitación deshabilitada",
    slot_disabled: "No: tramo deshabilitado",
    outdoor_unavailable: "No: sin dato exterior",
    indoor_unavailable: "No: sin dato interior",
    sinTramos: "Sin tramos",
    proximo: "(próximo tramo)",
  },
  tramo: { consigna: "consigna", exterior: "ext <", interior: "int <" },
  unidades: { grados: "°C", minutos: "min", horas: "h" },
  en: "en",
};
