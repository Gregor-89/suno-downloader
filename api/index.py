import sys
import os
import urllib.parse
import json
import re
from http.server import BaseHTTPRequestHandler

# Importuj silnik deszyfrowania z server.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from server import resolve_suno_song, get_decrypted_audio, metadata_cache

class handler(BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, HEAD")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Expose-Headers", "Content-Range, Accept-Ranges, Content-Length, Content-Type")
        self.send_header("X-Robots-Tag", "noindex, nofollow, noarchive, nosnippet")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        
        if parsed.path.endswith("/api/ping") or parsed.path == "/api/ping":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "service": "Suno Downloader Vercel Cloud", "mango_drm": True}).encode("utf-8"))
            return

        if parsed.path.endswith("/api/resolve") or parsed.path == "/api/resolve":
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

        if parsed.path.endswith("/api/stream") or parsed.path.endswith("/api/download"):
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
            safe_filename = re.sub(r'[/\\?%*:|"<> ]', '_', f"{title}.m4a")

            if parsed.path.endswith("/api/download"):
                self.send_response(200)
                self.send_header("Content-Type", "audio/mp4")
                self.send_header("Content-Length", str(total_size))
                self.send_header("Content-Disposition", f'attachment; filename="{safe_filename}"')
                self.end_headers()
                self.wfile.write(audio_bytes)
                return

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

        self.send_response(404)
        self.end_headers()
