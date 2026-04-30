#!/bin/sh
set -a
. /home/dave/.env.sonos-trmnl
set +a
. /home/dave/sonos-local/bin/activate
python3 /home/dave/trmnl-sonos-local.py
