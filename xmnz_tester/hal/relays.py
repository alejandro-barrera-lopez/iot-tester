import pyhid_usb_relay
import time

class RelayController:
    """
    Gestiona una placa de relés USB HID usando la librería pyhid_usb_relay.
    """
    def __init__(self, num_relays: int, serial_number: str = None):
        """
        Inicializa el controlador de relés.

        Args:
            num_relays (int): El número de relés en la placa.
            serial_number (str, optional): El número de serie del dispositivo.
                Si es None, se conectará a la primera placa encontrada.
        """
        self.num_relays = num_relays
        self.serial_number = serial_number if serial_number else None
        self.relay_device = None # Aquí guardaremos el objeto de la librería

    def connect(self):
        """Encuentra y se conecta a la placa de relés HID."""
        print(f"🔎 Buscando placa de relés HID (S/N: {self.serial_number or 'cualquiera'})...")
        try:
            self.relay_device = pyhid_usb_relay.find()
            if self.relay_device is None:
                raise ConnectionError("No se encontró ninguna placa de relés HID.")

            # serial = self.relay_device.serial_number
            # print(f"Conectado al controlador de relés (S/N: {serial}).")
            self.all_off() # Asegura un estado inicial conocido y seguro
        except Exception as e:
            # La librería puede lanzar varias excepciones si hay problemas de drivers
            print(f"Error al conectar con la placa HID: {e}")
            raise

    def disconnect(self):
        """Apaga todos los relés. No se necesita cerrar la conexión en HID."""
        if self.relay_device:
            print("Desconectando, apagando todos los relés...")
            self.all_off()
            self.relay_device = None
            print("Recurso del relé liberado.")

    def set_relay(self, relay_num: int, state: bool):
        """
        Establece el estado de un relé específico.

        Args:
            relay_num (int): El número del relé a controlar (empezando en 1).
            state (bool): True para encender (ON), False para apagar (OFF).
        """
        if self.relay_device is None:
            raise ConnectionError("No conectado. Llama a 'connect()' primero.")

        if not 1 <= relay_num <= self.num_relays:
            raise ValueError(f"Número de relé inválido: {relay_num}. Debe estar entre 1 y {self.num_relays}.")

        print(f"Estableciendo relé #{relay_num} en {'ON' if state else 'OFF'}")
        # La librería se encarga de la lógica de control
        self.relay_device.set_state(relay_num, state)

    def all_off(self):
        """Apaga todos los relés de la placa."""
        if self.relay_device:
            for i in range(1, self.num_relays + 1):
                self.relay_device.set_state(i, False)

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()