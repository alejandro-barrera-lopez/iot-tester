import customtkinter as ctk
import threading
from xmnz_tester.engine.test_runner import TestRunner
from xmnz_tester.config import ConfigManager

# Define una paleta de colores para los estados
STATUS_COLORS = {
    "default": ("#3498DB", "#2980B9"),  # Azul
    "pass": ("#2ECC71", "#27AE60"),    # Verde
    "fail": ("#E74C3C", "#C0392B"),    # Rojo
    "testing": ("#F1C40F", "#F39C12") # Amarillo
}


class TestStepWidget(ctk.CTkFrame):
    """Un widget para mostrar el estado de un único paso de test."""

    def __init__(self, master, step_name: str, step_id: str):
        super().__init__(master, fg_color="transparent")
        self.step_id = step_id

        self.status_indicator = ctk.CTkLabel(self, text="⚪", font=("", 14))
        self.status_indicator.pack(side="left", padx=(0, 5))

        self.name_label = ctk.CTkLabel(self, text=step_name, anchor="w")
        self.name_label.pack(side="left", fill="x", expand=True)

        self.rerun_button = ctk.CTkButton(self, text="Re-run", width=60, state="disabled")
        self.rerun_button.pack(side="right", padx=(5, 0))

    def set_status(self, status: str):
        if status == "PASS":
            self.status_indicator.configure(text="🟢", text_color="green")
        elif status == "FAIL":
            self.status_indicator.configure(text="🔴", text_color="red")
        elif status == "TESTING":
            self.status_indicator.configure(text="🟡", text_color="yellow")
        else:  # PENDIENTE
            self.status_indicator.configure(text="⚪", text_color="gray")

class MainWindow:
    def __init__(self, root: ctk.CTk):
        self.config = ConfigManager()

        self.root = root
        self.root.title(self.config.app_title)
        self.root.geometry(self.config.app_resolution)

        # --- Variables de estado ---
        self.serial_number_var = ctk.StringVar(value="---")
        self.status_var = ctk.StringVar(value="EN ESPERA")

        # --- Configuración del layout (grid) ---
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)

        # --- Variables de control del test ---
        self.stop_event = threading.Event()
        self.is_running = False
        self.step_widgets = {}

        # --- Creación de widgets ---
        self._create_side_panel()
        self._create_main_panel()

        # --- Layout con panel lateral ---
        self.root.grid_columnconfigure(0, weight=1) # Panel lateral
        self.root.grid_rowconfigure(1, weight=3)    # Área principal
        self.root.grid_rowconfigure(0, weight=1)    # Fila principal

    def _create_side_panel(self):
        self.side_panel = ctk.CTkScrollableFrame(self.root, label_text="Pasos del Test")
        self.side_panel.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # Esto es un ejemplo. La lista real vendría del TestRunner.
        test_steps = [
            {"name": "Conectar batería", "id": "_test_step_enable_battery"},
            {"name": "Aplicar Vin (12V)", "id": "_test_step_enable_vin"},
            # ... etc.
        ]

        for step in test_steps:
            widget = TestStepWidget(self.side_panel, step["name"], step["id"])
            widget.pack(fill="x", expand=True, pady=2)
            self.step_widgets[step["id"]] = widget

    def _create_main_panel(self):
        main_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        main_frame.grid(row=0, column=1, rowspan=2, padx=10, pady=10, sticky="nsew")
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)

        # Reutilizamos los métodos que ya tenías, pero los metemos en este panel
        self._create_status_frame(parent=main_frame)
        self._create_log_frame(parent=main_frame)
        self._create_action_frame(parent=self.root)  # Botones abajo del todo

    def _create_status_frame(self, parent):
        """Crea el marco superior con el estado general y el número de serie."""
        frame = ctk.CTkFrame(parent)
        frame.grid(row=0, column=0, sticky="ew")
        # frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(frame, text="Número de serie:", font=("", 14, "bold")).grid(row=0, column=0, padx=10, pady=5)
        ctk.CTkLabel(frame, textvariable=self.serial_number_var, font=("", 14)).grid(row=0, column=1, padx=10, pady=5, sticky="w")

        self.status_label = ctk.CTkLabel(frame, textvariable=self.status_var, font=("", 20, "bold"), fg_color=STATUS_COLORS["default"])
        self.status_label.grid(row=0, column=2, padx=20, pady=10, sticky="e")

    def _create_log_frame(self, parent):
        """Crea el área de texto central para el log en tiempo real."""
        self.log_textbox = ctk.CTkTextbox(parent, font=("", 12), state="disabled")
        self.log_textbox.grid(row=1, column=0, pady=5, sticky="nsew")
        self.log_textbox = ctk.CTkTextbox(self.root, font=("", 12), state="disabled")
        self.log_textbox.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")

    def _create_action_frame(self, parent):
        """Crea el marco superior con el estado general y el número de serie."""
        frame = ctk.CTkFrame(parent)
        frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        # frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
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

    def on_start_stop_button_click(self):
        if self.is_running:
            self.stop_test()
        else:
            self.start_test_thread()

    def stop_test(self):
        if self.is_running:
            self.log_message("Solicitando detención del test...")
            self.stop_event.set()
            self.start_button.configure(state="disabled", text="DETENIENDO...")


    def start_test_thread(self):
        """Inicia la lógica del test en un hilo separado para no bloquear la GUI."""
        self.is_running = True
        self.stop_event.clear()
        self.start_button.configure(text="DETENER TEST", command=self.stop_test)
        # Limpiar log anterior
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.configure(state="disabled")

        self.log_message("Iniciando secuencia de test...")
        self.set_status("PROBANDO", STATUS_COLORS["testing"])
        # self.start_button.configure(state="disabled", text="PROBANDO...")

        # Crear una instancia del TestRunner, pasándole el config y el callback
        runner = TestRunner(config_manager=self.config, gui_callback=self.update_gui_callback)

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
            self.is_running = False
            if final_result == "PASS":
                self.set_status("PASS", STATUS_COLORS["pass"])
            else:
                self.set_status("FAIL", STATUS_COLORS["fail"])
            self.start_button.configure(state="normal", text="INICIAR NUEVO TEST")

        self.root.after(0, final_update)
