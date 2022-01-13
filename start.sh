#! /usr/bin/env bash

if [ ! -f /instance/config.py ]; then
    echo "SECRET_KEY = '"`python -c 'import os;print(os.urandom(12).hex())'`"'" > /instance/config.py
fi

if [ ! -f /instance/usocial.db ]; then
    FLASK_APP=main flask create-db
fi

python ./main.py
