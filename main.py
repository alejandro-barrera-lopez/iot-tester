import customtkinter as ctk
from xmnz_tester.config import ConfigManager
from xmnz_tester.gui.main_window import MainWindow

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
        config = ConfigManager()
        launch_gui()

    except Exception as e:
        print(f"\nOcurrió un error fatal: {e}")