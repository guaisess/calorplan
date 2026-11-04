# Versión: 2026.11.11
"""Configuración central: todas las constantes y valores por defecto.

Ningún otro fichero del proyecto debe contener valores fijos (horas, umbrales,
textos por defecto, nombres de eventos...). Todo se define aquí.
"""
from __future__ import annotations

# --- Identificación ---------------------------------------------------------
VERSION = "2026.11.11"
DOMAIN = "calorplan"
NOMBRE = "Calorplan"

# --- Almacenamiento ---------------------------------------------------------
SCHEMA_VERSION = 1
STORAGE_KEY = "calorplan"

# --- Calendario -------------------------------------------------------------
DIAS_SEMANA = (0, 1, 2, 3, 4, 5, 6)  # 0 = lunes ... 6 = domingo
FORMATO_HORA = "%H:%M"
MINUTOS_DIA = 1440
MINUTOS_SEMANA = 7 * MINUTOS_DIA
HORIZONTE_PLANIFICACION_DIAS = 8
DIAS_MARGEN_PLANIFICACION = 3  # días hacia atrás para hallar tramos que cruzan días
MINUTOS_MAX_REINTENTO = MINUTOS_DIA
MINUTOS_MAX_DURACION = MINUTOS_DIA
TOLERANCIA_RETRASO_SEGUNDOS = 300  # eventos más antiguos se consideran caducados

# --- Actuadores -------------------------------------------------------------
TIPO_CLIMATE = "climate"
TIPO_SWITCH = "switch"
TIPOS_ACTUADOR = (TIPO_CLIMATE, TIPO_SWITCH)
HVAC_MODO_ENCENDIDO = "heat"
HVAC_MODO_APAGADO = "off"
ESTADOS_NO_DISPONIBLE = ("unavailable", "unknown")
ESTADO_SWITCH_ENCENDIDO = "on"
ESTADO_SWITCH_APAGADO = "off"

# Bloqueo infantil: acción a aplicar al encender y al apagar
BLOQUEO_BLOQUEAR = "lock"
BLOQUEO_DESBLOQUEAR = "unlock"
BLOQUEO_NADA = "none"
ACCIONES_BLOQUEO = (BLOQUEO_BLOQUEAR, BLOQUEO_DESBLOQUEAR, BLOQUEO_NADA)
BLOQUEO_AL_ENCENDER_DEFECTO = BLOQUEO_BLOQUEAR
BLOQUEO_AL_APAGAR_DEFECTO = BLOQUEO_NADA

APAGAR_SOLO_SI_ENCENDIDO_DEFECTO = True
REINTENTO_APAGADO_MINUTOS_DEFECTO = 5
VERIFICAR_INTENTOS_DEFECTO = 3
VERIFICAR_ESPERA_SEGUNDOS = 30
DISPONIBILIDAD_TIMEOUT_SEGUNDOS = 180
DISPONIBILIDAD_SONDEO_SEGUNDOS = 10

# --- Condiciones ------------------------------------------------------------
POLITICA_NO_ENCENDER = "do_not_start"
POLITICA_ENCENDER_IGUAL = "start_anyway"
POLITICAS_NO_DISPONIBLE = (POLITICA_NO_ENCENDER, POLITICA_ENCENDER_IGUAL)
POLITICA_NO_DISPONIBLE_DEFECTO = POLITICA_NO_ENCENDER
MODO_SOMBRA_DEFECTO = False

# Agregación de varios sensores de temperatura
AGREGACION_MIN = "min"
AGREGACION_MAX = "max"
AGREGACION_MEDIA = "mean"
AGREGACIONES = (AGREGACION_MIN, AGREGACION_MAX, AGREGACION_MEDIA)
AGREGACION_DEFECTO = AGREGACION_MIN
MODO_AUSENCIA_DEFECTO = False

