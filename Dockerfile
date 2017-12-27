FROM arm32v6/python:3.6-alpine3.7

WORKDIR /usr/src/bobnet-sensors
COPY . /usr/src/bobnet-sensors

RUN apk update \
    && apk add --virtual build-deps gcc python3-dev musl-dev make linux-headers \
        libffi-dev \
    && apk add openssl-dev \
    && pip3 install --no-cache-dir -e .[mcp3008,envirophat] \
    && apk del build-deps

CMD bobnet-sensors --help
