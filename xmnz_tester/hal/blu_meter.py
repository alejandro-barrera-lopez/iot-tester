"""
Módulo para el medidor de intensidad BLU939.
Implementa la interfaz CurrentMeterInterface.
"""

import logging
import time
from typing import Optional, List, Tuple
from .meter_interface import CurrentMeterInterface

try:
    from blu2_api.blu2_api import BLU2_API
except ImportError:
    BLU2_API = None
    logging.warning("BLU2_API no disponible. Instale blu-api-python para usar BLU939.")

logger = logging.getLogger(__name__)


class BLUMeter(CurrentMeterInterface):
    """
    Clase para manejar el medidor BLU939.
    Implementa la interfaz CurrentMeterInterface.
    """

    def __init__(self, serial_number: Optional[str] = None, source_voltage_mv: int = 3700):
        """
        Inicializa el medidor BLU939.

        Args:
            serial_number: Número de serie del dispositivo (opcional)
            source_voltage_mv: Voltaje de fuente en mV (por defecto 3.7V)
        """
        super().__init__(serial_number, source_voltage_mv)
        self.device = None
        self.port = None

        if BLU2_API is None:
            raise ImportError("BLU2_API no disponible. Instale blu-api-python.")

    def connect(self) -> bool:
        """
        Conecta al medidor BLU939.

        Returns:
            True si la conexión fue exitosa, False en caso contrario
        """
        try:
            # Buscar dispositivos BLU2 conectados
            blu2s_connected = BLU2_API.list_devices()

            if not blu2s_connected:
                self.logger.error("No se encontraron dispositivos BLU2")
                return False

            # Si se especifica un número de serie, buscar ese dispositivo específico
            if self.serial_number:
                target_port = None
                for port in blu2s_connected:
                    # Aquí deberías implementar lógica para verificar el S/N
                    # Por ahora, usamos el primer puerto si coincide con algún patrón
                    if self.serial_number in port:
                        target_port = port
                        break

                if not target_port:
                    self.logger.error(f"No se encontró dispositivo con S/N: {self.serial_number}")
                    return False

                self.port = target_port
            else:
                # Si hay múltiples dispositivos y no se especifica S/N, usar el primero
                if len(blu2s_connected) > 1:
                    self.logger.warning(
                        f"Múltiples dispositivos BLU2 encontrados: {blu2s_connected}. Usando el primero.")

                self.port = blu2s_connected[0]

            # Conectar al dispositivo
            self.device = BLU2_API(self.port, timeout=1, write_timeout=0, exclusive=True)

            # Obtener modificadores (inicialización necesaria)
            self.device.get_modifiers()

            # Configurar en modo source meter
            self.device.use_source_meter()

            self.is_connected = True
            self.logger.info(f"Conectado al medidor BLU939 en puerto: {self.port}")
            return True

        except Exception as e:
            self.logger.error(f"Error al conectar al medidor BLU939: {e}")
            return False

    def disconnect(self) -> None:
        """Desconecta del medidor BLU939."""
        try:
            if self.device and self.is_connected:
                # Deshabilitar fuente antes de desconectar
                self.set_source_enabled(False)

                # Detener mediciones si están activas
                try:
                    self.device.stop_measuring()
                except:
                    pass  # Puede que no esté midiendo

                # Cerrar conexión
                self.device = None
                self.is_connected = False
                self.logger.info("Desconectado del medidor BLU939")

        except Exception as e:
            self.logger.error(f"Error al desconectar del medidor BLU939: {e}")

    def set_source_enabled(self, enabled: bool) -> bool:
        """Activa o desactiva la alimentación del DUT."""
        if not self.is_connected:
            logging.error("BLU-Meter no conectado.")
            return False
        try:
            state = "ON" if enabled else "OFF"
            self.device.toggle_DUT_power(state)
            log_state = "activada" if enabled else "desactivada"
            logging.info(f"Fuente de alimentación del BLU-Meter {log_state}.")
            return True
        except Exception as e:
            logging.error(f"Error al cambiar el estado de la fuente del BLU-Meter: {e}")
            return False

    def set_voltage(self, millivolts: int) -> bool:
        """
        Configura la tensión de salida del BLU-Meter y activa la fuente.
        """
        if not self.is_connected:
            logging.error("BLU-Meter no conectado. No se puede configurar el voltaje.")
            return False

        try:
            # 1. Configurar el modo del medidor
            self.device.get_modifiers()
            self.device.use_source_meter()

            # 2. Establecer el nivel de voltaje deseado
            self.device.set_source_voltage(millivolts)

            # 3. Activar la salida de alimentación
            self.set_source_enabled(True)

            logging.info(f"BLU-Meter suministrando {millivolts} mV.")
            return True
        except Exception as e:
            logging.error(f"Error al configurar el voltaje del BLU-Meter: {e}")
            return False

    def get_current_measurement(self, samples: int = 100, sample_rate_hz: int = 1000) -> Optional[float]:
        """
        Obtiene una medición de corriente promedio.

        Args:
            samples: Número de muestras a tomar
            sample_rate_hz: Frecuencia de muestreo en Hz (no usado en BLU939, usa su rate interno)

        Returns:
            Corriente promedio en microamperios (μA) o None si hay error
        """
        if not self.is_connected or not self.device:
            self.logger.error("Dispositivo no conectado")
            return None

        try:
            # Iniciar medición
            self.device.start_measuring()

            all_samples = []
            attempts = 0
            max_attempts = 100  # Máximo número de intentos para obtener suficientes muestras

            while len(all_samples) < samples and attempts < max_attempts:
                # Leer datos del dispositivo
                read_data = self.device.get_data()

                if read_data != b'':
                    # Convertir datos a muestras
                    current_samples, raw_digital = self.device.get_samples(read_data)
                    all_samples.extend(current_samples)

                    self.logger.debug(f"Obtenidas {len(current_samples)} muestras. Total: {len(all_samples)}")

                attempts += 1
                time.sleep(0.01)  # Pequeña pausa entre lecturas

            # Detener medición
            self.device.stop_measuring()

            if all_samples:
                # Tomar solo las muestras solicitadas
                samples_to_use = all_samples[:samples]
                avg_current = sum(samples_to_use) / len(samples_to_use)

                self.logger.debug(f"Medición promedio: {avg_current:.2f} μA ({len(samples_to_use)} muestras)")
                return avg_current
            else:
                self.logger.error("No se pudieron obtener mediciones")
                return None

        except Exception as e:
            self.logger.error(f"Error al obtener medición: {e}")
            # Asegurar que se detenga la medición en caso de error
            try:
                self.device.stop_measuring()
            except:
                pass
            return None

    def get_continuous_measurements(self, duration_s: float, sample_rate_hz: int = 1000) -> List[Tuple[float, float]]:
        """
        Obtiene mediciones continuas durante un tiempo específico.

        Args:
            duration_s: Duración en segundos
            sample_rate_hz: Frecuencia de muestreo en Hz (no usado en BLU939)

        Returns:
            Lista de tuplas (tiempo, corriente_ua)
        """
        if not self.is_connected or not self.device:
            self.logger.error("Dispositivo no conectado")
            return []

        try:
            measurements = []
            start_time = time.time()

            # Iniciar medición
            self.device.start_measuring()

            while (time.time() - start_time) < duration_s:
                current_time = time.time() - start_time

                # Leer datos del dispositivo
                read_data = self.device.get_data()

                if read_data != b'':
                    # Convertir datos a muestras
                    current_samples, raw_digital = self.device.get_samples(read_data)

                    # Agregar cada muestra con su timestamp
                    for sample in current_samples:
                        measurements.append((current_time, sample))

                time.sleep(0.01)  # Pequeña pausa entre lecturas

            # Detener medición
            self.device.stop_measuring()

            self.logger.info(f"Obtenidas {len(measurements)} mediciones continuas en {duration_s}s")
            return measurements

        except Exception as e:
            self.logger.error(f"Error en mediciones continuas: {e}")
            # Asegurar que se detenga la medición en caso de error
            try:
                self.device.stop_measuring()
            except:
                pass
            return []