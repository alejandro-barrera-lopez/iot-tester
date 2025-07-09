import time
import statistics
from xmnz_tester.hal.relays import RelayController
from xmnz_tester.hal.rs485 import RS485Controller
from xmnz_tester.hal.ppk2 import PowerMeterPPK2
from xmnz_tester.hal.ina3221 import PowerMeterINA3221

class TestRunner:
    """
    Orquesta la secuencia completa de tests, interactuando con la capa HAL
    y reportando los resultados a través de una función callback.
    """
    def __init__(self, config: dict, gui_callback: callable):
        """
        Inicializa el motor de test.

        Args:
            config (dict): El diccionario de configuración cargado desde config.yaml.
            gui_callback (callable): Función para enviar actualizaciones a la GUI.
                                     Debe aceptar dos argumentos: (mensaje, estado).
        """
        self.config = config
        self.callback = gui_callback
        self.overall_status = "PASS"

        # Los controladores se inicializarán en connect_all_hardware()
        self.relay_controller = None
        self.rs485_controller = None
        self.ppk2_meter = None
        self.ina3221_meter = None

    def _report(self, message: str, status: str = "INFO"):
        """Método centralizado para enviar mensajes a la GUI."""
        # Si un paso falla, el estado general del test falla.
        if status == "FAIL":
            self.overall_status = "FAIL"

        if self.callback:
            self.callback(message, status)

    def run_full_test(self):
        """
        Punto de entrada principal. Ejecuta la secuencia completa de tests.
        Este método está diseñado para ser ejecutado en un hilo separado.
        """
        try:
            # --- 1. Conexión al Hardware ---
            self._connect_all_hardware()

            # --- 2. Ejecución de los Pasos del Test ---
            self._run_test_steps()

        except Exception as e:
            self._report(f"ERROR CRÍTICO: {e}", "FAIL")

        finally:
            # --- 3. Desconexión del Hardware ---
            self._disconnect_all_hardware()
            self._report(f"Test finalizado. Resultado general: {self.overall_status}", self.overall_status)
            return self.overall_status

    def _connect_all_hardware(self):
        """Inicializa y conecta todos los controladores del HAL."""
        self._report("--- Conectando al hardware ---", "HEADER")

        hardware_cfg = self.config.get("hardware", {})

        # Conectar relés
        relay_cfg = hardware_cfg.get("relay_controller", {})
        self.relay_controller = RelayController(
            num_relays=len(self.config.get("resource_mapping", {}).get("relay_map", {})),
            serial_number=relay_cfg.get("serial_number", ""),
            port=relay_cfg.get("port", None)
        )

        self.relay_controller.connect()

        # Conectar RS485
        rs485_cfg = hardware_cfg.get("rs485", {})
        self.rs485_controller = RS485Controller(
            port=rs485_cfg.get("port"),
            baud_rate=rs485_cfg.get("baud_rate")
        )
        self.rs485_controller.connect()

        meters_cfg = hardware_cfg.get("power_meters", {})

        # Conectar PPK2
        ppk2_cfg = meters_cfg.get("ua_meter_ppk2", {})
        self.ppk2_meter = PowerMeterPPK2(serial_number=ppk2_cfg.get("serial_number"))
        self.ppk2_meter.connect()

        # Conectar INA3221
        ina_cfg = meters_cfg.get("active_meter_ina3221", {})
        self.ina3221_meter = PowerMeterINA3221(**ina_cfg)
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

    def _run_test_steps(self):
        """Define y ejecuta la secuencia de pruebas una por una."""
        self._report("--- Iniciando secuencia de pruebas ---", "HEADER")

        # Test procedure:
        # 1- Connect the battery (REL4 ON). DUT start autotesting
        # self._test_step_enable_battery()

        # 2- Power the device from Vin (REL3 ON)
        # self._test_step_enable_vin()

        # 3- By rs485, check status, get imei, icc, i2c sensors...
        # self._test_step_check_board_autotest()

        # 4- Measure INA3221 both channels
        # self._test_step_measure_ina3221() # TODO: ¿Abstraer INA3221 a un método genérico?

        # 5- Test tampering inputs
        # self._test_step_check_tampers()

        # 6- Test board relay (REL1 ON, ...)
        # self._test_step_check_board_relay()

        # 7- Disconnect the battery (REL4 OFF)
        # self._test_step_disable_battery()

        # 8- Enable 3v7 with uA
        # self._test_step_enable_3v7()

        # 9- Disconnect Vin (REL3 OFF)
        # self._test_step_disable_vin()

        # 10- GetStatus
        # self._test_step_get_status()

        # 11- Send the board to LowPower
        # self._test_step_send_low_power()

        # 12- Measure low current with uA
        # self._test_step_measure_low_current()

        # 13- Wait to normal mode
        # self._test_step_wait_normal_mode()

        # 14- Send uA current value to DUT
        # self._test_step_send_uA_current()

        # 15- Get barcode and serial number
        # self._test_step_get_barcode_and_serial()

        # 16- Force sending modem json
        # self._test_step_force_send_modem_json()

        # 17- Finish testing


        # Cada paso es una función separada
        # self._test_step_check_serial()
        self._test_step_check_relays()
        # self._test_step_measure_current()
        # self._test_step_check_ina3221()
        # self._test_step_check_ina3221_averaged()

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

            # Desactivar los relñes
            self.relay_controller.all_off()
            time.sleep(1)  # Esperar un segundo para estabilizar

            if not self.relay_controller.get_relay_state(1):
                self._report("Relé 1 desactivado correctamente -> PASS", "PASS")
            else:
                self._report("Fallo al desactivar el Relé 1 -> FAIL", "FAIL")

        except Exception as e:
            self._report(f"Error al verificar relés: {e}", "FAIL")

    def _test_step_check_ina3221(self):
        """Ejemplo de paso: Verifica que el INA3221 responde correctamente."""
        self._report("Paso 3: Verificando INA3221...", "INFO")

        try:
            meter_cfg = self.config.get("power_meter_ina3221", {})

            with PowerMeterINA3221(**meter_cfg) as power_meter:
                all_channels_ok = True
                report_lines = []

                # Iterar sobre los 3 canales del INA3221
                for channel in range(1, 4):
                    data = power_meter.read_channel(channel)

                    if data:
                        voltage = data['bus_voltage_V']
                        current = data['current_mA']
                        report_lines.append(f"  - Canal {channel}: {voltage:.3f} V, {current:.3f} mA")
                    else:
                        self._report(f"Fallo al leer el canal {channel} del INA3221 -> FAIL", "FAIL")
                        all_channels_ok = False
                        break

                if all_channels_ok:
                    full_report = "Lecturas del INA3221 correctas:\n" + "\n".join(report_lines)
                    self._report(f"{full_report}\n -> PASS", "PASS")

        except Exception as e:
            self._report(f"Error al inicializar o comunicar con el INA3221: {e}", "FAIL")

    def _test_step_check_ina3221_averaged(self):
        """Verifica el INA3221 tomando una media de mediciones durante un tiempo determinado."""
        self._report("Paso 3: Verificando INA3221 (promedio de 2 segundos)...", "INFO")

        duration_s = 2.0  # Duración del muestreo

        try:
            meter_cfg = self.config.get("power_meter_ina3221", {})

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

    def _test_step_check_serial(self):
        """Ejemplo de paso: Lee el número de serie y verifica que no esté vacío."""
        self._report("Paso 1: Verificando comunicación y S/N...", "INFO")
        response = self.rs485_controller.send_command("GETSERIAL")
        if response and len(response) > 5:
            self._report(f"Comunicación OK. S/N Leído: {response}", "PASS")
        else:
            self._report("Fallo al leer S/N o respuesta inválida.", "FAIL")

    def _test_step_measure_current(self):
        """Ejemplo: Mide el consumo en reposo y lo compara con un umbral."""
        self._report("Paso 2: Midiendo consumo en reposo...", "INFO")

        try:
            # 1. Cargar toda la configuración necesaria al principio
            ppk2_cfg = self.config.get("power_meter_ppk2", {})
            serial_number = ppk2_cfg.get("serial_number")
            voltage_mv = ppk2_cfg.get("source_voltage_mv", 3300)
            threshold_ua = self.config.get("test_thresholds", {}).get("sleep_current_max_ua", 50.0)

            with PowerMeterPPK2(serial_number=serial_number) as ppk2_meter:
                # 2a. Configurar el PPK2 y encender el dispositivo
                ppk2_meter.configure_source_meter(voltage_mv)
                ppk2_meter.set_dut_power(True)
                self._report(f"PPK2 configurado a {voltage_mv}mV y alimentación ON.", "INFO")

                # 3. Pedir al dispositivo que entre en modo de bajo consumo
                self.rs485_controller.send_command("SLEEP")
                time.sleep(2)  # Aumentado a 2s para asegurar la estabilización

                # 4. Medir la corriente
                # El método ya devuelve la media en uA, como se ve en el PoC.
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