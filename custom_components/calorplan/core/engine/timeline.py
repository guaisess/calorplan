# Versión: 2026.11.5
"""Línea de tiempo: segmentos por día de los tramos de una habitación."""
from __future__ import annotations

from typing import Any

from .. import settings as ajustes
from ..models import Room, Slot


def segmentos_dia(tramo: Slot, dia: int) -> list[dict[str, Any]]:
    """Segmentos de un tramo dentro de un día de la semana (0 = lunes).

    Un tramo que cruza la medianoche aparece en dos días: en el día de inicio
    (`continues_next`) y en el siguiente (`continued_from_prev`). La semana se
    trata como circular (el domingo enlaza con el lunes).
    """
    inicio_dia = dia * ajustes.MINUTOS_DIA
    fin_dia = inicio_dia + ajustes.MINUTOS_DIA
    segmentos = []
    for inicio, duracion in tramo.intervalos_semana():
        for desplazamiento in (-ajustes.MINUTOS_SEMANA, 0, ajustes.MINUTOS_SEMANA):
            s = inicio + desplazamiento
            e = s + duracion
            if s < fin_dia and e > inicio_dia:
                segmentos.append({
                    "slot_id": tramo.id,
                    "start": max(s, inicio_dia) - inicio_dia,
                    "end": min(e, fin_dia) - inicio_dia,
                    "continued_from_prev": s < inicio_dia,
                    "continues_next": e > fin_dia,
                })
    return sorted(segmentos, key=lambda x: x["start"])


def semana_habitacion(sala: Room) -> list[list[dict[str, Any]]]:
    """Segmentos de todos los tramos de la habitación, para los 7 días."""
    return [sorted((seg for tramo in sala.slots for seg in segmentos_dia(tramo, dia)),
                   key=lambda x: (x["start"], x["slot_id"]))
            for dia in ajustes.DIAS_SEMANA]
