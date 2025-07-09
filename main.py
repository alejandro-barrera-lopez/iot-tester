import time
import customtkinter as ctk
from xmnz_tester.config import ConfigManager
from xmnz_tester.hal.relays import RelayController
from xmnz_tester.hal.ina3221 import PowerMeterINA3221
from xmnz_tester.hal.ppk2 import PowerMeterPPK2
from xmnz_tester.hal.rs485 import RS485Controller
from xmnz_tester.gui.main_window import MainWindow

def poc_relay_controller():
    """
    Prueba de concepto para controlar relés usando la librería pyhid_usb_relay.
    Esta función se conecta a un controlador de relés y activa/desactiva relés específicos.
    """
    print("Iniciando PoC con pyhid_usb_relay...")

    # Cargar configuración
    hw_cfg = config.get("hardware_ports", {})
    relay_serial = hw_cfg.get("relay_controller_serial_number")

    # Iniciar el controlador de relés
    with RelayController(num_relays=2, serial_number=relay_serial) as controller:
        print("\nIniciando secuencia de prueba...")

        controller.set_relay(1, True)
        time.sleep(2)

        controller.set_relay(2, True)
        time.sleep(2)

        controller.all_off()
        time.sleep(1)

    print("\n--- Prueba de concepto finalizada ---")

def poc_rs485_controller():
    """
    Prueba de concepto para comunicación RS485 usando la librería pyserial.
    Esta función se conecta a un dispositivo RS485 y envía un comando simple.
    """
    print("Iniciando PoC con RS485...")

    # Cargar configuración
    hw_cfg = config.get("hardware_ports", {})
    rs485_port = hw_cfg.get("rs485_port")
    baud_rate = hw_cfg.get("baud_rate", 115200)

    # Iniciar el controlador RS485
    with RS485Controller(port=rs485_port, baud_rate=baud_rate) as rs485:
        print("\nConectando al dispositivo RS485...")
        rs485.connect()

        print("\nEnviando comando 'GETSERIAL'...")
        response = rs485.send_command("GETSERIAL")
        if response:
            print(f"Respuesta del dispositivo: {response}")
        else:
            print("No se recibió respuesta del dispositivo.")

        rs485.disconnect()

    print("\n--- Prueba de concepto finalizada ---")

def poc_ina3221():
    meter_cfg = config.get("power_meter_ina3221")

    if not meter_cfg:
        raise ValueError("No se encontró la configuración 'power_meter_ina3221' en config.yaml")

    # 1. Inicializar y conectar con el sensor usando 'with'
    with PowerMeterINA3221(**meter_cfg) as power_meter:

        # 2. Leer un canal específico
        print("\nLeyendo canal 1...")
        data_ch1 = power_meter.read_channel(1)

        if data_ch1:
            print(f"  -> Voltaje: {data_ch1['bus_voltage_V']:.3f} V")
            print(f"  -> Corriente: {data_ch1['current_mA']:.3f} mA")
        else:
            print("  -> No se pudieron leer los datos.")

        time.sleep(2)

        # Repetir para otro canal si es necesario
        print("\nLeyendo canal 2...")
        data_ch2 = power_meter.read_channel(2)
        if data_ch2:
            print(f"  -> Voltaje: {data_ch2['bus_voltage_V']:.3f} V")
            print(f"  -> Corriente: {data_ch2['current_mA']:.3f} mA")


    print("\n--- Prueba finalizada ---")

def poc_ppk2():
    print("--- PoC del la placa PPK2 ---")

    # 1. Cargar configuración
    ppk2_cfg = config.get("power_meter_ppk2", {})
    serial_number = ppk2_cfg.get("serial_number")
    voltage_mv = ppk2_cfg.get("source_voltage_mv", 3300)

    # 2. Inicializar y conectar con el PPK2 usando 'with'
    with PowerMeterPPK2(serial_number=serial_number) as ppk2:

        # 3. Configurar el PPK2 y encender el dispositivo a probar
        ppk2.configure_source_meter(voltage_mv)
        ppk2.set_dut_power(True)

        # 4. Realizar una medición de 5 segundos
        # Esta única línea reemplaza todo el bucle complejo del script original.
        average_current = ppk2.measure_average_current(duration_s=5)

        print(f"\nRESULTADO FINAL: La corriente media fue de {average_current:.3f} uA.")

        # 5. Apagar el dispositivo (se hace automáticamente al salir del 'with')

    print("\n--- Prueba finalizada ---")

def launch_gui():
    """
    Lanza la interfaz gráfica de usuario (GUI) para el tester.
    Esta función es un placeholder y debería ser implementada con una GUI real.
    """
    print("Lanzando GUI...")
    ctk.set_appearance_mode("system") # "System", "Light", "Dark"
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    app = MainWindow(root)
    root.mainloop()

if __name__ == "__main__":
    print("--- Iniciando PoC con librería pyhid_usb_relay ---")

    try:
        # Cargar la configuración
        config = ConfigManager()

        launch_gui()

        # Probar relés
        # poc_relay_controller()

        # Probar RS485
        # poc_rs485_controller()

        # Probar INA3221
        # poc_ina3221()

        # Probar PPK2
        # poc_ppk2()

    except Exception as e:
        print(f"\nOcurrió un error fatal: {e}")