# Códigos de decisión del evaluador
COD_OK = "ok"
COD_AUSENCIA = "away"
COD_HABITACION_DESHABILITADA = "room_disabled"
COD_TRAMO_DESHABILITADO = "slot_disabled"
COD_EXTERIOR_NO_DISPONIBLE = "outdoor_unavailable"
COD_INTERIOR_NO_DISPONIBLE = "indoor_unavailable"
COD_EXTERIOR_ALTO = "outdoor_too_warm"
COD_INTERIOR_CALIDO = "indoor_warm_enough"
COD_ERROR = "error"
COD_SIMULACION = "dry_run"
COD_FORZADO = "forced"
COD_APAGADO_NO_VERIFICADO = "off_not_verified"
COD_NO_DISPONIBLE = "actuator_unavailable"

# Códigos del evaluador que se consideran un fallo (aviso de error siempre)
CODIGOS_FALLO = (COD_EXTERIOR_NO_DISPONIBLE, COD_INTERIOR_NO_DISPONIBLE)

# Textos de motivo (variables: valor, umbral, sensor)
MOTIVO_OK = "Condiciones cumplidas"
MOTIVO_AUSENCIA = "Modo ausencia activo"
MOTIVO_HABITACION_DESHABILITADA = "Habitación deshabilitada"
MOTIVO_TRAMO_DESHABILITADO = "Tramo deshabilitado"
MOTIVO_EXTERIOR_NO_DISPONIBLE = "Sin datos de temperatura exterior"
MOTIVO_INTERIOR_NO_DISPONIBLE = "Sin datos de temperatura interior"
MOTIVO_EXTERIOR_ALTO = "Exterior {valor} °C no es menor que {umbral} °C"
MOTIVO_INTERIOR_CALIDO = "Interior {valor} °C no es menor que {umbral} °C"
MOTIVO_FORZADO = "Ejecución manual"
MOTIVO_APAGADO_NO_VERIFICADO = "No se pudo verificar el apagado tras {intentos} intentos"
MOTIVO_ACTUADOR_ERROR = "Error al accionar el actuador: {error}"
MOTIVO_SIMULACION = "Modo sombra: habría hecho «{accion}» ({motivo})"
MOTIVO_TRAMO_INEXISTENTE = "Tramo o habitación inexistente"

# --- Arranque ---------------------------------------------------------------
CATCH_UP_NINGUNO = "none"
CATCH_UP_EVALUAR = "evaluate"
CATCH_UP_OPCIONES = (CATCH_UP_NINGUNO, CATCH_UP_EVALUAR)
CATCH_UP_DEFECTO = CATCH_UP_NINGUNO

# --- Avisos -----------------------------------------------------------------
AVISO_NINGUNO = "none"
AVISO_ENCENDIDO = "on"
AVISO_APAGADO = "off"
AVISO_AMBOS = "both"
MODOS_AVISO = (AVISO_NINGUNO, AVISO_ENCENDIDO, AVISO_APAGADO, AVISO_AMBOS)
AVISO_DEFECTO = AVISO_NINGUNO
CANAL_TIPO_NOTIFY = "notify"
CANAL_TIPOS = (CANAL_TIPO_NOTIFY,)
VARIABLES_PLANTILLA = (
    "room", "slot", "action", "setpoint", "outdoor", "indoor", "reason", "time",
)
FORMATO_NUMERO = "{:g}"

ACCION_ENCENDER = "on"
ACCION_APAGAR = "off"
ACCION_OMITIR = "skip"
ACCION_ERROR = "error"

