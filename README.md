# 🎵 Suno Downloader

Nowoczesny, uniwersalny portal webowy oraz odtwarzacz do pobierania utworów wygenerowanych na **Suno.com**, w pełni kompatybilny z **GitHub Pages** oraz zintegrowany z lokalnym asystentem na pulpicie.

---

## ✨ Kluczowe Możliwości

- 🎧 **Pobieranie MP3 (320 kbps) z pełnymi tagami ID3**:
  - Konwersja w przeglądarce za pomocą Web Audio API oraz biblioteki LAME MP3.
  - Automatyczne zaszycie w pliku MP3 okładki albumu (APIC), tytułu, wykonawcy, nazwy albumu oraz pełnego tekstu piosenki (USLT).
- ⚡ **Pobieranie Oryginalnego Strumienia (M4A)**:
  - Błyskawiczne pobieranie bezpośredniego pliku audio o najwyższej jakości z CDN Suno.
- 🖼️ **Pobieranie Okładki HD (JPEG)**:
  - Ekstrakcja grafiki w pełnej rozdzielczości generowanej przez AI.
- 📜 **Przeglądarka Tekstu & Promptu**:
  - Wyodrębnianie zwrotek, refrenów i promptu ze struktur Next.js z opcją kopiowania 1-kliknięciem.
- 🎛️ **Wbudowany Odtwarzacz Muzyczny**:
  - Płynny pasek postępu (seek), licznik czasu, regulacja głośności i wyciszanie.
- 💾 **Lokalna Historia Utworów**:
  - Zapamiętywanie ostatnio badanych utworów w `localStorage` przeglądarki.
- 🌐 **Dwa Tryby Działania**:
  1. **Tryb GitHub Pages / Web**: Działa w 100% statycznie na darmowym hostingu GitHub Pages.
  2. **Tryb Lokalny (Companion Server)**: Błyskawiczny mikro-serwer w Pythonie (zero zależności zewnętrznych) rozwiązujący skrócone linki `/s/...` w ułamku sekundy.

---

## 🚀 Uruchomienie na GitHub Pages

Projekt jest w 100% przygotowany do działania na GitHub Pages:
1. Wejdź do repozytorium na GitHub: `https://github.com/Gregor-89/suno-downloader`
2. Przejdź do zakładki **Settings** -> **Pages**.
3. W sekcji **Build and deployment**:
   - **Source**: `Deploy from a branch`
   - **Branch**: `main` (lub `master`) / `/ (root)`
4. Kliknij **Save**. Twoja strona będzie dostępna pod adresem:
   `https://gregor-89.github.io/suno-downloader/`

---

## ☁️ Dostęp Zdalny i Mobilny (Poza Domem - Bez VPS i za 0 zł!)

Nowe strumienie Suno chronione są szyfrowaniem **Mango DRM (AES-CTR)**. Ponieważ GitHub Pages to wyłącznie statyczny hosting (bez kodu backendowego), istnieją **dwa darmowe sposoby korzystania z portalu poza domem**:

### Opcja A: Wdrożenie na Vercel (1 kliknięcie, 100% w Chmurze)
Repozytorium posiada gotowe pliki serverless (`api/index.py`, `vercel.json`):
1. Wejdź na darmowy [vercel.com](https://vercel.com) i zaloguj się kontem GitHub.
2. Kliknij **Add New...** -> **Project** i wybierz `Gregor-89/suno-downloader`.
3. Kliknij **Deploy**.
4. Gotowe! Otrzymasz stały, bezpieczny adres HTTPS (np. `https://suno-downloader-twojanazwa.vercel.app`), z którego możesz pobierać i odsłuchiwać utwory na telefonie w podróży.

### Opcja B: 1-Kliknięcie na Pulpicie (Cloudflare Tunnel z PC)
Jeśli Twój komputer w domu jest włączony:
1. Kliknij na Pulpicie skrót: **`Suno Downloader (Dostęp Zdalny / Telefon)`** (lub uruchom `./start_remote_tunnel.sh`).
2. W oknie terminala pojawi się unikalny link HTTPS (np. `https://twoj-adres.trycloudflare.com`).
3. Otwórz ten link na telefonie lub prześlij sobie smsem/mailem — uzyskasz natychmiastowy dostęp do pełnego deszyfrowania i pobierania bez konfigurowania routera!

---

## 🖥️ Uruchomienie Lokalne (Linux)

### 1. Skrót na Pulpicie
Na Twoim pulpicie znajduje się plik **`Suno Downloader`**. Wystarczy kliknąć dwukrotnie, aby serwer wystartował w tle i otworzył aplikację pod adresem `http://localhost:8989`.

### 2. Z linii poleceń
```bash
./launch.sh
```
Lub bezpośrednio w Pythonie:
```bash
python3 server.py
```
Aplikacja uruchomi się pod adresem `http://localhost:8989`.

---

## 🔍 Obsługiwane Formaty Linków

Portal automatycznie rozpoznaje:
- Linki udostępniania: `https://suno.com/s/F6zkWD2zAM0iJT5V`
- Bezpośrednie linki do utworu: `https://suno.com/song/a0788b17-a966-41dc-bd5c-4c1fb784c3b3`
- Same identyfikatory UUID utworu: `a0788b17-a966-41dc-bd5c-4c1fb784c3b3`
