#!/usr/bin/env bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

# Sprawdź, czy serwer już działa
if ! curl -s --max-time 1 "http://localhost:8989/api/ping" > /dev/null 2>&1; then
    nohup python3 -u server.py --no-browser > /tmp/suno_server.log 2>&1 &
    sleep 1
fi

xdg-open "http://localhost:8989" > /dev/null 2>&1 &
