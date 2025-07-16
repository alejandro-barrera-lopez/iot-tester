TEST_SEQUENCE = [
    {'key': 'test_step_connect_battery'},
    {'key': 'test_step_apply_vin'},
    {'key': 'test_step_check_initial_status'},
    {'key': 'test_step_measure_active_power'},
    {'key': 'test_step_test_tampers'},
    {'key': 'test_step_test_onboard_relay'},
    {'key': 'test_step_disconnect_battery'},
    {'key': 'test_step_simulate_battery'},  # TODO: ¿Rename?
    {'key': 'test_step_disconnect_vin'},
    {'key': 'test_step_check_board_status', 'args': ["STORED"]},
    {'key': 'test_step_set_low_power_mode'},
    {'key': 'test_step_measure_sleep_current'},
    {'key': 'test_step_wakeup_from_sleep'},
    {'key': 'test_step_send_current_result'},
    {'key': 'test_step_get_barcode'},
    {'key': 'test_step_modem_send'}
]