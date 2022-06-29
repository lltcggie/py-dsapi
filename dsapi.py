import json
import os
import re
import time
import urllib.error
import urllib.request
import uuid
from array import array
from base64 import b64encode
from decimal import *
from socket import *

from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA

from define import *

_LOCAL_TARGET_UDP_PORT = 30050
_USER_AGENT = 'RemoApp/8 CFNetwork/1333.0.4 Darwin/21.5.0'
_UUID_FILE_PATH = 'uuid.txt'
_OAUTH_RESULT_PATH = 'oauth.txt'

class dsapi_cloud_setting:
    domain: str = ''
    user_id: str = ''
    user_password: str = ''
    model: str = ''
    client_id: str = ''
    client_secret: str = ''
    rsa_public_key_path: str = ''
    app: str = ''
    target: array = []

class dsapi_cloud:
    setting: dsapi_cloud_setting = None
    access_token: str = None
    refresh_token: str = None
    oauth_json: dict = None
    expires_in: str = None
    ref_id: str = None
    uuid: str = None

    def init(self, setting: dsapi_cloud_setting) -> None:
        if not os.path.isfile(_UUID_FILE_PATH):
            self.uuid = str(uuid.uuid4()).upper()
            with open(_UUID_FILE_PATH, mode='w') as f:
                f.write(self.uuid)

        with open(_UUID_FILE_PATH) as f:
            self.uuid = f.readline()

        self.setting = setting

        self.oauth_json = None
        self.refresh_token = None
        self.expires_in = None

        try:
            with open(_OAUTH_RESULT_PATH) as f:
                oauth_text = ''.join(f.readlines())
                self.oauth_json = json.loads(oauth_text)
                self.expires_in = int(self.oauth_json['expires_in'])
                self.access_token = self.oauth_json['access_token']
                self.refresh_token = self.oauth_json['refresh_token']
        except:
            if os.path.isfile(_OAUTH_RESULT_PATH):
                os.remove(_OAUTH_RESULT_PATH)

        if self.refresh_token is None:
            self._create_token()

        self._refresh_token()

        def get_ref_id(config_json, path_list):
            buildings = config_json['responses'][0]['/dsiot/buildings']['pc']
            for p in buildings:
                if p['name'] != path_list[0]:
                    continue
                zones = p['zones']
                for zone in zones:
                    if zone['name'] != path_list[1]:
                        continue
                    edges = zone['edges']
                    for edge in edges:
                        if edge['api_type'] == 'DSAPI':
                            return edge['ref_id']
            return None

        content = self._request_daikin_cloud('https://{}/dkapp/app_config_all'.format(self.setting.domain))
        config_json = json.loads(content)
        self.ref_id = get_ref_id(config_json, setting.target)

    def set_ventilation_speed(self, speed: DGC_STATUS.VentilationSpeed) -> bool:
        if speed == DGC_STATUS.VentilationSpeed.OFF:
            js = self._create_write_request([
                {'key': DGC_STATUS.VentilationUnknown.KEY, 'value': DGC_STATUS.VentilationUnknown.UNKNOWN}, 
                {'key': DGC_STATUS.VentilationPower.KEY, 'value': DGC_STATUS.VentilationPower.OFF}
            ])
        else:
            js = self._create_write_request([
                {'key': DGC_STATUS.VentilationUnknown.KEY, 'value': DGC_STATUS.VentilationUnknown.UNKNOWN}, 
                {'key': DGC_STATUS.VentilationPower.KEY, 'value': DGC_STATUS.VentilationPower.ON},
                {'key': DGC_STATUS.VentilationSpeed.KEY, 'value': speed}
            ])

        return self._send_write_request(js)

    def _send_write_request(self, js: dict) -> bool:
        encoded_data = json.dumps(js).encode('utf-8')

        try:
            content = self._request_daikin_cloud('https://{}/dsiot/multireq'.format(self.setting.domain), body = encoded_data, method = 'PUT')
            # FIXME: 本当はcontent見て成功したか見たほうがよい
            return True
        except urllib.error.HTTPError as e:
            if e.status == 400: # 他のリモコンから操作された直後だと400で拒否られることがある
                return False
            raise e

    def _create_token(self) -> None:
        pubkey = RSA.importKey(open(self.setting.rsa_public_key_path).read())

        code_data = {
            'id': self.setting.user_id,
            'password': self.setting.user_password,
            'model': self.setting.model,
            'app': self.setting.app,
            'timestamp': str(int(time.time() * 1000)),
        }

        code_encoded_data = json.dumps(code_data).encode('utf-8')

        public_cipher = PKCS1_v1_5.new(pubkey)
        ciphertext = public_cipher.encrypt(code_encoded_data)
        encoded_code = b64encode(ciphertext).decode('utf-8')

        data = {
            'code': encoded_code,
            'client_id': self.setting.client_id,
            'uuid': self.uuid,
            'client_secret': self.setting.client_secret,
            'grant_type': 'authorization_code',
        }

        encoded_data = json.dumps(data).encode('utf-8')

        req = urllib.request.Request(
            'https://{}/premise/dsiot/login'.format(self.setting.domain),
            encoded_data,
            headers = {
                'User-Agent': _USER_AGENT,
                'Content-Type': 'application/json',
            },
        )

        with urllib.request.urlopen(req) as res:
            with open(_OAUTH_RESULT_PATH, mode='w') as f:
                content = res.read().decode('utf-8')
                f.write(content)
                self.oauth_json = json.loads(content)
                self.refresh_token = self.oauth_json['refresh_token']
                self.expires_in = int(self.oauth_json['expires_in'])

    # 必要があればトークンを更新する
    def _refresh_token(self) -> None:
        expires_sec = int(os.path.getmtime(_OAUTH_RESULT_PATH)) + self.expires_in
        current_sec = int(time.time())
        if expires_sec <= current_sec:
            data = {
                'refresh_token': self.refresh_token,
                'grant_type': 'refresh_token',
            }

            encoded_data = json.dumps(data).encode('utf-8')

            req = urllib.request.Request(
                'https://{}/premise/dsiot/token'.format(self.setting.domain),
                encoded_data,
                headers = {
                    'User-Agent': _USER_AGENT,
                    'Content-Type': 'application/json',
                },
            )

            with urllib.request.urlopen(req) as res:
                content = res.read().decode('utf-8')
                content_json = json.loads(content)
                pairs = content_json.items()
                for key, value in pairs:
                    self.oauth_json[key] = value

                with open(_OAUTH_RESULT_PATH, mode='w') as f:
                    text = json.dumps(self.oauth_json)
                    f.write(text)

        self.access_token = self.oauth_json['access_token']

    # 認証付きでダイキンクラウドにリクエストする
    def _request_daikin_cloud(self, url: str, body = None, method: str = None) -> str:
        self._refresh_token()

        headers = {
            'User-Agent': _USER_AGENT,
            'Authorization': 'Bearer ' + self.access_token,
        }
        if body is not None: # bodyはjsonと仮定する
            headers['Content-Type'] = 'application/json'

        req = urllib.request.Request(
            url,
            headers = headers,
            data = body,
            method = method
        )

        with urllib.request.urlopen(req) as res:
            content = res.read().decode('utf-8')
        return content

    @staticmethod
    def _value_to_pv_string(value) -> str:
        if type(value) is int:
            str = '{:X}'.format(value)
            if len(str) % 2 == 1:
                str = '0' + str
            return str
        elif type(value) is str:
            return value
        return None

    @staticmethod
    def _set_pv(parent_pch, keys, value) -> None:
        current_key = keys[0]
        keys.pop(0)
        if len(keys) > 0:
            is_find = False
            for p in parent_pch:
                key = p['pn']
                if key == current_key:
                    is_find = True
                    dsapi_cloud._set_pv(p['pch'], keys, value)
                    break
            if not is_find:
                pch = []
                parent_pch.append({
                    "pn": current_key,
                    "pch": pch
                })
                dsapi_cloud._set_pv(pch, keys, value)
        else:
            is_find = False
            for p in parent_pch:
                key = p['pn']
                if key == current_key:
                    is_find = True
                    parent_pch['pv'] = dsapi_cloud._value_to_pv_string(value)
                    break
            if not is_find:
                parent_pch.append({
                    "pn": current_key,
                    "pv": dsapi_cloud._value_to_pv_string(value)
                })

    def _create_write_request(self, dgc_status_list) -> dict:
        root_key = dgc_status_list[0]['key'].split('.')[0] # pc.pnは1つしか指定できないので1つ目の要素からだけ計算すればOK
        root_pch = []
        for p in dgc_status_list:
            keys = p['key'].split('.')
            keys.pop(0) # rootキーは計算済みかつ全dgc_status_listで共通なのでいらない

            dsapi_cloud._set_pv(root_pch, keys, p['value'])

        return {
            "requests": [
                {
                "op": 3,
                "to": "/dsiot/edges/{}/adr_0100.dgc_status".format(self.ref_id),
                "pc": {
                        "pn": root_key,
                        "pch": root_pch
                    }
                }
            ]
        }

