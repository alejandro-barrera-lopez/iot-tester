"""
Módulo para el medidor de intensidad Nordic Power Profiler Kit II (PPK2).
Implementa la interfaz CurrentMeterInterface.
"""

import logging
import time
from typing import Optional, List, Tuple

from serial.tools import list_ports
from .meter_interface import CurrentMeterInterface

try:
    from ppk2_api.ppk2_api import PPK2_API
except ImportError:
    PPK2_API = None
    logging.warning("ppk2_api no disponible. Instale ppk2-api-python para usar PPK2.")

logger = logging.getLogger(__name__)


class PPK2Meter(CurrentMeterInterface):
    """
    Clase para manejar el PPK2 de Nordic.
    Implementa la interfaz CurrentMeterInterface.
    """

    def __init__(self, serial_number: Optional[str] = None, source_voltage_mv: int = 3700):
        """
        Inicializa el medidor PPK2.

        Args:
            serial_number: Número de serie del dispositivo (opcional).
            source_voltage_mv: Voltaje de fuente en mV (por defecto 3.7V).
        """
        super().__init__(serial_number, source_voltage_mv)
        self.device: Optional[PPK2_API] = None
        self.port: Optional[str] = None

        if PPK2_API is None:
            raise ImportError("ppk2_api no disponible. Instale ppk2-api-python.")

    def connect(self) -> bool:
        """
        Encuentra y conecta al medidor PPK2.

        Returns:
            True si la conexión fue exitosa, False en caso contrario.
        """
        self.logger.info(f"Buscando PPK2 (S/N: {self.serial_number or 'cualquiera'})...")
        try:
            all_ports = list_ports.comports()
            found_port_info = None

            for port in all_ports:
                # El VID de Nordic Semiconductor es 0x1915, pero la API usa 6421 (0x1915 en decimal?)
                # La descripción suele ser más fiable.
                is_ppk2 = "PPK2" in port.description or (port.vid == 0x1915 or port.vid == 6421)

                if is_ppk2:
                    if self.serial_number and port.serial_number == self.serial_number:
                        found_port_info = port
                        break
                    elif not self.serial_number:
                        found_port_info = port
                        break

            if not found_port_info:
                self.logger.error(
                    f"No se encontró un PPK2 con los criterios especificados (S/N: {self.serial_number}).")
                return False

            self.port = found_port_info.device
            actual_serial = found_port_info.serial_number or "N/A"

            self.device = PPK2_API(self.port)
            self.device.get_modifiers()  # Inicialización necesaria

            self.is_connected = True
            self.logger.info(f"Conectado al PPK2 en {self.port} (S/N: {actual_serial}).")
            return True

        except Exception as e:
            self.logger.error(f"Error al conectar al medidor PPK2: {e}")
            return False

    def disconnect(self) -> None:
        """Desconecta del medidor PPK2."""
        try:
            if self.device and self.is_connected:
                self.set_source_enabled(False)
                try:
                    self.device.stop_measuring()
                except:
                    pass

                self.device = None
                self.is_connected = False
                self.logger.info("Desconectado del medidor PPK2.")
        except Exception as e:
            self.logger.error(f"Error al desconectar del medidor PPK2: {e}")

    def set_source_enabled(self, enabled: bool) -> bool:
        """Habilita o deshabilita la fuente de alimentación."""
        if not self.is_connected or not self.device:
            self.logger.error("Dispositivo no conectado.")
            return False

        try:
            if enabled:
                self.device.set_source_voltage(self.source_voltage_mv)
                self.device.use_source_meter()
                self.device.toggle_DUT_power("ON")
                self.is_source_enabled = True
                self.logger.info(f"Fuente habilitada a {self.source_voltage_mv}mV.")
            else:
                if self.is_source_enabled:  # Evitar enviar comando si ya está apagado
                    self.device.toggle_DUT_power("OFF")
                    self.is_source_enabled = False
                    self.logger.info("Fuente deshabilitada.")
            return True
        except Exception as e:
            self.logger.error(f"Error al configurar la fuente del PPK2: {e}")
            return False

    def get_current_measurement(self, samples: int = 100, sample_rate_hz: int = 1000) -> Optional[float]:
        """Obtiene una medición de corriente promedio."""
        if not self.is_connected or not self.device:
            self.logger.error("Dispositivo no conectado.")
            return None

        try:
            self.device.start_measuring()

            all_samples = []
            max_attempts = 100
            attempts = 0
            while len(all_samples) < samples and attempts < max_attempts:
                read_data = self.device.get_data()
                if read_data:
                    current_samples, _ = self.device.get_samples(read_data)
                    all_samples.extend(current_samples)
                attempts += 1
                time.sleep(0.01)

            self.device.stop_measuring()

            if not all_samples:
                self.logger.error("No se pudieron obtener mediciones del PPK2.")
                return None

            samples_to_use = all_samples[:samples]
            avg_current = sum(samples_to_use) / len(samples_to_use)
            self.logger.debug(f"Medición promedio: {avg_current:.2f} μA ({len(samples_to_use)} muestras).")
            return avg_current

        except Exception as e:
            self.logger.error(f"Error al obtener medición del PPK2: {e}")
            try:
                self.device.stop_measuring()
            except:
                pass
            return None

    def get_continuous_measurements(self, duration_s: float, sample_rate_hz: int = 1000) -> List[Tuple[float, float]]:
        """Obtiene mediciones continuas durante un tiempo específico."""
        if not self.is_connected or not self.device:
            self.logger.error("Dispositivo no conectado.")
            return []

        try:
            measurements = []
            self.device.start_measuring()
            start_time = time.time()

            while (time.time() - start_time) < duration_s:
                read_data = self.device.get_data()
                if read_data:
                    current_samples, _ = self.device.get_samples(read_data)
                    # Asociar todas las muestras de este paquete al mismo timestamp
                    timestamp = time.time() - start_time
                    for sample in current_samples:
                        measurements.append((timestamp, sample))
                time.sleep(0.01)

            self.device.stop_measuring()
            self.logger.info(f"Obtenidas {len(measurements)} mediciones continuas del PPK2 en {duration_s}s.")
            return measurements
        except Exception as e:
            self.logger.error(f"Error en mediciones continuas del PPK2: {e}")
            try:
                self.device.stop_measuring()
            except:
                pass
            return []