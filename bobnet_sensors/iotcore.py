import json
import datetime
import os
import threading
import urllib.request

import paho.mqtt.client as mqtt
import jwt


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


def create_jwt(project_id, private_key):
    token = {
        'iat': datetime.datetime.utcnow(),
        'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=60),
        'aud': project_id,
    }
    return jwt.encode(token, private_key, algorithm='RS256')


# TODO move as much out of the class as possible

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
                 private_key, ca_certs_path):
        self.region = region
        self.project_id = project_id
        self.registry_id = registry_id
        self.device_id = device_id
        self.private_key = private_key
        self.ca_certs_path = ca_certs_path

        self.connected = False
        self.connect_event = threading.Event()
        self.has_message_event = threading.Event()
        self.new_message_event = threading.Event()
        self._client = self._setup_mqtt()

    def connect(self):
        self._client.connect(GOOGLE_MQTT_BRIDGE_HOST, GOOGLE_MQTT_BRIDGE_PORT)
        self._client.loop_start()

        self._wait_for_connection()

        self._client.subscribe(self.config_topic, qos=1)

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

    def _setup_mqtt(self):
        client = mqtt.Client(client_id=self.client_id)
        client.username_pw_set(
            username='unused',
            password=create_jwt(self.project_id, self.private_key))
        client.tls_set(ca_certs=self.ca_certs_path)

        client.on_connect = self.on_connect
        client.on_disconnect = self.on_disconnect
        client.on_subscribe = self.on_subscribe
        client.on_message = self.on_message

        return client

    def on_connect(self, _client, _userdata, _flags, rc):
        # TODO: logging
        self.connected = True
        self.connect_event.set()

    def on_disconnect(self, _client, _userdata, rc):
        self.connected = False
        # TODO: logging
        self.connect_event.clear()

    def on_subscribe(self, _client, _userdata, _mid, granted_qos):
        print('on_subscribe')
        if granted_qos[0] == 128:
            raise RuntimeError('Subscription failed')

    def on_message(self, _client, _userdata, message):
        # TODO: logging
        payload = message.payload.decode('utf8')
        if payload:
            payload = json.loads(payload)
            self._message = payload  # only the most recent is relevant
            self.has_message_event.set()
            self.new_message_event.set()

    @property
    def message(self):
        self.has_message_event.wait()
        return self._message

    def publish(self, message):
        return self._client.publish(
            self.events_topic, json.dumps(message), qos=1
        )

    def _wait_for_connection(self):
        if not self.connect_event.wait(timeout=5):
            raise RuntimeError('Could not connect to MQTT bridge')


class IOTCoreClient:
    def __init__(self, client):
        self._client = client

    def send(self, message):
        return self._client.publish(message)

    @property
    def has_new_config(self):
        return self._client.new_message_event.is_set()

    @property
    def config(self):
        self._client.new_message_event.clear()
        return self._client.message


def load_iotcore(config):
    conn = Connection.from_config(config)
    conn.connect()

    return IOTCoreClient(conn)
