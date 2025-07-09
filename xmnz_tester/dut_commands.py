class DutCommands:
    """
    Define todos los comandos RS485 aceptados por el firmware del DUT.
    """
    # Comandos para obtener información
    GET_STATUS = "GETSTATUS" # GETSTATUS -> STATUS=2 (1=INIT, 2=STORED, 3=PLUGGED, 4=MOVING)    (systemData.state)
    GET_SERIAL = "GETSERIAL" # GETSERIAL -> SERIAL=25070001
    GET_IMEI = "GETIMEI" # GETIMEI -> IMEI=123456789012345
    GET_ICCID = "GETICCID" # GETICCID -> ICCID=89014103211118510720
    GET_TAMPER_STATUS = "GETTAMPERSTATUS" # GETTAMPERSTATUS -> TAMPER=0 (0=OK, 1=TAMPER1, 2=TAMPER2, 3=TAMPER1+TAMPER2)

    # Comandos de acción
    PING_BOARD = "PING" # PING -> OK (para comprobar conexión)
    SET_LOW_POWER = "SLEEP" # SLEEP=30 (30 segundos de bajo consumo) -> OK, ERROR
    WAKE_UP = "WAKEUP" # WAKEUP -> OK (para despertar del modo de bajo consumo), ERROR
    SET_LAST_CURRENT = "SET_CURRENT" # SET_CURRENT=5.2 -> OK, ERROR
    SET_SERIAL = "SETSERIAL"  # SERIAL=25070001 -> OK en caso de éxito, ERROR en caso de fallo
    FORCE_MODEM_SEND = "SENDJSON" # SENDJSON -> OK (para forzar el envío de datos al servidor), ERROR
    # TODO: En send, primero una confirmación de que se ha recibido el comando, y luego un ACK cuando se envían los datos al servidor?

    # Comandos para controlar el relé de la placa
    BOARD_RELAY_ON = "RELAY_ON"
    BOARD_RELAY_OFF = "RELAY_OFF"