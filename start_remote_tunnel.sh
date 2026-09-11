#!/usr/bin/env bash
# Skrypt do udostępnienia lokalnego Suno Downloader do internetu (dla telefonu / poza domem)

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

# 1. Upewnij się, że serwer lokalny działa
if ! curl -s --max-time 1 "http://localhost:8989/api/ping" > /dev/null 2>&1; then
    nohup python3 -u server.py --no-browser > /tmp/suno_server.log 2>&1 &
    sleep 1
fi

echo "================================================================="
echo "  🚀 Uruchamianie bezpiecznego tunelu do Internetu dla telefonu"
echo "================================================================="

# Pobierz cloudflared jeśli nie istnieje
if [ ! -f "$DIR/cloudflared" ]; then
    echo "Pobieranie lekkiego klienta tunelu Cloudflare (1-razowo)..."
    curl -sL "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64" -o "$DIR/cloudflared"
    chmod +x "$DIR/cloudflared"
fi

echo ""
echo "Tunel zaraz wygeneruje Twój prywatny link HTTPS."
echo "Otwórz ten link w telefonie lub dowolnej przeglądarce poza domem!"
echo "Wciśnij Ctrl+C, aby zamknąć dostęp zdalny."
echo "================================================================="

"$DIR/cloudflared" tunnel --url http://localhost:8989
