from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class DutInfo:
    """Representa la información estática y de identificación del DUT."""
    device_serial: str = "UNKNOWN"
    imei: str = "UNKNOWN"
    iccid: str = "UNKNOWN"
    temp_sensor_id: int = 0
    hardware_ok: Dict[str, bool] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DutInfo":
        """Crea una instancia de DutInfo desde un diccionario."""
        return cls(
            device_serial=data.get("device_serial", "ERROR"),
            imei=data.get("imei", "ERROR"),
            iccid=data.get("iccid", "ERROR"),
            temp_sensor_id=data.get("temp_sensor_id", -1),
            hardware_ok=data.get("hardware_ok", {})
        )