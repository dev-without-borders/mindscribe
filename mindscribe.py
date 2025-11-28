import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
from pathlib import Path
import threading
import sys
import whisperx
import torch
import gc
import requests
import yt_dlp
from datetime import datetime
import json
import subprocess
import os

# Ensure TkinterDnD is available and import it
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    messagebox.showerror("Import Error", "TkinterDnD2 not found. Please install it using 'pip install tkinterdnd2'.")
    sys.exit(1)

# Ensure yt_dlp is available and import it
try:
    import yt_dlp
except ImportError:
    messagebox.showerror("Import Error", "yt-dlp not found. Please install it using 'pip install yt-dlp'.")
    sys.exit(1)

# Ensure whisperx is available and import it (only for type hinting and potential future direct use)
# Actual WhisperX execution is via subprocess for better isolation and resource management.
try:
    import whisperx
    # Check for HuggingFace token proactively
    HF_TOKEN = os.environ.get("HF_TOKEN")
except ImportError:
    messagebox.showwarning("Import Warning", "whisperx not found. While not strictly required for this GUI to *run* (as it uses subprocess), direct import might fail. Ensure it's installed via 'pip install -U whisperx'.")
    HF_TOKEN = os.environ.get("HF_TOKEN")
except Exception as e:
    messagebox.showwarning("HuggingFace Token Check", f"Could not check HuggingFace token during whisperx import: {e}. Diarization might fail without it.")
    HF_TOKEN = os.environ.get("HF_TOKEN")

# Safe Import für Drag & Drop (verhindert Absturz, falls nicht installiert)
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAIL = True
except ImportError:
    DND_AVAIL = False
    print("Warning: tkinterdnd2 not found. Drag & Drop will be disabled.")

class MindscribeGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("WhisperX Transcription")
        self.root.geometry("700x800")
        
        # Settings file
        self.settings_file = Path(__file__).parent / "whisperx_settings.json"
        
        # Track temporary files
        self.temp_files = []
        
        self.create_widgets()
        self.load_settings()
        
        # Check FFmpeg
        if not self.check_ffmpeg():
            messagebox.showwarning(
                "FFmpeg Warning",
                "FFmpeg not found in PATH!\n\n"
                "Audio conversion may fail.\n"
                "Please install FFmpeg if needed."
            )
    
    def check_ffmpeg(self):
        """Check if FFmpeg is available"""
        try:
            subprocess.run(['ffmpeg', '-version'], 
                          capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def create_widgets(self):
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        row = 0
        
        # === Source File/URL ===
        ttk.Label(main_frame, text="Source (File/URL/YouTube):").grid(row=row, column=0, sticky=tk.W, pady=5)
        row += 1
        
        source_frame = ttk.Frame(main_frame)
        source_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=5)
        
        self.file_entry = ttk.Entry(source_frame, width=70)
        self.file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # ✅ Drag & Drop support (conditional)
        if DND_AVAIL:
            self.file_entry.drop_target_register(DND_FILES)
            self.file_entry.dnd_bind('<<Drop>>', lambda e: self.on_drop(e, self.file_entry))
        
        # ✅ Right-click menu
        self.create_context_menu(self.file_entry)
        
        ttk.Button(source_frame, text="Browse", command=self.browse_file).pack(side=tk.LEFT, padx=5)
        row += 1

        self.url_type_label = ttk.Label(main_frame, text="", foreground="blue")
        self.url_type_label.grid(row=row, column=0, sticky=tk.E, padx=5)
        row += 1
        
        self.file_entry.bind('<KeyRelease>', self.detect_url_type)
        
        # === Output Filename ===
        ttk.Label(main_frame, text="Output Filename (without extension):").grid(row=row, column=0, sticky=tk.W, pady=5)
        row += 1
        
        filename_frame = ttk.Frame(main_frame)
        filename_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=5)
        
        self.filename_entry = ttk.Entry(filename_frame, width=70)
        self.filename_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # ✅ Right-click menu
        self.create_context_menu(self.filename_entry)
        
        ttk.Button(filename_frame, text="Auto", command=self.auto_generate_filename).pack(side=tk.LEFT, padx=5)
        row += 1
        
        # === Parameters Frame ===
        params_frame = ttk.LabelFrame(main_frame, text="Parameters", padding="10")
        params_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=10)
        row += 1
        
        # Model
        ttk.Label(params_frame, text="Model:").grid(row=0, column=0, sticky=tk.W)
        self.model_var = tk.StringVar(value="large-v2")
        model_combo = ttk.Combobox(params_frame, textvariable=self.model_var, 
                                   values=["tiny", "base", "small", "medium", "large-v2", "large-v3"],
                                   width=20)
        model_combo.grid(row=0, column=1, sticky=tk.W, padx=5)
        
        # Language
        ttk.Label(params_frame, text="Language:").grid(row=0, column=2, sticky=tk.W, padx=(20,0))
        self.language_var = tk.StringVar(value="de")
        ttk.Entry(params_frame, textvariable=self.language_var, width=10).grid(row=0, column=3, sticky=tk.W, padx=5)
        
        # Compute Type
        ttk.Label(params_frame, text="Compute Type:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.compute_var = tk.StringVar(value="int8")
        compute_combo = ttk.Combobox(params_frame, textvariable=self.compute_var,
                                     values=["int8", "float16", "float32"],
                                     width=20)
        compute_combo.grid(row=1, column=1, sticky=tk.W, padx=5)
        
        # Batch Size
        ttk.Label(params_frame, text="Batch Size:").grid(row=1, column=2, sticky=tk.W, padx=(20,0))
        self.batch_var = tk.StringVar(value="8")
        ttk.Entry(params_frame, textvariable=self.batch_var, width=10).grid(row=1, column=3, sticky=tk.W, padx=5)
        
        # Diarization
        self.diarize_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(params_frame, text="Enable Diarization", variable=self.diarize_var).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Speakers
        ttk.Label(params_frame, text="Min Speakers:").grid(row=3, column=0, sticky=tk.W)
        self.min_speakers_var = tk.StringVar(value="2")
        ttk.Entry(params_frame, textvariable=self.min_speakers_var, width=10).grid(row=3, column=1, sticky=tk.W, padx=5)
        
        ttk.Label(params_frame, text="Max Speakers:").grid(row=3, column=2, sticky=tk.W, padx=(20,0))
        self.max_speakers_var = tk.StringVar(value="2")
        ttk.Entry(params_frame, textvariable=self.max_speakers_var, width=10).grid(row=3, column=3, sticky=tk.W, padx=5)
        
        # HF Token
        ttk.Label(params_frame, text="HuggingFace Token:").grid(row=4, column=0, sticky=tk.W, pady=5)
        token_frame = ttk.Frame(params_frame)
        token_frame.grid(row=4, column=1, columnspan=3, sticky=(tk.W, tk.E), padx=5)
        
        self.token_var = tk.StringVar()
        self.token_entry = ttk.Entry(token_frame, textvariable=self.token_var, show="*", width=40)
        self.token_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.show_token_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(token_frame, text="Show", variable=self.show_token_var, 
                       command=self.toggle_token_visibility).pack(side=tk.LEFT, padx=5)
        
        # Output Directory
        ttk.Label(params_frame, text="Output Directory:").grid(row=5, column=0, sticky=tk.W, pady=5)
        output_frame = ttk.Frame(params_frame)
        output_frame.grid(row=5, column=1, columnspan=3, sticky=(tk.W, tk.E), padx=5)
        
        self.output_dir_var = tk.StringVar(value="./_output")
        self.output_dir_entry = ttk.Entry(output_frame, textvariable=self.output_dir_var, width=35)
        self.output_dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # ✅ Drag & Drop + Right-click for output dir
        if DND_AVAIL:
            self.output_dir_entry.drop_target_register(DND_FILES)
            self.output_dir_entry.dnd_bind('<<Drop>>', lambda e: self.on_drop(e, self.output_dir_entry))
        self.create_context_menu(self.output_dir_entry)
        
        ttk.Button(output_frame, text="Browse", command=self.browse_output_dir).pack(side=tk.LEFT, padx=5)
        
        # Output Formats
        ttk.Label(params_frame, text="Output Formats:").grid(row=6, column=0, sticky=tk.W, pady=5)
        formats_frame = ttk.Frame(params_frame)
        formats_frame.grid(row=6, column=1, columnspan=3, sticky=tk.W, padx=5)
        
        self.format_vars = {}
        formats = ["txt", "srt", "vtt", "json", "tsv"]
        for i, fmt in enumerate(formats):
            var = tk.BooleanVar(value=(fmt == "txt"))
            self.format_vars[fmt] = var
            ttk.Checkbutton(formats_frame, text=fmt.upper(), variable=var).grid(row=0, column=i, padx=5)
        
        # === Progress ===
        self.progress_var = tk.StringVar(value="Ready")
        ttk.Label(main_frame, textvariable=self.progress_var).grid(row=row, column=0, sticky=tk.W, pady=5)
        row += 1
        
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=5)
        row += 1
        
        # === Log ===
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="5")
        log_frame.grid(row=row, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        row += 1
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=80)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # === Buttons ===
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=10)
        
        ttk.Button(button_frame, text="Transcribe", command=self.start_transcription).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Clear Log", command=self.clear_log).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Open Output Folder", command=self.open_output_folder).pack(side=tk.LEFT, padx=5)
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(row-1, weight=1)
    
    def create_context_menu(self, widget):
        """Add right-click context menu to entry widgets"""
        menu = tk.Menu(widget, tearoff=0)
        menu.add_command(label="Cut", command=lambda: widget.event_generate("<<Cut>>"))
        menu.add_command(label="Copy", command=lambda: widget.event_generate("<<Copy>>"))
        menu.add_command(label="Paste", command=lambda: widget.event_generate("<<Paste>>"))
        menu.add_separator()
        menu.add_command(label="Select All", command=lambda: widget.select_range(0, tk.END))
        
        def show_menu(event):
            menu.tk_popup(event.x_root, event.y_root)
        
        widget.bind("<Button-3>", show_menu)
    
    def on_drop(self, event, widget):
        """Handle drag & drop"""
        path = event.data.strip('{}')
        
        # Handle multiple files (take first)
        if '\n' in path:
            path = path.split('\n')[0]
        
        # Clean path
        path = path.strip()
        
        widget.delete(0, tk.END)
        widget.insert(0, path)
        
        # Trigger URL detection if it's the file entry
        if widget == self.file_entry:
            self.detect_url_type(None)
    
    def open_output_folder(self):
        """Open output directory in file explorer"""
        output_dir = Path(self.output_dir_var.get())
        
        if not output_dir.exists():
            response = messagebox.askyesno(
                "Create Directory?",
                f"Output directory doesn't exist:\n{output_dir}\n\nCreate it?"
            )
            if response:
                output_dir.mkdir(parents=True, exist_ok=True)
            else:
                return
        
        # Open in file explorer (cross-platform)
        if sys.platform == 'win32':
            os.startfile(output_dir)
        elif sys.platform == 'darwin':  # macOS
            subprocess.run(['open', output_dir])
        else:  # Linux
            subprocess.run(['xdg-open', output_dir])
        
        self.log(f"📁 Opened: {output_dir}")
    
    def toggle_token_visibility(self):
        if self.show_token_var.get():
            self.token_entry.config(show="")
        else:
            self.token_entry.config(show="*")
    
    def detect_url_type(self, event):
        text = self.file_entry.get().strip()
        
        if not text:
            self.url_type_label.config(text="")
        elif self.is_youtube_url(text):
            self.url_type_label.config(text="🎥 YouTube", foreground="red")
        elif text.startswith(('http://', 'https://')):
            self.url_type_label.config(text="🌐 URL", foreground="blue")
        elif Path(text).exists():
            self.url_type_label.config(text="📁 Local File", foreground="green")
        else:
            self.url_type_label.config(text="⚠ Invalid", foreground="orange")
    
    def is_youtube_url(self, url):
        youtube_domains = ['youtube.com', 'youtu.be', 'youtube-nocookie.com']
        return any(domain in url.lower() for domain in youtube_domains)
    
    def auto_generate_filename(self):
        """Auto-generate filename from source (threaded to prevent freezing)"""
        source = self.file_entry.get().strip()
        
        if not source:
            messagebox.showwarning("No Source", "Please enter a source file/URL first")
            return

        # Start background thread
        self.progress_var.set("Fetching title...")
        thread = threading.Thread(target=self._auto_filename_worker, args=(source,), daemon=True)
        thread.start()

    def _auto_filename_worker(self, source):
        """Background worker for auto_generate_filename"""
        try:
            new_filename = ""
            if self.is_youtube_url(source):
                # Extract YouTube title
                self.log("Fetching YouTube title...")
                with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                    info = ydl.extract_info(source, download=False)
                    title = info['title']
                    new_filename = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
                    self.log(f"✓ Found: {title}")
            
            elif source.startswith(('http://', 'https://')):
                # URL filename
                filename = source.split('/')[-1]
                new_filename = Path(filename).stem
            
            else:
                # Local file
                new_filename = Path(source).stem

            # Update GUI in main thread
            if new_filename:
                self.root.after(0, lambda: self._update_filename_entry(new_filename))
        
        except Exception as e:
            self.root.after(0, lambda: self.log(f"✗ Auto-generate failed: {e}", "error"))
            self.root.after(0, lambda: messagebox.showerror("Error", f"Could not generate filename:\n{e}"))
        finally:
            self.root.after(0, lambda: self.progress_var.set("Ready"))

    def _update_filename_entry(self, name):
        self.filename_entry.delete(0, tk.END)
        self.filename_entry.insert(0, name)
        self.log(f"✓ Generated: {name}")
    
    def browse_file(self):
        filename = filedialog.askopenfilename(
            title="Select Audio File",
            filetypes=[
                ("Audio Files", "*.mp3 *.wav *.m4a *.flac *.ogg *.aac"),
                ("All Files", "*.*")
            ]
        )
        if filename:
            self.file_entry.delete(0, tk.END)
            self.file_entry.insert(0, filename)
            self.detect_url_type(None)
    
    def browse_output_dir(self):
        directory = filedialog.askdirectory(title="Select Output Directory")
        if directory:
            self.output_dir_var.set(directory)
    
    def log(self, message, level="info"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if level == "error":
            prefix = "❌"
        elif level == "warning":
            prefix = "⚠️"
        elif level == "success":
            prefix = "✅"
        else:
            prefix = "ℹ️"
        
        log_message = f"[{timestamp}] {prefix} {message}\n"
        
        self.log_text.insert(tk.END, log_message)
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def clear_log(self):
        self.log_text.delete(1.0, tk.END)
    
    def load_settings(self):
        """Load saved settings"""
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                
                self.model_var.set(settings.get("model", "large-v2"))
                self.language_var.set(settings.get("language", "de"))
                self.compute_var.set(settings.get("compute_type", "int8"))
                self.batch_var.set(settings.get("batch_size", "8"))
                self.diarize_var.set(settings.get("diarize", True))
                self.min_speakers_var.set(settings.get("min_speakers", "2"))
                self.max_speakers_var.set(settings.get("max_speakers", "2"))
                self.token_var.set(settings.get("hf_token", ""))
                self.output_dir_var.set(settings.get("output_dir", "./_output"))
                
                for fmt, enabled in settings.get("formats", {"txt": True}).items():
                    if fmt in self.format_vars:
                        self.format_vars[fmt].set(enabled)
                
                self.log("✓ Settings loaded")
            except Exception as e:
                self.log(f"⚠ Could not load settings: {e}", "warning")
    
    def save_settings(self):
        """Save current settings"""
        settings = {
            "model": self.model_var.get(),
            "language": self.language_var.get(),
            "compute_type": self.compute_var.get(),
            "batch_size": self.batch_var.get(),
            "diarize": self.diarize_var.get(),
            "min_speakers": self.min_speakers_var.get(),
            "max_speakers": self.max_speakers_var.get(),
            "hf_token": self.token_var.get(),
            "output_dir": self.output_dir_var.get(),
            "formats": {fmt: var.get() for fmt, var in self.format_vars.items()}
        }
        
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            self.log(f"⚠ Could not save settings: {e}", "warning")
    
    def start_transcription(self):
        # Validate inputs
        if not self.file_entry.get().strip():
            messagebox.showerror("Error", "Please select a file or enter a URL")
            return
        
        if not self.token_var.get().strip() and self.diarize_var.get():
            messagebox.showerror("Error", "HuggingFace token required for diarization")
            return
        
        # Get selected formats
        formats = [fmt for fmt, var in self.format_vars.items() if var.get()]
        if not formats:
            messagebox.showerror("Error", "Please select at least one output format")
            return
        
        # Save settings
        self.save_settings()
        
        # Prepare settings
        settings = {
            "file": self.file_entry.get().strip(),
            "output_filename": self.filename_entry.get().strip(),
            "model": self.model_var.get(),
            "language": self.language_var.get(),
            "compute_type": self.compute_var.get(),
            "batch_size": int(self.batch_var.get()),
            "diarize": self.diarize_var.get(),
            "min_speakers": int(self.min_speakers_var.get()) if self.diarize_var.get() else None,
            "max_speakers": int(self.max_speakers_var.get()) if self.diarize_var.get() else None,
            "hf_token": self.token_var.get().strip(),
            "output_dir": self.output_dir_var.get(),
            "output_formats": formats
        }
        
        # Run in thread
        thread = threading.Thread(target=self.run_transcription, args=(settings,))
        thread.daemon = True
        thread.start()
    
    def convert_to_wav(self, input_file, output_file):
        """Convert any audio format to WAV using ffmpeg"""
        self.log(f"Converting to WAV: {input_file.name}")
        
        try:
            result = subprocess.run([
                'ffmpeg',
                '-i', str(input_file),
                '-ar', '16000',  # 16kHz sample rate
                '-ac', '1',      # Mono
                '-c:a', 'pcm_s16le',
                '-y',
                str(output_file)
            ], capture_output=True, text=True, check=True)
            
            self.log(f"✓ Converted to WAV (16kHz mono)")
            
        except subprocess.CalledProcessError as e:
            self.log(f"✗ FFmpeg error: {e.stderr}", "error")
            raise
        except FileNotFoundError:
            self.log("✗ FFmpeg not found!", "error")
            raise RuntimeError("FFmpeg not installed")
    
    def get_temp_dir(self):
        """
        Create and return a temporary directory INSIDE the selected output directory.
        Fulfills requirement: 'temp path same as output path'
        """
        output_path = Path(self.output_dir_var.get())
        
        # Ensure output path exists
        if not output_path.exists():
            output_path.mkdir(parents=True, exist_ok=True)
            
        # Create a dedicated temp folder inside the output dir
        temp_path = output_path / "_temp_work"
        temp_path.mkdir(exist_ok=True)
        
        return temp_path

    def get_audio_file(self, file_path):
        """Handle local files, URLs, and YouTube links"""
        
        # Local file
        if Path(file_path).exists():
            local_path = Path(file_path)
            
            # Convert non-WAV formats
            if local_path.suffix.lower() != '.wav':
                self.log(f"Converting local file to WAV: {local_path.name}")
                
                temp_dir = self.get_temp_dir()
                wav_path = temp_dir / f"{local_path.stem}_converted.wav"
                
                self.convert_to_wav(local_path, wav_path)
                
                # ✅ Track temp file for cleanup
                self.temp_files.append(wav_path)
                
                return str(wav_path)
            
            return file_path
        
        # URL or YouTube
        if file_path.startswith(('http://', 'https://')) or self.is_youtube_url(file_path):
            temp_dir = self.get_temp_dir()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # YouTube
            if self.is_youtube_url(file_path):
                self.log(f"Downloading YouTube video: {file_path}")
                
                # ✅ Use unique temp name
                temp_output = temp_dir / f"yt_download_{timestamp}"
                
                ydl_opts = {
                    # Optimization: Prefer m4a/opus (smaller) over best video
                    'format': 'bestaudio[ext=m4a]/bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'wav',
                        'preferredquality': '192',
                    }],
                    'outtmpl': str(temp_output) + '.%(ext)s',
                    'quiet': True,
                    'no_warnings': True,
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(file_path, download=True)
                    
                    # ✅ Find the actual downloaded file
                    downloaded_file = temp_output.with_suffix('.wav')
                    
                    if not downloaded_file.exists():
                        # Fallback search
                        possible_files = list(temp_dir.glob(f"yt_download_{timestamp}*.wav"))
                        if possible_files:
                            downloaded_file = possible_files[0]
                        else:
                            raise FileNotFoundError(f"Downloaded WAV not found in {temp_dir}")
                    
                    self.log(f"✓ Downloaded as WAV: {downloaded_file.name}")
                    return str(downloaded_file)
            
            # Regular URL
            else:
                self.log(f"Downloading from URL: {file_path}")
                
                filename = file_path.split('/')[-1]
                base_name = Path(filename).stem
                
                # Download to temp
                temp_file = temp_dir / f"{base_name}_{timestamp}_temp"
                
                response = requests.get(file_path, stream=True)
                response.raise_for_status()
                
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                with open(temp_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size:
                            percent = (downloaded / total_size) * 100
                            self.progress_var.set(f"Downloading: {percent:.1f}%")
                
                self.log(f"✓ Downloaded: {temp_file.name}")
                
                # Convert to WAV
                wav_file = temp_dir / f"{base_name}_{timestamp}.wav"
                self.convert_to_wav(temp_file, wav_file)
                
                # ✅ Delete raw temp, keep WAV temporarily
                try:
                    temp_file.unlink()
                except:
                    pass
                
                return str(wav_file)
    
        raise ValueError(f"Invalid file path: {file_path}")

    def cleanup_temp_files(self):
        """Delete temporary WAV files"""
        for temp_file in self.temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
                    self.log(f"🗑️ Deleted temp: {temp_file.name}")
            except Exception as e:
                self.log(f"⚠ Could not delete {temp_file.name}: {e}", "warning")
        
        self.temp_files.clear()
        
        # Try to remove the temp directory if empty
        try:
            temp_dir = self.get_temp_dir()
            if temp_dir.exists() and not any(temp_dir.iterdir()):
                temp_dir.rmdir()
                self.log("🗑️ Cleaned up empty temp folder")
        except:
            pass
    
    def ask_cleanup_source(self, source_path):
        """Ask user if downloaded source file should be deleted"""
        response = messagebox.askyesno(
            "Delete Source File?",
            f"Delete downloaded source file?\n\n"
            f"File: {source_path.name}\n"
            f"Size: {source_path.stat().st_size / (1024*1024):.1f} MB\n\n"
            f"(Temporary WAV files are always deleted)"
        )
        
        if response:
            try:
                source_path.unlink()
                self.log(f"🗑️ Deleted source: {source_path.name}")
                messagebox.showinfo("Deleted", f"Source file deleted:\n{source_path.name}")
            except Exception as e:
                self.log(f"✗ Delete failed: {e}", "error")
                messagebox.showerror("Error", f"Could not delete:\n{e}")
        else:
            self.log(f"📦 Kept source: {source_path.name}")
    
    def run_transcription(self, settings):
        try:
            self.progress.start()
            self.temp_files.clear()  # Reset temp tracking

            # Get audio file (download/convert if needed)
            self.progress_var.set("Preparing audio file...")
            self.log("=" * 60)
            self.log("Starting transcription...")
            self.log("=" * 60)

            original_input = settings["file"]
            audio_file = self.get_audio_file(original_input)
            audio_path = Path(audio_file)

            # Check if this was a download (URL or YouTube)
            is_downloaded = (
                original_input.startswith(('http://', 'https://')) or 
                self.is_youtube_url(original_input)
            )

            self.log(f"Processing: {audio_path.name}")

            # Rename BEFORE transcription (safe now)
            if settings["output_filename"] and settings["output_filename"] != audio_path.stem:
                new_name = settings["output_filename"]
                # Clean filename
                new_name = "".join(c for c in new_name if c.isalnum() or c in (' ', '-', '_', '.')).strip()

                new_path = audio_path.parent / f"{new_name}.wav"

                # Handle existing file
                if new_path.exists():
                    response = messagebox.askyesno(
                        "File exists",
                        f"File already exists in temp:\n{new_path.name}\n\nOverwrite?"
                    )
                    if response:
                        new_path.unlink()
                        self.log(f"Deleted existing temp file: {new_path.name}")
                    else:
                        self.log("✗ User cancelled - file exists", "error")
                        self.cleanup_temp_files()
                        return

                try:
                    audio_path.rename(new_path)
                    audio_path = new_path
                    audio_file = str(audio_path)
                    self.log(f"✓ Renamed temp file to: {audio_path.name}")
                except Exception as e:
                    self.log(f"⚠ Rename failed, using original name: {e}", "warning")

            # Load model
            self.progress_var.set("Loading model...")
            self.log(f"Loading model: {settings['model']}")

            device = "cuda" if torch.cuda.is_available() else "cpu"
            compute_type = settings["compute_type"]

            model = whisperx.load_model(
                settings["model"],
                device,
                compute_type=compute_type
            )

            self.log(f"✓ Model loaded on {device}")

            # Load audio
            self.progress_var.set("Loading audio...")
            self.log(f"Loading audio: {audio_path.name}")

            audio = whisperx.load_audio(audio_file)
            self.log(f"✓ Audio loaded ({len(audio)/16000:.1f}s)")

            # Transcribe
            self.progress_var.set("Transcribing...")
            self.log("Transcribing...")

            language = settings["language"] if settings["language"] else None

            result = model.transcribe(
                audio,
                batch_size=settings["batch_size"],
                language=language
            )

            self.log(f"✓ Transcription complete")
            self.log(f"  Language: {result.get('language', 'unknown')}")
            self.log(f"  Segments: {len(result.get('segments', []))}")

            # Alignment
            self.progress_var.set("Aligning...")
            self.log("Aligning timestamps...")

            model_a, metadata = whisperx.load_align_model(
                language_code=result["language"],
                device=device
            )

            result = whisperx.align(
                result["segments"],
                model_a,
                metadata,
                audio,
                device,
                return_char_alignments=False
            )

            self.log(f"✓ Alignment complete")

            # Diarization
            if settings["diarize"] and settings["hf_token"]:
                self.progress_var.set("Diarizing speakers...")
                min_spk = settings.get("min_speakers", 1)
                max_spk = settings.get("max_speakers", 2)
                self.log(f"Diarizing speakers ({min_spk}-{max_spk})...")
                
                try:
                    from whisperx.diarize import DiarizationPipeline
                    
                    diarize_model = DiarizationPipeline(
                        use_auth_token=settings["hf_token"],
                        device=device
                    )
                    
                    # Pass audio waveform, not path
                    diarize_segments = diarize_model(
                        audio,
                        min_speakers=min_spk,
                        max_speakers=max_spk
                    )
                    
                    result = whisperx.assign_word_speakers(diarize_segments, result)
                    self.log("✓ Diarization complete")
                    
                except Exception as e:
                    self.log(f"⚠ Diarization failed: {e}", "warning")
                    self.log("Continuing without speaker labels...")

            # === EXPORT ===
            self.progress_var.set("Exporting results...")
            
            output_dir = Path(settings["output_dir"])
            output_dir.mkdir(parents=True, exist_ok=True)

            # Determine output filename
            if settings["output_filename"]:
                output_name = settings["output_filename"]
                output_name = "".join(c for c in output_name if c.isalnum() or c in (' ', '-', '_', '.')).strip()
            else:
                output_name = audio_path.stem

            self.log(f"Exporting to: {output_dir}")
            
            from whisperx.utils import get_writer
            
            exported_files = []
            
            for fmt in settings["output_formats"]:
                if fmt == "all":
                    for sub_fmt in ["txt", "srt", "vtt", "tsv", "json"]:
                        output_file = output_dir / f"{output_name}.{sub_fmt}"
                        try:
                            writer = get_writer(sub_fmt, str(output_dir))
                            writer(result, str(output_file.stem), {
                                "max_line_width": None,
                                "max_line_count": None,
                                "highlight_words": False
                            })
                            exported_files.append(output_file)
                            self.log(f"✓ Exported: {output_file.name}")
                        except Exception as e:
                            self.log(f"⚠ Failed to export {sub_fmt}: {e}", "warning")
                    continue
                
                output_file = output_dir / f"{output_name}.{fmt}"
                
                try:
                    writer = get_writer(fmt, str(output_dir))
                    writer(result, str(output_file.stem), {
                        "max_line_width": None,
                        "max_line_count": None,
                        "highlight_words": False
                    })
                    exported_files.append(output_file)
                    self.log(f"✓ Exported: {output_file.name}")
                    
                except Exception as e:
                    self.log(f"⚠ Failed to export {fmt}: {e}", "warning")
                    import traceback
                    self.log(f"  Details: {traceback.format_exc()}", "warning")

            # Cleanup
            self.progress.stop()
            self.progress_var.set("Complete!")

            # Cleanup Logic
            # Check if current audio_path is inside our temp dir
            temp_dir = self.get_temp_dir()
            is_in_temp = temp_dir in audio_path.parents

            if is_in_temp:
                if is_downloaded:
                    # If it was a download, ask user if they want to keep the WAV
                    # (Usually we assume users want the text, not the wav, but logic is preserved)
                    self.root.after(0, lambda: self.ask_cleanup_source(audio_path))
                else:
                    # It was a local file converted to WAV -> Auto delete temp WAV
                    try:
                        audio_path.unlink()
                        self.log(f"🗑️ Deleted temp wav: {audio_path.name}")
                    except Exception as e:
                        self.log(f"⚠ Could not delete temp: {e}", "warning")
            
            # Final attempt to clean temp dir if empty
            self.root.after(1000, self.cleanup_temp_files)

            # Success message
            self.log("="*60)
            self.log("✓ Transcription complete!")
            self.log(f"  Output: {output_dir}")
            self.log("="*60)
            
            self.root.after(0, lambda: messagebox.showinfo(
                "Success",
                f"Transcription complete!\n\n"
                f"Output: {output_dir}\n"
                f"Files: {len(exported_files)}"
            ))

            # Cleanup memory
            del model
            if settings["diarize"]:
                try:
                    del diarize_model
                except:
                    pass
            gc.collect()
            torch.cuda.empty_cache()

        except Exception as e:
            self.progress.stop()
            self.progress_var.set("Error!")
            self.log(f"✗ Error: {str(e)}", "error")

            import traceback
            self.log(f"Traceback:\n{traceback.format_exc()}", "error")

            self.root.after(0, lambda: messagebox.showerror(
                "Error", 
                f"Transcription failed:\n\n{str(e)}"
            ))

            self.cleanup_temp_files()

def main():
    if DND_AVAIL and len(sys.argv) > 1:
        root = TkinterDnD.Tk()
    elif DND_AVAIL:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()

    app = MindscribeGUI(root)
    
    if len(sys.argv) > 1:
        app.file_entry.insert(0, sys.argv[1])
        app.detect_url_type(None)
    
    root.mainloop()

if __name__ == "__main__":
    main()