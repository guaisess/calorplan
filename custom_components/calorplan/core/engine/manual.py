# Versión: 2026.11.22
"""Vigilante de encendidos manuales: fija un límite de tiempo a lo que no encendió Calorplan."""
from __future__ import annotations

from datetime import datetime, timedelta

from .. import settings as ajustes
from ..models import Plan, Room


class ManualGuard:
    """Lleva, por habitación, la hora límite de un encendido manual (puro, sin Home Assistant)."""

    def __init__(self, plan: Plan) -> None:
        self.plan = plan
        self._inicio: dict[str, datetime] = {}  # cuándo se detectó el encendido manual
        self._propios: dict[str, datetime] = {}  # última orden de encendido de Calorplan

    # --- Entradas -----------------------------------------------------------------
    def marcar_propio(self, room_id: str, ahora: datetime) -> None:
        """Anota que Calorplan acaba de enviar una orden de encendido (no es manual)."""
        self._propios[room_id] = ahora
        self._inicio.pop(room_id, None)

    def _es_propio(self, room_id: str, ahora: datetime) -> bool:
        ultimo = self._propios.get(room_id)
        return ultimo is not None and ahora - ultimo <= timedelta(seconds=ajustes.MANUAL_VENTANA_PROPIA_SEGUNDOS)

    def _vigilada(self, sala: Room | None) -> bool:
        """Solo se vigilan habitaciones habilitadas con límite configurado."""
        return sala is not None and sala.enabled and sala.manual_max_minutes is not None

    def cambio_estado(self, room_id: str, encendido: bool, ahora: datetime) -> None:
        """Procesa un cambio de estado del dispositivo."""
        sala = self.plan.room(room_id)
        if not encendido or not self._vigilada(sala):
            self._inicio.pop(room_id, None)
        elif not self._es_propio(room_id, ahora):
            self._inicio.setdefault(room_id, ahora)  # primer encendido manual: no se renueva

    def adoptar(self, room_id: str, ahora: datetime) -> None:
        """Dispositivo encendido de origen desconocido (p. ej. tras un reinicio): empieza a contar ya."""
        if self._vigilada(self.plan.room(room_id)):
            self._inicio.setdefault(room_id, ahora)

    def olvidar(self, room_id: str) -> None:
        """Deja de vigilar una habitación."""
        self._inicio.pop(room_id, None)

    # --- Consultas ----------------------------------------------------------------
    def limite(self, room_id: str) -> datetime | None:
        """Hora límite del encendido manual (None si no hay)."""
        sala = self.plan.room(room_id)
        inicio = self._inicio.get(room_id)
        if inicio is None or not self._vigilada(sala):
            return None
        return inicio + timedelta(minutes=sala.manual_max_minutes)

    def proximo_limite(self) -> datetime | None:
        """El límite más cercano de todas las habitaciones."""
        limites = [l for r in list(self._inicio) if (l := self.limite(r)) is not None]
        return min(limites) if limites else None

    def vencidos(self, ahora: datetime) -> list[str]:
        """Habitaciones cuyo límite ya se alcanzó."""
        return sorted(r for r in list(self._inicio) if (l := self.limite(r)) is not None and l <= ahora)

    def minutos_encendida(self, room_id: str, ahora: datetime) -> int:
        """Minutos transcurridos desde el encendido manual."""
        inicio = self._inicio.get(room_id)
        return 0 if inicio is None else int((ahora - inicio).total_seconds() // 60)

    # --- Persistencia ---------------------------------------------------------------
    def estado(self) -> dict[str, str]:
        """Copia serializable (room_id → ISO del inicio)."""
        return {r: i.isoformat() for r, i in self._inicio.items()}

    def cargar(self, datos: dict | None) -> None:
        """Restaura el estado guardado (ignora lo que no sea válido)."""
        self._inicio = {}
        for room_id, iso in (datos or {}).items():
            try:
                self._inicio[str(room_id)] = datetime.fromisoformat(iso)
            except (TypeError, ValueError):
                continue
