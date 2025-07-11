import time
import threading
import statistics
import json
from pathlib import Path
from .sequence_definition import TEST_SEQUENCE
from ..config import ConfigManager
from ..hal.relays import RelayController
from ..hal.rs485 import RS485Controller
from ..hal.ppk2 import PowerMeterPPK2
from ..hal.ina3221 import PowerMeterINA3221
from ..models.test_result import TestResult, TestStepResult
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

        # Controladores del HAL
        self.relay_controller = None
        self.rs485_controller = None
        self.ppk2_meter = None
        self.ina3221_meter = None

    def _report(self, message: str, status: str = "INFO", *, step_id: str = None, details: dict = None):
        """Metodo centralizado para enviar mensajes y guardar el resultado del paso."""
        # Si un paso falla, el estado general del test falla.
        if self.callback:
            self.callback(step_id, message, status)

        if self.test_result:
            step = TestStepResult(
                step_name=f"Paso {self.step_counter}",
                status=status,
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
        self._report("--- Conectando al hardware ---", "HEADER", step_id="connect_hardware")

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

        # Conectar PPK2
        self.ppk2_meter = PowerMeterPPK2(serial_number=self.config.ppk2_serial_number)
        self.ppk2_meter.connect()

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
        if self.ppk2_meter:
            self.ppk2_meter.disconnect()
        if self.ina3221_meter:
            self.ina3221_meter.disconnect()

    def _run_test_steps(self):
        """Itera sobre la secuencia, extrae los argumentos y ejecuta el método."""
        self._report("--- Iniciando secuencia de pruebas ---", "HEADER")

        for step_info in TEST_SEQUENCE:
            if self.stop_event and self.stop_event.is_set():
                self._report("Test detenido por el usuario.", "FAIL")
                break

            step_key = step_info['key']
            method_name = f"_{step_key}"

            # Extraemos los argumentos del diccionario (con valores por defecto vacíos)
            args = step_info.get('args', [])
            kwargs = step_info.get('kwargs', {})

            try:
                method_to_call = getattr(self, method_name)
            except AttributeError:
                self._report(f"Error: No se encontró el método '{method_name}'", "FAIL")
                break

            # Llamamos al método pasando los argumentos desempaquetados
            method_to_call(*args, **kwargs)

            if self.test_result.overall_status == "FAIL" and self.config.stop_on_fail:
                self._report("La secuencia se detuvo debido a un fallo.", "INFO")
                break

    def _log_result_locally(self):
        """
        Guarda el objeto de resultado completo en un fichero JSON local.
        """
        log_dir = self.config.log_file_path
        if not log_dir:
            self._report("Ruta de logs no configurada. No se guardará el resultado local.", "FAIL", step_id="local_log")
            return

        try:
            # 1. Asegurarse de que el directorio de logs existe
            Path(log_dir).mkdir(parents=True, exist_ok=True)

            # 2. Crear un nombre de fichero único usando el S/N y la fecha/hora
            sn = self.test_result.serial_number or "SN_UNKNOWN"
            timestamp = self.test_result.start_time.strftime("%Y%m%d_%H%M%S")
            file_name = f"{sn}_{timestamp}.json"
            file_path = Path(log_dir) / file_name

            # 3. Convertir el resultado a un string JSON (con formato para legibilidad)
            json_data = json.dumps(self.test_result.to_dict(), indent=2, ensure_ascii=False)

            # 4. Escribir en el fichero
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(json_data)

            self._report(f"Resultado guardado localmente en: {file_path}", "INFO", step_id="local_log")

        except Exception as e:
            self._report(f"Error al guardar el log local: {e}", "FAIL", step_id="local_log")

    def _send_results_to_api(self):
        """Crea el cliente API y envía los resultados."""
        api_client = ApiClient(self.config.api_config)
        success = api_client.send_test_result(self.test_result)

        if success:
            self._report("Resultados sincronizados con la plataforma.", "INFO", step_id="api_send")
        else:
            # TODO: Implementar lógica de reintentos o manejo de errores
            self._report("Fallo al sincronizar resultados con la plataforma.", "FAIL", step_id="api_send")

    def _test_step_connect_battery(self):
        """Step 1: Connect the battery (REL4 ON) to power the DUT. """
        self._start_step("step_connect_battery")
        relay_id = self.config.relay_num_battery

        try:
            self.relay_controller.set_relay(relay_id, True)
            time.sleep(1)
            if self.relay_controller.get_relay_state(relay_id):
                self._report("Batería conectada correctamente -> PASS", "PASS")
            else:
                self._report("Fallo al conectar la batería -> FAIL", "FAIL")
        except Exception as e:
            self._report(f"Error al conectar la batería: {e}", "FAIL")

    def _test_step_apply_vin(self):
        """Step 2: Power the device from Vin (REL3 ON). """
        self._start_step("step_connect_battery")
        relay_id = self.config.relay_num_vin_power

        try:
            self.relay_controller.set_relay(relay_id, True)
            time.sleep(1)  # Esperar un segundo para estabilizar
            if self.relay_controller.get_relay_state(relay_id):
                self._report("Vin activado correctamente -> PASS", "PASS")
            else:
                self._report("Fallo al activar Vin -> FAIL", "FAIL")
        except Exception as e:
            self._report(f"Error al activar Vin: {e}", "FAIL")

    def _test_step_check_initial_status(self):
        """Step 3: Checks DUT initial status."""
        self._start_step("step_check_initial_status")

        response = self.rs485_controller.check_initial_status()

        if response and len(response) > 5:
            serial = response.get("serial", "Desconocido")
            imei = response.get("imei", "Desconocido")
            iccid = response.get("iccid", "Desconocido")
            status = response.get("status", "Desconocido")

            self._report(f"Comunicación OK. S/N: {serial}, IMEI: {imei}, ICCID: {iccid}, Estado: {status}", "PASS", step_id="check_initial_status")
        else:
            self._report("Fallo al leer información del dispositivo o respuesta inválida.", "FAIL", step_id="check_initial_status")

    def _test_step_measure_active_power(self):
        """Step 4: Measure INA3221 channels and report results."""
        self._start_step("step_measure_active_power")

        try:
            meter_cfg = self.config.ina3221_config

            with PowerMeterINA3221(**meter_cfg) as power_meter:
                # Medir cada canal y reportar
                for channel in range(1, 4):
                    data = power_meter.read_channel(channel)
                    if data:
                        voltage = data['bus_voltage_V']
                        current = data['current_mA']
                        details = {
                            'channel': channel,
                            'voltage': voltage,
                            'current': current
                        }
                        self._report(f"Canal {channel}: {voltage:.3f} V, {current:.3f} mA", "PASS", step_id="measure_active_power", details=details)
                    else:
                        self._report(f"Fallo al leer el canal {channel} -> FAIL", "FAIL", step_id="measure_active_power")

        except Exception as e:
            self._report(f"Error al medir INA3221: {e}", "FAIL")

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
        relay_id = self.config.relay_num_battery

        try:
            self.relay_controller.set_relay(relay_id, False)
            time.sleep(1)  # Esperar un segundo para estabilizar
            if not self.relay_controller.get_relay_state(relay_id):
                self._report("Batería desconectada correctamente -> PASS", "PASS")
            else:
                self._report("Fallo al desconectar la batería -> FAIL", "FAIL")
        except Exception as e:
            self._report(f"Error al desconectar la batería: {e}", "FAIL")

    def _test_step_simulate_battery(self):
        """Step 8: Enable 3v7 with uA meter."""
        self._start_step("step_simulate_battery")

        try:
            # Cargar toda la configuración necesaria al principio
            serial_number = self.config.ppk2_serial_number
            voltage_mv = self.config.ppk2_source_voltage_mv

            with PowerMeterPPK2(serial_number=serial_number) as ppk2_meter:
                # Configurar el PPK2 y encender el dispositivo
                ppk2_meter.configure_source_meter(voltage_mv)
                ppk2_meter.set_dut_power(True)
                self._report(f"PPK2 configurado a {voltage_mv}mV y alimentación ON.", "INFO")

                self._report("3v7 activado correctamente -> PASS", "PASS")

        except Exception as e:
            self._report(f"Error al activar 3v7: {e}", "FAIL")

    def _test_step_disconnect_vin(self):
        """Step 9: Disconnect Vin (REL3 OFF)."""
        self._start_step("step_disconnect_vin")
        relay_id = self.config.relay_num_vin_power

        try:
            self.relay_controller.set_relay(relay_id, False)
            time.sleep(1)  # Esperar un segundo para estabilizar
            if not self.relay_controller.get_relay_state(relay_id):
                self._report("Vin desactivado correctamente -> PASS", "PASS")
            else:
                self._report("Fallo al desactivar Vin -> FAIL", "FAIL")
        except Exception as e:
            self._report(f"Error al desactivar Vin: {e}", "FAIL")

    def _test_step_check_board_status(self, expected_status: str):
        """Step 10: Asks DUT for status, parses returned JSON and checks it meets the expected status."""
        self._start_step("step_check_initial_status")

        try:
            response_str = self.rs485_controller.send_command(DutCommands.GET_STATUS)

            if not response_str:
                self._report("No se recibió respuesta del GETSTATUS.", "FAIL")
                return

            # Parseamos la respuesta JSON a un diccionario de Python
            status_data = json.loads(response_str)

            current_status = status_data.get("device_state")

            if current_status == expected_status:
                self._report(f"Estado '{current_status}' es el esperado -> PASS", "PASS", details=status_data)
            else:
                self._report(f"Estado incorrecto. Esperado: '{expected_status}', Recibido: '{current_status}' -> FAIL", "FAIL", details=status_data)

        except json.JSONDecodeError:
            self._report(f"Error: La respuesta no es un JSON válido: '{response_str}'", "FAIL")
        except Exception as e:
            self._report(f"Error al comprobar el estado del dispositivo: {e}", "FAIL")

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

        try:
            # Cargar toda la configuración necesaria al principio
            serial_number = self.config.ppk2_serial_number
            voltage_mv = self.config.ppk2_source_voltage_mv
            threshold_ua = self.config.threshold_sleep_current_ua

            with PowerMeterPPK2(serial_number=serial_number) as ppk2_meter:
                # Configurar el PPK2 y encender el dispositivo
                ppk2_meter.configure_source_meter(voltage_mv)
                ppk2_meter.set_dut_power(True)
                self._report(f"PPK2 configurado a {voltage_mv}mV y alimentación ON.", "INFO")

                # Medir la corriente en modo de bajo consumo
                avg_current = ppk2_meter.measure_average_current(duration_s=3)

                if avg_current is not None:
                    if avg_current < threshold_ua:
                        self._report(f"Corriente medida en bajo consumo: {avg_current} uA -> PASS", "PASS")
                    else:
                        self._report(f"Corriente medida en bajo consumo: {avg_current} uA (supera el umbral de {threshold_ua} uA) -> FAIL", "FAIL")
                else:
                    self._report("Fallo al medir corriente en bajo consumo -> FAIL", "FAIL")

        except Exception as e:
            self._report(f"Error al medir corriente en bajo consumo: {e}", "FAIL")

    def _test_step_wakeup_from_sleep(self):
        """Step 13: Wait for the device to return to normal mode."""
        self._start_step("step_wakeup_from_sleep")

        try:
            # Esperar un tiempo razonable para que el dispositivo vuelva a modo normal
            time.sleep(5)  # TODO: Ajustar según sea necesario

            # Comprobar el estado del dispositivo
            response = self.rs485_controller.send_command(DutCommands.GET_STATUS)
            if response == "STATUS=1":  # Asumiendo que 1 es el estado normal
                self._report("Dispositivo en modo normal -> PASS", "PASS")
            else:
                self._report(f"Estado inesperado: {response} -> FAIL", "FAIL")

        except Exception as e:
            self._report(f"Error al esperar modo normal: {e}", "FAIL")

    def _test_step_send_current_result(self):
        """Step 14: Send uA current value to DUT."""
        self._start_step("step_send_current_result")

        try:
            # Cargar toda la configuración necesaria al principio
            serial_number = self.config.ppk2_serial_number
            voltage_mv = self.config.ppk2_source_voltage_mv

            with PowerMeterPPK2(serial_number=serial_number) as ppk2_meter:
                # Configurar el PPK2 y encender el dispositivo
                ppk2_meter.configure_source_meter(voltage_mv)
                ppk2_meter.set_dut_power(True)
                self._report(f"PPK2 configurado a {voltage_mv}mV y alimentación ON.", "INFO")

                # Medir la corriente promedio
                avg_current = ppk2_meter.measure_average_current(duration_s=3)

                if avg_current is not None:
                    # Enviar el valor de corriente al DUT
                    command_to_send = f"{DutCommands.SET_LAST_CURRENT}={avg_current:.2f}"
                    response = self.rs485_controller.send_command(command_to_send)
                    if response == "OK":
                        self._report(f"Corriente enviada al DUT: {avg_current} uA -> PASS", "PASS")
                    else:
                        self._report("Fallo al enviar corriente al DUT -> FAIL", "FAIL")
                else:
                    self._report("Fallo al medir corriente para enviar -> FAIL", "FAIL")

        except Exception as e:
            self._report(f"Error al enviar corriente uA: {e}", "FAIL")

    def _test_step_get_barcode(self):
        """Step 15: Get barcode and serial number from the DUT."""
        self._start_step("step_get_barcode")

        # TODO: Leer del lector de código de barras y guardar en el DUT

        try:
            # Leer el número de serie del dispositivo
            response = self.rs485_controller.send_command(DutCommands.GET_SERIAL)
            if response and len(response) > 5:
                self._report(f"Número de serie leído: {response}", "PASS")
            else:
                self._report("Fallo al leer el número de serie o respuesta inválida.", "FAIL")

            barcode_response = self.rs485_controller.send_command(DutCommands.SET_SERIAL) # TODO: Enviar número de serie
            if barcode_response:
                self._report(f"Código de barras leído: {barcode_response}", "PASS")
            else:
                self._report("Fallo al leer el código de barras o respuesta inválida.", "FAIL")

        except Exception as e:
            self._report(f"Error al obtener S/N y código de barras: {e}", "FAIL")

    def _test_step_modem_send(self):
        """Step 16: Force sending modem JSON data."""
        self._start_step("step_modem_send")

        try:
            response = self.rs485_controller.send_command(DutCommands.FORCE_MODEM_SEND)
            if response == "OK":
                self._report("Modem JSON enviado correctamente -> PASS", "PASS")
            else:
                self._report("Fallo al enviar Modem JSON -> FAIL", "FAIL")
        except Exception as e:
            self._report(f"Error al forzar envío de Modem JSON: {e}", "FAIL")

    # FUNCIONES DE PRUEBA
    def _test_step_check_relays(self):
        """Ejemplo de paso: Verifica que los relés se pueden activar y desactivar."""
        self._report("Paso 1: Verificando relés...", "INFO")
        try:
            # Activar el primer relé
            self.relay_controller.set_relay(1, True)
            time.sleep(1)  # Esperar un segundo para estabilizar

            # Comprobar estado del relé
            if self.relay_controller.get_relay_state(1):
                self._report("Relé 1 activado correctamente -> PASS", "PASS")
            else:
                self._report("Fallo al activar el Relé 1 -> FAIL", "FAIL")

            # Activar el segundo relé
            self.relay_controller.set_relay(2, True)
            time.sleep(1)

            if self.relay_controller.get_relay_state(2):
                self._report("Relé 2 activado correctamente -> PASS", "PASS")
            else:
                self._report("Fallo al activar el Relé 2 -> FAIL", "FAIL")

            # Desactivar los relés
            self.relay_controller.all_off()
            time.sleep(1)  # Esperar un segundo para estabilizar

            if not self.relay_controller.get_relay_state(1):
                self._report("Relé 1 desactivado correctamente -> PASS", "PASS")
            else:
                self._report("Fallo al desactivar el Relé 1 -> FAIL", "FAIL")

        except Exception as e:
            self._report(f"Error al verificar relés: {e}", "FAIL")

    def _test_step_check_ina3221_averaged(self):
        """Verifica el INA3221 tomando una media de mediciones durante un tiempo determinado."""
        self._report("Paso 3: Verificando INA3221 (promedio de 2 segundos)...", "INFO")

        duration_s = 2.0  # Duración del muestreo

        try:
            meter_cfg = self.config.ina3221_config

            with PowerMeterINA3221(**meter_cfg) as power_meter:
                # 1. Estructura para almacenar todas las lecturas de cada canal
                # Ejemplo: {1: {'voltages': [v1, v2, ...], 'currents': [c1, c2, ...]}, 2: {...}}
                readings = {ch: {'voltages': [], 'currents': []} for ch in range(1, 4)}

                start_time = time.monotonic()
                sample_count = 0

                # 2. Bucle de muestreo durante el tiempo especificado
                while time.monotonic() - start_time < duration_s:
                    for channel in range(1, 4):
                        data = power_meter.read_channel(channel)
                        if data:
                            readings[channel]['voltages'].append(data['bus_voltage_V'])
                            readings[channel]['currents'].append(data['current_mA'])
                        else:
                            self._report(f"Fallo al leer el canal {channel} durante el muestreo -> FAIL", "FAIL")
                            return

                    sample_count += 1
                    time.sleep(0.1) # Pequeña pausa para no saturar el bus I2C

                # 3. Calcular y reportar los promedios
                if sample_count == 0:
                    self._report("No se tomaron muestras del INA3221 en 2 segundos -> FAIL", "FAIL")
                    return

                report_lines = []
                all_channels_ok = True

                for channel in range(1, 4):
                    voltage_samples = readings[channel]['voltages']
                    current_samples = readings[channel]['currents']

                    if not voltage_samples or not current_samples:
                        report_lines.append(f"  - Canal {channel}: No se obtuvieron datos.")
                        all_channels_ok = False
                        continue

                    avg_voltage = statistics.mean(voltage_samples)
                    avg_current = statistics.mean(current_samples)

                    report_lines.append(f"  - Canal {channel}: {avg_voltage:.3f} V, {avg_current:.3f} mA (promedio de {len(voltage_samples)} muestras)")

                # 4. Reporte final
                if all_channels_ok:
                    full_report = "Lecturas promedio del INA3221 correctas:\n" + "\n".join(report_lines)
                    self._report(f"{full_report}\n -> PASS", "PASS")
                else:
                    full_report = "Fallo al procesar lecturas del INA3221:\n" + "\n".join(report_lines)
                    self._report(f"{full_report}\n -> FAIL", "FAIL")

        except Exception as e:
            self._report(f"Error al verificar INA3221: {e}", "FAIL")

    def _test_step_measure_current(self):
        """Ejemplo: Mide el consumo en reposo y lo compara con un umbral."""
        self._report("Paso 2: Midiendo consumo en reposo...", "INFO")

        try:
            # 1. Cargar toda la configuración necesaria al principio
            serial_number = self.config.ppk2_serial_number
            voltage_mv = self.config.ppk2_source_voltage_mv
            threshold_ua = self.config.test_thresholds.get("low_power_current_threshold_ua", 1000)

            with PowerMeterPPK2(serial_number=serial_number) as ppk2_meter:
                # 2a. Configurar el PPK2 y encender el dispositivo
                ppk2_meter.configure_source_meter(voltage_mv)
                ppk2_meter.set_dut_power(True)
                self._report(f"PPK2 configurado a {voltage_mv}mV y alimentación ON.", "INFO")

                # 3. Pedir al dispositivo que entre en modo de bajo consumo
                self.rs485_controller.send_command(DutCommands.SET_LOW_POWER)
                time.sleep(2)  # Aumentado a 2s para asegurar la estabilización

                # 4. Medir la corriente
                # El metodo ya devuelve la media en uA, como se ve en el PoC.
                avg_current = ppk2_meter.measure_average_current(duration_s=3)

                # 5. Verificar que la medición fue exitosa antes de comparar
                if avg_current is not None:
                    # 6. Comparar y reportar el resultado
                    if avg_current < threshold_ua:
                        self._report(f"Consumo: {avg_current:.3f} uA (Límite: < {threshold_ua} uA) -> PASS", "PASS")
                    else:
                        self._report(f"Consumo: {avg_current:.3f} uA (Límite: < {threshold_ua} uA) -> FAIL", "FAIL")
                else:
                    self._report("No se pudo obtener una medición de corriente del PPK2 -> FAIL", "FAIL")

        except Exception as e:
            self._report(f"Error durante la medición con PPK2: {e}", "FAIL")