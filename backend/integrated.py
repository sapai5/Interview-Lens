import os
import soundcard as sc
import numpy as np
import asyncio
import time
import cv2
import boto3
import threading
from collections import deque
from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import TranscriptEvent
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import warnings
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Suppress matplotlib warnings
warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")

# Initialize AWS clients
rekognition = boto3.client(
    'rekognition',
    aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
    aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'],
    region_name=os.environ['AWS_REGION']
)


class InterviewMetrics:
    def __init__(self, window_seconds=60):
        self.filler_words = {
            'um': 0, 'uh': 0, 'er': 0, 'ah': 0, 'like': 0,
            'you know': 0, 'sort of': 0, 'kind of': 0
        }
        self.total_words = 0
        self.window_seconds = window_seconds
        self.word_timestamps = deque()
        self.start_time = time.time()

        # Visual metrics
        self.confidence = 50
        self.eye_contact = 0

        # Arrays for tracking all metrics
        self.timestamps = []
        self.speech_rates = []
        self.filler_percentages = []
        self.confidence_values = []
        self.eye_contact_values = []

    def add_words(self, text: str):
        current_time = time.time()
        words = text.lower().split()

        self.total_words += len(words)

        for _ in words:
            self.word_timestamps.append(current_time)

        while (self.word_timestamps and
               current_time - self.word_timestamps[0] > self.window_seconds):
            self.word_timestamps.popleft()

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

    def analyze_frame_with_rekognition(self, frame):
        _, buffer = cv2.imencode('.jpg', frame)
        image_bytes = buffer.tobytes()

        try:
            response = rekognition.detect_faces(
                Image={'Bytes': image_bytes},
                Attributes=['ALL']
            )

            eye_contact = 0

            if response['FaceDetails']:
                face = response['FaceDetails'][0]

                eyes_open = (face['EyesOpen']['Value'] and
                             face['EyesOpen']['Confidence'] > 80)
                pitch = abs(face['Pose']['Pitch'])
                roll = abs(face['Pose']['Roll'])
                yaw = abs(face['Pose']['Yaw'])

                if eyes_open and pitch < 15 and roll < 15 and yaw < 15:
                    eye_contact = 100

                emotions = face['Emotions']
                positive_emotions = ['HAPPY', 'SURPRISED']
                negative_emotions = ['SAD', 'DISGUSTED', 'ANGRY', 'CONFUSED']

                positive_score = sum(emotion['Confidence'] for emotion in emotions
                                     if emotion['Type'] in positive_emotions)
                negative_score = sum(emotion['Confidence'] for emotion in emotions
                                     if emotion['Type'] in negative_emotions)

                if positive_score > negative_score:
                    self.confidence = min(self.confidence + 2, 100)
                elif negative_score > positive_score:
                    self.confidence = max(self.confidence - 1, 0)

            self.eye_contact = eye_contact

        except Exception as e:
            print(f"Error in Rekognition analysis: {e}")


