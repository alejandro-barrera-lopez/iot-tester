import time
from ppk2_api.ppk2_api import PPK2_API

class PowerMeterPPK2:
    """
    Clase de alto nivel para interactuar con el Power Profiler Kit II (PPK2).
    Abstrae la comunicación y el procesamiento de datos.
    """
    def __init__(self, serial_number: str = None):
        """
        Inicializa el controlador del PPK2.

        Args:
            serial_number (str, optional): El S/N del PPK2 al que conectar.
                Si es None, se conectará al primero que encuentre.
        """
        self.serial_number = serial_number
        self.port = None
        self.ppk2_api = None

    def connect(self):
        """Encuentra y se conecta al PPK2."""
        print(f"🔎 Buscando PPK2 (S/N: {self.serial_number or 'cualquiera'})...")
        devices = PPK2_API.list_devices()

        if not devices:
            raise ConnectionError("No se encontró ningún PPK2 conectado.")

        if self.serial_number:
            device_info = next((d for d in devices if d.serial_number == self.serial_number), None)
            if not device_info:
                raise ConnectionError(f"No se encontró el PPK2 con S/N {self.serial_number}.")
            self.port = device_info.port
        else:
            if len(devices) > 1:
                print("ADVERTENCIA: Se encontraron múltiples PPK2. Conectando al primero.")
            self.port = devices[0].port

        try:
            self.ppk2_api = PPK2_API(self.port)
            self.ppk2_api.get_modifiers() # Necesario para inicializar las mediciones
            print(f"Conectado al PPK2 en {self.port} (S/N: {self.ppk2_api.serial_number}).")
        except Exception as e:
            print(f"Error al conectar con el PPK2: {e}")
            raise

    def disconnect(self):
        """Detiene las mediciones y libera el recurso."""
        if self.ppk2_api:
            self.ppk2_api.stop_measuring()
            self.set_dut_power(False)
            self.ppk2_api = None # La librería se encarga de cerrar el puerto
            print("Recurso PPK2 liberado.")

    def configure_source_meter(self, voltage_mv: int):
        """Configura el PPK2 para actuar como fuente de alimentación y medidor."""
        if self.ppk2_api:
            print(f"Configurando modo 'Source Meter' con {voltage_mv}mV...")
            self.ppk2_api.set_source_voltage(voltage_mv)
            self.ppk2_api.use_source_meter()

    def set_dut_power(self, state: bool):
        """Activa o desactiva la alimentación al dispositivo bajo test (DUT)."""
        if self.ppk2_api:
            power_state = "ON" if state else "OFF"
            print(f"⚡ Alimentación DUT en {power_state}")
            self.ppk2_api.toggle_DUT_power(power_state)

    def measure_average_current(self, duration_s: float) -> float:
        """
        Mide la corriente durante un periodo de tiempo y devuelve la media.
        Este es el método principal que usará el motor de test.

        Args:
            duration_s (float): El número de segundos durante los que medir.

        Returns:
            float: La corriente media en microamperios (uA) durante el periodo.
        """
        if not self.ppk2_api:
            raise ConnectionError("PPK2 no conectado.")

        print(f"Iniciando medición de corriente durante {duration_s} segundos...")
        all_samples = []

        self.ppk2_api.start_measuring()
        start_time = time.time()

        while time.time() - start_time < duration_s:
            read_data = self.ppk2_api.get_data()
            if read_data:
                samples, _ = self.ppk2_api.get_samples(read_data)
                all_samples.extend(samples)

        self.ppk2_api.stop_measuring()

        if not all_samples:
            print("No se tomaron muestras.")
            return 0.0

        average = sum(all_samples) / len(all_samples)
        print(f"Medición finalizada. Media: {average:.3f} uA sobre {len(all_samples)} muestras.")
        return average

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()