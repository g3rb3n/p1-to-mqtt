import json
import logging

from p1_to_mqtt.p1 import Processor

logging.basicConfig(level=logging.DEBUG)


def test_processor_json():
    config = {
        "timezone":"Europe/Amsterdam",
    }
    f = open('tests/data/p1-output.txt', 'r')

    processor = Processor(f, config)
    data = processor.json()['data']
    assert data['Timestamp']['datetime'] == "2022-04-14T22:08:09+02:00"
    assert data['Electricity']['In']['MeterReading']['Tarrif1']['value'] == 10450.6
    assert data['Electricity']['In']['MeterReading']['Tarrif1']['unit'] == "kWh"
    assert data['Electricity']['In']['Power']['value'] == 0.914
    assert data['Electricity']['In']['Power']['unit'] == "kW"
    assert data['Electricity']['PowerFailureEventLog']['number'] == 2
    assert data['Electricity']['PowerFailureEventLog']['events'][0]['datetime'] == "2021-05-06T19:29:22+02:00"
    assert data['Electricity']['PowerFailureEventLog']['events'][0]['duration']['value'] == 35451
    assert data['Electricity']['PowerFailureEventLog']['events'][1]['datetime'] == "2021-02-06T19:29:22+01:00"
    assert data['Electricity']['PowerFailureEventLog']['events'][1]['duration']['value'] == 12876
    assert data['TextMessage'] == ""
