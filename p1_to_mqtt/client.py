#!/usr/bin/env python3

import json
import logging
import paho.mqtt.client as paho_mqtt
import pytz
import time

import datetime

from p1_to_mqtt.p1 import Reader, Processor, P1Exception


default_config = {
    "mqtt":{
        "username":"<MQTT_USERNAME>",
        "password":"<MQTT_PASSWORD>",
        "host": "mqtt.lan",
        "port": 1883,
        "client": "p1",
        "topic": "p1",
    },
    "p1": {
        "serial":{
          "dev": "/dev/ttyUSB0",
        },
    },
    "timezone":"Europe/Amsterdam"
}

def now():
    return datetime.datetime.now()

def merge(destination, source):
    for key, value in source.items():
        if isinstance(value, dict):
            node = destination.setdefault(key, {})
            merge(node, value)
        else:
            destination[key] = value
    return destination


class Client():

    mqtt_client = None
    is_connected = False
    config = {}

    def __init__(self, config):
        self.config = merge(default_config, config)
        self.timezone = pytz.timezone(config['timezone'])
        if 'file' in config['p1']:
            self.p1_reader = self.init_p1_file(config['p1']['file'])
        else:
            self.p1_reader = self.init_p1_serial(config['p1']['serial'])
        self.p1_processor = Processor(self.p1_reader, self.config)
        self.mqtt_client = self.init_mqtt_client(config['mqtt'])

    def init_p1_file(self, config):
        return open(config['name'], 'r')

    def init_p1_serial(self, config):
        return Reader(config)

    def init_mqtt_client(self, config):
        self.topic = config['topic']
        client = paho_mqtt.Client(config['client'])
        client.on_publish = self.on_publish
        client.on_connect = self.on_connect
        client.on_disconnect = self.on_disconnect
        client.username_pw_set(config['username'], password=config['password'])
        client.will_set('{}/online'.format(self.topic), "false")
        self.mqtt_client = client
        return client

    def connect(self, config):
        self.mqtt_client.connect(config['host'], config['port'])
        self.mqtt_client.loop_start()
 
    def on_connect(self, client, userdata, flags, rc):
        if (rc == 0):
            self.is_connected = True
            logging.error('Connected to mqtt server')
            client.publish('{}/online'.format(self.topic), 'true')
        else:
            logging.error('Could not connect to mqtt server, result code {}'.format(rc))

    def on_disconnect(self, client, userdata, rc):
        self.is_connected = False
        logging.error('Disconnected to mqtt server')

    def on_publish(self, client, userdata, result):
        logging.info('published {}'.format(result))

    def get_client_data(self):
        return {
            'datetime': now().astimezone().isoformat()
        }

    def get_data(self):
        p1_data = self.p1_processor.json()
        client_data = self.get_client_data()
        return {
            'client': client_data,
            'p1': p1_data
        }

    def cycle(self):
        self.mqtt_client.publish(self.topic, json.dumps(self.get_data()))

    def run(self):
        logging.info('loop started')
        while True:
            try:
                if not self.is_connected:
                    self.connect(self.config['mqtt'])
                self.cycle()
            except P1Exception as exception:
                logging.exception(exception)
                time.sleep(.1)
            except Exception as exception:
                logging.exception(exception)
                time.sleep(10)
