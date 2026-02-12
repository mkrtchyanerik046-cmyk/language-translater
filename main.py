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
# Load models
model = whisper.load_model("turbo", device="cpu")

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
        
