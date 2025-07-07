# main.py

import time
from xmnz_tester.config import load_config
from xmnz_tester.hal.relays import RelayController

if __name__ == "__main__":
    print("--- Iniciando PoC con librería pyhid_usb_relay ---")

    try:
        # 1. Cargar la configuración
        config = load_config()
        hw_cfg = config.get("hardware_ports", {})
        relay_serial = hw_cfg.get("relay_controller_serial_number")

        # Para la PoC, usamos 2 relés
        num_relays_poc = 2

        # 2. Iniciar el controlador con los nuevos parámetros
        with RelayController(num_relays=num_relays_poc, serial_number=relay_serial) as controller:
            print("\nIniciando secuencia de prueba...")

            controller.set_relay(1, True)
            time.sleep(2)

            controller.set_relay(2, True)
            time.sleep(2)

            controller.all_off()
            time.sleep(1)

        print("\n--- Prueba de Concepto Finalizada ---")

    except Exception as e:
        print(f"\nOcurrió un error fatal: {e}")