# 🎙️ mindscribe GUI - Audio Transcription Tool


[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![GitHub issues](https://img.shields.io/github/issues/dev-without-borders/mindscribe)](https://github.com/dev-without-borders/mindscribe/issues)
[![GitHub stars](https://img.shields.io/github/stars/dev-without-borders/mindscribe)](https://github.com/dev-without-borders/mindscribe/stargazers)

Ein benutzerfreundliches GUI-Tool für hochpräzise Audio-Transkription mit WhisperX, optimiert für ADHS-freundliche Workflows und Wissensorganisation.
✨ Features

    🎯 Drag & Drop Support - Dateien einfach ins Fenster ziehen
    🎬 YouTube Integration - Direkte Transkription von YouTube-Videos
    📝 Multiple Formate - TXT, SRT, VTT, JSON Export
    🌍 Auto-Spracherkennung - Erkennt Sprache automatisch
    🔄 Speaker Diarization - Unterscheidet verschiedene Sprecher
    🧹 Auto-Cleanup - Temporäre Dateien werden automatisch gelöscht
    📂 Quick Access - Öffne Zielordner direkt aus dem Tool

🚀 Installation
1. Voraussetzungen

    Python 3.9 - 3.11 (3.12+ noch nicht vollständig unterstützt)
    FFmpeg muss installiert sein
    CUDA (optional, für GPU-Beschleunigung)

FFmpeg Installation:

Windows:

# Mit Chocolatey:
choco install ffmpeg

# Oder manuell von: https://ffmpeg.org/download.html
# Und zu PATH hinzufügen

Linux:

sudo apt update && sudo apt install ffmpeg

macOS:

brew install ffmpeg

2. Repository klonen / Download

git clone https://github.com/deinusername/whisperx-gui.git
cd whisperx-gui

3. Virtual Environment erstellen

# Virtual Environment erstellen
python -m venv venv

# Aktivieren
# Windows:
venv\Scripts\activate

# Linux/macOS:
source venv/bin/activate

4. Dependencies installieren

pip install -r requirements.txt

Für CUDA-Unterstützung (NVIDIA GPU):

# CUDA 11.8 (empfohlen):
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118

# CUDA 12.1:
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121

🎮 Verwendung
Start

python whisperx_gui.py

Workflow

    Source File(s) auswählen:
        📁 Browse-Button
        🖱️ Drag & Drop
        🔗 YouTube-URL einfügen

    Output Directory festlegen (optional - Standard: ./transcriptions)

    Optionen konfigurieren:
        🌍 Sprache (Auto-Detect empfohlen)
        🎤 Model (large-v2 für beste Qualität)
        🔄 Speaker Diarization aktivieren
        📝 Output-Formate wählen

    Transcribe klicken!

    📂 Open Output Folder - Direkter Zugriff auf Ergebnisse

📋 Unterstützte Formate
Input:

    Audio: .mp3, .wav, .m4a, .flac, .ogg, .aac, .wma
    Video: .mp4, .avi, .mkv, .mov, .webm
    Streaming: YouTube-URLs

Output:

    .txt - Einfacher Text
    .srt - Untertitel (mit Timestamps)
    .vtt - WebVTT Untertitel
    .json - Vollständige Metadaten

⚙️ Konfiguration
Models
Model 	Qualität 	Geschwindigkeit 	VRAM
tiny 	⭐ 	⚡⚡⚡ 	~1 GB
base 	⭐⭐ 	⚡⚡⚡ 	~1 GB
small 	⭐⭐⭐ 	⚡⚡ 	~2 GB
medium 	⭐⭐⭐⭐ 	⚡ 	~5 GB
large-v2 	⭐⭐⭐⭐⭐ 	⚡ 	~10 GB

Empfehlung: large-v2 für beste Ergebnisse
Speaker Diarization

Benötigt HuggingFace Token:

    Erstelle Account auf huggingface.co
    Gehe zu Settings → Access Tokens
    Erstelle Token und füge es im GUI ein
    Akzeptiere die Bedingungen für:
        pyannote/segmentation
        pyannote/speaker-diarization

🎯 ADHS-optimierte Features

    Visuelle Fortschrittsanzeige - Immer wissen wo du stehst
    Log-Fenster - Alle Aktionen nachvollziehbar
    Quick-Access - Zielordner sofort öffnen
    Auto-Cleanup - Keine temporären Datei-Leichen
    Batch-Processing - Alles auf einmal erledigen
    YouTube-Direct - Kein manuelles Download nötig

💡 Workflow-Tipps

Für Podcasts/Interviews:

✅ Speaker Diarization aktivieren
✅ large-v2 Model
✅ SRT + TXT Export

Für schnelle Notizen:

✅ Auto-Detect Language
✅ small/medium Model
✅ Nur TXT Export

Für YouTube-Recherche:

✅ URL direkt einfügen
✅ Source files löschen aktivieren
✅ Alle Formate exportieren

🔧 Troubleshooting
"FFmpeg not found"

# Teste ob FFmpeg verfügbar ist:
ffmpeg -version

# Falls nicht, installiere es (siehe oben)

"CUDA out of memory"

    Verwende kleineres Model (medium statt large-v2)
    Schließe andere GPU-Programme
    Reduziere batch_size im Code

"ModuleNotFoundError: tkinterdnd2"

pip install tkinterdnd2 --force-reinstall

YouTube Download schlägt fehl

# Aktualisiere yt-dlp:
pip install -U yt-dlp

Langsame Transkription (CPU)

    Nutze kleineres Model
    Oder installiere CUDA-Support (siehe oben)

📦 PyInstaller Build (Optional)

Erstelle standalone .exe:

# Install PyInstaller
pip install pyinstaller

# Build
pyinstaller --onefile --windowed --name="WhisperX-GUI" whisperx_gui.py

# Executable in: dist/WhisperX-GUI.exe

⚠️ Wichtig: FFmpeg muss trotzdem separat installiert sein!
🤝 Integration mit Obsidian

Perfect für Wissensmanagement:

    Setze Output Directory auf Obsidian Vault
    Nutze TXT-Format
    Erstelle Template für Metadaten:

    ---
    source: {{filename}}
    date: {{date}}
    type: transcription
    ---

    # {{title}}

    {{transcript}}

📄 License

MIT License - Siehe LICENSE Datei
🙏 Credits

    WhisperX - Max Bain
    OpenAI Whisper
    yt-dlp

💬 Support

Bei Fragen oder Problemen:

    🐛 Issues
    💡 Discussions

Made with ❤️ for better focus and productivity