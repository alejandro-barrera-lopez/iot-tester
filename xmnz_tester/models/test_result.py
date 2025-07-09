from dataclasses import dataclass, field
from typing import Any, Dict, List
import datetime

@dataclass
class TestStepResult:
    """Representa el resultado de un único paso del test."""
    step_name: str
    status: str  # "PASS", "FAIL", "INFO"
    message: str
    # Datos específicos como mediciones, umbrales, etc.
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestResult:
    """Representa el resultado completo de una ejecución de test para un DUT."""
    station_id: str
    serial_number: str = "NOT_READ"
    overall_status: str = "PASS"
    start_time: datetime.datetime = field(default_factory=datetime.datetime.now)
    end_time: datetime.datetime | None = None
    steps: List[TestStepResult] = field(default_factory=list)

    def add_step(self, step: TestStepResult):
        """Añade un paso al resultado y actualiza el estado general."""
        self.steps.append(step)
        if step.status == "FAIL":
            self.overall_status = "FAIL"

    def finalize(self):
        """Marca el test como finalizado, estableciendo la hora de fin."""
        self.end_time = datetime.datetime.now()

    def to_dict(self) -> dict:
        """Convierte el objeto de resultado en un diccionario para enviarlo como JSON."""
        return {
            "station_id": self.station_id,
            "serial_number": self.serial_number,
            "overall_status": self.overall_status,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "steps": [step.__dict__ for step in self.steps]
        }