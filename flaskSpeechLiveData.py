from flask import Flask, jsonify, render_template
import os
import soundcard as sc
import numpy as np
import asyncio
import time
from collections import deque
from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import TranscriptEvent
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import warnings
import threading
from dotenv import load_dotenv

load_dotenv()

# Suppress matplotlib warnings
warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")

# Flask app setup
app = Flask(__name__)

timestamps = []
speech_rates = []
filler_percentages = []


# Global dictionary for latest metrics
latest_metrics = {
    "timestamp": 0,
    "speech_rate": 0,
    "filler_percentage": 0
}

# Flask route to serve HTML page
@app.route('/')
def index():
    return render_template("index.html")

# Flask route to provide metrics data as JSON
@app.route('/metrics', methods=['GET'])
def get_metrics():
    return jsonify(latest_metrics)

# Function to start Flask server in a separate thread
def start_flask():
    app.run(port=5000, debug=False, use_reloader=False)

# Metrics tracking class
class SpeechMetrics:
    def __init__(self, window_seconds=60):
        self.filler_words = {
            'um': 0, 'uh': 0, 'er': 0, 'ah': 0, 'like': 0,
            'you know': 0, 'sort of': 0, 'kind of': 0
        }
        self.total_words = 0
        self.window_seconds = window_seconds
        self.word_timestamps = deque()
        self.start_time = time.time()

    def add_words(self, text: str):
        current_time = time.time()
        words = text.lower().split()

        self.total_words += len(words)

        # Record timestamps for each word to calculate speech rate
        for _ in words:
            self.word_timestamps.append(current_time)

        # Remove words outside the time window
        while (self.word_timestamps and
               current_time - self.word_timestamps[0] > self.window_seconds):
            self.word_timestamps.popleft()

        # Count filler words
        for filler in self.filler_words:
            self.filler_words[filler] += text.lower().count(filler)

    def get_speech_rate(self):
        if not self.word_timestamps:
            return 0

        current_time = time.time()
        window_words = len([t for t in self.word_timestamps
                            if current_time - t <= self.window_seconds])

        minutes = min(self.window_seconds / 60,
                      (current_time - self.start_time) / 60)
        return ((window_words / minutes) / 10) if minutes > 0 else 0

    def get_filler_percentage(self):
        total_fillers = sum(self.filler_words.values())
        return (total_fillers / self.total_words) * 100 if self.total_words > 0 else 0

metrics = SpeechMetrics(window_seconds=60)

class MyEventHandler(TranscriptResultStreamHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_printed_words = set()

    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        results = transcript_event.transcript.results

        for result in results:
            for alt in result.alternatives:
                words = alt.transcript.strip().split()
                current_words = set(words)

                metrics.add_words(alt.transcript)

                # Display live words
                new_words = current_words - self.last_printed_words
                for word in words:
                    if word in new_words:
                        print(word, end=' ', flush=True)

                self.last_printed_words = current_words if result.is_partial else set()

# Update global metrics dictionary for Flask
def update_global_metrics():
    latest_metrics["timestamp"] = round(time.time() - metrics.start_time, 1)
    latest_metrics["speech_rate"] = metrics.get_speech_rate()
    latest_metrics["filler_percentage"] = metrics.get_filler_percentage()

# Function to periodically update metrics for tkinter and Flask
def update_metrics():
    current_time = round(time.time() - metrics.start_time, 1)
    speech_rate = metrics.get_speech_rate()
    filler_percentage = metrics.get_filler_percentage()

    timestamps.append(current_time)
    speech_rates.append(speech_rate)
    filler_percentages.append(filler_percentage)

    # Log metrics for verification
    print(
        f"Time: {current_time}s | Speech Rate: {speech_rate:.2f} words/min | "
        f"Filler Word Usage: {filler_percentage:.2f}%"
    )

    # Update tkinter labels
    speech_rate_label.config(text=f"{speech_rate:.2f} words/min")
    filler_percentage_label.config(text=f"{filler_percentage:.2f}%")

    # Update global metrics for Flask
    update_global_metrics()

def update_graph():
    update_metrics()

    ax_speech_rate.clear()
    ax_filler_percentage.clear()

    # Plot speech rate
    ax_speech_rate.plot(timestamps, speech_rates, label="Speech Rate (words/min)", color='blue')
    ax_speech_rate.set_xlabel("Time (s)")
    ax_speech_rate.set_ylabel("Speech Rate")
    ax_speech_rate.legend(loc="upper left")

    # Plot filler word percentage
    ax_filler_percentage.plot(timestamps, filler_percentages, label="Filler Word %", color='green')
    ax_filler_percentage.set_xlabel("Time (s)")
    ax_filler_percentage.set_ylabel("Filler Word %")
    ax_filler_percentage.legend(loc="upper left")

    canvas.draw()
    root.after(500, update_graph)

async def capture_audio(stream):
    samplerate = 16000
    chunk_size = 1024
    mic = sc.default_microphone()

    async def audio_stream():
        try:
            with mic.recorder(samplerate=samplerate, channels=1, blocksize=chunk_size) as recorder:
                print("🎤 Listening... Press Ctrl+C to stop.")
                while True:
                    data = recorder.record(chunk_size)
                    audio_chunk = (data * 32767).astype(np.int16).tobytes()
                    await stream.input_stream.send_audio_event(audio_chunk=audio_chunk)
                    await asyncio.sleep(0.001)
        except KeyboardInterrupt:
            print("\nStopping...")
        finally:
            await stream.input_stream.end_stream()

    await audio_stream()

async def main():
    client = TranscribeStreamingClient(region="us-west-2")
    stream = await client.start_stream_transcription(
        language_code="en-US",
        media_sample_rate_hz=16000,
        media_encoding="pcm"
    )
    handler = MyEventHandler(stream.output_stream)
    await asyncio.gather(capture_audio(stream), handler.handle_events())

# Set up the tkinter window
root = tk.Tk()
root.title("Real-time Speech Metrics")
root.geometry("1000x700")

# Set up the matplotlib figures and axes
fig, (ax_speech_rate, ax_filler_percentage) = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

# Add labels to display the latest values of speech rate and filler word percentage
frame = tk.Frame(root)
frame.pack(pady=10)

tk.Label(frame, text="Current Speech Rate: ").grid(row=0, column=0, sticky="w")
speech_rate_label = tk.Label(frame, text="0 words/min")
speech_rate_label.grid(row=0, column=1, sticky="w")

tk.Label(frame, text="Current Filler Word Usage: ").grid(row=1, column=0, sticky="w")
filler_percentage_label = tk.Label(frame, text="0%")
filler_percentage_label.grid(row=1, column=1, sticky="w")

# Start Flask server in a new thread
threading.Thread(target=start_flask).start()

# Start the graph update loop
root.after(500, update_graph)

# Run the asyncio main function in a separate thread
threading.Thread(target=lambda: asyncio.run(main())).start()

# Start the tkinter main loop
root.mainloop()