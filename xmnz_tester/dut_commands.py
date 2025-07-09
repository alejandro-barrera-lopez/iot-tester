class DutCommands:
    """
    Define todos los comandos RS485 aceptados por el firmware del DUT.
    """
    # Comandos para obtener información
    GET_STATUS = "GETSTATUS"
    GET_SERIAL = "GETSERIAL"
    GET_IMEI = "GETIMEI"
    GET_ICCID = "GETICCID"

    # Comandos de acción
    SET_LOW_POWER = "SLEEP"
    WAKE_UP = "WAKEUP"
    SET_LAST_CURRENT = "SET_CURRENT"  # Ejemplo: SET_CURRENT=5.2
    SER_SERIAL = "SETSERIAL"  # Ejemplo: SERIAL=25070001
    FORCE_MODEM_SEND = "SENDJSON"

    # Comandos para controlar el relé de la placa
    BOARD_RELAY_ON = "RELAY_ON"
    BOARD_RELAY_OFF = "RELAY_OFF"