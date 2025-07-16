"""
Interfaz base para medidores de corriente.
Define el contrato que deben implementar todos los medidores.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Tuple
import logging

logger = logging.getLogger(__name__)


class CurrentMeterInterface(ABC):
    """
    Interfaz abstracta para medidores de corriente.
    Define los métodos que deben implementar todos los medidores.
    """

    def __init__(self, serial_number: Optional[str] = None, source_voltage_mv: int = 3700):
        """
        Inicializa el medidor.

        Args:
            serial_number: Número de serie del dispositivo (opcional)
            source_voltage_mv: Voltaje de fuente en mV
        """
        self.serial_number = serial_number
        self.source_voltage_mv = source_voltage_mv
        self.source_voltage_v = source_voltage_mv / 1000.0
        self.is_connected = False
        self.is_source_enabled = False
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    def connect(self) -> bool:
        """
        Conecta al medidor.

        Returns:
            True si la conexión fue exitosa, False en caso contrario
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Desconecta del medidor."""
        pass

    @abstractmethod
    def set_source_enabled(self, enabled: bool) -> bool:
        """
        Habilita o deshabilita la fuente de alimentación.

        Args:
            enabled: True para habilitar, False para deshabilitar

        Returns:
            True si fue exitoso, False en caso contrario
        """
        pass

    @abstractmethod
    def get_current_measurement(self, samples: int = 100, sample_rate_hz: int = 1000) -> Optional[float]:
        """
        Obtiene una medición de corriente promedio.

        Args:
            samples: Número de muestras a tomar
            sample_rate_hz: Frecuencia de muestreo en Hz

        Returns:
            Corriente promedio en microamperios (μA) o None si hay error
        """
        pass

    @abstractmethod
    def get_continuous_measurements(self, duration_s: float, sample_rate_hz: int = 1000) -> List[Tuple[float, float]]:
        """
        Obtiene mediciones continuas durante un tiempo específico.

        Args:
            duration_s: Duración en segundos
            sample_rate_hz: Frecuencia de muestreo en Hz

        Returns:
            Lista de tuplas (tiempo, corriente_ua)
        """
        pass

    # Métodos comunes que pueden ser heredados
    def __enter__(self):
        """Entrada del context manager."""
        if self.connect():
            return self
        else:
            raise ConnectionError(f"No se pudo conectar al medidor {self.__class__.__name__}")

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Salida del context manager."""
        self.disconnect()

    def get_info(self) -> dict:
        """
        Retorna información del medidor.

        Returns:
            Diccionario con información del medidor
        """
        return {
            'type': self.__class__.__name__,
            'serial_number': self.serial_number,
            'source_voltage_mv': self.source_voltage_mv,
            'is_connected': self.is_connected,
            'is_source_enabled': self.is_source_enabled
        }