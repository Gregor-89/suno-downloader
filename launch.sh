#!/usr/bin/env bash
# Skrypt uruchamiający Suno Downloader i otwierający interfejs w przeglądarce

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

# Sprawdź, czy serwer już działa na porcie 8989
if ! curl -s --max-time 1 "http://localhost:8989/api/ping" > /dev/null 2>&1; then
    nohup python3 server.py --no-browser > /dev/null 2>&1 &
    sleep 0.8
fi

# Otwórz w domyślnej przeglądarce
xdg-open "http://localhost:8989" > /dev/null 2>&1 &
