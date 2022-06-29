import sys
from dsapi import *

if True:
    setting = dsapi_cloud_setting()
    setting.domain = 'example.com'
    setting.user_id = 'example@example.com'
    setting.user_password = 'example'
    setting.model = 'example'
    setting.client_id = 'yranusyca5tzrtydee8g9pd8m'
    setting.client_secret = '87czpkn73acgn55int2w39764das323xrs894uiadudc3mcyrka'
    setting.rsa_public_key_path = 'rsa_public_key.pem'
    setting.app = 'AB000000'
    setting.target = ["自宅", "リビング"]

    cloud_controller = dsapi_cloud()
    try:
        cloud_controller.init(setting)
    except:
        print('Failed cloud_controller.init()')
        sys.exit(1)

    MAX_TRY_COUNT = 5
    for i in range(MAX_TRY_COUNT):
        try:
            cloud_controller.set_ventilation_speed(DGC_STATUS.VentilationSpeed.OFF)
            break
        except urllib.error.HTTPError as e:
            if i == MAX_TRY_COUNT - 1: # 何回もリトライしても駄目だったので断念
                print('Failed cloud_controller.set_ventilation_speed(): ' + e.reason)
                sys.exit(1)
            elif e.code == 400: # 他のリモコンから操作された直後だと400で拒否られることがある
                time.sleep(5) # 何秒か待ってリトライ
                continue
        except Exception as e:
            print('Failed lcloud_controller.set_ventilation_speed()')
            sys.exit(1)

if True:
    local_controller = dsapi_local()
    try:
        local_controller.init('192.168.0.255')
    except:
        print('Failed local_controller.init()')
        sys.exit(1)
    try:
        local_controller.update()
    except Exception as e:
        print('Failed local_controller.update_status()')
        sys.exit(1)
    print('power: {}'.format(local_controller.power))
    print('mode: {}'.format(local_controller.mode))
    print('ventilation_power: {}'.format(local_controller.ventilation_power))
    print('ventilation_speed: {}'.format(local_controller.ventilation_speed))
    print('room_temperature: {}'.format(local_controller.room_temperature))
    print('room_humidity: {}'.format(local_controller.room_humidity))
    print('outdoor_temperature: {}'.format(local_controller.outdoor_temperature))
pass
