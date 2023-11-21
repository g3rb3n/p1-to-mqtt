import logging
import argparse
import json

from p1_to_mqtt.client import Client


if __name__ == '__main__':
    logging.basicConfig(level=logging.ERROR)
    parser = argparse.ArgumentParser(description='Start p1 to mqtt')
    parser.add_argument('--config', help='config file', default='config.json')
    args = parser.parse_args()
    with open(args.config) as f:
        config = json.load(f)
    Client(config).run()
