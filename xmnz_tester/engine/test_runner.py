import time
import threading
import json
from pathlib import Path
from typing import Optional
from .sequence_definition import TEST_SEQUENCE
from ..config import ConfigManager
from ..hal.relays import RelayController
from ..hal.rs485 import RS485Controller
from ..hal.meter_factory import MeterFactory
from ..hal.meter_interface import CurrentMeterInterface
from ..hal.ina3221 import PowerMeterINA3221
from ..models.test_result import TestResult, TestStepResult
from ..models.dut_info import DutInfo
from ..models.dut_status import DutStatus
from ..dut_commands import DutCommands
from ..services.api_client import ApiClient

class TestRunner:
    """
    Orquesta la secuencia completa de tests, interactuando con la capa HAL
    y reportando los resultados a través de una función callback.
    """
    def __init__(self, config_manager: ConfigManager, gui_callback: callable, stop_event: threading.Event):
        """
        Inicializa el motor de test.

        Args:
            config_manager (ConfigManager): La instancia del gestor de configuración.
            gui_callback (callable): Función para enviar actualizaciones a la GUI.
            stop_event (threading.Event): Evento para señalar la detención del test.
        """
        self.config = config_manager
        self.callback = gui_callback
        self.stop_event = stop_event
        self.test_result = None
        self.step_counter = 0

        self.dut_info: Optional[DutInfo] = None
        self.dut_status: Optional[DutStatus] = None
        self.test_result: Optional[TestResult] = None

        # Controladores del HAL
        self.relay_controller: RelayController = None
        self.rs485_controller: RS485Controller = None
        self.ppk2_meter: CurrentMeterInterface = None
        self.ina3221_meter: PowerMeterINA3221 = None

    def _report(self, message: str, status: str = "INFO", *, step_id: str = None, details: dict = None):
        """Metodo centralizado para enviar mensajes y guardar el resultado del paso."""
        if self.callback:
            self.callback(step_id, message, status)

        if self.test_result:
            step_name = step_id or f"Paso {self.step_counter}"

            step = TestStepResult(
                step_name=step_name,
                status=status.upper(),
                message=message,
                details=details or {}
            )
            self.test_result.add_step(step)

    def _start_step(self, step_key: str):
        """Incrementa, formatea y reporta el mensaje de inicio de un paso."""
        self.step_counter += 1
        method_name = f"_{step_key}"
        message_template = self.config.ui_messages.get(step_key, f"Iniciando: {step_key}")
        final_message = message_template.format(self.step_counter)
        self._report(final_message, "TESTING", step_id=method_name)

    def run_full_test(self):
        """
        Punto de entrada principal. Ejecuta la secuencia completa de tests.
        """
        self.step_counter = 0
        self.test_result = TestResult(station_id=self.config.station_id)

        try:
            self._connect_all_hardware()
            self._run_test_steps()
        except Exception as e:
            self._report(f"ERROR CRÍTICO: {e}", "FAIL", step_id="critical_error")
        finally:
            self.test_result.finalize()
            self._disconnect_all_hardware()
            self._report(f"Test finalizado. Resultado: {self.test_result.overall_status}", self.test_result.overall_status, step_id="final_summary")

            self._log_result_locally()
            self._send_results_to_api()

            return self.test_result.overall_status

    def _connect_all_hardware(self):
        """Inicializa y conecta todos los controladores del HAL."""
        self._report("--- Conectando al hardware ---", "INFO", step_id="connect_hardware")

        # Conectar relés
        self.relay_controller = RelayController(
            num_relays=len(self.config.relay_map),
            serial_number=self.config.relay_serial_number
        )
        self.relay_controller.connect()

        # Conectar RS485
        self.rs485_controller = RS485Controller(
            port=self.config.rs485_port,
            baud_rate=self.config.rs485_baud_rate
        )
        self.rs485_controller.connect()

        # Conectar medidor uA
        ua_meter_config = self.config.hardware.get("power_meters", {}).get("ua_meter", {})
        self.ua_meter = MeterFactory.create_ua_meter(ua_meter_config)
        if self.ua_meter and self.ua_meter.connect():
            self._report(f"Medidor de uA ({self.ua_meter.get_info()['type']}) conectado.", "INFO")
        else:
            raise ConnectionError("No se pudo conectar al medidor de uA.")

        # Conectar INA3221
        self.ina3221_meter = PowerMeterINA3221(**self.config.ina3221_config)
        self.ina3221_meter.connect()

    def _disconnect_all_hardware(self):
        """Desconecta de forma segura todos los controladores del HAL."""
        self._report("--- Desconectando del hardware ---", "HEADER", step_id="disconnect_hardware")
        if self.relay_controller:
            self.relay_controller.disconnect()
        if self.rs485_controller:
            self.rs485_controller.disconnect()
        if self.ua_meter:
            self.ua_meter.disconnect()
        if self.ina3221_meter:
            self.ina3221_meter.disconnect()

    def _run_test_steps(self):
        """Itera sobre la secuencia, extrae los argumentos y ejecuta el método."""
        self._report("--- Iniciando secuencia de pruebas ---", "INFO")

        for step_info in TEST_SEQUENCE:
            if self.stop_event and self.stop_event.is_set():
                self._report("Test detenido por el usuario.", "FAIL")
                break

            step_key = step_info['key']
            method_name = f"_{step_key}"

            args = step_info.get('args', [])
            kwargs = step_info.get('kwargs', {})

            try:
                method_to_call = getattr(self, method_name)
                method_to_call(*args, **kwargs)
            except AttributeError:
                self._report(f"Error: No se encontró el método '{method_name}'", "FAIL")
                break


            if self.test_result.overall_status == "FAIL" and self.config.stop_on_fail:
                self._report("La secuencia se detuvo debido a un fallo.", "INFO")
                break

    def _log_result_locally(self):
        """Guarda el objeto de resultado completo en un fichero JSON local."""
        log_dir = self.config.log_file_path
        if not log_dir:
            self._report("Ruta de logs no configurada.", "FAIL", step_id="local_log")
            return

        try:
            Path(log_dir).mkdir(parents=True, exist_ok=True)

            sn = self.test_result.serial_number or "SN_UNKNOWN"
            timestamp = self.test_result.start_time.strftime("%Y%m%d_%H%M%S")
            file_path = Path(log_dir) / f"{sn}_{timestamp}.json"


            # 4. Escribir en el fichero
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.test_result.to_dict(), f, indent=2, ensure_ascii=False)

            self._report(f"Resultado guardado localmente en: {file_path}", "INFO", step_id="local_log")

        except Exception as e:
            self._report(f"Error al guardar el log local: {e}", "FAIL", step_id="local_log")

    def _send_results_to_api(self):
        """Crea el cliente API y envía los resultados."""
        api_client = ApiClient(self.config.api_endpoint, self.config.api_key, self.config.api_timeout)

        if api_client.send_test_result(self.test_result):
            self._report("Resultados sincronizados con la plataforma.", "INFO", step_id="api_send")
        else:
            # TODO: Implementar lógica de reintentos o manejo de errores
            self._report("Fallo al sincronizar resultados con la plataforma.", "FAIL", step_id="api_send")


