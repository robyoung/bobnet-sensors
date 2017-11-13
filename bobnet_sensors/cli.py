import argparse

from .config import load_config
from .iotcore import load_iotcore
from .sensors import load_sensors
from .main import run


def parse_args():
    parser = argparse.ArgumentParser(
        description='Run a BobNet sensor')
    parser.add_argument('-c', '--config', dest='config')

    return parser.parse_args()


def main():
    args = parse_args()
    c = load_config(args.config)

    iotcore = load_iotcore(c)
    sensors = load_sensors(c)

    run(iotcore, sensors)
