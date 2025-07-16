class DutCommands:
    """
    Define todos los comandos RS485 aceptados por el firmware del DUT.
    """
    # Comandos para obtener información
    GET_STATUS = "status" # STATUS -> STATUS=2 (1=INIT, 2=STORED, 3=PLUGGED, 4=MOVING)    (systemData.state)
    GET_DEVICE_DATA = "getdevicedata"
    GET_SERIAL = "getserial" # GETSERIAL -> SERIAL=25070001
    # GET_IMEI = "GETIMEI" # GETIMEI -> IMEI=123456789012345
    # GET_ICCID = "GETICCID" # GETICCID -> ICCID=89014103211118510720
    # GET_TAMPER_STATUS = "GETTAMPERSTATUS" # GETTAMPERSTATUS -> TAMPER=0 (0=OK, 1=TAMPER1, 2=TAMPER2, 3=TAMPER1+TAMPER2)

    # Comandos de acción
    PING_BOARD = "ping" # PING -> OK (para comprobar conexión)
    RESET = "RESET" # RESET -> OK (para reiniciar el dispositivo)
    SET_LOW_POWER = "setlowpower" # SLEEP=30 (30 segundos de bajo consumo) -> OK, ERROR
    # WAKE_UP = "WAKEUP" # WAKEUP -> OK (para despertar del modo de bajo consumo), ERROR
    SET_LAST_CURRENT = "setmeascurrents" # SET_CURRENT=5.2 -> OK, ERROR
    SET_SERIAL = "setserial"  # SERIAL=25070001 -> OK en caso de éxito, ERROR en caso de fallo
    FORCE_MODEM_SEND = "senddata" # SENDJSON -> OK (para forzar el envío de datos al servidor), ERROR
    # TODO: En send, primero una confirmación de que se ha recibido el comando, y luego un ACK cuando se envían los datos al servidor?

    # Comandos para controlar el relé de la placa
    BOARD_RELAY_ON = "relay on"
    BOARD_RELAY_OFF = "relay off"