import argparse
import time

from bobnet_sensors import iotcore, config


def parse_args():
    parser = argparse.ArgumentParser(
        description='Send messages to IoT Core')
    parser.add_argument('-c', '--config')

    return parser.parse_args()


def main():
    args = parse_args()
    c = config.load_config(args.config)

    client = iotcore.load_iotcore(c)

    print('send results', client.send({'message': 'value'}))

    time.sleep(5)


if __name__ == '__main__':
    main()
