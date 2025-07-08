import time
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

        # Conectar Relés
        relay_cfg = self.config.get("hardware_ports", {})
        self.relay_controller = RelayController(
            num_relays=len(self.config.get("resource_mapping", {}).get("relay_map", {})),
            serial_number=relay_cfg.get("relay_controller_serial_number")
        )
        self.relay_controller.connect()

        # Conectar RS485
        rs485_cfg = self.config.get("hardware_ports", {})
        self.rs485_controller = RS485Controller(
            port=rs485_cfg.get("rs485_port"),
            baud_rate=rs485_cfg.get("baud_rate")
        )
        self.rs485_controller.connect()

        # Conectar PPK2
        ppk2_cfg = self.config.get("power_meter_ppk2", {})
        self.ppk2_meter = PowerMeterPPK2(serial_number=ppk2_cfg.get("serial_number"))
        self.ppk2_meter.connect()

    def _disconnect_all_hardware(self):
        """Desconecta de forma segura todos los controladores del HAL."""
        self._report("--- Desconectando del hardware ---", "HEADER")
        if self.relay_controller:
            self.relay_controller.disconnect()
        if self.rs485_controller:
            self.rs485_controller.disconnect()
        if self.ppk2_meter:
            self.ppk2_meter.disconnect()

    def _run_test_steps(self):
        """Define y ejecuta la secuencia de pruebas una por una."""
        self._report("--- Iniciando secuencia de pruebas ---", "HEADER")

        # Cada paso es una función separada
        # self._test_step_check_serial()
        self._test_step_check_relays()
        self._test_step_measure_current()
        self._test_step_check_ina3221()
        # self._test_step_check_vin()
        # self._test_step_check_tampers()

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