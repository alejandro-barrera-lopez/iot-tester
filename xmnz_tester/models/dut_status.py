from dataclasses import dataclass, field
from typing import Dict

@dataclass
class DutStatus:
    """Representa el estado del DUT parseado desde la respuesta JSON."""
    power_source: str = "UNKNOWN"
    vin_voltage_v: float = 0.0
    battery_voltage_v: float = 0.0
    onboard_relay_state: str = "UNKNOWN"
    temperature_c: float = 0.0
    humidity_rh: float = 0.0
    tamper_states: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict) -> "DutStatus":
        """Crea una instancia de DutStatus desde un diccionario."""
        return cls(
            power_source=data.get("power_source", "ERROR"),
            vin_voltage_v=data.get("vin_voltage_v", 0.0),
            battery_voltage_v=data.get("battery_voltage_v", 0.0),
            onboard_relay_state=data.get("onboard_relay_state", "ERROR"),
            temperature_c=data.get("temperature_c", 0.0),
            humidity_rh=data.get("humidity_rh", 0.0),
            tamper_states=data.get("tamper_states", {})
        )