class DGC_STATUS:
    class Power:
        KEY = 'dgc_status.e_1002.e_A002.p_01'
        VALUE_TYPE = int

        OFF = 0
        ON = 1

    class VentilationUnknown:
        KEY = 'dgc_status.e_1002.e_3003.p_2D'
        VALUE_TYPE = int

        UNKNOWN = 2

    class VentilationSpeed:
        KEY = 'dgc_status.e_1002.e_3001.p_1C'
        VALUE_TYPE = int

        OFF = 0
        HIGH = 1
        AUTO = 2

    class VentilationPower:
        KEY = 'dgc_status.e_1002.e_3001.p_36'
        VALUE_TYPE = int

        OFF = 0
        ON = 1

    class RoomTemperature:
        KEY = 'dgc_status.e_1002.e_A00B.p_01'
        VALUE_TYPE = int

    class RoomHumidity:
        KEY = 'dgc_status.e_1002.e_A00B.p_02'
        VALUE_TYPE = int

    class OutdoorTemperature:
        KEY = 'dgc_status.e_1003.e_A00D.p_01'
        VALUE_TYPE = int

    class Mode:
        KEY = 'dgc_status.e_1002.e_3001.p_01'
        VALUE_TYPE = int

        HEATING = 1
        COOLING = 2
        AUTO = 3
        DEHUMIDIFY = 5
        HUMIDIFY = 8
