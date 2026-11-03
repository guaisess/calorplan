# Versión: 2026.11.8
"""Notificador: elige modo y canales efectivos y envía los avisos."""
from __future__ import annotations

import logging

from .. import settings as ajustes
from ..models import Channel, NotifyConfig, Plan, Room, Slot
from .ports import ClockPort, NotifyPort
from .records import Record

_LOGGER = logging.getLogger(__name__)


class _VariablesSeguras(dict):
    """Diccionario que devuelve cadena vacía para variables ausentes."""

    def __missing__(self, clave: str) -> str:
        return ""


class Notifier:
    """Envía avisos de encendido, apagado, omisión y error."""

    def __init__(self, plan: Plan, notify: NotifyPort, clock: ClockPort) -> None:
        self.plan = plan
        self._notify = notify
        self._clock = clock

    # --- Configuración efectiva -------------------------------------------
    def efectivo(self, room: Room, slot: Slot) -> NotifyConfig:
        """Aviso efectivo: tramo → habitación → global."""
        return slot.notify or room.notify or self.plan.config.default_notify

    def _canales(self, room: Room, slot: Slot) -> list[Channel]:
        """Canales efectivos; si no hay ninguno, los del aviso global."""
        ids = self.efectivo(room, slot).channels or self.plan.config.default_notify.channels
        canales = [self.plan.config.canal(i) for i in ids]
        return [c for c in canales if c is not None]

    def debe_avisar(self, room: Room, slot: Slot, accion: str, codigo: str | None = None) -> bool:
        """Indica si la acción genera aviso según el modo efectivo."""
        modo = self.efectivo(room, slot).mode
        if accion == ajustes.ACCION_ERROR:
            return True  # los errores se avisan siempre
        if accion == ajustes.ACCION_OMITIR:
            # Ausencia, pausa y deshabilitados no avisan nunca (serían avisos diarios sin interés)
            return slot.notify_on_skip and codigo not in ajustes.CODIGOS_OMISION_SILENCIOSA
        if accion == ajustes.ACCION_ENCENDER:
            return modo in (ajustes.AVISO_ENCENDIDO, ajustes.AVISO_AMBOS)
        if accion == ajustes.ACCION_APAGAR:
            return modo in (ajustes.AVISO_APAGADO, ajustes.AVISO_AMBOS)
        return False

    # --- Mensajes ----------------------------------------------------------
    @staticmethod
    def _numero(valor: float | None) -> str:
        """Formatea un número opcional."""
        return "" if valor is None else ajustes.FORMATO_NUMERO.format(valor)

    def componer(self, canal: Channel, registro: Record) -> str:
        """Construye el mensaje con la plantilla del canal o la global."""
        plantilla = canal.templates.get(registro.action) or self.plan.config.plantilla(registro.action)
        variables = _VariablesSeguras(
            room=registro.room_name,
            slot=registro.slot_name,
            action=registro.action,
            setpoint=self._numero(registro.setpoint),
            outdoor=self._numero(registro.outdoor),
            indoor=self._numero(registro.indoor),
            reason=registro.reason,
            time=self._clock.now().strftime(ajustes.FORMATO_HORA),
        )
        return plantilla.format_map(variables)

    async def _enviar(self, canal: Channel, titulo: str, mensaje: str) -> bool:
        """Envía a un canal; un fallo no impide avisar al resto."""
        try:
            await self._notify.send(canal.service, titulo, mensaje)
            return True
        except Exception:  # noqa: BLE001 - cualquier fallo del servicio de aviso
            _LOGGER.exception("No se pudo enviar el aviso por '%s'", canal.id)
            return False

    # --- API pública -------------------------------------------------------
    async def notificar(self, room: Room, slot: Slot, registro: Record) -> int:
        """Avisa si corresponde. Devuelve cuántos canales recibieron el aviso."""
        if not self.debe_avisar(room, slot, registro.action, registro.code):
            return 0
        enviados = 0
        for canal in self._canales(room, slot):
            if await self._enviar(canal, ajustes.TITULO_AVISO, self.componer(canal, registro)):
                enviados += 1
        return enviados

    async def probar(self, canal_id: str) -> bool:
        """Envía un aviso de prueba a un canal concreto."""
        canal = self.plan.config.canal(canal_id)
        if canal is None:
            return False
        hora = self._clock.now().strftime(ajustes.FORMATO_HORA)
        return await self._enviar(canal, ajustes.TITULO_PRUEBA,
                                  ajustes.MENSAJE_PRUEBA.format(time=hora))
