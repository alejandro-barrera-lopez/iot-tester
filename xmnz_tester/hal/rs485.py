import serial
import time
from typing import List

class RS485Controller:
    """
    Gestiona la comunicación con un dispositivo a través de un adaptador USB-RS485,
    adaptado para una CLI con respuestas multilínea y con un prompt '#'.
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
        """Abre la conexión con el puerto serie y espera a que el dispositivo esté listo (prompt '#')."""
        try:
            self.serial_conn = serial.Serial(self.port, self.baud_rate, timeout=self.timeout)
            print(f"Conectado al dispositivo RS485 en {self.port}.")
            # self.wait_for_prompt()
        except serial.SerialException as e:
            print(f"Error al conectar a RS485: {e}")
            raise

    def disconnect(self):
        """Cierra la conexión del puerto serie."""
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            print("Desconectado de RS485 de forma segura.")

    def send_command(self, command: str) -> List[str] | None:
        """
        Envía un comando y lee todas las líneas de la respuesta hasta
        encontrar el siguiente prompt ('#').

        Args:
            command (str): El comando a enviar (ej. "GETDEVICEDATA").

        Returns:
            List[str] | None: Una lista con las líneas de la respuesta,
                              o None si no se recibe respuesta (timeout).
        """
        if self.serial_conn is None or not self.serial_conn.is_open:
            raise ConnectionError("No conectado. Llama a 'connect()' primero.")

        print(f"TX --> {command}")
        self.serial_conn.write(f"{command}\n".encode('utf-8'))

        response_lines = []
        while True:
            try:
                line_bytes = self.serial_conn.readline()
                if not line_bytes: # Timeout
                    print("RX <-- (Timeout) No se recibió respuesta.")
                    return None

                line_str = line_bytes.decode('utf-8', errors='ignore').strip()

                if line_str.startswith('#'):
                    break

                if line_str:
                    response_lines.append(line_str)

            except Exception as e:
                print(f"Error durante la lectura del puerto serie: {e}")
                break

        print(f"RX <-- {response_lines}")
        return response_lines

    def wait_for_prompt(self, timeout_s: int = 5):
        """Lee y descarta datos del buffer hasta encontrar el prompt '#' o que se agote el tiempo."""
        print("Esperando al prompt del dispositivo ('#')...")
        start_time = time.time()
        while time.time() - start_time < timeout_s:
            line_bytes = self.serial_conn.readline()
            if line_bytes and line_bytes.strip().startswith(b'#'):
                print("Prompt '#' detectado. El dispositivo está listo.")
                return True
        raise TimeoutError(f"No se detectó el prompt '#' en {timeout_s} segundos.")

    def check_initial_status(self) -> dict:
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