# Versión: 2026.11.2
"""Planificador: calcula inicios, fines y reintentos de los tramos."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Iterator

from .. import settings as ajustes
from ..models import Plan, Room, Slot
from .records import PlannedEvent


class Planner:
    """Genera los eventos planificados a partir de un plan (sin estado)."""

    def __init__(self, plan: Plan) -> None:
        self.plan = plan

    @staticmethod
    def _ocurrencias(slot: Slot, desde: datetime, hasta: datetime) -> Iterator[tuple[datetime, datetime]]:
        """Pares (inicio, fin) de las ocurrencias que empiezan cerca del rango.

        El día de un tramo es el día de su inicio. Se incluye un margen hacia
        atrás para detectar tramos que empezaron antes y siguen activos.
        """
        zona = desde.tzinfo
        dia: date = desde.date() - timedelta(days=ajustes.DIAS_MARGEN_PLANIFICACION)
        ultimo: date = hasta.date()
        while dia <= ultimo:
            if dia.weekday() in slot.days:
                inicio = datetime.combine(dia, slot.start, tzinfo=zona)
                if slot.duration_minutes is not None:
                    fin = inicio + timedelta(minutes=slot.duration_minutes)
                else:
                    assert slot.end is not None
                    dia_fin = dia if slot.end > slot.start else dia + timedelta(days=1)
                    fin = datetime.combine(dia_fin, slot.end, tzinfo=zona)
                yield inicio, fin
            dia += timedelta(days=1)

    def _eventos_tramo(self, room: Room, slot: Slot, desde: datetime, hasta: datetime) -> list[PlannedEvent]:
        """Eventos de un tramo con desde < instante <= hasta."""
        eventos = []
        for inicio, fin in self._ocurrencias(slot, desde, hasta):
            candidatos = [(inicio, ajustes.EVENTO_INICIO), (fin, ajustes.EVENTO_FIN)]
            if slot.retry_off_minutes > 0:
                candidatos.append((fin + timedelta(minutes=slot.retry_off_minutes),
                                   ajustes.EVENTO_REINTENTO))
            for cuando, tipo in candidatos:
                if desde < cuando <= hasta:
                    eventos.append(PlannedEvent(cuando, tipo, room.id, slot.id))
        return eventos

    def events_between(self, desde: datetime, hasta: datetime,
                       room_id: str | None = None) -> list[PlannedEvent]:
        """Eventos con desde < instante <= hasta, ordenados (fin→reintento→inicio)."""
        eventos: list[PlannedEvent] = []
        for sala in self.plan.rooms:
            if room_id is not None and sala.id != room_id:
                continue
            for tramo in sala.slots:
                eventos.extend(self._eventos_tramo(sala, tramo, desde, hasta))
        return sorted(eventos, key=lambda e: e.orden)

    def next_event(self, desde: datetime, room_id: str | None = None) -> PlannedEvent | None:
        """Primer evento estrictamente posterior a `desde` dentro del horizonte."""
        hasta = desde + timedelta(days=ajustes.HORIZONTE_PLANIFICACION_DIAS)
        eventos = self.events_between(desde, hasta, room_id)
        return eventos[0] if eventos else None

    def next_start(self, desde: datetime, room_id: str) -> PlannedEvent | None:
        """Próximo inicio de tramo (ignora fines y reintentos) de una habitación."""
        hasta = desde + timedelta(days=ajustes.HORIZONTE_PLANIFICACION_DIAS)
        for evento in self.events_between(desde, hasta, room_id):
            if evento.kind == ajustes.EVENTO_INICIO:
                return evento
        return None

    def active_slots(self, room: Room, instante: datetime) -> list[Slot]:
        """Tramos de la habitación activos en `instante` (inicio <= t < fin)."""
        activos = []
        for tramo in room.slots:
            for inicio, fin in self._ocurrencias(tramo, instante, instante):
                if inicio <= instante < fin:
                    activos.append(tramo)
                    break
        return activos
