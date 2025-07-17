import time
import json
from xmnz_tester.config import ConfigManager
from xmnz_tester.hal.relays import RelayController
from xmnz_tester.hal.ina3221 import PowerMeterINA3221
from xmnz_tester.hal.meter_factory import MeterFactory
from xmnz_tester.hal.rs485 import RS485Controller

# Mapeo de nombres de relés a sus números para facilitar el uso
# Se cargará desde la configuración
RELAY_NAME_MAP = {}

def print_menu():
    """Imprime el menú de comandos disponibles."""
    print("\n--- Menú de test de hardware ---")
    print("Comandos de Relé:")
    print("  relay on <id>   - Encender un relé (id: num, nombre o 'all')")
    print("                                     (ej. 'relay on connect_battery')")
    print("  relay off <id>  - Apagar un relé (id: num, nombre o 'all')")
    print("  relay state <num/nombre> - Consultar estado de un relé")
    print("  all_off                   - Apagar todos los relés")
    print("\nComandos de puerto serie (al DUT):")
    print("  serial <comando>            - Enviar comando al DUT y ver la respuesta")
    print("                                (ej: serial GETSTATUS)")
    print("\nComandos de medidor de potencia (uA meter):")
    print("  power on                  - Habilitar salida de 3.7V del medidor uA")
    print("  power off                 - Deshabilitar salida de 3.7V")
    print("  measure ua                - Realizar una medición de corriente (uA)")
    print("\nComandos de medidor de activo (INA3221):")
    print("  measure ma <canal>        - Medir un canal del INA3221 (ej: 'measure ma 1')")
    print("\nOtros:")
    print("  status                    - Mostrar estado de los dispositivos")
    print("  help                      - Mostrar este menú")
    print("  exit                      - Salir de la aplicación")
    print("---------------------------------")

def main():
    """Función principal del tester interactivo."""
    print("--- Inicializando herramienta de test de hardware ---")

    # --- Variables de controladores ---
    relay_controller = None
    ua_meter = None
    ina_meter = None
    rs485_controller = None

    # --- Cargar configuración e inicializar hardware ---
    try:
        config = ConfigManager()

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

        print("\nConectando al puerto serie...")
        rs485_controller = RS485Controller(**config.rs485_config)
        if not rs485_controller.connect():
             raise ConnectionError("No se pudo conectar al puerto serie del DUT.")
        print(f"Puerto serie {config.rs485_config['port']} conectado.")

    except Exception as e:
        print(f"\nERROR CRÍTICO durante la inicialización: {e}")
        print("Asegúrate de que el hardware está conectado y 'config.yaml' es correcto.")
        return

    # --- Bucle principal de comandos ---
    print_menu()
    while True:
        try:
            cmd_input = input("\n> Introduce un comando: ").strip().lower()
            parts = cmd_input.split()
            if not parts:
                continue

            command = parts[0]

            if command == "quit" or command == "exit":
                break

            elif command == "menu" or command == "help":
                print_menu()

            # --- Lógica de relés ---
            elif command == "relay":
                action = parts[1]
                target = parts[2]

                if target == "all":
                    if action == "on":
                        print("Encendiendo todos los relés...")
                        relay_controller.all_on()
                    elif action == "off":
                        print("Apagando todos los relés...")
                        relay_controller.all_off()
                    else:
                        print("Error: La acción 'state' no es compatible con 'all'.")
                else:
                    try:
                        relay_num = RELAY_NAME_MAP.get(target, target)
                        relay_num = int(relay_num)

                        if action == "on":
                            relay_controller.set_relay(relay_num, True)
                            print(f"Relé {relay_num} ({target}) encendido.")
                        elif action == "off":
                            relay_controller.set_relay(relay_num, False)
                            print(f"Relé {relay_num} ({target}) apagado.")
                        elif action == "state":
                            state = relay_controller.get_relay_state(relay_num)
                            print(f"Resultado: El relé {relay_num} ({target}) está {'ON' if state else 'OFF'}.")
                    except (ValueError, KeyError):
                        print(f"Error: Identificador de relé '{target}' no válido.")

            elif command == "all_off":
                print("Apagando todos los relés...")
                relay_controller.all_off()
            # --- Lógica de puerto serie ---
            elif command == "serial":
                if len(parts) < 2:
                    print("Error: Debes especificar un comando a enviar. Ej: 'serial GETSTATUS'")
                    continue

                dut_command = " ".join(parts[1:])

                response_lines = rs485_controller.send_command(dut_command)

                if response_lines is not None:
                    if len(response_lines) == 1:
                        try:
                            json_response = json.loads(response_lines[0])
                            print("Respuesta (JSON formateado):")
                            print(json.dumps(json_response, indent=2))
                        except json.JSONDecodeError:
                            print("Respuesta (texto):")
                            print(response_lines[0])
                        print("Respuesta (multilínea):")
                        for line in response_lines:
                            print(line)
                else:
                    print("No se obtuvo una respuesta completa del dispositivo.")

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
                print(f"Comando '{command}' desconocido. Escribe 'help' para ver las opciones.")

        except (IndexError, ValueError) as e:
            print(f"Error en el comando: {e}. Revisa la sintaxis. Escribe 'help' para ayuda.")
        except Exception as e:
            print(f"Ha ocurrido un error inesperado: {e}")


    # --- Desconexión segura ---
    print("\n--- Desconectando hardware de forma segura ---")
    if relay_controller: relay_controller.disconnect()
    if ua_meter: ua_meter.disconnect()
    if ina_meter: ina_meter.disconnect()
    if rs485_controller: rs485_controller.disconnect()
    print("Chau!")


if __name__ == "__main__":
    main()