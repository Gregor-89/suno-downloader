/**
 * Suno Downloader - Frontend Logic
 * Wsparcie dla pracy lokalnej (z deszyfrowaniem Mango DRM) oraz podglądu online
 */

const LOCAL_SERVER_PORT = 8989;
let isLocalServer = false;
let currentTrack = null;
let historyItems = [];

// Elementy DOM
const serverStatusPill = document.getElementById('serverStatus');
const statusText = document.getElementById('statusText');
const searchForm = document.getElementById('searchForm');
const urlInput = document.getElementById('urlInput');
const btnPaste = document.getElementById('btnPaste');
const btnSubmit = document.getElementById('btnSubmit');
const loadingBox = document.getElementById('loadingBox');
const trackCard = document.getElementById('trackCard');
const modeNotice = document.getElementById('modeNotice');
const modeNoticeText = document.getElementById('modeNoticeText');

// Karta utworu
const trackCover = document.getElementById('trackCover');
const btnCoverDl = document.getElementById('btnCoverDl');
const trackTitle = document.getElementById('trackTitle');
const trackArtist = document.getElementById('trackArtist');
const trackTags = document.getElementById('trackTags');
const trackBadgeModel = document.getElementById('trackBadgeModel');
const trackBadgeArtist = document.getElementById('trackBadgeArtist');
const trackBadgeDuration = document.getElementById('trackBadgeDuration');

// Odtwarzacz
const audioElement = document.getElementById('audioElement');
const btnPlayPause = document.getElementById('btnPlayPause');
const playIcon = document.getElementById('playIcon');
const pauseIcon = document.getElementById('pauseIcon');
const currentTimeEl = document.getElementById('currentTime');
const totalTimeEl = document.getElementById('totalTime');
const progressBarContainer = document.getElementById('progressBarContainer');
const progressBarFill = document.getElementById('progressBarFill');
const volumeSlider = document.getElementById('volumeSlider');
const btnMute = document.getElementById('btnMute');

// Przyciski akcji
const btnDownloadMp3 = document.getElementById('btnDownloadMp3');
const btnDownloadM4a = document.getElementById('btnDownloadM4a');
const btnDownloadCover = document.getElementById('btnDownloadCover');
const encodingProgressBox = document.getElementById('encodingProgressBox');
const encodingStatusText = document.getElementById('encodingStatusText');
const encodingPercent = document.getElementById('encodingPercent');
const encodingBarFill = document.getElementById('encodingBarFill');

// Tekst
const lyricsAccordion = document.getElementById('lyricsAccordion');
const lyricsHeader = document.getElementById('lyricsHeader');
const lyricsContent = document.getElementById('lyricsContent');
const lyricsText = document.getElementById('lyricsText');
const btnCopyLyrics = document.getElementById('btnCopyLyrics');
const lyricsArrow = document.getElementById('lyricsArrow');

// Historia
const historySection = document.getElementById('historySection');
const historyGrid = document.getElementById('historyGrid');
const btnClearHistory = document.getElementById('btnClearHistory');
const toastContainer = document.getElementById('toastContainer');

document.addEventListener('DOMContentLoaded', () => {
  checkServerConnection();
  loadHistory();
  setupEventListeners();
});

function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.innerHTML = `
    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
    </svg>
    <span>${message}</span>
  `;
  toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Pobierz skonfigurowany adres backendu (domyślnie pusty dla localhost/Vercel)
function getApiBaseUrl() {
  const urlParams = new URLSearchParams(window.location.search);
  const paramBackend = urlParams.get('backend');
  if (paramBackend) {
    localStorage.setItem('suno_custom_backend', paramBackend.replace(/\/$/, ''));
    return paramBackend.replace(/\/$/, '');
  }
  const saved = localStorage.getItem('suno_custom_backend');
  if (saved) return saved;

  const isLocalHost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
  if (isLocalHost) return '';
  
  // Jeśli to domena Vercel
  if (window.location.hostname.includes('vercel.app')) return '';

  return null;
}