class dsapi_local:
    target_ip = None

    # ステータス
    power: DGC_STATUS.Power.VALUE_TYPE = None
    mode: DGC_STATUS.Mode.VALUE_TYPE = None
    ventilation_power: DGC_STATUS.VentilationPower.VALUE_TYPE = None
    ventilation_speed: DGC_STATUS.VentilationSpeed.VALUE_TYPE = None
    room_temperature: DGC_STATUS.RoomTemperature.VALUE_TYPE = None
    room_humidity: DGC_STATUS.RoomHumidity.VALUE_TYPE = None
    outdoor_temperature: DGC_STATUS.OutdoorTemperature.VALUE_TYPE = None

    def init(self, broadcast_address: str) -> None:
        self.target_ip = self._search_target(broadcast_address)

    # ステータス更新
    def update(self) -> None:
        status_json = self._get_status_json()
        self._update_status_from_json(status_json)

    @staticmethod
    def _search_target(broadcast_address: str) -> str:
        udp_sock = socket(AF_INET, SOCK_DGRAM)
        udp_sock.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
        udp_sock.bind(('', 11119)) # ソースポートは適当

        target_ip = None
        try:
            MAX_TRY_COUNT = 5

            # 1回だと失敗することがあるので何回か繰り返す
            for i in range(MAX_TRY_COUNT):
                try:
                    data = "DAIKIN_UDP/common/basic_info"
                    data = data.encode('utf-8')

                    udp_sock.sendto(data, (broadcast_address, _LOCAL_TARGET_UDP_PORT))

                    udp_sock.settimeout(1.0)
                    data, addr = udp_sock.recvfrom(1024)
                    target_ip = addr[0]
                    # 本当はメッセージを見て本当にエアコンからメッセージが来てるのか調べたほうがよいが今回はネットワーク内にエアコン1台しかないと仮定する
                    #print(data.decode())
                    break
                except Exception as e:
                    if i == MAX_TRY_COUNT - 1: # リトライしても駄目だった
                        raise e
        finally:
            udp_sock.close()

        return target_ip

    def _get_status_json(self) -> dict:
        data = {
            "requests": [
                {
                    "op": 2,
                    "to": "/dsiot/edge/adr_0100.dgc_status?filter=pv,md"
                },
                {
                    "op": 2,
                    "to": "/dsiot/edge/adr_0200.dgc_status?filter=pv,md"
                }
            ]
        }

        encoded_data = json.dumps(data).encode('utf-8')

        req = urllib.request.Request(
            'http://{}/dsiot/multireq'.format(self.target_ip),
            encoded_data,
            headers = {
                'User-Agent': _USER_AGENT,
                'Content-Type': 'application/json',
            },
            method = 'POST',
        )

        status_json = None
        with urllib.request.urlopen(req) as res:
            content = res.read().decode('utf-8')
            status_json = json.loads(content)

        return status_json

    def _update_status_from_json(self, status_json: dict) -> None:
        root = status_json['responses']
        self.power = self._get_DGC_STATUS(root, DGC_STATUS.Power)
        self.mode = self._get_DGC_STATUS(root, DGC_STATUS.Mode)
        self.ventilation_power = self._get_DGC_STATUS(root, DGC_STATUS.VentilationPower)
        self.ventilation_speed = self._get_DGC_STATUS(root, DGC_STATUS.VentilationSpeed)
        self.room_temperature = self._get_DGC_STATUS(root, DGC_STATUS.RoomTemperature)
        self.room_humidity = self._get_DGC_STATUS(root, DGC_STATUS.RoomHumidity)
        self.outdoor_temperature = self._get_DGC_STATUS(root, DGC_STATUS.OutdoorTemperature)

    @staticmethod
    def _get_DGC_STATUS(root, cs) -> None:
        error = None
        for adr in root:
            try:
                _, pv, md = dsapi_local._get_element(adr, cs.KEY)
                if cs.VALUE_TYPE is int:
                    dec = dsapi_local._decode_pv_to_int(pv, md)
                    return dec
                elif cs.VALUE_TYPE is float:
                    dec = dsapi_local._decode_pv(pv, md)
                    return float(dec)
                return cs.VALUE_TYPE(pv)
            except KeyError as e:
                error = e
        raise error

    @staticmethod
    def _get_element(root, key):
        keys = key.split('.')
        current_elm = root
        while len(keys) > 0:
            current_key = keys[0]
            is_find = False
            if 'pc' in current_elm:
                if current_elm['pc']['pn'] == current_key:
                    current_elm = current_elm['pc']
                    keys.pop(0)
                    is_find = True
            elif 'pch' in current_elm:
                for pch in current_elm['pch']:
                    if pch['pn'] == current_key:
                        current_elm = pch
                        keys.pop(0)
                        is_find = True
                        break

            if not is_find:
                raise KeyError(key)

        return current_elm['pt'], current_elm['pv'], current_elm['md']

    @staticmethod
    def _decode_pv_to_int(pv, md) -> int:
        dec = dsapi_local._decode_pv(pv, md)
        quantize = dec.quantize(Decimal('1.'),  rounding = ROUND_DOWN)
        return int(quantize)

    @staticmethod
    def _decode_pv(pv, md) -> Decimal:
        st = md['st']
        str = dsapi_local._convert_endian(pv)
        base = Decimal(int(str, 16))
        step = dsapi_local._decode_step_value(st)
        if step == Decimal(0):
            return base
        mul = base * step
        return mul

    @staticmethod
    def _convert_endian(value) -> str:
        list = re.split('(..)', value)[1::2]
        list.reverse()
        return ''.join(list)

    @staticmethod
    def _decode_step_value(step) -> Decimal:
        if 0 > step or step > 255:
            raise ValueError(step)
        base = Decimal(step & 0x0F)
        step_value_coefficient = dsapi_local._get_step_value_coefficient((step & 0xF0) >> 4)
        return base * step_value_coefficient

    @staticmethod
    def _get_step_value_coefficient(i) -> Decimal:
        if i == 0:
            return Decimal('1.0')
        elif i == 1:
            return Decimal('10.0')
        elif i == 2:
            return Decimal('100.0')
        elif i == 3:
            return Decimal('1000.0')
        elif i == 4:
            return Decimal('1.0E4')
        elif i == 5:
            return Decimal('1.0E5')
        elif i == 6:
            return Decimal('1.0E6')
        elif i == 7:
            return Decimal('1.0E7')
        elif i == 8:
            return Decimal('1.0E-8')
        elif i == 9:
            return Decimal('1.0E-7')
        elif i == 10:
            return Decimal('1.0E-6')
        elif i == 11:
            return Decimal('1.0E-5')
        elif i == 12:
            return Decimal('1.0E-4')
        elif i == 13:
            return Decimal('0.001')
        elif i == 14:
            return Decimal('0.01')
        elif i == 15:
            return Decimal('0.1')
        raise ValueError(i)