# Plantillas por defecto (variables: room, slot, action, setpoint, outdoor,
# indoor, reason, time)
PLANTILLAS_DEFECTO = {
    ACCION_ENCENDER: (
        "🔥 CALEFACCIÓN ACTIVADA\n🏠 {room} · {slot}\n"
        "🌡️ Exterior: {outdoor} °C · Estancia: {indoor} °C · 🎯 Objetivo: {setpoint} °C"
    ),
    ACCION_APAGAR: "🔥 CALEFACCIÓN DESACTIVADA\n🏠 {room} · {slot}",
    ACCION_OMITIR: "⏭️ No se enciende {room} · {slot}\n{reason}",
    ACCION_ERROR: "⚠️ Problema en {room} · {slot}\n{reason}",
}
TITULO_AVISO = "Calorplan"
TITULO_PRUEBA = "Calorplan · prueba de aviso"
MENSAJE_PRUEBA = "Aviso de prueba de Calorplan ({time})"

# --- Eventos y señales ------------------------------------------------------
EVENTO_ACCION = "calorplan_action"
SENAL_ACTUALIZACION = "calorplan_actualizacion"

# --- Orden de eventos simultáneos (apagar antes de encender) ----------------
EVENTO_FIN = "end"
EVENTO_REINTENTO = "retry"
EVENTO_INICIO = "start"
ORDEN_EVENTOS = {EVENTO_FIN: 0, EVENTO_REINTENTO: 1, EVENTO_INICIO: 2}

# --- Capa de Home Assistant: servicios, campos y nombres de entidad ---------
SERVICIO_IMPORTAR = "import_config"
SERVICIO_EJECUTAR = "run_slot"
SERVICIO_AUSENCIA = "set_away"
SERVICIO_PRUEBA = "test_notification"
SERVICIO_RECARGAR = "reload"

CAMPO_RUTA = "path"
CAMPO_CONFIG = "config"
CAMPO_HABITACION = "room_id"
CAMPO_TRAMO = "slot_id"
CAMPO_FORZAR = "force"
CAMPO_AUSENTE = "away"
CAMPO_CANAL = "channel"

NOMBRE_SWITCH_HABITACION = "Calorplan {habitacion}"
NOMBRE_SWITCH_AUSENCIA = "Calorplan modo ausencia"
NOMBRE_SENSOR_PROXIMO = "Calorplan {habitacion} próximo"
NOMBRE_SENSOR_ULTIMA = "Calorplan {habitacion} última acción"
NOMBRE_TRAMO_ACTIVO = "Calorplan {habitacion} tramo activo"

ID_UNICO_SWITCH_HABITACION = "{dominio}_{habitacion}_habilitada"
ID_UNICO_SWITCH_AUSENCIA = "{dominio}_modo_ausencia"
ID_UNICO_SENSOR_PROXIMO = "{dominio}_{habitacion}_proximo"
ID_UNICO_SENSOR_ULTIMA = "{dominio}_{habitacion}_ultima_accion"
ID_UNICO_TRAMO_ACTIVO = "{dominio}_{habitacion}_tramo_activo"

PLATAFORMAS = ("switch", "sensor", "binary_sensor")

# Avisos mediante entidades notify (integraciones modernas)
NOTIFY_DOMINIO = "notify"
NOTIFY_SERVICIO_ENTIDAD = "send_message"

# --- Panel y API WebSocket ----------------------------------------------------
WS_OVERVIEW = "calorplan/overview"
PANEL_URL = "calorplan"
PANEL_TITULO = "Calorplan"
PANEL_ICONO = "mdi:radiator"
PANEL_COMPONENTE = "calorplan-panel"
PANEL_FICHERO = "calorplan-panel.js"
ESTATICO_URL = "/calorplan_static"
ESTATICO_CARPETA = "frontend"
CLAVE_ESTATICO = "calorplan_estatico_registrado"
CLAVE_PANEL = "calorplan_panel_registrado"