// Sprawdź status serwera (lokalny, Vercel lub zdalny)
async function checkServerConnection() {
  const apiBase = getApiBaseUrl();

  if (apiBase !== null) {
    try {
      const res = await fetch(`${apiBase}/api/ping`, { signal: AbortSignal.timeout(3000) });
      if (res.ok) {
        isLocalServer = true;
        serverStatusPill.className = 'server-status-pill online';
        const isCloud = window.location.hostname.includes('vercel.app') || (apiBase && apiBase.startsWith('http'));
        statusText.textContent = isCloud ? 'Silnik Chmurowy (Aktywny)' : 'Lokalny Silnik DRM (Aktywny)';
        modeNotice.style.background = 'rgba(16, 185, 129, 0.1)';
        modeNotice.style.borderColor = 'rgba(16, 185, 129, 0.3)';
        modeNoticeText.innerHTML = `🟢 <b>Tryb Pełny Aktywny:</b> Deszyfrowanie Mango DRM, odtwarzanie w przeglądarce i konwersja MP3 działają w 100%!`;
        return;
      }
    } catch (e) {}
  }

  // Jeśli strona jest na GitHub Pages bez skonfigurowanego backendu
  isLocalServer = false;
  serverStatusPill.className = 'server-status-pill offline';
  statusText.textContent = 'Tryb Online (Wymaga Backend)';
  modeNotice.style.background = 'rgba(245, 158, 11, 0.1)';
  modeNotice.style.borderColor = 'rgba(245, 158, 11, 0.3)';
  modeNoticeText.innerHTML = '⚠️ <b>Uwaga:</b> Nowe pliki Suno są szyfrowane (Mango DRM). Aby pobierać poza domem bez VPS: wdróż to repozytorium <b>w 1 kliknięcie na darmowym Vercel.com</b> (instrukcja w <a href="https://github.com/Gregor-89/suno-downloader#readme" target="_blank" style="color:#f59e0b; text-decoration:underline;">README</a>) lub uruchom lokalnie z Pulpitu!';
}

function setupEventListeners() {
  searchForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const val = urlInput.value.trim();
    if (val) processUrl(val);
  });

  btnPaste.addEventListener('click', async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        urlInput.value = text.trim();
        showToast('Wklejono link ze schowka!');
      }
    } catch (err) {
      showToast('Użyj Ctrl+V, aby wkleić link', 'warn');
    }
  });

  document.querySelectorAll('.chip-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      const url = btn.dataset.url;
      urlInput.value = url;
      processUrl(url);
    });
  });

  // Player
  btnPlayPause.addEventListener('click', togglePlay);
  audioElement.addEventListener('timeupdate', updateProgress);
  audioElement.addEventListener('loadedmetadata', () => {
    totalTimeEl.textContent = formatTime(audioElement.duration);
    trackBadgeDuration.textContent = formatTime(audioElement.duration);
  });
  audioElement.addEventListener('ended', () => {
    playIcon.style.display = 'block';
    pauseIcon.style.display = 'none';
  });
  audioElement.addEventListener('error', (e) => {
    console.warn('Audio element error:', audioElement.error);
    if (!isLocalServer) {
      showToast('Suno zaszyfrowało ten strumień audio. Uruchom serwer ze skrótu na Pulpicie (http://localhost:8989), aby go odsłuchać!', 'warn');
    }
  });

  progressBarContainer.addEventListener('click', (e) => {
    const rect = progressBarContainer.getBoundingClientRect();
    const pos = (e.clientX - rect.left) / rect.width;
    if (audioElement.duration) {
      audioElement.currentTime = pos * audioElement.duration;
    }
  });

  volumeSlider.addEventListener('input', (e) => {
    audioElement.volume = e.target.value;
  });

  btnMute.addEventListener('click', () => {
    audioElement.muted = !audioElement.muted;
    volumeSlider.value = audioElement.muted ? 0 : audioElement.volume;
  });

  // Pobieranie
  btnDownloadMp3.addEventListener('click', () => downloadAsMp3());
  btnDownloadM4a.addEventListener('click', () => downloadOriginalM4a());
  btnDownloadCover.addEventListener('click', () => downloadCoverArt());
  btnCoverDl.addEventListener('click', () => downloadCoverArt());

  // Akordeon tekstu
  lyricsHeader.addEventListener('click', () => {
    const isShown = lyricsContent.style.display === 'block';
    lyricsContent.style.display = isShown ? 'none' : 'block';
    lyricsArrow.style.transform = isShown ? 'rotate(0deg)' : 'rotate(180deg)';
  });

  btnCopyLyrics.addEventListener('click', () => {
    if (currentTrack && currentTrack.lyrics) {
      navigator.clipboard.writeText(currentTrack.lyrics);
      showToast('Tekst skopiowany do schowka!');
    }
  });

  btnClearHistory.addEventListener('click', () => {
    localStorage.removeItem('suno_dl_history');
    historyItems = [];
    renderHistory();
    showToast('Historia wyczyszczona.');
  });
}

