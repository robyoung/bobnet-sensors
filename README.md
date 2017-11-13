# Bobnet sensors

```bash
$ bobnet-sensors -c config.yml
```

```yaml
sensors:
  temperature:
    type:    MCP3008
    channel: 0
  light:
    type:    MCP3008
    channel: 1
  dust:
    type: DustSensorDevice
    pin:  14

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

## main

The main loop
