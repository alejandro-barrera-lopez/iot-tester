import time
from xmnz_tester.config import ConfigManager
from xmnz_tester.hal.relays import RelayController
from xmnz_tester.hal.ina3221 import PowerMeterINA3221
from xmnz_tester.hal.meter_factory import MeterFactory

# Mapeo de nombres de relés a sus números para facilitar el uso
# Se cargará desde la configuración
RELAY_NAME_MAP = {}

def print_menu():
    """Imprime el menú de comandos disponibles."""
    print("\n--- Menú de test de hardware ---")
    print("Comandos de Relé:")
    print("  relay on <num_o_nombre>   - Encender un relé (ej: 'relay on 1' o 'relay on connect_battery')")
    print("  relay off <num_o_nombre>  - Apagar un relé")
    print("  relay state <num_o_nombre> - Consultar estado de un relé")
    print("  all_off                   - Apagar todos los relés")
    print("\nComandos de Medidor de Potencia (uA Meter):")
    print("  power on                  - Habilitar salida de 3.7V del medidor uA")
    print("  power off                 - Deshabilitar salida de 3.7V")
    print("  measure ua                - Realizar una medición de corriente (uA)")
    print("\nComandos de Medidor de Activo (INA3221):")
    print("  measure ma <canal>        - Medir un canal del INA3221 (ej: 'measure ma 1')")
    print("\nOtros:")
    print("  status                    - Mostrar estado de los dispositivos")
    print("  menu                      - Mostrar este menú")
    print("  quit                      - Salir de la aplicación")
    print("---------------------------------")

def main():
    """Función principal del tester interactivo."""
    print("--- Inicializando Herramienta de Test de Hardware ---")

    # --- 1. Cargar configuración e inicializar hardware ---
    try:
        config = ConfigManager()
        # Invertimos el mapa para poder buscar por nombre
        global RELAY_NAME_MAP
        RELAY_NAME_MAP = config.relay_map

        print("Conectando a la placa de relés...")
        relay_controller = RelayController(
            num_relays=len(RELAY_NAME_MAP),
            serial_number=config.relay_serial_number
        )
        relay_controller.connect()

        print("\nConectando al medidor de uA...")
        ua_meter_config = config.hardware.get("power_meters", {}).get("ua_meter", {})
        ua_meter = MeterFactory.create_ua_meter(ua_meter_config)
        if not ua_meter or not ua_meter.connect():
            raise ConnectionError("No se pudo conectar al medidor de uA.")
        print(f"Medidor de uA ({ua_meter.get_info()['type']}) conectado.")

        print("\nConectando al medidor INA3221...")
        ina_meter = PowerMeterINA3221(**config.ina3221_config)
        ina_meter.connect()

    except Exception as e:
        print(f"\nERROR CRÍTICO durante la inicialización: {e}")
        print("Asegúrate de que el hardware está conectado y 'config.yaml' es correcto.")
        return

    # --- 2. Bucle principal de comandos ---
    print_menu()
    while True:
        try:
            cmd_input = input("\n> Introduce un comando: ").strip().lower()
            parts = cmd_input.split()
            if not parts:
                continue

            command = parts[0]

            if command == "quit":
                break

            elif command == "menu":
                print_menu()

            # --- Lógica de relés ---
            elif command == "relay":
                action = parts[1]
                # Permitir usar tanto el número como el nombre del relé
                relay_id_str = parts[2]
                relay_num = RELAY_NAME_MAP.get(relay_id_str, relay_id_str)
                relay_num = int(relay_num)

                if action == "on":
                    relay_controller.set_relay(relay_num, True)
                elif action == "off":
                    relay_controller.set_relay(relay_num, False)
                elif action == "state":
                    state = relay_controller.get_relay_state(relay_num)
                    print(f"Resultado: El relé {relay_num} está {'ON' if state else 'OFF'}.")

            elif command == "all_off":
                print("Apagando todos los relés...")
                relay_controller.all_off()

            # --- Lógica del medidor de uA ---
            elif command == "power":
                if parts[1] == "on":
                    ua_meter.set_source_enabled(True)
                elif parts[1] == "off":
                    ua_meter.set_source_enabled(False)

            elif command == "measure" and parts[1] == "ua":
                print("Midiendo corriente (puede tardar un momento)...")
                current = ua_meter.get_current_measurement()
                if current is not None:
                    print(f"Resultado: {current:.2f} uA")
                else:
                    print("Error: No se pudo obtener la medición.")

            # --- Lógica del medidor INA3221 ---
            elif command == "measure" and parts[1] == "ma":
                channel = int(parts[2])
                print(f"Midiendo canal {channel} del INA3221...")
                data = ina_meter.read_channel(channel)
                if data:
                    print(f"  - Voltaje: {data['bus_voltage_V']:.3f} V")
                    print(f"  - Corriente: {data['current_mA']:.2f} mA")
                    print(f"  - Potencia: {data['power_mW']:.2f} mW")
                else:
                    print("Error: No se pudo leer el canal.")

            elif command == "status":
                print("\n--- Estado Actual del Hardware ---")
                print("Medidor uA:", ua_meter.get_info())
                print("Relés: (No implementado, usa 'relay state <n>')")


            else:
                print(f"Comando '{command}' desconocido. Escribe 'menu' para ver las opciones.")

        except (IndexError, ValueError) as e:
            print(f"Error en el comando: {e}. Revisa la sintaxis. Escribe 'menu' para ayuda.")
        except Exception as e:
            print(f"Ha ocurrido un error inesperado: {e}")


    # --- 3. Desconexión segura ---
    print("\n--- Desconectando hardware de forma segura ---")
    relay_controller.disconnect()
    ua_meter.disconnect()
    ina_meter.disconnect()
    print("Chau!")


if __name__ == "__main__":
    main()