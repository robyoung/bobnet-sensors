docker run \
  --rm \
  --cap-add SYS_RAWIO \
  --device /dev/i2c-1 \
  --device /dev/mem \
  -v /etc/bobnet:/etc/bobnet \
  robyoung/bobnet-sensors:latest \
  bobnet-sensors --config /etc/bobnet/sensors-config.yml --log-level DEBUG
