import asyncio
import datetime
import json
import logging
import os
import threading
import urllib.request

import paho.mqtt.client as mqtt
import jwt


logger = logging.getLogger(__name__)

GOOGLE_PKI_ROOTS = 'https://pki.google.com/roots.pem'
GOOGLE_MQTT_BRIDGE_HOST = 'mqtt.googleapis.com'
GOOGLE_MQTT_BRIDGE_PORT = 8883


def error_str(rc):
    return f'{rc}: {mqtt.error_string(rc)}'


def load_private_key(config):
    if 'private_key' in config:
        return config['private_key']
    else:
        with open(config['private_key_path']) as f:
            return f.read()


def load_ca_certs(ca_certs_path):
    if not os.path.exists(ca_certs_path):
        with urllib.request.urlopen(GOOGLE_PKI_ROOTS) as u:
            with open(ca_certs_path, 'w+') as f:
                data = u.read().decode('utf-8')
                f.write(data)

    return ca_certs_path


def create_jwt(project_id, private_key):
    token = {
        'iat': datetime.datetime.utcnow(),
        'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=60),
        'aud': project_id,
    }
    return jwt.encode(token, private_key, algorithm='RS256')


class Connection:
    @staticmethod
    def from_config(config):
        iot = config['iotcore']

        return Connection(
            iot['region'], iot['project_id'],
            iot['registry_id'], iot['device_id'],
            load_private_key(iot),
            load_ca_certs(iot['ca_certs_path']))

    def __init__(self, region, project_id, registry_id, device_id,
                 private_key, ca_certs_path, on_message=None):
        self.region = region
        self.project_id = project_id
        self.registry_id = registry_id
        self.device_id = device_id
        self.private_key = private_key
        self.ca_certs_path = ca_certs_path
        self.on_message_callback = on_message

        self.connected = False
        self.connect_event = threading.Event()
        self._message = None

    def connect(self):
        self._client = mqtt.Client(client_id=self.client_id)
        self._client.tls_set(ca_certs=self.ca_certs_path)

        self._client.on_connect = self.on_connect
        self._client.on_disconnect = self.on_disconnect
        self._client.on_subscribe = self.on_subscribe
        self._client.on_message = self.on_message

        self._client.username_pw_set(
            username='unused',
            password=create_jwt(self.project_id, self.private_key))
        self._client.connect(GOOGLE_MQTT_BRIDGE_HOST, GOOGLE_MQTT_BRIDGE_PORT)
        self._client.loop_start()

    @property
    def config_topic(self):
        return f'/devices/{self.device_id}/config'

    @property
    def events_topic(self):
        return f'/devices/{self.device_id}/events'

    @property
    def client_id(self):
        return f'projects/{self.project_id}/locations/{self.region}' + \
            f'/registries/{self.registry_id}/devices/{self.device_id}'

    def on_connect(self, _client, _userdata, _flags, rc):
        self._client.subscribe(self.config_topic, qos=1)
        self.connected = True
        self.connect_event.set()
        logger.info('connected')

    def on_disconnect(self, _client, _userdata, rc):
        logger.info('reconnecting')
        self.connected = False
        self.connect_event.clear()
        self._client.loop_stop()
        self.connect()

    def on_subscribe(self, _client, _userdata, _mid, granted_qos):
        if granted_qos[0] == 128:
            raise RuntimeError('Subscription failed')

    def on_message(self, _client, _userdata, message):
        logger.info(f'on_message event received')
        payload = message.payload.decode('utf8')
        if payload:
            logger.debug(f'on_message payload {payload}')
            payload = json.loads(payload)
            if self.on_message_callback:
                # TODO: raise on error
                self.on_message_callback(payload)

    @property
    def message(self):
        return self._message

    def publish(self, message):
        self.wait_for_connection()
        return self._client.publish(
            self.events_topic, json.dumps(message), qos=1
        )

    def wait_for_connection(self):
        result = self.connect_event.wait(5.0)
        if not result:
            raise RuntimeError('Could not connect to MQTT bridge')


class IOTCoreClient:
    def __init__(self, client):
        self._client = client

    def start(self):
        self._client.connect()
        self._client.wait_for_connection()

    def send(self, message):
        return self._client.publish(message)

    async def run_send(self, loop, stop, values):
        while not stop.is_set():
            values_task = loop.create_task(values.get())
            stop_task = loop.create_task(stop.wait())

            complete, pending = await asyncio.wait(
                [values_task, stop_task],
                loop=loop, return_when=asyncio.FIRST_COMPLETED)
            task = complete.pop()

            if task == values_task:
                self.send(values_task.result())
                stop_task.cancel()
            else:
                values_task.cancel()

    def setup_config_handler(self, target):
        def on_message(message):
            ok, errors = target.update_config(message)
            if not ok:
                logger.error(f'config update errors {errors}')
            return ok

        self._client.on_message_callback = on_message


def load_iotcore(loop, config):
    conn = Connection.from_config(config)

    return IOTCoreClient(conn)
