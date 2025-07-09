import yaml
from pathlib import Path

class ConfigManager:
    """
    Clase Singleton que carga, gestiona y proporciona acceso a la configuración
    del proyecto desde el fichero config.yaml.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        # El patrón Singleton asegura que solo exista una instancia de esta clase.
        if not cls._instance:
            cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, config_path: Path = Path("config.yaml")):
        # El __init__ se ejecutará solo la primera vez que se cree la instancia.
        if not hasattr(self, '_config'):
            self._config_path = config_path
            self._config = self._load_config()

    def _load_config(self) -> dict:
        """Carga el fichero de configuración YAML."""
        print(f"⚙Cargando configuración desde {self._config_path}")
        try:
            with open(self._config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"ERROR: Fichero de configuración no encontrado en '{self._config_path}'")
            raise
        except yaml.YAMLError as e:
            print(f"ERROR: El fichero '{self._config_path}' tiene un formato incorrecto: {e}")
            raise

    # --- Propiedades de acceso por sección ---
    @property
    def station(self) -> dict: return self._config.get("station", {})
    @property
    def hardware(self) -> dict: return self._config.get("hardware", {})
    @property
    def resource_mapping(self) -> dict: return self._config.get("resource_mapping", {})
    @property
    def test_thresholds(self) -> dict: return self._config.get("test_thresholds", {})
    @property
    def ui_messages(self) -> dict: return self._config.get("ui_messages", {})
    @property
    def api_config(self) -> dict: return self._config.get("api", {})

    # --- Propiedades de hardware detalladas ---
    @property
    def rs485_config(self) -> dict: return self.hardware.get("rs485", {})
    @property
    def relay_config(self) -> dict: return self.hardware.get("relay_controller", {})
    @property
    def ppk2_config(self) -> dict: return self.hardware.get("power_meters", {}).get("ua_meter_ppk2", {})
    @property
    def ina3221_config(self) -> dict: return self.hardware.get("power_meters", {}).get("active_meter_ina3221", {})

    @property
    def ppk2_source_voltage_mv(self) -> int: return self.ppk2_config.get("source_voltage_mv", 3700)
    @property
    def ppk2_serial_number(self) -> str: return self.ppk2_config.get("serial_number", "UNKNOWN_PPK2")

    @property
    def rs485_port(self) -> str: return self.rs485_config.get("port", "/dev/ttyUSB0")
    @property
    def rs485_baud_rate(self) -> int: return self.rs485_config.get("baud_rate", 115200)

    @property
    def relay_serial_number(self) -> str: return self.relay_config.get("serial_number", None)


    # --- Propiedades de mapeo de recursos detalladas ---
    @property
    def relay_map(self) -> dict: return self.resource_mapping.get("relay_map", {})
    @property
    def ina3221_channel_map(self) -> dict: return self.resource_mapping.get("ina3221_channel_map", {})

    @property
    def relay_num_battery(self) -> int: return self.relay_map.get("connect_battery")
    @property
    def relay_num_vin_power(self) -> int: return self.relay_map.get("apply_vin_power")
    @property
    def relay_num_tamper_1(self) -> int: return self.relay_map.get("connect_tamper_1")
    @property
    def relay_num_tamper_2(self) -> int: return self.relay_map.get("connect_tamper_2")

    @property
    def ina3221_ch_vin_current(self) -> int: return self.ina3221_channel_map.get("vin_current")
    @property
    def ina3221_ch_battery_charge(self) -> int: return self.ina3221_channel_map.get("battery_charge_current")

    # --- Propiedades de umbrales de test detalladas ---
    @property
    def threshold_sleep_current_ua(self) -> float: return self.test_thresholds.get("sleep_current_max_ua")
    @property
    def threshold_vin_current_min_ma(self) -> float: return self.test_thresholds.get("vin_current_min_ma")
    @property
    def threshold_vin_current_max_ma(self) -> float: return self.test_thresholds.get("vin_current_max_ma")
    @property
    def threshold_battery_charge_min_ma(self) -> float: return self.test_thresholds.get("battery_charge_min_ma")
    @property
    def threshold_battery_charge_max_ma(self) -> float: return self.test_thresholds.get("battery_charge_max_ma")

    # --- Propiedades de aplicación y API ---
    @property
    def app_title(self) -> str: return self.station.get("app_title", "JIT Tester")
    @property
    def app_resolution(self) -> str: return self.station.get("app_resolution", "800x600")
    @property
    def station_id(self) -> str: return self.station.get("id", "UNKNOWN_STATION")
    @property
    def api_endpoint(self) -> str: return self.api_config.get("endpoint_url")
    @property
    def api_key(self) -> str: return self.api_config.get("key")