class MyEventHandler(TranscriptResultStreamHandler):
    def __init__(self, *args, metrics=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_printed_words = set()
        self.metrics = metrics

    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        results = transcript_event.transcript.results

        for result in results:
            for alt in result.alternatives:
                words = alt.transcript.strip().split()
                current_words = set(words)

                self.metrics.add_words(alt.transcript)

                new_words = current_words - self.last_printed_words
                for word in words:
                    if word in new_words:
                        print(word, end=' ', flush=True)

                self.last_printed_words = current_words if result.is_partial else set()


class InterviewFeedbackApp:
    def __init__(self):
        self.metrics = InterviewMetrics(window_seconds=60)
        self.root = tk.Tk()
        self.root.title("Interview Feedback System")
        self.root.geometry("1400x900")

        # Create main container
        self.main_container = ttk.Frame(self.root)
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create left panel for video and metrics
        self.left_panel = ttk.Frame(self.main_container)
        self.left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 10))

        # Create video label
        self.video_label = tk.Label(self.left_panel)
        self.video_label.pack(pady=(0, 10))

        # Create metrics display with large numbers
        self.metrics_frame = ttk.Frame(self.left_panel)
        self.metrics_frame.pack(fill=tk.X, pady=10)

        # Style for metric displays
        style = ttk.Style()
        style.configure("Metric.TLabel", font=('Arial', 12))
        style.configure("MetricValue.TLabel", font=('Arial', 24, 'bold'))

        # Create metric display boxes
        self.metric_boxes = {}
        metrics_config = [
            ("Speech Rate", "speech_rate", "words/min", "#2196F3"),
            ("Filler Words", "filler", "%", "#F44336"),
            ("Confidence", "confidence", "%", "#4CAF50"),
            ("Eye Contact", "eye_contact", "%", "#9C27B0")
        ]

        for i, (title, key, unit, color) in enumerate(metrics_config):
            box_frame = ttk.Frame(self.metrics_frame, relief="raised", borderwidth=2)
            box_frame.grid(row=i // 2, column=i % 2, padx=5, pady=5, sticky="nsew")

            ttk.Label(box_frame, text=title, style="Metric.TLabel").pack(pady=(5, 0))
            value_label = ttk.Label(box_frame, text="0", style="MetricValue.TLabel")
            value_label.pack(pady=(0, 2))
            ttk.Label(box_frame, text=unit, style="Metric.TLabel").pack(pady=(0, 5))

            self.metric_boxes[key] = value_label

        # Configure grid
        self.metrics_frame.grid_columnconfigure(0, weight=1)
        self.metrics_frame.grid_columnconfigure(1, weight=1)

        # Create right panel for graphs
        self.right_panel = ttk.Frame(self.main_container)
        self.right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Create matplotlib figure with 4 subplots
        self.fig, ((self.ax1, self.ax2), (self.ax3, self.ax4)) = plt.subplots(2, 2, figsize=(10, 8))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.right_panel)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Start the camera
        self.cap = cv2.VideoCapture(0)

        # Set video resolution for the embedded feed
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 480)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)

        # Start update loops
        self.root.after(500, self.update_graphs)
        self.root.after(33, self.update_video_feed)

        # Bind cleanup on window close
        self.root.protocol("WM_DELETE_WINDOW", self.cleanup)

    def update_video_feed(self):
        ret, frame = self.cap.read()
        if ret:
            # Analyze frame with Rekognition
            self.metrics.analyze_frame_with_rekognition(frame)

            # Convert frame to RGB and then to PhotoImage
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            img_tk = ImageTk.PhotoImage(image=img)

            # Update video label
            self.video_label.configure(image=img_tk)
            self.video_label.image = img_tk

        self.root.after(33, self.update_video_feed)

    def update_graphs(self):
        current_time = round(time.time() - self.metrics.start_time, 1)

        # Update metrics
        speech_rate = self.metrics.get_speech_rate()
        filler_percentage = self.metrics.get_filler_percentage()

        # Store metrics
        self.metrics.timestamps.append(current_time)
        self.metrics.speech_rates.append(speech_rate)
        self.metrics.filler_percentages.append(filler_percentage)
        self.metrics.confidence_values.append(self.metrics.confidence)
        self.metrics.eye_contact_values.append(self.metrics.eye_contact)

        # Update metric box values
        self.metric_boxes['speech_rate'].configure(text=f"{speech_rate:.1f}")
        self.metric_boxes['filler'].configure(text=f"{filler_percentage:.1f}")
        self.metric_boxes['confidence'].configure(text=f"{self.metrics.confidence:.1f}")
        self.metric_boxes['eye_contact'].configure(text=f"{self.metrics.eye_contact:.1f}")

        # Clear and update plots
        for ax in [self.ax1, self.ax2, self.ax3, self.ax4]:
            ax.clear()

        # Plot all metrics
        self.ax1.plot(self.metrics.timestamps[-60:], self.metrics.speech_rates[-60:],
                      label="Speech Rate", color='#2196F3')
        self.ax1.set_title("Speech Rate (words/min)")

        self.ax2.plot(self.metrics.timestamps[-60:], self.metrics.filler_percentages[-60:],
                      label="Filler Words", color='#F44336')
        self.ax2.set_title("Filler Word Usage (%)")

        self.ax3.plot(self.metrics.timestamps[-60:], self.metrics.confidence_values[-60:],
                      label="Confidence", color='#4CAF50')
        self.ax3.set_title("Confidence Level (%)")

        self.ax4.plot(self.metrics.timestamps[-60:], self.metrics.eye_contact_values[-60:],
                      label="Eye Contact", color='#9C27B0')
        self.ax4.set_title("Eye Contact (%)")

        for ax in [self.ax1, self.ax2, self.ax3, self.ax4]:
            ax.set_xlabel("Time (s)")
            ax.set_ylabel("%")
            ax.grid(True)
            ax.set_ylim(0, 100)

        self.fig.tight_layout()
        self.canvas.draw()
        self.root.after(500, self.update_graphs)

    def cleanup(self):
        self.cap.release()
        self.root.quit()

    async def capture_audio(self, stream):
        samplerate = 16000
        chunk_size = 1024
        mic = sc.default_microphone()

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

    async def start_transcription(self):
        client = TranscribeStreamingClient(region="us-west-2")
        stream = await client.start_stream_transcription(
            language_code="en-US",
            media_sample_rate_hz=16000,
            media_encoding="pcm"
        )
        handler = MyEventHandler(stream.output_stream, metrics=self.metrics)
        await asyncio.gather(self.capture_audio(stream), handler.handle_events())


def main():
    app = InterviewFeedbackApp()

    # Start transcription in a separate thread
    threading.Thread(target=lambda: asyncio.run(app.start_transcription())).start()

    # Start the tkinter main loop
    app.root.mainloop()


if __name__ == "__main__":
    main()