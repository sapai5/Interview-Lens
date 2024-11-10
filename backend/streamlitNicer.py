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
import streamlit as st
from PIL import Image
import matplotlib.pyplot as plt
from dotenv import load_dotenv
import warnings

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
            st.error(f"Error in Rekognition analysis: {e}")


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
                        st.write(word, end=' ')

                self.last_printed_words = current_words if result.is_partial else set()


async def capture_audio(stream):
    samplerate = 16000
    chunk_size = 1024
    mic = sc.default_microphone()

    try:
        with mic.recorder(samplerate=samplerate, channels=1, blocksize=chunk_size) as recorder:
            while True:
                data = recorder.record(chunk_size)
                audio_chunk = (data * 32767).astype(np.int16).tobytes()
                await stream.input_stream.send_audio_event(audio_chunk=audio_chunk)
                await asyncio.sleep(0.001)
    except Exception as e:
        st.error(f"Audio capture error: {e}")
    finally:
        await stream.input_stream.end_stream()


async def start_transcription(metrics):
    client = TranscribeStreamingClient(region="us-west-2")
    stream = await client.start_stream_transcription(
        language_code="en-US",
        media_sample_rate_hz=16000,
        media_encoding="pcm"
    )
    handler = MyEventHandler(stream.output_stream, metrics=metrics)
    await asyncio.gather(capture_audio(stream), handler.handle_events())


def main():
    st.set_page_config(layout="wide", page_title="Interview Feedback System")

    # Custom CSS to ensure dark background
    st.markdown("""
        <style>
        .stApp {
            background-color: #0E1117;
            color: white;
        }
        </style>
        """, unsafe_allow_html=True)

    # Initialize session state
    if 'analysis_started' not in st.session_state:
        st.session_state.analysis_started = False

    # Title and description
    st.title("Interview Practice Assistant")
    st.markdown("""
    This tool helps you practice your interview skills by analyzing:
    - Speech patterns and filler words
    - Facial expressions and eye contact
    - Overall confidence metrics

    Click 'Start Analysis' to begin.
    """)

    # Start button
    if not st.session_state.analysis_started:
        if st.button("Start Analysis"):
            st.session_state.analysis_started = True
            st.rerun()

    if st.session_state.analysis_started:
        metrics = InterviewMetrics(window_seconds=60)

        # Start transcription in a separate thread
        threading.Thread(target=lambda: asyncio.run(start_transcription(metrics)), daemon=True).start()

        # Create containers for layout
        sidebar = st.sidebar
        main_container = st.container()
        metrics_container = st.container()

        # Sidebar for video feed and metrics
        with sidebar:
            st.markdown("### Video Feed")
            video_placeholder = st.empty()

            st.markdown("### Metrics")
            metrics_section = st.container()
            with metrics_section:
                speech_rate = st.empty()
                filler_words = st.empty()
                confidence = st.empty()
                eye_contact = st.empty()

        # Main container for graphs
        with main_container:
            st.markdown("### Live Metrics Graphs")
            graph_placeholder = st.empty()

        # Stop button
        if st.button("Stop Analysis"):
            st.session_state.analysis_started = False
            st.rerun()

        # Capture video and update metrics
        cap = cv2.VideoCapture(0)
        while st.session_state.analysis_started:
            ret, frame = cap.read()
            if ret:
                # Analyze frame with Rekognition
                metrics.analyze_frame_with_rekognition(frame)

                # Convert frame for display
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                video_placeholder.image(frame_rgb, use_container_width=True)

                # Update metric display
                with metrics_section:
                    speech_rate.metric("Speech Rate (words/min)", f"{metrics.get_speech_rate():.1f}")
                    filler_words.metric("Filler Words (%)", f"{metrics.get_filler_percentage():.1f}")
                    confidence.metric("Confidence (%)", f"{metrics.confidence:.1f}")
                    eye_contact.metric("Eye Contact (%)", f"{metrics.eye_contact:.1f}")

                # Collect new timestamp and metrics data
                current_time = round(time.time() - metrics.start_time, 1)
                metrics.timestamps.append(current_time)
                metrics.speech_rates.append(metrics.get_speech_rate())
                metrics.filler_percentages.append(metrics.get_filler_percentage())
                metrics.confidence_values.append(metrics.confidence)
                metrics.eye_contact_values.append(metrics.eye_contact)

                # Create figure with dark theme
                fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 8))
                fig.patch.set_facecolor('#0E1117')

                # Set max points to prevent excessive memory use
                max_points = 60

                # Plot with custom colors that pop against dark background
                ax1.plot(metrics.timestamps[-max_points:], metrics.speech_rates[-max_points:],
                         color='#00FF7F', label="Speech Rate")
                ax1.set_title("Speech Rate (words/min)", color='white')
                ax1.set_facecolor('#0E1117')

                ax2.plot(metrics.timestamps[-max_points:], metrics.filler_percentages[-max_points:],
                         color='#FF4500', label="Filler Words")
                ax2.set_title("Filler Word Usage (%)", color='white')
                ax2.set_facecolor('#0E1117')

                ax3.plot(metrics.timestamps[-max_points:], metrics.confidence_values[-max_points:],
                         color='#00FFFF', label="Confidence")
                ax3.set_title("Confidence Level (%)", color='white')
                ax3.set_facecolor('#0E1117')

                ax4.plot(metrics.timestamps[-max_points:], metrics.eye_contact_values[-max_points:],
                         color='#FF1493', label="Eye Contact")
                ax4.set_title("Eye Contact (%)", color='white')
                ax4.set_facecolor('#0E1117')

                for ax in [ax1, ax2, ax3, ax4]:
                    ax.set_xlim(left=max(0, current_time - metrics.window_seconds), right=current_time)
                    ax.set_ylim(0, 100)
                    ax.set_xlabel("Time (s)", color='white')
                    ax.set_ylabel("Value", color='white')
                    ax.tick_params(colors='white')
                    ax.legend(facecolor='#0E1117', labelcolor='white')
                    ax.grid(True, color='#2C3E50')
                    for spine in ax.spines.values():
                        spine.set_color('#2C3E50')

                fig.tight_layout()
                graph_placeholder.pyplot(fig)
                plt.close(fig)

            time.sleep(0.5)

        # Clean up video capture when stopped
        cap.release()


if __name__ == "__main__":
    main()