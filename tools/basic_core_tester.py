import customtkinter as ctk
import threading
import time
from typing import Optional

# We use the BLU-Meter API library
# Make sure it's installed: pip install blu-api-python
try:
    from blu2_api.blu2_api import BLU2_API
except ImportError:
    BLU2_API = None

# --- TEST CONSTANTS (Based on the PDF) ---
# Supply voltage for the core test.
VOLTAGE_MV = 4000
# Wait time for the DUT (Device Under Test) to enter sleep mode (10s according to PDF + 2s margin).
WAIT_FOR_SLEEP_S = 12
# Maximum current consumption threshold in sleep mode.
SLEEP_CURRENT_THRESHOLD_UA = 30.0


class SimpleBLUMeter:
    """Simplified version of the BLU939 controller for this test."""
    def __init__(self):
        if BLU2_API is None:
            raise ImportError("The 'blu-api-python' library is not installed.")
        self.device: Optional[BLU2_API] = None
        self.is_connected = False

    def connect(self) -> bool:
        """Finds and connects to the first available BLU939 device."""
        try:
            ports = BLU2_API.list_devices()
            if not ports:
                print("Error: No BLU939 meter found.")
                return False

            self.device = BLU2_API(ports[0])
            self.device.get_modifiers()
            self.device.use_source_meter()
            self.is_connected = True
            print(f"Connected to BLU939 on port: {ports[0]}")
            return True
        except Exception as e:
            print(f"Error connecting to BLU939: {e}")
            return False

    def disconnect(self):
        """Turns off power and disconnects from the meter."""
        if self.device:
            try:
                self.device.toggle_DUT_power("OFF")
                self.device = None
                self.is_connected = False
                print("Safely disconnected from BLU939.")
            except Exception as e:
                print(f"Error disconnecting: {e}")

    def set_voltage(self, millivolts: int) -> bool:
        """Configures the output voltage and turns on power."""
        if not self.is_connected:
            return False
        try:
            self.device.set_source_voltage(millivolts)
            self.device.toggle_DUT_power("ON")
            print(f"Source activated. Supplying {millivolts} mV.")
            return True
        except Exception as e:
            print(f"Error setting voltage: {e}")
            return False

    def get_current_measurement(self) -> Optional[float]:
        """Takes a burst of measurements and returns the average in microamperes (uA)."""
        if not self.is_connected:
            return None
        try:
            self.device.start_measuring()
            time.sleep(0.2) # Capture for 200ms
            data = self.device.get_data()
            self.device.stop_measuring()

            if data:
                samples, _ = self.device.get_samples(data)
                if samples:
                    return sum(samples) / len(samples)
            return None
        except Exception as e:
            print(f"Error during measurement: {e}")
            return None


class App(ctk.CTk):
    """Main graphical interface for the core test."""
    def __init__(self):
        super().__init__()
        self.title("Basic Core Test (AC Controller)")
        self.geometry("500x450")

        ctk.set_appearance_mode("System")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # --- Widgets ---
        self.title_label = ctk.CTkLabel(self, text="Current consumption test - Phase 1", font=ctk.CTkFont(size=20, weight="bold"))
        self.title_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.start_button = ctk.CTkButton(self, text="Start test", command=self.start_test_thread)
        self.start_button.grid(row=1, column=0, padx=20, pady=10, ipady=10)

        self.status_frame = ctk.CTkFrame(self)
        self.status_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        self.status_frame.grid_columnconfigure(0, weight=1)

        self.instruction_label = ctk.CTkLabel(self.status_frame, text="Waiting to start...", wraplength=380)
        self.instruction_label.grid(row=0, column=0, padx=15, pady=15)

        self.current_label = ctk.CTkLabel(self.status_frame, text="Sleep consumption: -- µA", font=ctk.CTkFont(size=16))
        self.current_label.grid(row=1, column=0, padx=15, pady=10)

        self.result_label = ctk.CTkLabel(self.status_frame, text="RESULT: PENDING", font=ctk.CTkFont(size=24, weight="bold"))
        self.result_label.grid(row=2, column=0, padx=15, pady=(10, 20))

        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.blu_meter = SimpleBLUMeter()
        self.test_thread = None

    def start_test_thread(self):
        """Starts the test logic in a separate thread."""
        self.start_button.configure(state="disabled", text="Testing...")
        self.test_thread = threading.Thread(target=self.run_test_logic, daemon=True)
        self.test_thread.start()

    def run_test_logic(self):
        """Sequence of steps for the core test."""
        # 1. Reset GUI
        self.update_ui(instruction="Connecting to BLU939 meter...", result="PENDING", color="gray")

        # 2. Connect to meter
        if not self.blu_meter.connect():
            self.update_ui(instruction="Error: Could not connect to BLU939. Check connection and restart.", result="ERROR", color="red")
            self.start_button.configure(state="normal", text="Start Core Test")
            return

        # 3. Apply power
        self.update_ui(instruction="Power ON. The DUT is running its self-test.\n\nPlease wait...")
        if not self.blu_meter.set_voltage(VOLTAGE_MV):
            self.update_ui(instruction="Error activating BLU939 source.", result="ERROR", color="red")
            self.blu_meter.disconnect()
            self.start_button.configure(state="normal", text="Start Core Test")
            return

        # 4. Wait for DUT to enter sleep mode
        time.sleep(WAIT_FOR_SLEEP_S)

        # 5. Measure current consumption
        self.update_ui(instruction="Measuring sleep mode current consumption...")
        sleep_current = self.blu_meter.get_current_measurement()

        # 6. Disconnect power
        self.blu_meter.disconnect()

        # 7. Evaluate and display results
        if sleep_current is None:
            self.update_ui(instruction="Could not perform current consumption measurement.", result="FAIL", color="red")
        else:
            self.current_label.configure(text=f"Sleep Consumption: {sleep_current:.2f} µA")
            if sleep_current < SLEEP_CURRENT_THRESHOLD_UA:
                msg = f"Consumption OK ({sleep_current:.2f} µA).\n\nPhase 1 test passed. You can now proceed with the manual Phase 2 test (power with 12V, test tampers and relay)."
                self.update_ui(instruction=msg, result="PASS", color="green")
            else:
                msg = f"Consumption too high ({sleep_current:.2f} µA). The limit is {SLEEP_CURRENT_THRESHOLD_UA} µA."
                self.update_ui(instruction=msg, result="FAIL", color="red")

        self.start_button.configure(state="normal", text="Start Core Test")

    def update_ui(self, instruction=None, result=None, color=None, current=None):
        """Helper function to update the GUI from the test thread."""
        if instruction is not None:
            self.instruction_label.configure(text=instruction)
        if result is not None:
            self.result_label.configure(text=f"RESULT: {result}")
        if color is not None:
            self.result_label.configure(text_color=color)
        if current is not None:
            self.current_label.configure(text=f"Sleep Consumption: {current:.2f} µA")

    def on_closing(self):
        """Ensures safe disconnection when closing the window."""
        if self.blu_meter.is_connected:
            self.blu_meter.disconnect()
        self.destroy()

if __name__ == "__main__":
    if BLU2_API is None:
        print("Critical Error: The 'blu-api-python' library was not found.")
        print("Please install it with: pip install blu-api-python")
    else:
        app = App()
        app.mainloop()