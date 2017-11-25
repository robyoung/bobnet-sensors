# Bobnet sensors

```bash
$ bobnet-sensors -c config.yml
```

```yaml
sensors:
  temperature:
    device:  mcp3008
    channel: 0
    every: 1s
  light:
    device:  mcp3008
    channel: 1
    every: 10s

iotcore:
  region:      europe-west1
  project_id:  example-project
  registry_id: example-registry
  device_id:   example01
  private_key_path: /path/to/private-key.pem
  ca_certs_path: /path/to/google-roots.pem
```

# Modules

## cli

Entry point and command line argument parsing

## config

Parse the config file

## iotcore

Interface to IoT core

## sensors

The sensor library

### Devices

#### MCP3008

#### Enviro-pHat

sensor config
```
sensors:
  temperature:
    device: envirophat
    sensors:
      - light.rgb
      - sensor: light.light
        label: light
      - weather.temperature
      - weather.pressure
      - weather.altitude
    sensor: light.rgb
    every: 30s
```

update config
```
leds: on
```
or
```
leds: off
```

## main

The main loop
