# Versión: 2026.11.5
"""Configuración central: todas las constantes y valores por defecto.

Ningún otro fichero del proyecto debe contener valores fijos (horas, umbrales,
textos por defecto, nombres de eventos...). Todo se define aquí.
"""
from __future__ import annotations

# --- Identificación ---------------------------------------------------------
VERSION = "2026.11.5"
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
MOTIVO_EXTERIOR_ALTO = "Exterior {valor} ≥ {umbral}"
MOTIVO_INTERIOR_CALIDO = "Interior {valor} ≥ {umbral}"
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
