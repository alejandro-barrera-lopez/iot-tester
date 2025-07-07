# xmnz_tester/config.py

import yaml
from pathlib import Path

# Variable global para almacenar la configuración y evitar lecturas repetidas del fichero.
_config = None

def load_config(config_path: Path = Path("config.yaml")):
    """
    Carga la configuración desde un fichero YAML.

    La configuración se carga solo una vez y se almacena en caché
    para futuras llamadas.

    Returns:
        dict: Un diccionario con toda la configuración.
    """
    global _config
    if _config is None:
        print("Cargando configuración desde", config_path)
        try:
            with open(config_path, 'r') as f:
                _config = yaml.safe_load(f)
        except FileNotFoundError:
            print(f"ERROR: Fichero de configuración no encontrado en '{config_path}'")
            print("Asegúrate de que 'config.yaml' existe en la raíz del proyecto.")
            raise
        except yaml.YAMLError as e:
            print(f"ERROR: El fichero 'config.yaml' tiene un formato incorrecto: {e}")
            raise

    return _config

# Opcional: puedes crear funciones "getter" para un acceso más limpio
def get_hardware_config():
    """Devuelve la sección de configuración de hardware."""
    return load_config().get("hardware_ports", {})

def get_relay_config():
    """Devuelve la configuración específica de los relés."""
    cfg = load_config()
    return {
        "port": cfg.get("hardware_ports", {}).get("relay_controller_port"),
        "num_relays": len(cfg.get("resource_mapping", {}).get("relay_map", {}))
    }