"""
Factory para crear instancias de medidores según la configuración.
"""

import logging
from typing import Optional
from .meter_interface import CurrentMeterInterface
from .ppk2_meter import PPK2Meter
from .blu_meter import BLUMeter

logger = logging.getLogger(__name__)


class MeterFactory:
    """Factory para crear medidores de corriente."""

    @staticmethod
    def create_ua_meter(config: dict) -> Optional[CurrentMeterInterface]:
        """
        Crea una instancia del medidor de microamperios según la configuración.

        Args:
            config: Configuración del medidor desde config.yaml

        Returns:
            Instancia del medidor correspondiente o None si hay error
        """
        try:
            meter_type = config.get('type', 'ppk2')

            if meter_type == 'ppk2':
                ppk2_config = config.get('ppk2', {})
                return PPK2Meter(
                    serial_number=ppk2_config.get('serial_number'),
                    source_voltage_mv=ppk2_config.get('source_voltage_mv', 3700)
                )

            elif meter_type == 'blu_meter':
                blu_config = config.get('blu_meter', {})
                return BLUMeter(
                    serial_number=blu_config.get('serial_number'),
                    source_voltage_mv=blu_config.get('source_voltage_mv', 3700)
                )

            else:
                logger.error(f"Tipo de medidor no soportado: {meter_type}")
                return None

        except Exception as e:
            logger.error(f"Error al crear medidor: {e}")
            return None

    @staticmethod
    def get_supported_types() -> list:
        """
        Retorna los tipos de medidores soportados.

        Returns:
            Lista de tipos soportados
        """
        return ['ppk2', 'blu_meter']