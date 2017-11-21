import argparse
import asyncio
import logging

from .config import load_config
from .iotcore import load_iotcore
from .sensors import load_sensors
from .main import run


def parse_args():
    parser = argparse.ArgumentParser(
        description='Run a BobNet sensor')
    parser.add_argument('-c', '--config', dest='config')
    parser.add_argument('-l', '--log-level',
                        help='Log level',
                        choices=['ERROR', 'WARNING', 'INFO', 'DEBUG'],
                        dest='log_level', default='INFO')

    return parser.parse_args()


def set_up_logging(log_level):
    logging.basicConfig(
        level=logging.getLevelName(log_level),
        format='%(asctime)s %(name)s %(levelname)s %(message)s'
    )


def main():
    args = parse_args()
    c = load_config(args.config)

    set_up_logging(args.log_level)

    loop = asyncio.new_event_loop()
    stop = asyncio.Event(loop=loop)
    iotcore = load_iotcore(loop, c)
    sensors = load_sensors(loop, c)

    run(loop, stop, iotcore, sensors)
