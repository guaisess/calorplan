# Versión: 2026.11.26
"""Evaluador de condiciones de un tramo (temperatura exterior e interior)."""
from __future__ import annotations

from typing import Iterable

from .. import settings as ajustes
from ..models import Config, Room, Slot
from .ports import StatePort
from .records import Decision


class Evaluator:
    """Decide si un tramo debe encender según los sensores."""

    def __init__(self, state: StatePort) -> None:
        self._state = state

    def aggregate(self, entity_ids: Iterable[str],
                  modo: str = ajustes.AGREGACION_DEFECTO,
                  decimales: int = ajustes.DECIMALES_DEFECTO) -> float | None:
        """Agrega los sensores (mínimo, máximo o media) y redondea el resultado a los decimales
        configurados, de modo que lo que se compara es lo mismo que se muestra.
        Ignora los no numéricos o no disponibles."""
        valores = []
        for entidad in entity_ids:
            valor = self._state.get_float(entidad)
            if valor is not None:
                valores.append(valor)
        if not valores:
            return None
        if modo == ajustes.AGREGACION_MAX:
            resultado = max(valores)
        elif modo == ajustes.AGREGACION_MEDIA:
            resultado = sum(valores) / len(valores)
        else:
            resultado = min(valores)
        return round(resultado, decimales)

    def aggregate_min(self, entity_ids: Iterable[str]) -> float | None:
        """Mínimo de los sensores (atajo de `aggregate`)."""
        return self.aggregate(entity_ids, ajustes.AGREGACION_MIN)

    def evaluate(self, room: Room, slot: Slot, config: Config, politica: str | None = None) -> Decision:
        """Evalúa las condiciones del tramo con los valores actuales.

        `politica` permite forzar la política de «sin datos» (p. ej. conservadora tras un reinicio).
        """
        ignorar_sin_datos = (politica or config.unavailable_policy) == ajustes.POLITICA_ENCENDER_IGUAL
        exterior = (self.aggregate(config.outdoor_sensors, config.outdoor_aggregation, config.decimals)
                    if slot.outdoor_below is not None else None)
        interior = (self.aggregate(room.sensors, room.indoor_aggregation, config.decimals)
                    if slot.indoor_below is not None else None)

        # Exterior
        if slot.outdoor_below is not None:
            if exterior is None:
                if not ignorar_sin_datos:
                    return Decision(False, ajustes.COD_EXTERIOR_NO_DISPONIBLE,
                                    ajustes.MOTIVO_EXTERIOR_NO_DISPONIBLE, exterior, interior)
            elif not exterior < slot.outdoor_below:
                motivo = ajustes.MOTIVO_EXTERIOR_ALTO.format(
                    valor=_fmt(exterior, config.decimals), umbral=_fmt(slot.outdoor_below, config.decimals))
                return Decision(False, ajustes.COD_EXTERIOR_ALTO, motivo, exterior, interior)

        # Interior
        if slot.indoor_below is not None:
            if interior is None:
                if not ignorar_sin_datos:
                    return Decision(False, ajustes.COD_INTERIOR_NO_DISPONIBLE,
                                    ajustes.MOTIVO_INTERIOR_NO_DISPONIBLE, exterior, interior)
            elif not interior < slot.indoor_below:
                motivo = ajustes.MOTIVO_INTERIOR_CALIDO.format(
                    valor=_fmt(interior, config.decimals), umbral=_fmt(slot.indoor_below, config.decimals))
                return Decision(False, ajustes.COD_INTERIOR_CALIDO, motivo, exterior, interior)

        return Decision(True, ajustes.COD_OK, ajustes.MOTIVO_OK, exterior, interior)


def _fmt(valor: float, decimales: int) -> str:
    """Formatea un número con los decimales configurados."""
    return ajustes.FORMATO_NUMERO.format(decimales=decimales).format(valor)
