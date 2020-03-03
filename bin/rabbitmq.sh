#!/bin/bash

# Trap the EXIT signal to shut down rabbitmq
trap "{ /usr/sbin/rabbitmqctl stop; exit 0; }" EXIT

/usr/sbin/rabbitmq-server
