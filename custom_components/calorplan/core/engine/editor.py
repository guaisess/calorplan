# Versión: 2026.11.8
"""Editor del plan: altas, cambios y bajas de tramos con validación completa.

Cada operación devuelve un plan NUEVO (el original no se modifica): se vuelve a
construir desde un diccionario, de modo que se aplican todas las validaciones
(ids únicos, solapes, canales existentes...).
"""
from __future__ import annotations

import copy
import re
import unicodedata
from typing import Any

from .. import settings as ajustes
from ..models import ConfigError, Plan, Slot


def _slug(texto: str) -> str:
    """Convierte un nombre en un identificador: minúsculas, sin tildes, con guiones bajos."""
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", sin_tildes.lower()).strip("_")


def generar_id(nombre: str, existentes: list[str], prefijo: str = ajustes.ID_TRAMO_PREFIJO) -> str:
    """Id único a partir del nombre (`tramo`, `tramo_2`, ... si hay repetidos)."""
    base = _slug(nombre or "") or prefijo
    candidato, n = base, 2
    while candidato in existentes:
        candidato = f"{base}_{n}"
        n += 1
    return candidato


class PlanEditor:
    """Operaciones de edición sobre un plan (sin efectos secundarios)."""

    @staticmethod
    def _sala(datos: dict[str, Any], room_id: str) -> dict[str, Any]:
        """Diccionario de la habitación o ConfigError."""
        sala = next((r for r in datos["rooms"] if r["id"] == room_id), None)
        if sala is None:
            raise ConfigError(ajustes.ERROR_HABITACION_INEXISTENTE.format(habitacion=room_id))
        return sala

    @classmethod
    def guardar_tramo(cls, plan: Plan, room_id: str, tramo: dict[str, Any],
                      slot_id: str | None = None) -> tuple[Plan, str]:
        """Crea (slot_id=None) o sustituye un tramo. Devuelve (plan nuevo, id del tramo)."""
        datos = copy.deepcopy(plan.to_dict())
        sala = cls._sala(datos, room_id)
        tramo = dict(tramo)
        if slot_id is None:
            tramo["id"] = generar_id(str(tramo.get("name", "")), [t["id"] for t in sala["slots"]])
            sala["slots"].append(tramo)
        else:
            posicion = next((i for i, t in enumerate(sala["slots"]) if t["id"] == slot_id), None)
            if posicion is None:
                raise ConfigError(ajustes.ERROR_TRAMO_INEXISTENTE.format(
                    tramo=slot_id, habitacion=room_id))
            tramo["id"] = slot_id
            sala["slots"][posicion] = tramo
        if not str(tramo.get("name", "")).strip():
            tramo["name"] = tramo["id"]  # sin nombre: se usa el identificador
        return Plan.from_dict(datos), tramo["id"]

    @classmethod
    def guardar_habitacion(cls, plan: Plan, datos: dict[str, Any],
                           room_id: str | None = None) -> tuple[Plan, str]:
        """Crea (room_id=None) o modifica una habitación. Al modificar se conservan sus tramos.

        `datos` lleva nombre, actuador, sensores, agregación, avisos y habilitada; se ignoran
        `id` y `slots` si vienen del cliente.
        """
        completo = copy.deepcopy(plan.to_dict())
        datos = {k: v for k, v in datos.items() if k not in ("id", "slots")}
        if room_id is None:
            id_ = generar_id(str(datos.get("name", "")), [r["id"] for r in completo["rooms"]],
                             ajustes.ID_HABITACION_PREFIJO)
            sala = {**datos, "id": id_, "slots": []}
            completo["rooms"].append(sala)
        else:
            posicion = next((i for i, r in enumerate(completo["rooms"]) if r["id"] == room_id), None)
            if posicion is None:
                raise ConfigError(ajustes.ERROR_HABITACION_INEXISTENTE.format(habitacion=room_id))
            sala = {**completo["rooms"][posicion], **datos}  # conserva id y tramos
            completo["rooms"][posicion] = sala
        if not str(sala.get("name", "")).strip():
            sala["name"] = sala["id"]
        return Plan.from_dict(completo), sala["id"]

    @classmethod
    def borrar_habitacion(cls, plan: Plan, room_id: str) -> Plan:
        """Elimina una habitación con todos sus tramos."""
        completo = copy.deepcopy(plan.to_dict())
        restantes = [r for r in completo["rooms"] if r["id"] != room_id]
        if len(restantes) == len(completo["rooms"]):
            raise ConfigError(ajustes.ERROR_HABITACION_INEXISTENTE.format(habitacion=room_id))
        completo["rooms"] = restantes
        return Plan.from_dict(completo)

    @classmethod
    def validar_habitacion(cls, plan: Plan, datos: dict[str, Any],
                           room_id: str | None = None) -> dict[str, Any]:
        """Valida una habitación sin guardarla: {ok, error}."""
        try:
            cls.guardar_habitacion(plan, datos, room_id)
        except ConfigError as err:
            return {"ok": False, "error": str(err)}
        return {"ok": True, "error": None}

    @classmethod
    def _contenedor_pausas(cls, completo: dict[str, Any], room_id: str | None) -> dict[str, Any]:
        """Diccionario que contiene las pausas: la habitación o los ajustes globales."""
        return completo["global"] if room_id is None else cls._sala(completo, room_id)

    @classmethod
    def guardar_pausa(cls, plan: Plan, pausa: dict[str, Any], pause_id: str | None = None,
                      room_id: str | None = None) -> tuple[Plan, str]:
        """Crea (pause_id=None) o modifica una pausa de una habitación o global."""
        completo = copy.deepcopy(plan.to_dict())
        lista = cls._contenedor_pausas(completo, room_id).setdefault("pauses", [])
        pausa = dict(pausa)
        if pause_id is None:
            pausa["id"] = generar_id(str(pausa.get("reason", "")), [p["id"] for p in lista],
                                     ajustes.ID_PAUSA_PREFIJO)
            lista.append(pausa)
        else:
            posicion = next((i for i, p in enumerate(lista) if p["id"] == pause_id), None)
            if posicion is None:
                raise ConfigError(ajustes.ERROR_PAUSA_INEXISTENTE.format(pausa=pause_id))
            pausa["id"] = pause_id
            lista[posicion] = pausa
        return Plan.from_dict(completo), pausa["id"]

    @classmethod
    def borrar_pausa(cls, plan: Plan, pause_id: str, room_id: str | None = None) -> Plan:
        """Elimina una pausa."""
        completo = copy.deepcopy(plan.to_dict())
        contenedor = cls._contenedor_pausas(completo, room_id)
        restantes = [p for p in contenedor.get("pauses", []) if p["id"] != pause_id]
        if len(restantes) == len(contenedor.get("pauses", [])):
            raise ConfigError(ajustes.ERROR_PAUSA_INEXISTENTE.format(pausa=pause_id))
        contenedor["pauses"] = restantes
        return Plan.from_dict(completo)

    @classmethod
    def validar_pausa(cls, plan: Plan, pausa: dict[str, Any], pause_id: str | None = None,
                      room_id: str | None = None) -> dict[str, Any]:
        """Valida una pausa sin guardarla: {ok, error}."""
        try:
            cls.guardar_pausa(plan, pausa, pause_id, room_id)
        except ConfigError as err:
            return {"ok": False, "error": str(err)}
        return {"ok": True, "error": None}

    @classmethod
    def guardar_global(cls, plan: Plan, datos: dict[str, Any]) -> Plan:
        """Sustituye los ajustes globales. Valida todo el plan (p. ej. canales en uso).

        El modo ausencia se conserva: se gestiona con su propio interruptor.
        """
        completo = copy.deepcopy(plan.to_dict())
        completo["global"] = {**datos, "away_mode": plan.config.away_mode,
                              "pauses": plan.to_dict()["global"]["pauses"]}
        return Plan.from_dict(completo)

    @classmethod
    def validar_global(cls, plan: Plan, datos: dict[str, Any]) -> dict[str, Any]:
        """Valida los ajustes globales sin guardarlos: {ok, error}."""
        try:
            cls.guardar_global(plan, datos)
        except ConfigError as err:
            return {"ok": False, "error": str(err)}
        return {"ok": True, "error": None}

    @classmethod
    def borrar_tramo(cls, plan: Plan, room_id: str, slot_id: str) -> Plan:
        """Elimina un tramo."""
        datos = copy.deepcopy(plan.to_dict())
        sala = cls._sala(datos, room_id)
        restantes = [t for t in sala["slots"] if t["id"] != slot_id]
        if len(restantes) == len(sala["slots"]):
            raise ConfigError(ajustes.ERROR_TRAMO_INEXISTENTE.format(
                tramo=slot_id, habitacion=room_id))
        sala["slots"] = restantes
        return Plan.from_dict(datos)

    @classmethod
    def conflictos(cls, plan: Plan, room_id: str, tramo: dict[str, Any],
                   slot_id: str | None = None) -> list[str]:
        """Ids de los tramos de la habitación que se solapan con el propuesto."""
        sala = plan.room(room_id)
        if sala is None:
            return []
        propuesto = Slot.from_dict({**tramo, "id": slot_id or ajustes.ID_TRAMO_PREFIJO})
        return [t.id for t in sala.slots if t.id != slot_id and propuesto.solapa_con(t)]

    @classmethod
    def validar(cls, plan: Plan, room_id: str, tramo: dict[str, Any],
                slot_id: str | None = None) -> dict[str, Any]:
        """Valida sin guardar: {ok, error, conflicts}. Sirve para la vista previa del editor."""
        try:
            conflictos = cls.conflictos(plan, room_id, tramo, slot_id)
        except ConfigError as err:
            return {"ok": False, "error": str(err), "conflicts": []}
        try:
            cls.guardar_tramo(plan, room_id, tramo, slot_id)
        except ConfigError as err:
            return {"ok": False, "error": str(err), "conflicts": conflictos}
        return {"ok": True, "error": None, "conflicts": []}