# --- Edición de tramos e historial de versiones ---------------------------------
HISTORIAL_MAX = 10
HISTORIAL_STORAGE_KEY = "calorplan_history"
ID_TRAMO_PREFIJO = "tramo"
MOTIVO_HIST_IMPORTAR = "Importación de configuración"
MOTIVO_HIST_GUARDAR = "Guardar tramo {habitacion}/{tramo}"
MOTIVO_HIST_BORRAR = "Borrar tramo {habitacion}/{tramo}"
MOTIVO_HIST_RESTAURAR = "Antes de restaurar una versión anterior"
ERROR_HABITACION_INEXISTENTE = "La habitación '{habitacion}' no existe"
ERROR_TRAMO_INEXISTENTE = "El tramo '{tramo}' no existe en '{habitacion}'"
ERROR_VERSION_INEXISTENTE = "La versión {indice} del historial no existe"

WS_VALIDAR_TRAMO = "calorplan/validate_slot"
WS_GUARDAR_TRAMO = "calorplan/save_slot"
WS_BORRAR_TRAMO = "calorplan/delete_slot"
WS_HISTORIAL = "calorplan/history"
WS_RESTAURAR = "calorplan/restore"

# --- Configuración global («Casa») ----------------------------------------------------
WS_GET_GLOBAL = "calorplan/get_global"
WS_VALIDAR_GLOBAL = "calorplan/validate_global"
WS_GUARDAR_GLOBAL = "calorplan/save_global"
MOTIVO_HIST_GLOBAL = "Guardar ajustes globales"
ERROR_PLANTILLA_FORMATO = "Plantilla '{plantilla}': formato no válido ({detalle})"
ERROR_PLANTILLA_VARIABLE = "Plantilla '{plantilla}': variable desconocida {{{variable}}}"
ERROR_PLANTILLA_ACCION = "Plantilla para una acción desconocida: '{accion}'"
ADVERTENCIA_CANAL_INEXISTENTE = "El servicio o entidad de aviso '{servicio}' no existe en Home Assistant"
ADVERTENCIA_SENSOR_INEXISTENTE = "El sensor '{sensor}' no existe en Home Assistant"
ADVERTENCIA_SOMBRA_APAGADO = "El modo sombra está desactivado: el motor actuará sobre los dispositivos"

# --- Edición de habitaciones ----------------------------------------------------------
ID_HABITACION_PREFIJO = "habitacion"
MOTIVO_HIST_HAB_GUARDAR = "Guardar habitación {habitacion}"
MOTIVO_HIST_HAB_BORRAR = "Borrar habitación {habitacion}"
WS_VALIDAR_HABITACION = "calorplan/validate_room"
WS_GUARDAR_HABITACION = "calorplan/save_room"
WS_BORRAR_HABITACION = "calorplan/delete_room"
ADVERTENCIA_ACTUADOR_INEXISTENTE = "El actuador '{entidad}' no existe en Home Assistant"
ADVERTENCIA_SENSOR_NO_TEMPERATURA = "'{sensor}' no es un sensor de temperatura (device_class: {clase})"
DEVICE_CLASS_TEMPERATURA = "temperature"

# --- Pausas (vacaciones, visitas, obras...) ------------------------------------------------------
FORMATO_FECHA = "%Y-%m-%d"
PAUSA_ACTIVA = "active"
PAUSA_PROXIMA = "upcoming"
PAUSA_CADUCADA = "expired"
PAUSA_DESHABILITADA = "disabled"
ID_PAUSA_PREFIJO = "pausa"
COD_PAUSA = "paused"
PAUSA_SIN_FIN = "sin fecha de fin"
PAUSA_AMBITO_CASA = "toda la casa"
MOTIVO_PAUSA = "Pausa «{motivo}» ({ambito}, {desde} → {hasta})"
MOTIVO_PAUSA_SIN_NOMBRE = "sin motivo"
ERROR_PAUSA_FECHA = "Pausa: '{campo}' debe ser una fecha AAAA-MM-DD"
ERROR_PAUSA_OBJETO = "Una pausa debe ser un objeto"
ERROR_PAUSA_ID = "Una pausa necesita 'id'"
ERROR_PAUSA_ORDEN = "Pausa: la fecha final no puede ser anterior a la inicial"
ERROR_PAUSAS_LISTA = "'pauses' debe ser una lista"
ERROR_PAUSA_REPETIDA = "ids de pausa repetidos"
ERROR_PAUSA_INEXISTENTE = "La pausa '{pausa}' no existe"
MOTIVO_HIST_PAUSA_GUARDAR = "Guardar pausa {ambito}/{pausa}"
MOTIVO_HIST_PAUSA_BORRAR = "Borrar pausa {ambito}/{pausa}"
WS_VALIDAR_PAUSA = "calorplan/validate_pause"
WS_GUARDAR_PAUSA = "calorplan/save_pause"
WS_BORRAR_PAUSA = "calorplan/delete_pause"
NOMBRE_EN_PAUSA = "Calorplan {habitacion} en pausa"
ID_UNICO_EN_PAUSA = "{dominio}_{habitacion}_en_pausa"
# Omisiones que nunca avisan, ni siquiera con «avisar también si se omite»
CODIGOS_OMISION_SILENCIOSA = (COD_AUSENCIA, COD_HABITACION_DESHABILITADA, COD_TRAMO_DESHABILITADO, COD_PAUSA)

