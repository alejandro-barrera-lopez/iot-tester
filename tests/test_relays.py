import pytest
from unittest.mock import MagicMock, patch

from xmnz_tester.hal.relays import RelayController

# Usamos el decorador @patch para reemplazar 'pyhid_usb_relay' por un mock
@patch('xmnz_tester.hal.relays.pyhid_usb_relay')
def test_relay_connect_and_set_state(mock_hid_relay):
    """
    Test que verifica la conexión y el cambio de estado de un relé.
    """
    # --- 1. Configuración del mock ---
    # Simulamos que el mock devuelve un dispositivo falso cuando se llama a find()
    mock_device = MagicMock()
    mock_hid_relay.find.return_value = mock_device

    # --- 2. Ejecución del código a probar ---
    # Usamos 'with' para que connect() y disconnect() se llamen automáticamente
    # Pasamos parámetros de ejemplo
    with RelayController(num_relays=4, serial_number="TEST_SN") as controller:
        # Probamos a encender el relé 2
        controller.set_relay(2, True)

        # Probamos a apagar el relé 3
        controller.set_relay(3, False)

    # --- 3. Verificaciones (Asserts) ---
    # Verificamos que find() fue llamado una vez
    mock_hid_relay.find.assert_called_once_with()

    # Verificamos que set_state() fue llamado correctamente para encender el relé 2
    mock_device.set_state.assert_any_call(2, True)

    # Verificamos que set_state() fue llamado correctamente para apagar el relé 3
    mock_device.set_state.assert_any_call(3, False)

@patch('xmnz_tester.hal.relays.pyhid_usb_relay')
def test_relay_connection_failed(mock_hid_relay):
    """
    Test que verifica que se lanza una excepción si no se encuentra el dispositivo.
    """
    # Configuramos el mock para que devuelva None, como si no encontrara nada
    mock_hid_relay.find.return_value = None

    # Verificamos que se lanza una ConnectionError al intentar conectar
    with pytest.raises(ConnectionError, match="No se encontró ninguna placa de relés HID"):
        controller = RelayController(num_relays=2)
        controller.connect()

def test_invalid_relay_number():
    """
    Test que verifica que se lanza un error si el número de relé es incorrecto.
    No necesitamos mocks aquí porque este error es lógica interna de nuestra clase.
    """
    # Creamos una instancia sin conectar para probar la lógica de validación
    controller = RelayController(num_relays=2)

    with pytest.raises(ValueError, match="Número de relé inválido: 3"):
        controller.set_relay(3, True)