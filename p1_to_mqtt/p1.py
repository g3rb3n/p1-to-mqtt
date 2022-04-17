import json
import logging
import pytz
import re
import serial
import time

from datetime import datetime

class Message:
    def __init__(self):
        self.header = ''
        self.data = []
        self.checksum = ''

    def __str__(self):
        s = ''
        s += 'header = {}'.format(self.header) + '\n'
        for entry in self.data:
            s += entry + '\n'#'{}:{}*{}'.format(entry['key'], entry['value'], entry['unit'])
        return s

class Reader():
    # DSMR 4.0/4.2 > 115200 8N1:

    def __init__(self, config):
        p1 = serial.Serial()
        p1.baudrate = 115200
        p1.bytesize = serial.EIGHTBITS
        p1.parity = serial.PARITY_NONE
        p1.stopbits = serial.STOPBITS_ONE
        p1.xonxoff = 0
        p1.rtscts = 0
        p1.timeout = 12
        p1.port = config['dev']
        self.p1 = p1

    def readline(self):
        if not self.p1.is_open:
            logging.info('p1 serial closed, open p1 serial')
            self.p1.open()
        line = self.p1.readline()
        line = line.decode('ascii').strip()
        return line

class Processor():
    tag_value_pattern = re.compile(r'([^\(]+)(.*)$')
    int_pattern = re.compile(r'\(([0-9]+)\)$')
    timestamp_pattern = re.compile(r'\(([0-9]+)([SW])\)$')
    float_unit_pattern = re.compile(r'\(([0-9\.]+)\*([a-zA-Z]+)\)$')

    p1_timestamp_format='%y%m%d%H%M%S'

    tag_map = {
        '0-0:1.0.0'  : 'Timestamp',
        '0-0:96.1.1' : 'EquipmentIdentifier',
        '0-0:96.7.9' : 'Electricity/LongPowerFailures',
        '0-0:96.7.21': 'Electricity/PowerFailures',
        '0-0:96.13.0': 'TextMessage',
        '0-0:96.14.0': 'Electricity/TarrifIndicator',
        '1-0:1.7.0'  : 'Electricity/In/Power',
        '1-0:1.8.1'  : 'Electricity/In/MeterReading/Tarrif1',
        '1-0:1.8.2'  : 'Electricity/In/MeterReading/Tarrif2',
        '1-0:2.7.0'  : 'Electricity/Out/Power',
        '1-0:2.8.1'  : 'Electricity/Out/MeterReading/Tarrif1',
        '1-0:2.8.2'  : 'Electricity/Out/MeterReading/Tarrif2',
        '1-0:32.32.0': 'Electricity/L1/VoltageSags',
        '1-0:32.36.0': 'Electricity/L1/VoltageSwells',
        '1-0:52.32.0': 'Electricity/L2/VoltageSags',
        '1-0:52.36.0': 'Electricity/L2/VoltageSwells',
        '1-0:72.32.0': 'Electricity/L3/VoltageSags',
        '1-0:72.36.0': 'Electricity/L3/VoltageSwells',
        '1-0:99.97.0': 'Electricity/PowerFailureEventLog',
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
        '1-3:0.2.8'  : 'Version',
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

    def __init__(self, reader, config):
        self.reader = reader
        self.timezone = pytz.timezone(config['timezone'])

    def translate_tags(self, map):
        all_tags = [tag for tag in map]
        tags = [tag for tag in map if tag in self.tag_map]
        not_found = [tag for tag in map if tag not in self.tag_map]
        for tag in not_found:
            logging.warn('tag {} not found in tag map'.format(tag))
        return { self.tag_map[tag]: map[tag] for tag in tags }

    def filter_tags(self, map):
        not_found = [tag for tag in map if tag not in topics]
        for tag in not_found:
            logging.error('tag {} not found in topics'.format(tag))
        return { tag: map[tag] for tag in map if tag in topics }

    def split_line_tag_value(self, line):
        match = self.tag_value_pattern.match(line)
        if not match:
            logging.error('Line does not match regex {}'.format(line))
            return
        tag = match.group(1)
        value = match.group(2)
        return (tag, value)

    def lines_to_map(self, data):
        map = {}
        for line in data:
            (tag, value) = self.split_line_tag_value(line)
            map[tag] = value
        return map;

    def pairwise(self, t):
        it = iter(t)
        return zip(it,it)

    def parse_event_entry(self, timestamp, duration):
        duration_parts = duration.split('*')
        return {
            'timestamp': timestamp,
            'datetime': self.timestamp_to_iso8601(timestamp),
            'duration': {
                'value': int(duration_parts[0]),
                'unit': duration_parts[1],
            }
        }

    def parse_event_log(self, tag, value):
        parts = value[1:-1].split(')(');
        event_parts = parts[2:]
        events = [self.parse_event_entry(timestamp, duration) for timestamp, duration in self.pairwise(event_parts)]
        return {
            'number':int(parts[0]),
            'tag': parts[1],
            'events': events
        }

    def timestamp_to_iso8601(self, timestamp):
        dt = datetime.strptime(timestamp[:-1], self.p1_timestamp_format)
        dt = self.timezone.localize(dt)
        return dt.isoformat()

    def parse_value(self, tag, value):
        if tag == "Electricity/PowerFailureEventLog":
            return self.parse_event_log(tag, value)
        if tag == "TextMessage":
            return value[1:-1]
        match = self.timestamp_pattern.match(value)
        if match:
            return {
                'timestamp': value[1:-1],
                'datetime': self.timestamp_to_iso8601(value[1:-1]),
            }
        match = self.int_pattern.match(value)
        if match:
            return int(match.group(1))
        match = self.float_unit_pattern.match(value)
        if match:
            return {
                'value':float(match.group(1)),
                'unit': match.group(2)
            }
        raise Exception('No patterns for {} `{}`'.format(value))

    def parse_values(self, data):
        ret = {}
        for tag, value in data.items():
            try:
                ret[tag] = self.parse_value(tag, value)
            except Exception as exception:
                logging.error('Could not parse tag {} value {}: {}'.format(tag, value, exception))
        return ret;

    def tag_to_dict(self, d, tag, value):
        parts = tag.split('/')
        _d = d
        for part in parts[:-1]:
            if not part in d:
                d[part] = {}
            d = d[part]
        d[parts[-1]] = json.loads(json.dumps(value))
        logging.debug('{} {}'.format(tag,d[parts[-1]]))

    def tags_to_dict(self, map):
        data = {}
        for tag,value in map.items():
            self.tag_to_dict(data, tag, value)
        return data

    def readline(self):
        line = self.reader.readline().strip()
        logging.debug('read "{}"'.format(line))
        return line

    def first_not_empty_line(self):
        line = ''
        while line == '':
            line = self.readline()
        return line

    def read_message(self):
        logging.info('read message')
        message = {
            'data': []
        }

        line = self.first_not_empty_line()
        if not line[0] == '/':
            raise Exception('No header found `{}`'.format(line))
        message['header'] = line

        line = self.first_not_empty_line()
        while not line[0] == '!':
            message['data'].append(line)
            line = self.readline()

        message['checksum'] = line[1:]
        return message

    def json(self):
        message = self.read_message()
        data = self.lines_to_map(message['data'])
        data = self.translate_tags(data)
        data = self.parse_values(data)
        data = self.tags_to_dict(data)
        message['data'] = data
        return message