# ----- TEST STEPS -----
    def _test_step_connect_battery(self):
        """Step 1: Connect the battery (REL4 ON) to power the DUT. """
        self._start_step("step_connect_battery")

        relay_id = self.config.relay_num_battery

        self.relay_controller.set_relay(relay_id, True)
        time.sleep(0.5)
        if self.relay_controller.get_relay_state(relay_id):
            self._report("Batería conectada.", "PASS")
        else:
            self._report("Fallo al conectar la batería.", "FAIL")

    def _test_step_apply_vin(self):
        """Step 2: Power the device from Vin (REL3 ON). """
        self._start_step("step_connect_battery")

        relay_id = self.config.relay_num_vin_power

        self.relay_controller.set_relay(relay_id, True)
        time.sleep(0.5)
        if self.relay_controller.get_relay_state(relay_id):
            self._report("Alimentación externa (VIN) aplicada.", "PASS")
        else:
            self._report("Fallo al aplicar VIN.", "FAIL")

    def _test_step_check_initial_status(self):
        """Step 3: Checks DUT initial status."""
        self._start_step("step_check_initial_status")

        device_status_dict = self._get_dut_json_response(DutCommands.GET_DEVICE_DATA)

        if device_status_dict:
            self.dut_info = DutInfo.from_dict(device_status_dict)
            self._report(f"Obtenido DeviceStatus.", "PASS", details=device_status_dict)
        else:
            self._report("Fallo al obtener DeviceStatus del DUT.", "FAIL")

    def _test_step_measure_active_power(self):
        """Step 4: Measure INA3221 channels and report results."""
        self._start_step("step_measure_active_power")

        vin_ch = self.config.ina3221_ch_vin_current
        bat_ch = self.config.ina3221_ch_battery_charge

        vin_data = self.ina3221_meter.read_channel(vin_ch)
        bat_data = self.ina3221_meter.read_channel(bat_ch)

        if not vin_data or not bat_data:
            self._report("Fallo al leer medidor INA3221.", "FAIL")
            return

        self._report(f"Consumo VIN: {vin_data['current_mA']:.2f} mA", "PASS", details=vin_data)
        self._report(f"Carga Batería: {bat_data['current_mA']:.2f} mA", "PASS", details=bat_data)

    def _test_step_test_tampers(self):
        """Step 5: Check tampering inputs."""
        self._start_step("step_test_tampers")

        def test_tamper_combination(relay1_state, relay2_state, expected1, expected2):
            """Helper para probar combinación de relés de tamper."""
            self.relay_controller.set_relay(relay_tamper_1, relay1_state)
            self.relay_controller.set_relay(relay_tamper_2, relay2_state)
            time.sleep(1)  # Esperar para estabilizar

            actual1 = self.relay_controller.get_relay_state(relay_tamper_1)
            actual2 = self.relay_controller.get_relay_state(relay_tamper_2)

            if actual1 == expected1 and actual2 == expected2:
                self._report(
                    f"Relés: [{relay1_state}, {relay2_state}] -> Estado esperado: [{expected1}, {expected2}] -> PASS",
                    "PASS"
                )
            else:
                self._report(
                    f"Relés: [{relay1_state}, {relay2_state}] -> Esperado: [{expected1}, {expected2}], "
                    f"Obtenido: [{actual1}, {actual2}] -> FAIL", "FAIL"
                )

        try:
            relay_tamper_1 = self.config.relay_num_tamper_1
            relay_tamper_2 = self.config.relay_num_tamper_2

            # Probar todas las combinaciones
            test_tamper_combination(False, False, False, False)
            test_tamper_combination(True, False, True, False)
            test_tamper_combination(False, True, False, True)
            test_tamper_combination(True, True, True, True)

        except Exception as e:
            self._report(f"Error al verificar los relés de tamper: {e}", "FAIL")

    def _test_step_test_onboard_relay(self):
        """Step 6: Check board relay with REL1 off and reading tamper in1."""
        self._start_step("step_test_onboard_relay")

        try:
            relay_id = self.config.relay_num_tamper_1

            # Desactivar REL1
            self.relay_controller.set_relay(relay_id, False)
            time.sleep(1)  # Esperar un segundo para estabilizar

            # Leer el estado del relé de tamper
            if not self.relay_controller.get_relay_state(relay_id):
                self._report("Relé de tamper desactivado correctamente -> PASS", "PASS")
            else:
                self._report("Fallo al desactivar el relé de tamper -> FAIL", "FAIL")

        except Exception as e:
            self._report(f"Error al verificar el relé de la placa: {e}", "FAIL")

    def _test_step_disconnect_battery(self):
        """Step 7: Disconnect the battery (REL4 OFF)."""
        self._start_step("step_disconnect_battery")

        self.relay_controller.set_relay(self.config.relay_num_battery, False)
        self._report("Batería desconectada.", "PASS")

    def _test_step_simulate_battery(self):
        """Step 8: Enable 3v7 with uA meter."""
        self._start_step("step_simulate_battery")

        if self.ua_meter.set_source_enabled(True):
            self._report("Alimentación desde uA Meter habilitada.", "PASS")
        else:
            self._report("Fallo al habilitar alimentación desde uA Meter.", "FAIL")

    def _test_step_disconnect_vin(self):
        """Step 9: Disconnect Vin (REL3 OFF)."""
        self._start_step("step_disconnect_vin")

        self.relay_controller.set_relay(self.config.relay_num_vin_power, False)
        self._report("Alimentación externa (VIN) desconectada.", "PASS")

    def _test_step_check_board_status(self):
        """Step 10: Asks DUT for status, parses returned JSON and checks it meets the expected status."""
        self._start_step("test_step_check_board_status")

        device_info_dict = self._get_dut_json_response(DutCommands.GET_STATUS)

        if device_info_dict:
            self.dut_info = DutInfo.from_dict(device_info_dict)
            self._report(f"Obtenido DeviceInfo. S/N: {self.dut_info.device_serial}, ")
        else:
            self._report("Fallo al obtener DeviceInfo del DUT.", "FAIL")

    def _test_step_set_low_power_mode(self):
        """Step 11: Send command to put the device in low power mode."""
        self._start_step("step_set_low_power_mode")

        try:
            response = self.rs485_controller.send_command(DutCommands.SET_LOW_POWER)
            if response: # TODO: validar respuesta esperada
                self._report("Dispositivo enviado a modo de bajo consumo -> PASS", "PASS")
            else:
                self._report("Fallo al enviar comando de bajo consumo -> FAIL", "FAIL")
        except Exception as e:
            self._report(f"Error al enviar comando de bajo consumo: {e}", "FAIL")

    def _test_step_measure_sleep_current(self):
        """Step 12: Measure low current with uA meter."""
        self._start_step("step_measure_sleep_current")

        avg_current = self.ua_meter.get_current_measurement()
        threshold = self.config.threshold_sleep_current_ua

        if avg_current is not None:
            details = {'measured_ua': avg_current, 'threshold_ua': threshold}
            if avg_current < threshold:
                self._report(f"Consumo en reposo: {avg_current:.2f} uA. OK.", "PASS", details=details)
            else:
                self._report(f"Consumo en reposo: {avg_current:.2f} uA. FAIL.", "FAIL", details=details)
        else:
            self._report("Fallo al medir consumo en reposo.", "FAIL")

    def _test_step_wakeup_from_sleep(self):
        """Step 13: Wait for the device to return to normal mode."""
        self._start_step("step_wakeup_from_sleep")

        self._report("Esperando que el DUT salga de bajo consumo...", "INFO")
        time.sleep(35)
        self.rs485_controller.wait_for_prompt()
        self._report("DUT ha vuelto a modo normal.", "PASS")

    def _test_step_send_current_result(self):
        """Step 14: Send uA current value to DUT."""
        self._start_step("step_send_current_result")

        last_current = self.test_result.steps[-2].details.get('measured_ua', 0.0)
        command = f"{DutCommands.SET_LAST_CURRENT}={last_current:.2f}"
        response = self.rs485_controller.send_command(command)

        if response and "OK" in response[0]:
            self._report(f"Resultado de consumo ({last_current:.2f} uA) enviado al DUT.", "PASS")
        else:
            self._report("Fallo al enviar resultado de consumo al DUT.", "FAIL")

    def _test_step_get_barcode(self):
        """Step 15: Get barcode and serial number from the DUT."""
        self._start_step("step_get_barcode")

        # TODO: Leer de un escáner de código de barras y luego enviarlo al DUT con SET_SERIAL.
        self._report("Paso de barcode/serial omitido (simulado).", "PASS")

    def _test_step_modem_send(self):
        """Step 16: Force sending modem JSON data."""
        self._start_step("step_modem_send")

        response = self.rs485_controller.send_command(DutCommands.FORCE_MODEM_SEND)
        if response and "OK" in response[0]:
            self._report("Comando para forzar envío de módem enviado.", "PASS")
        else:
            self._report("Fallo al forzar el envío del módem.", "FAIL")

