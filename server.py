#!/usr/bin/env python3
"""
Suno Downloader Companion Server
Lekki serwer lokalny do obsługi zapytań, parsowania przekierowań Suno i serwowania aplikacji webowej.
Działa na standardowej bibliotece Pythona 3 (zero zewnętrznych zależności!).
"""

import http.server
import socketserver
import urllib.request
import urllib.parse
import json
import re
import os
import sys
import webbrowser

PORT = 8989
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

def resolve_suno_song(url_or_id):
    url_or_id = url_or_id.strip()
    
    # Sprawdź, czy przekazano bezpośrednio UUID
    uuid_match = re.search(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", url_or_id, re.I)
    
    # Przygotuj URL docelowy
    if url_or_id.startswith("http://") or url_or_id.startswith("https://"):
        target_url = url_or_id
    elif uuid_match:
        target_url = f"https://suno.com/song/{uuid_match.group(1)}"
    else:
        # Prawdopodobnie sam kod share np. F6zkWD2zAM0iJT5V
        target_url = f"https://suno.com/s/{url_or_id}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "pl,en-US;q=0.9,en;q=0.8",
    }

    req = urllib.request.Request(target_url, headers=headers)
    with urllib.request.urlopen(req, timeout=12) as response:
        final_url = response.geturl()
        html = response.read().decode("utf-8", errors="ignore")

    # Wyodrębnij UUID z finalnego URL lub kodu strony
    final_uuid_m = re.search(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", final_url, re.I)
    if not final_uuid_m:
        final_uuid_m = re.search(r"image_large_([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", html, re.I)
    if not final_uuid_m:
        final_uuid_m = re.search(r"/clip/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", html, re.I)
        
    uuid = final_uuid_m.group(1) if final_uuid_m else None
    if not uuid:
        raise ValueError("Nie udało się odnaleźć identyfikatora utworu (UUID).")

    # Parsuj Tytuł
    title = "Nieznany utwór"
    t_match = re.search(r"<meta property=\"og:title\" content=\"([^\"]+)\"", html)
    if t_match:
        title = t_match.group(1).strip()
    else:
        t_page = re.search(r"<title>(.*?)(?: by | \| Suno)", html)
        if t_page:
            title = t_page.group(1).strip()

    # Parsuj Wykonawcę / Twórcę
    artist = "Suno Creator"
    a_match = re.search(r"<title>.*?by (.*?) \| Suno</title>", html)
    if a_match:
        artist = a_match.group(1).strip()
    else:
        a_desc = re.search(r"content=\"[^\"]*?by ([^@\(\"]+)", html)
        if a_desc:
            artist = a_desc.group(1).strip()

    # Parsuj Okładkę
    image_url = f"https://cdn2.suno.ai/image_large_{uuid}.jpeg"
    img_m = re.search(r"<meta property=\"og:image\" content=\"([^\"]+)\"", html)
    if img_m and img_m.group(1).startswith("http"):
        image_url = img_m.group(1)

    # Bezpośredni strumień audio M4A (zawsze dostępny z CloudFront z CORS)
    audio_url = f"https://d2lwuy8qc234o3.cloudfront.net/1/clip/{uuid}.m4a"

    # Parsuj Tagi / Styl muzyczny
    tags = ""
    tags_m = re.search(r"\\\"tags\\\":\\\"(.*?)\\\"", html)
    if not tags_m:
        tags_m = re.search(r"\"tags\":\"(.*?)\"", html)
    if tags_m:
        tags = tags_m.group(1).replace("\\n", " ").strip()

    # Parsuj Tekst / Prompt
    lyrics = ""
    # Wyszukaj blok prompta lub tekstu piosenki w streamie Next.js
    prompt_chunks = re.findall(r"\d+:T[0-9a-f]+,(.+?)(?=\n\d+:|\Z)", html, re.DOTALL)
    for chunk in prompt_chunks:
        # Sprawdzamy czy wygląda jak tekst piosenki ze strukturą zwrotek
        if any(marker in chunk for marker in ["[Verse", "[Chorus", "[Intro", "[Outro", "[Bridge", "[Immediate"]):
            lyrics = chunk.encode().decode("unicode_escape", errors="ignore").strip()
            break
            
    if not lyrics:
        prompt_m = re.search(r"\\\"prompt\\\":\\\"(.*?)\\\"", html)
        if prompt_m:
            lyrics = prompt_m.group(1).encode().decode("unicode_escape", errors="ignore").strip()

    return {
        "success": True,
        "uuid": uuid,
        "title": title,
        "artist": artist,
        "audio_url": audio_url,
        "image_url": image_url,
        "tags": tags,
        "lyrics": lyrics,
        "resolved_url": final_url
    }

class SunoHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        # Dodajemy nagłówki CORS dla pełnej integracji z dowolnym klientem
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        
        # Endpoint sprawdzania statusu
        if parsed.path == "/api/ping":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "service": "Suno Downloader Companion"}).encode("utf-8"))
            return

        # Endpoint rozwiązywania URL piosenki
        if parsed.path == "/api/resolve":
            query = urllib.parse.parse_qs(parsed.query)
            target = query.get("url", [""])[0] or query.get("id", [""])[0]
            
            if not target:
                self.send_response(400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": "Brak parametru 'url' lub 'id'"}).encode("utf-8"))
                return

            try:
                data = resolve_suno_song(target)
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
            return

        # W przeciwnym razie serwuj pliki statyczne (index.html, style.css, app.js itp.)
        return super().do_GET()

def run():
    socketserver.TCPServer.allow_reuse_address = True
    server_address = ("", PORT)
    with socketserver.TCPServer(server_address, SunoHandler) as httpd:
        url = f"http://localhost:{PORT}"
        print("=" * 60)
        print(f"  🎵 Suno Downloader Portal & API działa!")
        print(f"  🌐 Adres: {url}")
        print("  Wciśnij Ctrl+C, aby zatrzymać serwer.")
        print("=" * 60)
        
        if "--no-browser" not in sys.argv:
            try:
                webbrowser.open(url)
            except Exception:
                pass

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nZatrzymywanie serwera...")
            httpd.server_close()

if __name__ == "__main__":
    run()
