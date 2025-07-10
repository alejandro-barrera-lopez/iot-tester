import customtkinter as ctk
import threading
from ..engine.sequence_definition import TEST_SEQUENCE
from ..engine.test_runner import TestRunner
from ..config import ConfigManager

STATUS_COLORS = {
    "default": ("#3498DB", "#2980B9"),  # Azul
    "pass": ("#2ECC71", "#27AE60"),     # Verde
    "fail": ("#E74C3C", "#C0392B"),     # Rojo
    "testing": ("#F1C40F", "#F39C12")   # Amarillo
}

class TestStepWidget(ctk.CTkFrame):
    """Un widget para mostrar el estado de un único paso de test."""
    def __init__(self, master, step_name: str, step_id: str):
        super().__init__(master, fg_color="transparent")
        self.step_id = step_id

        self.status_indicator = ctk.CTkLabel(self, text="⚪", font=("", 14), width=20)
        self.status_indicator.pack(side="left", padx=(0, 5))

        self.name_label = ctk.CTkLabel(self, text=step_name, anchor="w")
        self.name_label.pack(side="left", fill="x", expand=True)

        self.rerun_button = ctk.CTkButton(self, text="Re-run", width=60, state="disabled")
        self.rerun_button.pack(side="right", padx=(5, 0))

    def set_status(self, status: str):
        if status.upper() == "PASS":
            self.status_indicator.configure(text="🟢", text_color="green")
        elif status.upper() == "FAIL":
            self.status_indicator.configure(text="🔴", text_color="red")
        elif status.upper() == "TESTING":
            self.status_indicator.configure(text="🟡", text_color="yellow")
        else:  # PENDIENTE
            self.status_indicator.configure(text="⚪", text_color="gray")

