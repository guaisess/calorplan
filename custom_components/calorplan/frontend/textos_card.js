// Versión: 2026.11.16
// Configuración y textos de la tarjeta Lovelace (sin valores fijos en el código).

export const CONFIG_TARJETA = {
  nombreElemento: "calorplan-card",
  nombreEditor: "calorplan-card-editor",
  comandoResumen: "calorplan/card_summary",
  dominio: "calorplan",
  servicios: { ausencia: "set_away", pausa: "set_pause", quitarPausa: "clear_pause", habitacion: "set_room_enabled", tramo: "run_slot" },
  refrescoSegundos: 30,
  minutosDia: 1440,
  marcasHoras: [0, 6, 12, 18, 24],
  accionesDisponibles: ["away", "pause", "enable", "run"],
  porDefecto: { title: "Calefacción", show_timeline: true, actions: ["away", "pause"], rooms: [] },
};

export const TEXTOS_TARJETA = {
  cargando: "Cargando…",
  error: "No se pudo cargar Calorplan",
  sinHabitaciones: "No hay habitaciones que mostrar.",
  sombra: "Modo sombra",
  ausencia: "Ausencia",
  pausaGlobal: "Pausa global",
  exterior: "Exterior",
  nada: "—",
  deshabilitada: "Deshabilitada",
  enPausa: "En pausa",
  hasta: "hasta",
  sinTramoActivo: "Sin tramo activo",
  proximo: "Próximo",
  tramoActivo: "Activo",
  hastaHora: "hasta",
  eventos: { start: "inicio", end: "fin", retry: "reintento" },
  estados: { on: "Encendida", off: "Apagada", heat: "Calentando", unavailable: "No disponible" },
  acciones: {
    away: { activar: "Activar ausencia", desactivar: "Desactivar ausencia" },
    pause: { activar: "Pausar hasta mañana", desactivar: "Reanudar" },
    enable: { activar: "Habilitar", desactivar: "Deshabilitar" },
    run: "Ejecutar tramo ahora",
  },
  confirmarEjecutar: "¿Ejecutar «{tramo}» ahora en «{habitacion}»? Se enviarán las órdenes al aparato aunque no toque.",
  fallo: "La acción ha fallado",
  editor: {
    titulo: "Título",
    habitaciones: "Habitaciones (ids separados por comas; vacío = todas)",
    lineaTiempo: "Mostrar línea de tiempo de hoy",
    acciones: "Atajos",
    etiquetasAcciones: {
      away: "Modo ausencia",
      pause: "Pausar hasta mañana",
      enable: "Habilitar / deshabilitar habitación",
      run: "Ejecutar tramo ahora",
    },
  },
  descripcionSelector: "Resumen de la calefacción programada con Calorplan y su línea de tiempo de hoy.",
};
