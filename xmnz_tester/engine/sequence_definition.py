TEST_SEQUENCE = [
    'step_connect_battery',
    'step_apply_vin',
    'step_check_initial_status',
    'step_measure_active_power',
    'step_test_tampers',
    'step_test_onboard_relay',
    'step_disconnect_battery',
    'step_simulate_battery', # TODO: ¿Rename?
    'step_disconnect_vin',
    'step_check_board_status',
    'step_set_low_power_mode',
    'step_measure_sleep_current',
    'step_wakeup_from_sleep',
    'step_send_current_result',
    'step_get_barcode',
    'step_modem_send',
]