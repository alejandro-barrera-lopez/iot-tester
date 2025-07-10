import time
import statistics
from xmnz_tester.config import ConfigManager
from xmnz_tester.hal.relays import RelayController
from xmnz_tester.hal.rs485 import RS485Controller
from xmnz_tester.hal.ppk2 import PowerMeterPPK2
from xmnz_tester.hal.ina3221 import PowerMeterINA3221
from xmnz_tester.dut_commands import DutCommands
from xmnz_tester.models.test_result import TestResult, TestStepResult
from xmnz_tester.services.api_client import ApiClient
from .sequence_definition import TEST_SEQUENCE

class TestRunner:
    """
    Orquesta la secuencia completa de tests, interactuando con la capa HAL
    y reportando los resultados a través de una función callback.
    """
    def __init__(self, config_manager: ConfigManager, gui_callback: callable):
        """
        Inicializa el motor de test.

        Args:
            config_manager (ConfigManager): Instancia del gestor de configuración que contiene
                                            la configuración del test.
            gui_callback (callable): Función para enviar actualizaciones a la GUI.
                                     Debe aceptar dos argumentos: (mensaje, estado).
        """
        self.config = config_manager
        self.callback = gui_callback
        self.step_counter = 0
        self.test_result = None

        # Los controladores se inicializarán en connect_all_hardware()
        self.relay_controller = None
        self.rs485_controller = None
        self.ppk2_meter = None
        self.ina3221_meter = None

    def _report(self, message: str, status: str = "INFO", details: dict = None):
        """Metodo centralizado para enviar mensajes a la GUI."""
        # Si un paso falla, el estado general del test falla.
        if self.callback:
            self.callback(message)

        step = TestStepResult(
            step_name=f"Paso {self.step_counter}",
            status=status,
            message=message,
            details=details or {}
        )
        self.test_result.add_step(step)

    def run_full_test(self):
        """
        Punto de entrada principal. Ejecuta la secuencia completa de tests.
        Este metodo está diseñado para ser ejecutado en un hilo separado.
        """
        self.test_result = TestResult(station_id=self.config.station_id)
        self.step_counter = 0

        try:
            # --- 1. Conexión al hardware ---
            self._connect_all_hardware()

            # --- 2. Ejecución de los pasos del test ---
            self._run_test_steps()

        except Exception as e:
            self._report(f"ERROR CRÍTICO: {e}", "FAIL")

        finally:
            # --- 3. Desconexión del hardware ---
            self._disconnect_all_hardware()
            self.test_result.finalize()
            self._report(f"Test finalizado. Resultado general: {self.test_result.overall_status}", self.test_result.overall_status)

            self._send_results_to_api()

            # print(self.test_result.to_dict())
            return self.test_result.overall_status

    def _connect_all_hardware(self):
        """Inicializa y conecta todos los controladores del HAL."""
        self._report("--- Conectando al hardware ---", "HEADER")

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
        self._report("--- Desconectando del hardware ---", "HEADER")
        if self.relay_controller:
            self.relay_controller.disconnect()
        if self.rs485_controller:
            self.rs485_controller.disconnect()
        if self.ppk2_meter:
            self.ppk2_meter.disconnect()
        if self.ina3221_meter:
            self.ina3221_meter.disconnect()

    def _send_results_to_api(self):
        """Creates API client and sends results."""
        api_client = ApiClient(self.config.api_config)
        success = api_client.send_test_result(self.test_result)

        if success:
            self._report("Resultados sincronizados con la plataforma.", "INFO")
        else:
            # TODO: Manejar reintentos o errores específicos
            self._report("Fallo al sincronizar resultados con la plataforma.", "FAIL")

    def _run_test_steps(self):
        """Itera sobre la secuencia de claves y ejecuta el método correspondiente."""
        self._report("--- Iniciando secuencia de pruebas ---", "HEADER")

        for step_key in TEST_SEQUENCE:
            if self.stop_event and self.stop_event.is_set():
                self._report("Test detenido por el usuario.", "FAIL")
                break

            # Construimos el nombre del método a partir de la clave
            method_name = f"_{step_key}"

            try:
                method_to_call = getattr(self, method_name)
            except AttributeError:
                self._report(f"Error de implementación: No se encontró el método '{method_name}'", "FAIL")
                break

            # Llamamos al método del paso
            method_to_call()

            if self.test_result.overall_status == "FAIL":
                self._report("La secuencia se detuvo debido a un fallo.", "INFO")
                break

    # def _run_test_steps(self):
    #     """Define y ejecuta la secuencia de pruebas una por una."""
    #     self._report("--- Iniciando secuencia de pruebas ---", "HEADER")

    #     # Test procedure:
    #     # 1- Connect the battery (REL4 ON). DUT start autotesting
    #     self._test_step_enable_battery()

    #     # 2- Power the device from Vin (REL3 ON)
    #     self._test_step_enable_vin()

    #     # 3- By rs485, check status=plugged, get imei, icc, i2c sensors...
    #     self._test_step_get_board_info()

    #     # 4- Measure INA3221 both channels
    #     self._test_step_measure_ina3221() # TODO: ¿Abstraer INA3221 a un método genérico?

    #     # 5- Test tampering inputs
    #     self._test_step_check_tampers()

    #     # 6- Test board relay (with REL1 off and reading tamper in1)
    #     self._test_step_check_board_relay()

    #     # 7- Disconnect the battery (REL4 OFF)
    #     self._test_step_disable_battery()

    #     # 8- Enable 3v7 with uA
    #     self._test_step_enable_3v7()

    #     # 9- Disconnect Vin (REL3 OFF)
    #     self._test_step_disable_vin()

    #     # 10- GetStatus: stored
    #     self._test_step_get_status("STATUS=2")

    #     # 11- Send the board to LowPower
    #     self._test_step_send_low_power()

    #     # 12- Measure low current with uA
    #     self._test_step_measure_low_current()

    #     # 13- Wait to normal mode
    #     self._test_step_wait_normal_mode()

    #     # 14- Send uA current value to DUT
    #     self._test_step_send_uA_current()

    #     # 15- Get barcode and serial number
    #     self._test_step_get_barcode_and_serial()

    #     # 16- Force sending modem json
    #     self._test_step_force_send_modem_json()

    #     # 17- Finish testing
    #     self._report("--- Secuencia de pruebas finalizada ---", "HEADER")

    def _start_step(self, message_key: str):
        """
        Incrementa el contador, formatea y reporta el mensaje de inicio de un paso.
        """
        self.step_counter += 1

        messages = self.config.ui_messages

        message_template = messages.get(message_key, f"Iniciando: {message_key}")

        final_message = message_template.format(self.step_counter)
        self._report(final_message, "INFO")

    def _test_step_enable_battery(self):
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

    def _test_step_enable_vin(self):
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

    def _test_step_get_board_info(self):
        """Step 3: Checks DUT initial status."""
        self._start_step("step_check_initial_status")

        response = self.rs485_controller.get_board_info()

        if response and len(response) > 5:
            serial = response.get("serial", "Desconocido")
            imei = response.get("imei", "Desconocido")
            iccid = response.get("iccid", "Desconocido")
            status = response.get("status", "Desconocido")

            self._report(f"Comunicación OK. S/N: {serial}, IMEI: {imei}, ICCID: {iccid}, Estado: {status}", "PASS", response)
        else:
            self._report("Fallo al leer información del dispositivo o respuesta inválida.", "FAIL", response)

    def _test_step_measure_ina3221(self):
        """Step 4: Measure INA3221 channels and report results."""
        self._start_step("step_measure_ina3221")

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
                        self._report(f"Canal {channel}: {voltage:.3f} V, {current:.3f} mA", "PASS", details)
                    else:
                        self._report(f"Fallo al leer el canal {channel} -> FAIL", "FAIL")

        except Exception as e:
            self._report(f"Error al medir INA3221: {e}", "FAIL")

    def _test_step_check_tampers(self):
        """Step 5: Check tampering inputs."""
        self._start_step("step_check_tampers")

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

    def _test_step_check_board_relay(self):
        """Step 6: Check board relay with REL1 off and reading tamper in1."""
        self._start_step("step_check_board_relay")

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

    def _test_step_disable_battery(self):
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

    def _test_step_enable_3v7(self):
        """Step 8: Enable 3v7 with uA meter."""
        self._start_step("step_enable_3v7")

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

    def _test_step_disable_vin(self):
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

    def _test_step_get_status(self, expected_status):
        """Step 10: GetStatus command to check device status."""
        self._start_step("step_get_status")

        try:
            response = self.rs485_controller.send_command(DutCommands.GET_SERIAL)
            if response == expected_status:
                self._report(f"Estado del dispositivo: {response} -> PASS", "PASS", response)
            else:
                self._report("Fallo al obtener el estado del dispositivo -> FAIL", "FAIL", response)
        except Exception as e:
            self._report(f"Error al obtener el estado: {e}", "FAIL")

    def _test_step_send_low_power(self):
        """Step 11: Send command to put the device in low power mode."""
        self._start_step("step_send_low_power")

        try:
            response = self.rs485_controller.send_command(DutCommands.SET_LOW_POWER)
            if response: # TODO: validar respuesta esperada
                self._report("Dispositivo enviado a modo de bajo consumo -> PASS", "PASS", response)
            else:
                self._report("Fallo al enviar comando de bajo consumo -> FAIL", "FAIL", response)
        except Exception as e:
            self._report(f"Error al enviar comando de bajo consumo: {e}", "FAIL")

    def _test_step_measure_low_current(self):
        """Step 12: Measure low current with uA meter."""
        self._start_step("step_measure_low_current")

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

    def _test_step_wait_normal_mode(self):
        """Step 13: Wait for the device to return to normal mode."""
        self._start_step("step_wait_normal_mode")

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

    def _test_step_send_uA_current(self):
        """Step 14: Send uA current value to DUT."""
        self._start_step("step_send_uA_current")

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
                    response = self.rs485_controller.send_command(DutCommands.SET_LAST_CURRENT, str(avg_current))
                    if response == "OK":
                        self._report(f"Corriente enviada al DUT: {avg_current} uA -> PASS", "PASS")
                    else:
                        self._report("Fallo al enviar corriente al DUT -> FAIL", "FAIL")
                else:
                    self._report("Fallo al medir corriente para enviar -> FAIL", "FAIL")

        except Exception as e:
            self._report(f"Error al enviar corriente uA: {e}", "FAIL")

    def _test_step_get_barcode_and_serial(self):
        """Step 15: Get barcode and serial number from the DUT."""
        self._start_step("step_get_barcode_and_serial")

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

    def _test_step_force_send_modem_json(self):
        """Step 16: Force sending modem JSON data."""
        self._start_step("step_force_send_modem_json")

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