import serial
import time

class RS485Controller:
    """
    Gestiona la comunicación con un dispositivo a través de un adaptador USB-RS485.
    """
    def __init__(self, port: str, baud_rate: int = 115200, timeout: float = 2.0):
        """
        Inicializa el controlador RS485.

        Args:
            port (str): El puerto serie (ej. 'COM4' o '/dev/ttyUSB0').
            baud_rate (int): Velocidad de comunicación.
            timeout (float): Tiempo de espera en segundos para las lecturas.
        """
        if not port:
            raise ValueError("El puerto no puede ser nulo. Verifica tu 'config.yaml'.")

        self.port = port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.serial_conn = None

    def connect(self):
        """Abre la conexión con el puerto serie."""
        try:
            self.serial_conn = serial.Serial(self.port, self.baud_rate, timeout=self.timeout)
            print(f"Conectado al dispositivo RS485 en {self.port}.")
        except serial.SerialException as e:
            print(f"Error al conectar a RS485: {e}")
            raise

    def disconnect(self):
        """Cierra la conexión del puerto serie."""
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            print("Desconectado de RS485 de forma segura.")

    def send_command(self, command: str) -> str | None:
        """
        Envía un comando al dispositivo y espera una respuesta.

        Args:
            command (str): El comando a enviar (ej. "GETSERIAL").

        Returns:
            str | None: La respuesta del dispositivo como una cadena de texto,
                        o None si no se recibe respuesta (timeout).
        """
        if self.serial_conn is None or not self.serial_conn.is_open:
            raise ConnectionError("No conectado. Llama a 'connect()' primero.")

        print(f"TX --> {command}")

        # Limpiamos buffers antes de enviar para evitar leer respuestas viejas
        self.serial_conn.reset_input_buffer()
        self.serial_conn.reset_output_buffer()

        # Enviamos el comando codificado en UTF-8 y con un salto de línea
        self.serial_conn.write(f"{command}\n".encode('utf-8'))

        # Leemos la respuesta hasta encontrar un salto de línea
        response_bytes = self.serial_conn.readline()

        if not response_bytes:
            print("RX <-- (Timeout) No se recibió respuesta.")
            return None

        # Decodificamos y limpiamos la respuesta
        response_str = response_bytes.decode('utf-8').strip()
        print(f"RX <-- {response_str}")
        return response_str

    def get_board_info(self) -> dict:
        """
        Obtiene información básica del dispositivo conectado.

        Returns:
            dict: Un diccionario con la información del dispositivo.
        """
        info = {
            "serial": self.send_command("GETSERIAL"),
            "imei": self.send_command("GETIMEI"),
            "iccid": self.send_command("GETICCID"),
            "status": self.send_command("GETSTATUS")
        }
        return info

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()