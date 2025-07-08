import customtkinter as ctk
import threading
from xmnz_tester.engine.test_runner import TestRunner
from xmnz_tester.config import load_config

# Define una paleta de colores para los estados
STATUS_COLORS = {
    "default": ("#3498DB", "#2980B9"),  # Azul
    "pass": ("#2ECC71", "#27AE60"),    # Verde
    "fail": ("#E74C3C", "#C0392B"),    # Rojo
    "testing": ("#F1C40F", "#F39C12") # Amarillo
}

class MainWindow:
    def __init__(self, root: ctk.CTk):
        self.root = root
        self.root.title("XMNZ Test")
        self.root.geometry("700x500")

        # --- Variables de estado ---
        self.serial_number_var = ctk.StringVar(value="---")
        self.status_var = ctk.StringVar(value="EN ESPERA")

        # --- Configuración del layout (grid) ---
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)

        # --- Creación de Widgets ---
        self._create_status_frame()
        self._create_log_frame()
        self._create_action_frame()

        # --- Cargar configuración ---
        self.config = load_config()

    def _create_status_frame(self):
        """Crea el marco superior con el estado general y el número de serie."""
        frame = ctk.CTkFrame(self.root)
        frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(frame, text="Número de Serie:", font=("", 14, "bold")).grid(row=0, column=0, padx=10, pady=5)
        ctk.CTkLabel(frame, textvariable=self.serial_number_var, font=("", 14)).grid(row=0, column=1, padx=10, pady=5, sticky="w")

        self.status_label = ctk.CTkLabel(frame, textvariable=self.status_var, font=("", 20, "bold"), fg_color=STATUS_COLORS["default"])
        self.status_label.grid(row=0, column=2, padx=20, pady=10, sticky="e")

    def _create_log_frame(self):
        """Crea el área de texto central para el log en tiempo real."""
        self.log_textbox = ctk.CTkTextbox(self.root, font=("", 12), state="disabled")
        self.log_textbox.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")

    def _create_action_frame(self):
        """Crea el marco inferior con los botones de acción."""
        frame = ctk.CTkFrame(self.root)
        frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        frame.grid_columnconfigure(0, weight=1)

        self.start_button = ctk.CTkButton(frame, text="INICIAR TEST", font=("", 16, "bold"), command=self.start_test_thread)
        self.start_button.grid(row=0, column=0, padx=10, pady=10, ipady=10, sticky="ew")

    def log_message(self, message: str):
        """Añade un mensaje al cuadro de log de forma segura."""
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", f"> {message}\n")
        self.log_textbox.configure(state="disabled")
        self.log_textbox.see("end") # Auto-scroll

    def set_status(self, status: str, color: tuple):
        """Actualiza la etiqueta de estado principal."""
        self.status_var.set(status.upper())
        self.status_label.configure(fg_color=color)

    def update_gui_callback(self, message: str, status: str):
        """
        Esta es la función que el TestRunner llamará desde otro hilo.
        Usa `root.after` para asegurar que las actualizaciones de la GUI
        se ejecuten de forma segura en el hilo principal.
        """
        def update_task():
            if status == "PASS" or status == "FAIL" or status == "INFO" or status == "HEADER":
                self.log_message(message)

            # Puedes añadir lógica más compleja aquí, como cambiar colores
            # self.set_status(...)

        self.root.after(0, update_task)

    def start_test_thread(self):
        """Inicia la lógica del test en un hilo separado para no bloquear la GUI."""
        # Limpiar log anterior
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.configure(state="disabled")

        self.log_message("Iniciando secuencia de test...")
        self.set_status("PROBANDO", STATUS_COLORS["testing"])
        self.start_button.configure(state="disabled", text="PROBANDO...")

        # Crear una instancia del TestRunner, pasándole el config y el callback
        runner = TestRunner(config=self.config, gui_callback=self.update_gui_callback)

        # Ejecutar el test en un hilo
        test_thread = threading.Thread(
            target=self.run_and_finalize, # Llama a un wrapper para gestionar el final
            args=(runner,),
            daemon=True
        )
        test_thread.start()

    def run_and_finalize(self, runner: TestRunner):
        """Wrapper que ejecuta el test y actualiza la GUI al final."""
        final_result = runner.run_full_test()

        # Al final, actualizamos el estado principal de forma segura
        def final_update():
            if final_result == "PASS":
                self.set_status("PASS", STATUS_COLORS["pass"])
            else:
                self.set_status("FAIL", STATUS_COLORS["fail"])
            self.start_button.configure(state="normal", text="INICIAR NUEVO TEST")

        self.root.after(0, final_update)

    # def start_test_thread(self):
    #     """Inicia la lógica del test en un hilo separado para no bloquear la GUI."""
    #     self.log_message("Iniciando secuencia de test...")
    #     self.set_status("PROBANDO", STATUS_COLORS["testing"])
    #     self.start_button.configure(state="disabled", text="PROBANDO...")

    #     # Aquí es donde se crearía y lanzaría el hilo
    #     # El 'target' sería el método principal de tu TestRunner
    #     # test_runner = TestRunner(callback=self.update_from_thread)
    #     # thread = threading.Thread(target=test_runner.run_full_test)
    #     # thread.start()

    #     # --- Simulación para la PoC de la GUI ---
    #     # Borra estas líneas cuando integres el TestRunner real
    #     def fake_test_simulation():
    #         import time
    #         self.root.after(1000, lambda: self.log_message("Conectando a hardware... OK"))
    #         self.root.after(2000, lambda: self.log_message("Prueba de Vin... PASS"))
    #         self.root.after(3000, lambda: self.log_message("Midiendo consumo... 4.5uA -> PASS"))
    #         self.root.after(4000, self.on_test_complete) # Llama a la función de finalización

    #     threading.Thread(target=fake_test_simulation, daemon=True).start()


    # def on_test_complete(self):
    #     """Se llama cuando el test ha finalizado para actualizar la GUI."""
    #     # Aquí determinarías si el resultado final es PASS o FAIL
    #     final_result = "PASS" # Esto vendría del TestRunner

    #     if final_result == "PASS":
    #         self.set_status("PASS", STATUS_COLORS["pass"])
    #     else:
    #         self.set_status("FAIL", STATUS_COLORS["fail"])

    #     self.start_button.configure(state="normal", text="INICIAR NUEVO TEST")