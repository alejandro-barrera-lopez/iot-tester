import requests
import json
from xmnz_tester.models.test_result import TestResult

class ApiClient:
    """
    Cliente para enviar los resultados del test a la API central.
    """
    def __init__(self, api_config: dict):
        """
        Inicializa el cliente con la configuración de la API.

        Args:
            api_config (dict): Un diccionario con 'endpoint_url', 'key', y 'timeout_s'.
        """
        self.endpoint_url = api_config.get("endpoint_url")
        self.api_key = api_config.get("key")
        self.timeout = api_config.get("request_timeout_s", 10)

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