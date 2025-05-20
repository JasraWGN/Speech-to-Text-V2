import os
import sys
import json
import wave
import logging
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox, filedialog
import pyaudio
from vosk import Model, KaldiRecognizer

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("VoskSpeechToText")

class VoskSpeechToText:
    def __init__(self, root):
        logger.debug("Initializing VoskSpeechToText application")
        self.root = root
        self.root.title("Vosk Speech-to-Text")
        self.root.geometry("800x600")
        self.root.minsize(600, 400)
        
        # Initialize variables
        self.is_listening = False
        self.transcription_text = ""
        self.thread = None
        self.model = None
        self.recognizer = None
        self.audio = None
        self.stream = None
        
        # Create GUI elements
        self.create_widgets()
        
        # Configure model path
        self.model_path = os.path.join(os.getcwd(), "model")
        self.check_model_button.config(state=tk.NORMAL)
        
        logger.debug("Application initialized successfully")
    
    def create_widgets(self):
        """Create and configure all GUI elements"""
        logger.debug("Creating GUI widgets")
        
        # Status frame
        status_frame = tk.Frame(self.root)
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.status_label = tk.Label(status_frame, text="Status: Ready", font=("Arial", 10))
        self.status_label.pack(side=tk.LEFT)
        
        self.status_indicator = tk.Canvas(status_frame, width=20, height=20, bg=self.root["bg"], highlightthickness=0)
        self.status_indicator.pack(side=tk.LEFT, padx=5)
        self.status_indicator.create_oval(2, 2, 18, 18, fill="gray", outline="black", tags="indicator")
        
        # Model frame
        model_frame = tk.Frame(self.root)
        model_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(model_frame, text="Vosk Model Path:").pack(side=tk.LEFT, padx=5)
        
        self.model_path_var = tk.StringVar(value="./model")
        self.model_path_entry = tk.Entry(model_frame, textvariable=self.model_path_var, width=40)
        self.model_path_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        self.browse_button = tk.Button(model_frame, text="Browse", command=self.browse_model)
        self.browse_button.pack(side=tk.LEFT, padx=5)
        
        self.check_model_button = tk.Button(model_frame, text="Check Model", command=self.check_model)
        self.check_model_button.pack(side=tk.LEFT, padx=5)
        
        # Control buttons frame
        control_frame = tk.Frame(self.root)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.start_button = tk.Button(control_frame, text="Start Listening", command=self.start_listening, state=tk.DISABLED)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = tk.Button(control_frame, text="Stop Listening", command=self.stop_listening, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        self.clear_button = tk.Button(control_frame, text="Clear Transcript", command=self.clear_transcript)
        self.clear_button.pack(side=tk.LEFT, padx=5)
        
        self.save_button = tk.Button(control_frame, text="Save Transcript", command=self.save_transcript)
        self.save_button.pack(side=tk.LEFT, padx=5)
        
        # Transcription area
        frame = tk.Frame(self.root)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        tk.Label(frame, text="Transcription:").pack(anchor=tk.W)
        
        self.transcript_text = scrolledtext.ScrolledText(frame, wrap=tk.WORD, font=("Arial", 12))
        self.transcript_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Debug frame
        debug_frame = tk.Frame(self.root)
        debug_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(debug_frame, text="Debug Log:").pack(anchor=tk.W)
        
        self.debug_text = scrolledtext.ScrolledText(debug_frame, wrap=tk.WORD, height=6, font=("Courier", 9))
        self.debug_text.pack(fill=tk.X, expand=False, padx=5, pady=5)
        
        # Add log handler to show logs in debug text
        self.log_handler = TextHandler(self.debug_text)
        self.log_handler.setLevel(logging.DEBUG)
        logger.addHandler(self.log_handler)
        
        logger.debug("GUI widgets created successfully")
    
    def browse_model(self):
        """Open file dialog to select Vosk model directory"""
        logger.debug("Browsing for model directory")
        model_dir = filedialog.askdirectory(title="Select Vosk Model Directory")
        if model_dir:
            self.model_path_var.set(model_dir)
            logger.debug(f"Model directory selected: {model_dir}")
    
    def check_model(self):
        """Check if the Vosk model exists at the specified path"""
        model_path = self.model_path_var.get()
        logger.debug(f"Checking model at path: {model_path}")
        
        if not os.path.exists(model_path):
            logger.error(f"Model path does not exist: {model_path}")
            messagebox.showerror("Model Error", f"Model directory not found: {model_path}")
            return
        
        try:
            logger.debug("Loading Vosk model...")
            self.model = Model(model_path)
            logger.info("Vosk model loaded successfully")
            messagebox.showinfo("Model Check", "Vosk model loaded successfully!")
            self.start_button.config(state=tk.NORMAL)
        except Exception as e:
            logger.error(f"Error loading Vosk model: {str(e)}")
            messagebox.showerror("Model Error", f"Failed to load Vosk model: {str(e)}")
    
    def start_listening(self):
        """Start the speech recognition thread"""
        if self.is_listening:
            logger.debug("Already listening, ignoring start request")
            return
        
        logger.debug("Starting speech recognition")
        self.is_listening = True
        self.update_status("Listening...", "green")
        
        # Initialize PyAudio
        try:
            self.audio = pyaudio.PyAudio()
            self.recognizer = KaldiRecognizer(self.model, 16000)
            
            # Start recognition thread
            self.thread = threading.Thread(target=self.recognize_speech)
            self.thread.daemon = True
            self.thread.start()
            
            # Update UI
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.check_model_button.config(state=tk.DISABLED)
            
            logger.info("Speech recognition started")
        except Exception as e:
            self.is_listening = False
            logger.error(f"Error starting speech recognition: {str(e)}")
            messagebox.showerror("Start Error", f"Failed to start speech recognition: {str(e)}")
            self.update_status("Error", "red")
    
    def stop_listening(self):
        """Stop the speech recognition thread"""
        if not self.is_listening:
            logger.debug("Not listening, ignoring stop request")
            return
        
        logger.debug("Stopping speech recognition")
        self.is_listening = False
        self.update_status("Stopped", "gray")
        
        # Close audio stream
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception as e:
                logger.error(f"Error closing audio stream: {str(e)}")
        
        # Close PyAudio
        if self.audio:
            self.audio.terminate()
            self.audio = None
        
        # Update UI
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.check_model_button.config(state=tk.NORMAL)
        
        logger.info("Speech recognition stopped")
    
    def recognize_speech(self):
        """Main speech recognition function running in a separate thread"""
        logger.debug("Starting speech recognition thread")
        
        try:
            # Open microphone stream
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=8000
            )
            self.stream.start_stream()
            
            logger.debug("Microphone stream opened")
            
            # Main recognition loop
            while self.is_listening:
                try:
                    data = self.stream.read(4000, exception_on_overflow=False)
                    
                    if len(data) == 0:
                        logger.debug("Empty audio data received")
                        continue
                    
                    if self.recognizer.AcceptWaveform(data):
                        result = json.loads(self.recognizer.Result())
                        transcript = result.get("text", "")
                        
                        if transcript:
                            logger.debug(f"Recognized: {transcript}")
                            self.add_transcript(transcript)
                    else:
                        # Partial result
                        partial = json.loads(self.recognizer.PartialResult())
                        partial_text = partial.get("partial", "")
                        
                        if partial_text:
                            self.update_partial(partial_text)
                
                except Exception as e:
                    logger.error(f"Error in recognition loop: {str(e)}")
                    if not self.is_listening:
                        break
            
            logger.debug("Recognition thread exiting")
            
        except Exception as e:
            logger.error(f"Error in speech recognition thread: {str(e)}")
            self.is_listening = False
            self.root.after(0, lambda: self.update_status("Error", "red"))
    
    def add_transcript(self, text):
        """Add transcribed text to the transcript area"""
        self.root.after(0, lambda: self._add_transcript_impl(text))
    
    def _add_transcript_impl(self, text):
        """Implementation of add_transcript to be called from the main thread"""
        if text.strip():
            current_text = self.transcript_text.get("1.0", tk.END).strip()
            if current_text:
                self.transcript_text.insert(tk.END, " " + text.strip() + "\n")
            else:
                self.transcript_text.insert(tk.END, text.strip() + "\n")
            self.transcript_text.see(tk.END)
    
    def update_partial(self, text):
        """Update the partial result display"""
        self.root.after(0, lambda: self._update_partial_impl(text))
    
    def _update_partial_impl(self, text):
        """Implementation of update_partial to be called from the main thread"""
        # Update status to show we're getting partial results
        self.status_label.config(text=f"Status: Listening... [Partial: {text[:20]}{'...' if len(text) > 20 else ''}]")
    
    def update_status(self, status_text, color):
        """Update the status display"""
        self.root.after(0, lambda: self._update_status_impl(status_text, color))
    
    def _update_status_impl(self, status_text, color):
        """Implementation of update_status to be called from the main thread"""
        self.status_label.config(text=f"Status: {status_text}")
        self.status_indicator.itemconfig("indicator", fill=color)
    
    def clear_transcript(self):
        """Clear the transcript text area"""
        logger.debug("Clearing transcript")
        self.transcript_text.delete("1.0", tk.END)
    
    def save_transcript(self):
        """Save the transcript to a text file"""
        transcript = self.transcript_text.get("1.0", tk.END).strip()
        if not transcript:
            logger.debug("No transcript to save")
            messagebox.showinfo("Save Transcript", "No transcript to save.")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Save Transcript"
        )
        
        if filename:
            logger.debug(f"Saving transcript to {filename}")
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(transcript)
                logger.info(f"Transcript saved to {filename}")
                messagebox.showinfo("Save Transcript", f"Transcript saved to {filename}")
            except Exception as e:
                logger.error(f"Error saving transcript: {str(e)}")
                messagebox.showerror("Save Error", f"Failed to save transcript: {str(e)}")


