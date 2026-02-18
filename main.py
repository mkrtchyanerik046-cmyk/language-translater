import whisper
import pyaudio
import wave
import tempfile
import os
from transformers import pipeline
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import time

# Try to import ElevenLabs, but handle the case where it's not available
try:
    from elevenlabs.client import ElevenLabs
    from elevenlabs.play import play
    ELEVENLABS_AVAILABLE = True
except TypeError as e:
    if "follow_redirects" in str(e):
        print("ElevenLabs library error detected. Please upgrade httpx with: pip install --upgrade httpx")
        ELEVENLABS_AVAILABLE = False
    else:
        ELEVENLABS_AVAILABLE = False
except ImportError:
    ELEVENLABS_AVAILABLE = False
except Exception as e:
    print(f"ElevenLabs initialization error: {e}")
    ELEVENLABS_AVAILABLE = False

# Load models
model = whisper.load_model("tiny", device="cpu")

class SpeechTranslatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Speech Translator - English to Armenian")
        self.root.geometry("700x600")
        self.root.configure(bg="#f0f0f0")
        
        # Variables
        self.is_recording = False
        self.audio_frames = []
        self.temp_filename = None
        self.audio_instance = None
        self.stream = None
        
        # Create UI
        self.create_widgets()
        
        # Audio setup
        self.audio_format = pyaudio.paInt16
        self.channels = 1
        self.rate = 44100
        self.chunk = 1024
        self.record_seconds = 10  # Default recording duration
        
        # Initialize ElevenLabs client if available
        if ELEVENLABS_AVAILABLE:
            try:
                self.elevenlabs_client = ElevenLabs(
                    api_key="sk_229bed1791be92aa755346230309e66931262703e4dfa2be"  # Replace with your actual API key
                )
                self.elevenlabs_available = True
            except Exception as e:
                print(f"Could not initialize ElevenLabs: {e}")
                self.elevenlabs_available = False
        else:
            self.elevenlabs_available = False
        
    def create_widgets(self):
        # Main frame
        main_frame = tk.Frame(self.root, bg="#f0f0f0", padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = tk.Label(main_frame, text="Speech Translator", font=("Arial", 20, "bold"), bg="#f0f0f0", fg="#333")
        title_label.pack(pady=(0, 20))
        
        # Description
        desc_label = tk.Label(main_frame, text="Record your speech, see the English transcription, and get the Armenian translation", 
                             font=("Arial", 12), bg="#f0f0f0", fg="#666")
        desc_label.pack(pady=(0, 20))
        
        # Recording frame
        record_frame = tk.Frame(main_frame, bg="#f0f0f0")
        record_frame.pack(pady=(0, 20))
        
        # Record button
        self.record_button = tk.Button(record_frame, text="Start Recording", font=("Arial", 14), 
                                     command=self.toggle_recording, bg="#4CAF50", fg="white", 
                                     activebackground="#45a049", height=2, width=15)
        self.record_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Status label
        self.status_label = tk.Label(record_frame, text="Ready to record", font=("Arial", 12), 
                                    bg="#f0f0f0", fg="#333")
        self.status_label.pack(side=tk.LEFT)
        
        # Recording timer
        self.timer_label = tk.Label(record_frame, text="", font=("Arial", 12), bg="#f0f0f0", fg="#333")
        self.timer_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(main_frame, orient="horizontal", length=500, mode="determinate")
        self.progress_bar.pack(pady=(10, 20))
        
        # English text section
        english_frame = tk.LabelFrame(main_frame, text="English Text", font=("Arial", 12, "bold"), 
                                    bg="#f0f0f0", fg="#333", padx=10, pady=10)
        english_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.english_text = scrolledtext.ScrolledText(english_frame, wrap=tk.WORD, width=70, height=6,
                                                     font=("Arial", 11), bg="white", fg="#333")
        self.english_text.pack(fill=tk.BOTH, expand=True)
        
        # Armenian text section
        armenian_frame = tk.LabelFrame(main_frame, text="Armenian Translation", font=("Arial", 12, "bold"), 
                                     bg="#f0f0f0", fg="#333", padx=10, pady=10)
        armenian_frame.pack(fill=tk.BOTH, expand=True)
        
        self.armenian_text = scrolledtext.ScrolledText(armenian_frame, wrap=tk.WORD, width=70, height=6,
                                                      font=("Arial", 11), bg="white", fg="#333")
        self.armenian_text.pack(fill=tk.BOTH, expand=True)
        
        # Clear button
        clear_button = tk.Button(main_frame, text="Clear All", command=self.clear_all, 
                                font=("Arial", 12), bg="#f44336", fg="white", 
                                activebackground="#da190b", height=1, width=10)
        clear_button.pack(pady=(20, 0))
        
        # Text-to-speech buttons frame (only show if ElevenLabs is available)
        if ELEVENLABS_AVAILABLE:
            tts_frame = tk.Frame(main_frame, bg="#f0f0f0")
            tts_frame.pack(pady=(10, 0))
            
            # English TTS button
            self.english_tts_button = tk.Button(tts_frame, text="Listen English", font=("Arial", 12),
                                              command=self.speak_english, bg="#2196F3", fg="white",
                                              activebackground="#1976D2", height=1, width=12)
            self.english_tts_button.pack(side=tk.LEFT, padx=(0, 10))
            
            # Armenian TTS button
            self.armenian_tts_button = tk.Button(tts_frame, text="Listen Armenian", font=("Arial", 12),
                                               command=self.speak_armenian, bg="#FF9800", fg="white",
                                               activebackground="#F57C00", height=1, width=12)
            self.armenian_tts_button.pack(side=tk.LEFT)
        else:
            # Show a label explaining that TTS is not available
            tts_unavailable_label = tk.Label(main_frame, text="Text-to-Speech not available (requires ElevenLabs)", 
                                           font=("Arial", 10), bg="#f0f0f0", fg="#999")
            tts_unavailable_label.pack(pady=(10, 0))
            
    def toggle_recording(self):
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()
    
    def start_recording(self):
        self.is_recording = True
        self.audio_frames = []
        self.record_button.config(text="Stop Recording", bg="#f44336", activebackground="#da190b")
        self.status_label.config(text="Recording...")
        
        # Initialize audio
        self.audio_instance = pyaudio.PyAudio()
        self.stream = self.audio_instance.open(format=self.audio_format,
                                              channels=self.channels,
                                              rate=self.rate,
                                              input=True,
                                              frames_per_buffer=self.chunk)
        
        # Start recording in a separate thread
        self.recording_thread = threading.Thread(target=self.record_audio)
        self.recording_thread.start()
        
        # Update timer
        self.update_timer()
    
    def stop_recording(self):
        self.is_recording = False
        self.record_button.config(text="Start Recording", bg="#4CAF50", activebackground="#45a049")
        self.status_label.config(text="Processing...")
        self.progress_bar['value'] = 0
        
        # Close audio stream
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.audio_instance:
            self.audio_instance.terminate()
        
        # Save audio and process in a separate thread
        processing_thread = threading.Thread(target=self.process_audio)
        processing_thread.start()
    
    def record_audio(self):
        while self.is_recording:
            data = self.stream.read(self.chunk)
            self.audio_frames.append(data)
    
    def update_timer(self):
        if self.is_recording:
            elapsed = len(self.audio_frames) * self.chunk / self.rate
            remaining = max(0, self.record_seconds - elapsed)
            self.timer_label.config(text=f"Time left: {remaining:.1f}s")
            
            # Update progress bar
            progress = min(100, (elapsed / self.record_seconds) * 100)
            self.progress_bar['value'] = progress
            
            # Stop recording after specified duration
            if elapsed >= self.record_seconds:
                self.stop_recording()
            else:
                self.root.after(100, self.update_timer)
    
    def process_audio(self):
        # Save recorded audio to a temporary WAV file
        try:
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
                wf = wave.open(temp_wav.name, 'wb')
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.audio_instance.get_sample_size(self.audio_format))
                wf.setframerate(self.rate)
                wf.writeframes(b''.join(self.audio_frames))
                wf.close()
                self.temp_filename = temp_wav.name
            
            # Transcribe the audio
            self.root.after(0, lambda: self.status_label.config(text="Transcribing..."))
            result = model.transcribe(self.temp_filename, fp16=False)
            english_text = result["text"]
            
            # Update English text in main thread
            self.root.after(0, lambda: self.english_text.delete(1.0, tk.END))
            self.root.after(0, lambda: self.english_text.insert(tk.END, english_text))
            
            # Translate to Armenian
            self.root.after(0, lambda: self.status_label.config(text="Translating..."))
            translator = pipeline(
                "translation",
                model="facebook/nllb-200-distilled-600M",
                src_lang="eng_Latn",
                tgt_lang="hye_Armn"
            )
            armenian_result = translator(english_text)
            armenian_text = armenian_result[0]["translation_text"]
            
            # Update Armenian text in main thread
            self.root.after(0, lambda: self.armenian_text.delete(1.0, tk.END))
            self.root.after(0, lambda: self.armenian_text.insert(tk.END, armenian_text))
            
            # Update status
            self.root.after(0, lambda: self.status_label.config(text="Ready"))
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"An error occurred: {str(e)}"))
            self.root.after(0, lambda: self.status_label.config(text="Error occurred"))
        finally:
            # Clean up temporary file
            if self.temp_filename and os.path.exists(self.temp_filename):
                os.remove(self.temp_filename)
    
    def speak_english(self):
        if not self.elevenlabs_available:
            messagebox.showwarning("Warning", "ElevenLabs is not available. Please install the required dependencies.")
            return
            
        english_text = self.english_text.get(1.0, tk.END).strip()
        print(f"DEBUG: English text to speak: {repr(english_text[:100])}")  # Debug output
        if english_text:
            self.status_label.config(text="Playing English...")
            try:
                audio = self.elevenlabs_client.text_to_speech.convert(
                    text=english_text,
                    voice_id="JBFqnCBsd6RMkjVDRZzb",
                    model_id="eleven_multilingual_v2",
                    output_format="mp3_44100_128"
                )
                print(f"DEBUG: Audio received from ElevenLabs, type: {type(audio)}")  # Debug output
                play(audio)
                self.status_label.config(text="English played")
            except Exception as e:
                messagebox.showerror("Error", f"Could not play English audio: {str(e)}")
                self.status_label.config(text="Ready")
        else:
            messagebox.showinfo("Info", "No English text to speak")
    
    def speak_armenian(self):
        if not self.elevenlabs_available:
            messagebox.showwarning("Warning", "ElevenLabs is not available. Please install the required dependencies.")
            return
            
        armenian_text = self.armenian_text.get(1.0, tk.END).strip()
        print(f"DEBUG: Armenian text to speak: {repr(armenian_text[:100])}")  # Debug output
        if armenian_text:
            self.status_label.config(text="Playing Armenian...")
            try:
                audio = self.elevenlabs_client.text_to_speech.convert(
                    text=armenian_text,
                    voice_id="JBFqnCBsd6RMkjVDRZzb",
                    model_id="eleven_multilingual_v2",
                    output_format="mp3_44100_128"
                )
                print(f"DEBUG: Audio received from ElevenLabs, type: {type(audio)}")  # Debug output
                play(audio)
                self.status_label.config(text="Armenian played")
            except Exception as e:
                messagebox.showerror("Error", f"Could not play Armenian audio: {str(e)}")
                self.status_label.config(text="Ready")
        else:
            messagebox.showinfo("Info", "No Armenian text to speak")
    
    def clear_all(self):
        self.english_text.delete(1.0, tk.END)
        self.armenian_text.delete(1.0, tk.END)
        self.status_label.config(text="Cleared. Ready to record.")
        time.sleep(1)
        self.status_label.config(text="Ready to record")

# Create and run the application
if __name__ == "__main__":
    root = tk.Tk()
    app = SpeechTranslatorApp(root)
    root.mainloop()
        