class MainWindow:
    def __init__(self, root: ctk.CTk):
        self.root = root
        self.config = ConfigManager()
        self.step_definitions = self._build_gui_definitions()

        self.root.title(self.config.app_title)
        self.root.geometry(self.config.app_resolution)

        # --- Variables de control ---
        self.serial_number_var = ctk.StringVar(value="---")
        self.status_var = ctk.StringVar(value="EN ESPERA")
        self.stop_event = threading.Event()
        self.is_running = False
        self.step_widgets = {}

        # --- Configuración del layout principal ---
        self.root.grid_columnconfigure(0, weight=1)  # Panel lateral
        self.root.grid_columnconfigure(1, weight=3)  # Panel principal
        self.root.grid_rowconfigure(0, weight=1)     # Fila para paneles
        self.root.grid_rowconfigure(1, weight=0)     # Fila para botones de acción

        # --- Creación de widgets ---
        self._create_side_panel()
        self._create_main_panel()
        self._create_action_frame()

    def _build_gui_definitions(self):
        """Construye la lista de pasos para la GUI a partir de la secuencia."""
        definitions = []
        for i, step_info in enumerate(TEST_SEQUENCE):
            step_key = step_info['key']
            message_template = self.config.ui_messages.get(step_key, step_key)
            clean_name = message_template.replace("Paso {}: ", "")
            method_id = f"_{step_key}"
            definitions.append({"id": method_id, "name": f"{i + 1}. {clean_name}"})
        return definitions

    def _create_side_panel(self):
        """Crea el panel lateral con la lista de todos los pasos del test."""
        self.side_panel = ctk.CTkScrollableFrame(self.root, label_text="Pasos del test")
        self.side_panel.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        for step_def in self.step_definitions:
            widget = TestStepWidget(self.side_panel, step_def["name"], step_def["id"])
            widget.pack(fill="x", expand=True, pady=2, padx=5)
            self.step_widgets[step_def["id"]] = widget

    def _create_main_panel(self):
        """Crea el panel principal que contiene el estado y el log."""
        main_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        main_frame.grid(row=0, column=1, padx=(0, 10), pady=10, sticky="nsew")
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)

        self._create_status_frame(parent=main_frame)
        self._create_log_frame(parent=main_frame)

    def _create_status_frame(self, parent):
        """Crea el marco superior con el estado general y el número de serie."""
        frame = ctk.CTkFrame(parent)
        frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(frame, text="Número de serie:", font=("", 14, "bold")).grid(row=0, column=0, padx=10, pady=5)
        ctk.CTkLabel(frame, textvariable=self.serial_number_var, font=("", 14)).grid(row=0, column=1, padx=10, pady=5, sticky="w")
        self.status_label = ctk.CTkLabel(frame, textvariable=self.status_var, font=("", 20, "bold"), fg_color=STATUS_COLORS["default"])
        self.status_label.grid(row=0, column=2, padx=20, pady=10, sticky="e")

    def _create_log_frame(self, parent):
        """Crea el área de texto central para el log en tiempo real."""
        self.log_textbox = ctk.CTkTextbox(parent, font=("", 12), state="disabled")
        self.log_textbox.grid(row=1, column=0, sticky="nsew")

    def _create_action_frame(self):
        """Crea el marco inferior con los botones de acción."""
        frame = ctk.CTkFrame(self.root)
        frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        frame.grid_columnconfigure(0, weight=1)

        self.start_stop_button = ctk.CTkButton(frame, text="INICIAR TEST", font=("", 16, "bold"), command=self.on_start_stop_button_click)
        self.start_stop_button.grid(row=0, column=0, padx=10, pady=10, ipady=10, sticky="ew")

    def log_message(self, message: str):
        """Añade un mensaje al cuadro de log de forma segura."""
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", f"> {message}\n")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def set_overall_status(self, status: str, color: tuple):
        """Actualiza la etiqueta de estado principal."""
        self.status_var.set(status.upper())
        self.status_label.configure(fg_color=color)

    def update_gui_callback(self, step_id: str, message: str, status: str):
        """Callback que el TestRunner usa para actualizar la GUI en tiempo real."""
        def update_task():
            self.log_message(message)
            if step_id in self.step_widgets:
                self.step_widgets[step_id].set_status(status)
        self.root.after(0, lambda: update_task())

    def on_start_stop_button_click(self):
        """Gestiona el clic en el botón principal, ya sea para iniciar o detener."""
        if self.is_running:
            self.stop_test()
        else:
            self.start_test_thread()

    def stop_test(self):
        """Señala al hilo del test que debe detenerse."""
        if self.is_running:
            self.log_message("Solicitando detención del test...")
            self.stop_event.set()
            self.start_stop_button.configure(state="disabled", text="DETENIENDO...")

    def start_test_thread(self):
        """Inicia la lógica del test en un hilo separado para no bloquear la GUI."""
        self.is_running = True
        self.stop_event.clear()
        self._reset_ui_state()
        self.set_overall_status("PROBANDO", STATUS_COLORS["testing"])
        self.start_stop_button.configure(text="DETENER TEST")

        runner = TestRunner(
            config_manager=self.config,
            gui_callback=self.update_gui_callback,
            stop_event=self.stop_event
        )
        test_thread = threading.Thread(target=self.run_and_finalize, args=(runner,), daemon=True)
        test_thread.start()

    def _reset_ui_state(self):
        """Resetea la GUI a su estado inicial antes de un nuevo test."""
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.configure(state="disabled")
        for widget in self.step_widgets.values():
            widget.set_status("PENDING")

    def run_and_finalize(self, runner: TestRunner):
        """Wrapper que ejecuta el test y actualiza la GUI al final."""
        final_result = runner.run_full_test()

        def final_update():
            self.is_running = False
            if final_result == "PASS":
                self.set_overall_status("PASS", STATUS_COLORS["pass"])
            else:
                self.set_overall_status("FAIL", STATUS_COLORS["fail"])
            self.start_stop_button.configure(state="normal", text="INICIAR NUEVO TEST")
        self.root.after(0, lambda: final_update())
