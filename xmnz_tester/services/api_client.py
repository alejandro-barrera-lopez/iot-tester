import requests
import json
from xmnz_tester.models.test_result import TestResult

class ApiClient:
    """
    Cliente para enviar los resultados del test a la API central.
    """
    def __init__(self, endpoint_url: str = None, api_key: str = None, timeout_s: int = 10):
        """
        Inicializa el cliente con la configuración de la API.

        Args:
            endpoint_url (str): URL del endpoint de la API donde se enviarán los resultados.
            api_key (str): Clave de API para autenticación.
            timeout_s (int): Tiempo máximo de espera para la respuesta de la API en segundos.
        """
        self.endpoint_url = endpoint_url
        self.api_key = api_key
        self.timeout = timeout_s

    def send_test_result(self, test_result: TestResult) -> bool:
        """
        Envía el objeto de resultado del test a la API.

        Args:
            test_result (TestResult): El objeto completo con todos los datos del test.

        Returns:
            bool: True si el envío fue exitoso, False en caso contrario.
        """
        if not self.endpoint_url:
            print("URL de la API no configurada. No se enviarán los resultados.")
            return False

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        payload = test_result.to_dict()

        print(f"Enviando resultados a {self.endpoint_url}...")

        try:
            response = requests.post(
                self.endpoint_url,
                headers=headers,
                data=json.dumps(payload, indent=2),
                timeout=self.timeout
            )

            response.raise_for_status()

            print(f"Resultados enviados con éxito. Respuesta del servidor: {response.json()}")
            return True

        except requests.exceptions.RequestException as e:
            print(f"Error al enviar los resultados a la API: {e}")
            return False