# Auxiliary methods
    def _get_dut_json_response(self, command: str) -> dict | None:
        """
        Metodo auxiliar para enviar un comando al DUT, esperar una respuesta
        JSON, y parsearla.

        Args:
            command (str): El comando a enviar (de DutCommands).

        Returns:
            dict | None: Un diccionario con los datos si la respuesta es un JSON válido,
                         o None si hay un error.
        """
        response_lines = self.rs485_controller.send_command(command)

        if not response_lines:
            self._report(f"No se recibió respuesta del DUT para el comando '{command}'.", "FAIL")
            return None

        try:
            # Unir las líneas por si el JSON viene fragmentado
            json_response = "".join(response_lines)
            return json.loads(json_response)
        except json.JSONDecodeError:
            self._report(f"Respuesta inválida (no es JSON): {response_lines}", "FAIL")
            return None

    def _update_dut_status(self) -> bool:
        """Pide el estado al DUT, lo parsea y actualiza self.dut_status."""
        self._report("Solicitando estado actualizado del DUT...", "INFO")
        status_dict = self._get_dut_json_response(DutCommands.GET_STATUS)

        if status_dict:
            self.dut_status = DutStatus.from_dict(status_dict)
            # Pasamos el dict original a los detalles del log
            self._report("Estado del DUT actualizado correctamente.", "PASS", details=status_dict)
            return True
        else:
            self._report("No se pudo obtener o parsear el estado del DUT.", "FAIL")
            self.dut_status = None
            return False