# --- Reevaluación durante el tramo ----------------------------------------------------------------
REEVALUAR_MINUTOS_DEFECTO = 0  # 0 = solo se evalúa al inicio del tramo (comportamiento clásico)
REEVALUAR_MINUTOS_MAX = 1440
MOTIVO_REEVALUACION = "Condiciones cumplidas (reevaluación durante el tramo)"
ERROR_REEVALUAR = "'reevaluate_minutes' debe ser un entero entre 0 y {maximo}"
# Omisiones que pueden dejar de serlo más tarde: se reevalúan mientras el tramo siga activo
CODIGOS_REEVALUABLES = (COD_EXTERIOR_ALTO, COD_INTERIOR_CALIDO,
                        COD_EXTERIOR_NO_DISPONIBLE, COD_INTERIOR_NO_DISPONIBLE)

# --- Reinicio de Home Assistant: espera y estado ------------------------------------------------
ESPERA_ARRANQUE_DEFECTO = 120  # segundos sin actuar tras arrancar (las entidades se estabilizan)
ESPERA_ARRANQUE_MAX = 3600
ARRANQUE_REINTENTO_SEGUNDOS = 60  # reintento de tramos omitidos por falta de datos
ARRANQUE_REINTENTO_MAX_SEGUNDOS = 600  # hasta cuándo se reintenta tras la espera
ERROR_ESPERA_ARRANQUE = "'startup_delay_seconds' debe ser un entero entre 0 y {maximo}"
RUNTIME_STORAGE_KEY = "calorplan_runtime"
# Resultado del último inicio gestionado de un tramo (se guarda para sobrevivir a un reinicio)
RESULTADO_ENCENDIDO = "on"
RESULTADO_OMITIDO = "skip"
RESULTADO_ERROR = "error"
RESULTADO_PENDIENTE = "pending"  # omitido por condiciones: puede reevaluarse
RESULTADO_PENDIENTE_DATOS = "pending_data"  # omitido por falta de datos de sensores
CODIGOS_SIN_DATOS = (COD_EXTERIOR_NO_DISPONIBLE, COD_INTERIOR_NO_DISPONIBLE)

# --- Servicios de pausas para automatizaciones -----------------------------------------------------
SERVICIO_PAUSA = "set_pause"
SERVICIO_QUITAR_PAUSA = "clear_pause"
CAMPO_DESDE = "from"
CAMPO_HASTA = "until"
CAMPO_MOTIVO = "reason"
CAMPO_ACTIVA = "enabled"
CAMPO_ID_PAUSA = "pause_id"
PAUSA_CREADA = "created"
PAUSA_ACTUALIZADA = "updated"
PAUSA_SIN_CAMBIOS = "unchanged"
ERROR_QUITAR_PAUSA_FALTA = "Indica 'pause_id' o 'reason' para quitar una pausa"
