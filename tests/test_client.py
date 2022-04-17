import datetime
import json
import logging
import pytest
from mock import patch

from p1_to_mqtt.client import Client

logging.basicConfig(level=logging.DEBUG)

fake_now = datetime.datetime(2022, 4, 14, 22, 8, 9)

@patch('paho.mqtt.client.Client')
def test_p1_to_mqtt(mock_client):
    mock_client.return_value.connect.return_value = None
    config = json.load(open('tests/config.json'))
    f = open('tests/data/p1-output.txt', 'r')

    process = Client(config)
    data = process.get_data()
    assert data['p1']['data']['Timestamp']['datetime'] == "2022-04-14T22:08:09+02:00"
