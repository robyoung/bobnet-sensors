FROM arm32v6/python:3.6-alpine3.7

WORKDIR /usr/src/bobnet-sensors
COPY . /usr/src/bobnet-sensors

RUN apk update \
    && apk add --virtual build-deps gcc python3-dev musl-dev make \
        libffi-dev \
    && apk add openssl-dev \
    && pip3 install --no-cache-dir . \
    && apk del build-deps

CMD bobnet-sensors --help
