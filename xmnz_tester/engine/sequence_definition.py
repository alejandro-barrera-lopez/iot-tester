TEST_SEQUENCE = [
    'test_step_connect_battery',
    'test_step_apply_vin',
    'test_step_check_initial_status',
    'test_step_measure_active_power',
    'test_step_test_tampers',
    'test_step_test_onboard_relay',
    'test_step_disconnect_battery',
    'test_step_simulate_battery', # TODO: ¿Rename?
    'test_step_disconnect_vin',
    'test_step_check_board_status',
    'test_step_set_low_power_mode',
    'test_step_measure_sleep_current',
    'test_step_wakeup_from_sleep',
    'test_step_send_current_result',
    'test_step_get_barcode',
    'test_step_modem_send',
]