class TextHandler(logging.Handler):
    """Custom log handler to redirect logs to tkinter Text widget"""
    def __init__(self, text_widget):
        logging.Handler.__init__(self)
        self.text_widget = text_widget
        self.text_widget.config(state=tk.DISABLED)
        self.text_widget.tag_config("INFO", foreground="black")
        self.text_widget.tag_config("DEBUG", foreground="gray")
        self.text_widget.tag_config("WARNING", foreground="orange")
        self.text_widget.tag_config("ERROR", foreground="red")
        self.text_widget.tag_config("CRITICAL", foreground="red", underline=1)
    
    def emit(self, record):
        msg = self.format(record)
        
        def append():
            self.text_widget.config(state=tk.NORMAL)
            self.text_widget.insert(tk.END, msg + "\n", record.levelname)
            self.text_widget.see(tk.END)
            self.text_widget.config(state=tk.DISABLED)
        
        # Schedule insertion in the main thread
        self.text_widget.after(0, append)


def main():
    """Main function to start the application"""
    logger.info("Starting Vosk Speech-to-Text application")
    
    # Create main window
    root = tk.Tk()
    app = VoskSpeechToText(root)

    # Set up proper closing
    def on_closing():
        if app.is_listening:
            app.stop_listening()
        logger.info("Application closing")
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # Start the main loop
    logger.info("Entering main loop")
    root.mainloop()


if __name__ == "__main__":
    main()