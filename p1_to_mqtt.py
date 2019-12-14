#!/usr/bin/env python3

import serial
import paho.mqtt.client as paho_mqtt
import re
import time;

with open('config.json') as f:
    config = json.load(f)


MQTT_USERNAME = config['mqtt']['username']
MQTT_PASSWORD = config['mqtt']['password']
MQTT_HOST = config['mqtt']['host']
MQTT_PORT = config['mqtt']['port']
MQTT_CLIENT = config['mqtt']['client']


mqtt_connected = False

def on_publish(client, userdata, result):
    #print("published {}".format(result))
    pass

mqtt = paho_mqtt.Client(MQTT_CLIENT)
mqtt.username_pw_set(MQTT_USERNAME, password=MQTT_PASSWORD)
mqtt.on_publish = on_publish
mqtt.connect(MQTT_HOST, MQTT_PORT)
mqtt_connected = True

# DSMR 4.0/4.2 > 115200 8N1:
p1 = serial.Serial()
p1.baudrate = 115200
p1.bytesize = serial.EIGHTBITS
p1.parity = serial.PARITY_NONE
p1.stopbits = serial.STOPBITS_ONE
p1.xonxoff = 0
p1.rtscts = 0
p1.timeout = 12
p1.port = "/dev/ttyUSB0"

pattern = re.compile('([0-9]\-[0-9])\:([0-9]+\.[0-9]+\.[0-9]+)\(([^\*]*)\*?([^\)]*)\)')

class P1Message:
    def __init__(self):
        self.header = ''
        self.data = []
        self.checksum = ''

tag_map = {
    '1-3:0.2.8'  : 'Version',
    '0-0:1.0.0'  : 'Timestamp',
    '0-0:96.1.1' : 'EquipmentIdentifier',
    '1-0:1.8.1'  : 'Electricity/In/Tarrif1/MeterReading',
    '1-0:1.8.2'  : 'Electricity/In/Tarrif2/MeterReading',
    '1-0:2.8.1'  : 'Electricity/Out/Tarrif1/MeterReading',
    '1-0:2.8.2'  : 'Electricity/Out/Tarrif2/MeterReading',
    '0-0:96.14.0': 'Electricity/TarrifIndicator',
    '1-0:1.7.0'  : 'Electricity/In/Power',
    '1-0:2.7.0'  : 'Electricity/Out/Power',
    '0-0:96.7.21': 'Electricity/PowerFailures',
    '0-0:96.7.9' : 'Electricity/LongPowerFailures',
    '1-0:99.97.0': 'Electricity/PowerFailureEventLog',
    '1-0:32.32.0': 'Electricity/L1/VoltageSags',
    '1-0:52.32.0': 'Electricity/L2/VoltageSags',
    '1-0:72.32.0': 'Electricity/L3/VoltageSags',
    '1-0:32.36.0': 'Electricity/L1/VoltageSwells',
    '1-0:52.36.0': 'Electricity/L2/VoltageSwells',
    '1-0:72.36.0': 'Electricity/L3/VoltageSwells',
    '0-0:96.13.0': 'TextMessage',
    '1-0:32.7.0' : 'Electricity/L1/Voltage',
    '1-0:52.7.0' : 'Electricity/L2/Voltage',
    '1-0:72.7.0' : 'Electricity/L3/Voltage',
    '1-0:31.7.0' : 'Electricity/L1/Current',
    '1-0:51.7.0' : 'Electricity/L2/Current',
    '1-0:71.7.0' : 'Electricity/L3/Current',
    '1-0:21.7.0' : 'Electricity/L1/Power',
    '1-0:41.7.0' : 'Electricity/L2/Power',
    '1-0:61.7.0' : 'Electricity/L3/Power',
    '1-0:22.7.0' : 'Electricity/L1/PowerNegative',
    '1-0:42.7.0' : 'Electricity/L2/PowerNegative',
    '1-0:62.7.0' : 'Electricity/L3/PowerNegative',
    '0-n:24.1.0' : 'Gas/DeviceType',
    '0-n:96.1.0' : 'Gas/EquipmentIdentifier',
    '0-n:24.2.1' : 'Gas/CaptureTime',
    '0-n:24.2.1' : 'Gas/MeterReading',
    '0-n:24.1.0' : 'Gas/DeviceType',
    '0-n:96.1.0' : 'Thermal/DeviceType',
    '0-n:24.2.1' : 'Thermal/5min/Timestamp',
    '0-n:24.2.1' : 'Thermal/5min/MeterReading',
    '0-n:24.1.0' : 'Water/DeviceType',
    '0-n:96.1.0' : 'Water/EquipmentIdentifier',
    '0-n:24.2.1' : 'Water/5min/CaptureTime',
    '0-n:24.2.1' : 'Water/5min/MeterReading',
    '0-n:24.1.0' : 'DeviceType',
    '0-n:96.1.0' : 'EquipmentIdentifier',
    '0-n:24.2.1' : '5min/CaptureTime',
    '0-n:24.2.1' : '5min/MeterReading',
}
minimum_send = 60000
maximum_send = 1000

timestamp_map = {}
value_map = {}

def now():
    ts = time.time()
    ts = ts * 1000
    ts = int(ts)
    return ts

def mqtt_send(tag, value):
    timestamp_map[tag] = now()
    value_map[tag] = value
    if not tag in tag_map:
        return
    if tag in tag_map:
        tag = tag_map[tag]
    tag = 'P1/' + tag
    print('pub "{}" "{}"'.format(tag, value))
    mqtt.publish(tag, value)

def mqtt_send_conditional(tag, value):
    if not tag in timestamp_map:
        #print('Tag not in timestamp map {} {}'.format(tag, value))
        return mqtt_send(tag, value)
    if not tag in value_map:
        #print('Tag not in value map {} {}'.format(tag, value))
        return mqtt_send(tag, value)
    #if timestamp_map[tag] + maximum_send > now():
    #    return
    if now() > timestamp_map[tag] + minimum_send:
        #print('Time limit exceeded {} {}'.format(tag, value))
        return mqtt_send(tag, value)
    if value_map[tag] == value:
        #print('Value did not change {} {} {}'.format(tag, value_map[tag], value))
        return
    return mqtt_send(tag, value)

def process_line(line):
    match = pattern.match(line)
    if not match:
        #print('Line does not match regex {}'.format(line))
        return
    tag = match.group(1) + ':' + match.group(2)
    value = match.group(3)
    try:
        value = float(value)
    except:
        pass
    unit = match.group(4)
    #print('process_line {} {} {}'.format(tag, value, unit))
    #if tag in tag_map:
    mqtt_send_conditional(tag, value)

def process_message(message):
    print('process_message {}'.format(len(message.data)))
    for line in message.data:
        process_line(line)

def read_line():
    line = p1.readline()
    line = line.decode('ascii').strip()
    #print(line)
    return line

def read_message():
    line = read_line()
    if line and not line[0] == '/':
        raise Exception('No header found {}'.format(line))
    message = P1Message()
    message.header = line
    line = read_line()
    line = read_line()
    while line[0] != '!':
        message.data.append(line)
        line = read_line()
    message.checksum = line[1:]
    return message

while True:
    try:
        if not p1.is_open:
            p1.open()
        if not mqtt_connected:
            mqtt.reconnect()
            mqtt_connected = True
        #process_line(read_line())
        process_message(read_message())
    except Exception as e:
        print(e)
        p1.close()
        mqtt.disconnect()
        mqtt_connected = False