// Przetwarzanie adresu
async function processUrl(input) {
  loadingBox.style.display = 'block';
  trackCard.style.display = 'none';
  btnSubmit.disabled = true;

  try {
    let track = null;

    if (isLocalServer) {
      const apiBase = getApiBaseUrl() ?? '';
      const resp = await fetch(`${apiBase}/api/resolve?url=${encodeURIComponent(input)}`);
      const data = await resp.json();
      if (data.success) {
        track = data;
      } else {
        throw new Error(data.error || 'Błąd serwera');
      }
    } else {
      track = await resolveInWebMode(input);
    }

    if (!track || !track.uuid) {
      throw new Error('Nie udało się wyodrębnić identyfikatora utworu Suno.');
    }

    currentTrack = track;
    displayTrack(track);
    saveToHistory(track);
    showToast(`Wczytano: "${track.title}"!`);

  } catch (err) {
    console.error(err);
    showToast(`Błąd: ${err.message}`, 'error');
  } finally {
    loadingBox.style.display = 'none';
    btnSubmit.disabled = false;
  }
}

// Tryb Web (GitHub Pages)
async function resolveInWebMode(input) {
  const trimmed = input.trim();
  const uuidMatch = trimmed.match(/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/i);
  
  if (uuidMatch && !trimmed.includes('/s/')) {
    const uuid = uuidMatch[1];
    return {
      uuid: uuid,
      title: `Suno Track (${uuid.substring(0, 8)})`,
      artist: 'Suno Creator',
      audio_url: `https://d2lwuy8qc234o3.cloudfront.net/1/clip/${uuid}.m4a`,
      image_url: `https://cdn2.suno.ai/image_large_${uuid}.jpeg`,
      tags: 'Generowane przez Suno AI',
      lyrics: ''
    };
  }

  showToast('Rozwiązywanie skróconego linku...');
  try {
    const mlUrl = `https://api.microlink.io/?url=${encodeURIComponent(trimmed)}`;
    const res = await fetch(mlUrl, { signal: AbortSignal.timeout(8000) });
    const json = await res.json();
    
    if (json.status === 'success' && json.data) {
      const finalUrl = json.data.url || '';
      const finalUuidMatch = finalUrl.match(/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/i);
      
      if (finalUuidMatch) {
        const uuid = finalUuidMatch[1];
        return {
          uuid: uuid,
          title: json.data.title || 'Suno Track',
          artist: json.data.publisher || 'Suno AI',
          audio_url: `https://d2lwuy8qc234o3.cloudfront.net/1/clip/${uuid}.m4a`,
          image_url: json.data.image ? json.data.image.url : `https://cdn2.suno.ai/image_large_${uuid}.jpeg`,
          tags: 'Udostępniony utwór Suno',
          lyrics: ''
        };
      }
    }
  } catch (e) {}

  throw new Error('Otwórz ten link w nowej karcie, skopiuj z paska adresu pełny link /song/UUID i wklej go tutaj!');
}

