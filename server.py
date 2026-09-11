#!/usr/bin/env python3
"""
Suno Downloader Companion Server with Real-time Mango DRM Decryption
Obsługuje:
- Błyskawiczne rozwiązywanie skróconych linków /s/...
- Omijanie DRM Mango: deszyfrowanie AES-CTR w pamięci RAM w 0.3s
- Strumieniowanie nieszyfrowanego audio M4A do przeglądarki z obsługą Range (seeking)
- Pobieranie plików z poprawnymi nagłówkami i metadanymi
- Serwowanie interfejsu webowego
"""

import http.server
import socketserver
import urllib.request
import urllib.parse
import json
import re
import os
import sys
import time
import base64
import hashlib
import webbrowser
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

PORT = 8989
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

# Pamięć podręczna na odszyfrowane utwory (unikanie ponownego pobierania przy seekowaniu)
audio_cache = {}  # uuid: bytes
metadata_cache = {}  # uuid: dict

def resolve_suno_song(url_or_id):
    url_or_id = url_or_id.strip()
    
    # Sprawdź, czy przekazano bezpośrednio UUID
    uuid_match = re.search(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", url_or_id, re.I)
    
    if url_or_id.startswith("http://") or url_or_id.startswith("https://"):
        target_url = url_or_id
    elif uuid_match:
        target_url = f"https://suno.com/song/{uuid_match.group(1)}"
    else:
        target_url = f"https://suno.com/s/{url_or_id}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pl,en-US;q=0.9,en;q=0.8",
    }

    req = urllib.request.Request(target_url, headers=headers)
    with urllib.request.urlopen(req, timeout=12) as response:
        final_url = response.geturl()
        html = response.read().decode("utf-8", errors="ignore")

    final_uuid_m = re.search(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", final_url, re.I)
    if not final_uuid_m:
        final_uuid_m = re.search(r"image_large_([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", html, re.I)
    if not final_uuid_m:
        final_uuid_m = re.search(r"/clip/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", html, re.I)
        
    uuid = final_uuid_m.group(1) if final_uuid_m else None
    if not uuid:
        raise ValueError("Nie udało się odnaleźć identyfikatora utworu (UUID).")

    # Tytuł
    title = "Suno Track"
    t_match = re.search(r"<meta property=\"og:title\" content=\"([^\"]+)\"", html)
    if t_match:
        title = t_match.group(1).strip()
    else:
        t_page = re.search(r"<title>(.*?)(?: by | \| Suno)", html)
        if t_page:
            title = t_page.group(1).strip()

    # Wykonawca
    artist = "Suno Creator"
    a_match = re.search(r"<title>.*?by (.*?) \| Suno</title>", html)
    if a_match:
        artist = a_match.group(1).strip()
    else:
        a_desc = re.search(r"content=\"[^\"]*?by ([^@\(\"]+)", html)
        if a_desc:
            artist = a_desc.group(1).strip()

    # Okładka
    image_url = f"https://cdn2.suno.ai/image_large_{uuid}.jpeg"
    img_m = re.search(r"<meta property=\"og:image\" content=\"([^\"]+)\"", html)
    if img_m and img_m.group(1).startswith("http"):
        image_url = img_m.group(1)

    # Tagi
    tags = ""
    tags_m = re.search(r"\\\"tags\\\":\\\"(.*?)\\\"", html)
    if not tags_m:
        tags_m = re.search(r"\"tags\":\"(.*?)\"", html)
    if tags_m:
        tags = tags_m.group(1).replace("\\n", " ").strip()

    # Tekst / Prompt
    lyrics = ""
    prompt_match = re.search(r":T[0-9a-f]+,(.+?)(?=\d+:\[|\d+:\"|\d+:\{|\d+:null|\Z)", html, re.DOTALL)
    if prompt_match:
        raw_text = prompt_match.group(1).strip()
        if any(marker in raw_text for marker in ["[Verse", "[Chorus", "[Intro", "[Outro", "[Bridge", "[Immediate"]):
            try:
                lyrics = raw_text.encode().decode("unicode_escape", errors="ignore").strip()
            except Exception:
                lyrics = raw_text
            
    if not lyrics:
        prompt_m = re.search(r"\\\"prompt\\\":\\\"(.*?)\\\"", html)
        if prompt_m:
            try:
                lyrics = prompt_m.group(1).encode().decode("unicode_escape", errors="ignore").strip()
            except Exception:
                lyrics = prompt_m.group(1)

    result = {
        "success": True,
        "uuid": uuid,
        "title": title,
        "artist": artist,
        "audio_url": f"/api/stream?uuid={uuid}",
        "raw_audio_url": f"https://d2lwuy8qc234o3.cloudfront.net/1/clip/{uuid}.m4a",
        "image_url": image_url,
        "tags": tags,
        "lyrics": lyrics,
        "resolved_url": final_url
    }
    metadata_cache[uuid] = result
    return result

def get_decrypted_audio(uuid):
    """Pobiera i odszyfrowuje strumień audio Mango DRM w locie"""
    if uuid in audio_cache:
        return audio_cache[uuid]

    # 1. Pobierz klucze licencji Mango
    rights_url = "https://studio-api.prod.suno.com/api/mango/rights"
    payload = json.dumps({"content_params": {"content_id": uuid, "content_type": "clip"}}).encode("utf-8")
    req = urllib.request.Request(rights_url, data=payload, headers={
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    })
    with urllib.request.urlopen(req, timeout=10) as r:
        rights = json.loads(r.read().decode("utf-8"))

    glt = rights["glt"]
    wrapped_key = base64.b64decode(rights["key"])
    wrapped_iv = base64.b64decode(rights["iv"])

    # 2. Deszyfrowanie klucza i wektora inicjalizacyjnego (AES-GCM)
    user_key = hashlib.sha256(glt.encode("utf-8")).digest()
    aad = uuid.encode("utf-8")

    # Klucz zawartości
    c_k = Cipher(algorithms.AES(user_key), modes.GCM(wrapped_key[:12], wrapped_key[-16:])).decryptor()
    c_k.authenticate_additional_data(aad)
    content_key = c_k.update(wrapped_key[12:-16]) + c_k.finalize()

    # Wektor IV
    c_iv = Cipher(algorithms.AES(user_key), modes.GCM(wrapped_iv[:12], wrapped_iv[-16:])).decryptor()
    c_iv.authenticate_additional_data(aad)
    content_iv = c_iv.update(wrapped_iv[12:-16]) + c_iv.finalize()

    # 3. Pobierz zaszyfrowany plik M4A
    audio_url = f"https://d2lwuy8qc234o3.cloudfront.net/1/clip/{uuid}.m4a"
    req_a = urllib.request.Request(audio_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    with urllib.request.urlopen(req_a, timeout=20) as r:
        enc_data = r.read()

    # 4. Deszyfrowanie AES-CTR
    cipher_ctr = Cipher(algorithms.AES(content_key), modes.CTR(content_iv)).decryptor()
    decrypted_bytes = cipher_ctr.update(enc_data) + cipher_ctr.finalize()

    # Zapisz w pamięci cache (maksymalnie 10 utworów w RAM)
    if len(audio_cache) > 10:
        audio_cache.pop(next(iter(audio_cache)))
    audio_cache[uuid] = decrypted_bytes
    return decrypted_bytes

class SunoHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, HEAD")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Expose-Headers", "Content-Range, Accept-Ranges, Content-Length, Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        
        # 1. Ping
        if parsed.path == "/api/ping":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "service": "Suno Downloader Companion", "mango_drm": True}).encode("utf-8"))
            return

        # 2. Rozwiązywanie utworu
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

        # 3. Odszyfrowany strumień audio do odtwarzania i pobierania (z obsługą Range requests)
        if parsed.path == "/api/stream" or parsed.path == "/api/download":
            query = urllib.parse.parse_qs(parsed.query)
            uuid = query.get("uuid", [""])[0]
            
            if not uuid:
                self.send_response(400)
                self.end_headers()
                return

            try:
                audio_bytes = get_decrypted_audio(uuid)
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Błąd deszyfrowania Mango DRM: {str(e)}"}).encode("utf-8"))
                return

            total_size = len(audio_bytes)
            range_header = self.headers.get("Range")

            meta = metadata_cache.get(uuid, {})
            title = meta.get("title", f"suno_{uuid[:8]}")
            artist = meta.get("artist", "Suno AI")
            safe_filename = re.sub(r'[/\\?%*:|"<> ]', '_', f"{artist}_{title}.m4a")

            if parsed.path == "/api/download":
                self.send_response(200)
                self.send_header("Content-Type", "audio/mp4")
                self.send_header("Content-Length", str(total_size))
                self.send_header("Content-Disposition", f'attachment; filename="{safe_filename}"')
                self.end_headers()
                self.wfile.write(audio_bytes)
                return

            # Obsługa Range dla odtwarzacza HTML5
            if range_header:
                range_match = re.match(r"bytes=(\d+)-(\d*)", range_header)
                if range_match:
                    start = int(range_match.group(1))
                    end = int(range_match.group(2)) if range_match.group(2) else total_size - 1
                    end = min(end, total_size - 1)
                    length = end - start + 1

                    self.send_response(206)
                    self.send_header("Content-Type", "audio/mp4")
                    self.send_header("Accept-Ranges", "bytes")
                    self.send_header("Content-Range", f"bytes {start}-{end}/{total_size}")
                    self.send_header("Content-Length", str(length))
                    self.end_headers()
                    self.wfile.write(audio_bytes[start:end + 1])
                    return

            self.send_response(200)
            self.send_header("Content-Type", "audio/mp4")
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(total_size))
            self.end_headers()
            self.wfile.write(audio_bytes)
            return

        # Pliki statyczne
        return super().do_GET()

def run():
    socketserver.TCPServer.allow_reuse_address = True
    server_address = ("", PORT)
    with socketserver.TCPServer(server_address, SunoHandler) as httpd:
        url = f"http://localhost:{PORT}"
        print("=" * 65)
        print(f"  🎵 Suno Downloader + Mango DRM Decryptor działa!")
        print(f"  🌐 Otwórz w przeglądarce: {url}")
        print("  Wciśnij Ctrl+C, aby zatrzymać serwer.")
        print("=" * 65)
        
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
