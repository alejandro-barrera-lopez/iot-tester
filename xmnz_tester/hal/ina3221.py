from ina219 import INA219, DeviceRangeError

class PowerMeterINA3221:
    """
    Clase para interactuar con el sensor de potencia INA3221 a través de I2C.
    Abstrae la librería ina219 para presentar una interfaz coherente.
    """
    def __init__(self, i2c_bus: int, i2c_address: int, shunt_resistance_ohms: float):
        """
        Inicializa el sensor INA3221.

        Args:
            i2c_bus (int): El número del bus I2C.
            address (int): La dirección I2C del dispositivo.
            shunt_ohms (float): El valor de la resistencia de shunt.
        """
        self.address = i2c_address
        self.shunt_ohms = shunt_resistance_ohms
        self.i2c_bus = i2c_bus
        self.channels = []

    def connect(self):
        """
        Configura los tres canales del INA3221.
        En I2C no hay una 'conexión' real, pero usamos este método para inicializar.
        """
        print(f"Configurando INA3221 en la dirección I2C 0x{self.address:X}...")
        try:
            # La librería maneja cada canal como una instancia separada de INA219
            self.channels = [
                INA219(self.shunt_ohms, address=self.address, busnum=self.i2c_bus), # Canal 1
                INA219(self.shunt_ohms, address=self.address, busnum=self.i2c_bus), # Canal 2
                INA219(self.shunt_ohms, address=self.address, busnum=self.i2c_bus)  # Canal 3
            ]
            for channel in self.channels:
                channel.configure()
            print("Sensor INA3221 configurado correctamente.")
        except Exception as e:
            print(f"Error al configurar el INA3221: {e}")
            raise

    def disconnect(self):
        """Método de desconexión por consistencia con otros módulos HAL."""
        print("Recurso INA3221 liberado.")
        pass

    def read_channel(self, channel_number: int) -> dict | None:
        """
        Lee los datos de un canal específico (1, 2, o 3).

        Returns:
            Un diccionario con 'bus_voltage', 'current_mA', y 'power_mW', o None si hay error.
        """
        if not 1 <= channel_number <= len(self.channels):
            raise ValueError(f"El número de canal debe ser entre 1 y {len(self.channels)}.")

        sensor_channel = self.channels[channel_number - 1]

        try:
            return {
                'bus_voltage_V': sensor_channel.voltage(),
                'current_mA': sensor_channel.current(),
                'power_mW': sensor_channel.power()
            }
        except DeviceRangeError as e:
            print(f"Error de rango en el canal {channel_number}: {e}. La corriente podría ser demasiado alta.")
            return None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()