function displayTrack(track) {
  trackTitle.textContent = track.title || 'Nieznany utwór';
  trackArtist.textContent = `Autor / Twórca: ${track.artist || 'Suno AI'}`;
  trackBadgeArtist.textContent = track.artist || 'Suno Creator';

  trackCover.src = track.image_url || `https://cdn2.suno.ai/image_large_${track.uuid}.jpeg`;
  trackCover.onerror = () => {
    trackCover.src = `https://cdn2.suno.ai/image_${track.uuid}.jpeg`;
  };

  if (track.tags && track.tags.trim()) {
    trackTags.style.display = 'block';
    trackTags.textContent = `Styl / Tagi: ${track.tags}`;
  } else {
    trackTags.style.display = 'none';
  }

  if (track.lyrics && track.lyrics.trim()) {
    lyricsAccordion.style.display = 'block';
    lyricsText.textContent = track.lyrics;
    lyricsContent.style.display = 'none';
    lyricsArrow.style.transform = 'rotate(0deg)';
  } else {
    lyricsAccordion.style.display = 'none';
  }

  // Ustawienie źródła audio
  const apiBase = getApiBaseUrl() ?? '';
  const audioSource = isLocalServer ? `${apiBase}/api/stream?uuid=${track.uuid}` : track.audio_url;
  audioElement.src = audioSource;
  audioElement.load();
  playIcon.style.display = 'block';
  pauseIcon.style.display = 'none';
  progressBarFill.style.width = '0%';
  currentTimeEl.textContent = '0:00';

  trackCard.style.display = 'block';
  trackCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function togglePlay() {
  if (audioElement.paused) {
    audioElement.play().then(() => {
      playIcon.style.display = 'none';
      pauseIcon.style.display = 'block';
    }).catch((err) => {
      console.warn('Play error:', err);
      if (!isLocalServer) {
        showToast('Nowe pliki Suno są szyfrowane (Mango DRM). Uruchom lokalny skrót na Pulpicie (http://localhost:8989), aby odsłuchiwać!', 'warn');
      }
    });
  } else {
    audioElement.pause();
    playIcon.style.display = 'block';
    pauseIcon.style.display = 'none';
  }
}

function updateProgress() {
  if (audioElement.duration) {
    const pct = (audioElement.currentTime / audioElement.duration) * 100;
    progressBarFill.style.width = `${pct}%`;
    currentTimeEl.textContent = formatTime(audioElement.currentTime);
  }
}

function formatTime(sec) {
  if (isNaN(sec) || !isFinite(sec)) return '0:00';
  const mins = Math.floor(sec / 60);
  const rem = Math.floor(sec % 60);
  return `${mins}:${rem < 10 ? '0' : ''}${rem}`;
}

// Pobieranie oryginalnego M4A
async function downloadOriginalM4a() {
  if (!currentTrack) return;
  
  if (isLocalServer) {
    // Bezpośrednie pobranie odszyfrowanego pliku z serwera lokalnego lub chmurowego
    const apiBase = getApiBaseUrl() ?? '';
    window.location.href = `${apiBase}/api/download?uuid=${currentTrack.uuid}`;
    showToast('Pobieranie odszyfrowanego strumienia M4A...');
    return;
  }

  showToast('Uwaga: pobierany plik może wymagać lokalnego odszyfrowania ze względu na Suno DRM.');
  const a = document.createElement('a');
  a.href = currentTrack.audio_url;
  a.download = sanitizeFilename(`${currentTrack.artist} - ${currentTrack.title}.m4a`);
  a.target = '_blank';
  document.body.appendChild(a);
  a.click();
  a.remove();
}

// Pobieranie okładki HD
async function downloadCoverArt() {
  if (!currentTrack) return;
  showToast('Pobieranie okładki HD...');

  try {
    const filename = sanitizeFilename(`${currentTrack.artist} - ${currentTrack.title} (Cover).jpeg`);
    const res = await fetch(currentTrack.image_url);
    const blob = await res.blob();
    triggerDownload(blob, filename);
    showToast('Pobrano okładkę!');
  } catch (err) {
    window.open(currentTrack.image_url, '_blank');
  }
}

// Konwersja do MP3 z ID3
async function downloadAsMp3() {
  if (!currentTrack) return;

  if (!isLocalServer) {
    showToast('Suno zaszyfrowało strumienie (Mango DRM). Aby wygenerować MP3, uruchom program ze skrótu na Pulpicie (http://localhost:8989)!', 'warn');
    return;
  }

  btnDownloadMp3.disabled = true;
  encodingProgressBox.style.display = 'block';
  setEncodingProgress(5, 'Pobieranie odszyfrowanego strumienia audio...');

  try {
    const apiBase = getApiBaseUrl() ?? '';
    const audioUrl = `${apiBase}/api/stream?uuid=${currentTrack.uuid}`;
    const audioResp = await fetch(audioUrl);
    const audioArrayBuffer = await audioResp.arrayBuffer();

    setEncodingProgress(25, 'Dekodowanie strumienia do PCM...');
    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const audioBuffer = await audioCtx.decodeAudioData(audioArrayBuffer);

    setEncodingProgress(40, 'Inicjalizacja kodera LAME MP3...');
    const numChannels = audioBuffer.numberOfChannels;
    const sampleRate = audioBuffer.sampleRate;
    const length = audioBuffer.length;

    const left = audioBuffer.getChannelData(0);
    const right = numChannels > 1 ? audioBuffer.getChannelData(1) : left;

    const leftInt16 = new Int16Array(length);
    const rightInt16 = new Int16Array(length);

    for (let i = 0; i < length; i++) {
      leftInt16[i] = Math.max(-32768, Math.min(32767, left[i] * 32767.5));
      rightInt16[i] = Math.max(-32768, Math.min(32767, right[i] * 32767.5));
    }

    setEncodingProgress(50, 'Kodowanie do formatu MP3 (320 kbps)...');
    const mp3encoder = new lamejs.Mp3Encoder(numChannels > 1 ? 2 : 1, sampleRate, 320);
    const mp3Chunks = [];
    const sampleBlockSize = 1152;

    for (let i = 0; i < length; i += sampleBlockSize) {
      const leftChunk = leftInt16.subarray(i, i + sampleBlockSize);
      let mp3buf;
      if (numChannels > 1) {
        const rightChunk = rightInt16.subarray(i, i + sampleBlockSize);
        mp3buf = mp3encoder.encodeBuffer(leftChunk, rightChunk);
      } else {
        mp3buf = mp3encoder.encodeBuffer(leftChunk);
      }
      if (mp3buf.length > 0) {
        mp3Chunks.push(mp3buf);
      }

      if (i % (sampleBlockSize * 40) === 0) {
        const pct = 50 + Math.round((i / length) * 35);
        setEncodingProgress(pct, `Kodowanie: ${pct}%`);
        await new Promise((r) => setTimeout(r, 0));
      }
    }

    const endBuf = mp3encoder.flush();
    if (endBuf.length > 0) {
      mp3Chunks.push(endBuf);
    }

    let totalLen = 0;
    for (const c of mp3Chunks) totalLen += c.length;
    const fullMp3 = new Uint8Array(totalLen);
    let offset = 0;
    for (const c of mp3Chunks) {
      fullMp3.set(c, offset);
      offset += c.length;
    }

    setEncodingProgress(90, 'Zapisywanie metadanych ID3 i okładki...');
    let coverArrayBuffer = null;
    try {
      const coverRes = await fetch(currentTrack.image_url);
      if (coverRes.ok) {
        coverArrayBuffer = await coverRes.arrayBuffer();
      }
    } catch (e) {}

    let finalBlob;
    if (window.ID3Writer) {
      try {
        const writer = new ID3Writer(fullMp3.buffer);
        writer.setFrame('TIT2', currentTrack.title || 'Suno Song');
        writer.setFrame('TPE1', [currentTrack.artist || 'Suno AI']);
        writer.setFrame('TALB', 'Suno AI Generations');
        
        if (currentTrack.lyrics) {
          writer.setFrame('USLT', {
            description: 'Lyrics',
            lyrics: currentTrack.lyrics,
            language: 'pol'
          });
        }

        if (coverArrayBuffer) {
          writer.setFrame('APIC', {
            type: 3,
            data: coverArrayBuffer,
            description: 'Album Art'
          });
        }

        writer.addTag();
        finalBlob = writer.getBlob();
      } catch (id3Err) {
        finalBlob = new Blob([fullMp3], { type: 'audio/mpeg' });
      }
    } else {
      finalBlob = new Blob([fullMp3], { type: 'audio/mpeg' });
    }

    setEncodingProgress(100, 'Gotowe!');
    const filename = sanitizeFilename(`${currentTrack.artist} - ${currentTrack.title}.mp3`);
    triggerDownload(finalBlob, filename);
    showToast('Pomyślnie pobrano plik MP3 z okładką!');

  } catch (err) {
    console.error('Błąd kodowania MP3:', err);
    showToast(`Błąd konwersji MP3: ${err.message}`, 'error');
  } finally {
    btnDownloadMp3.disabled = false;
    setTimeout(() => {
      encodingProgressBox.style.display = 'none';
    }, 2000);
  }
}

function setEncodingProgress(percent, status) {
  encodingPercent.textContent = `${percent}%`;
  encodingStatusText.textContent = status;
  encodingBarFill.style.width = `${percent}%`;
}

function sanitizeFilename(name) {
  return name.replace(/[/\\?%*:|"<>]/g, '_').trim();
}

function triggerDownload(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  setTimeout(() => {
    URL.revokeObjectURL(url);
    a.remove();
  }, 100);
}

function saveToHistory(track) {
  try {
    const list = JSON.parse(localStorage.getItem('suno_dl_history') || '[]');
    const filtered = list.filter((item) => item.uuid !== track.uuid);
    filtered.unshift({
      uuid: track.uuid,
      title: track.title,
      artist: track.artist,
      image_url: track.image_url,
      audio_url: track.audio_url,
      tags: track.tags,
      lyrics: track.lyrics,
      date: new Date().toISOString()
    });
    const limited = filtered.slice(0, 12);
    localStorage.setItem('suno_dl_history', JSON.stringify(limited));
    loadHistory();
  } catch (e) {}
}

function loadHistory() {
  try {
    const list = JSON.parse(localStorage.getItem('suno_dl_history') || '[]');
    historyItems = list;
    renderHistory();
  } catch (e) {
    historyItems = [];
  }
}

function renderHistory() {
  if (historyItems.length === 0) {
    historySection.style.display = 'none';
    return;
  }

  historySection.style.display = 'block';
  historyGrid.innerHTML = '';

  historyItems.forEach((item) => {
    const card = document.createElement('div');
    card.className = 'history-item';
    card.innerHTML = `
      <img class="history-thumb" src="${item.image_url}" alt="Cover" onerror="this.src='https://cdn-o.suno.com/favicon-192x192.png'">
      <div class="history-details">
        <div class="history-title" title="${item.title}">${item.title}</div>
        <div class="history-artist">${item.artist || 'Suno AI'}</div>
      </div>
    `;

    card.addEventListener('click', () => {
      currentTrack = item;
      displayTrack(item);
      urlInput.value = `https://suno.com/song/${item.uuid}`;
    });

    historyGrid.appendChild(card);
  });
}
