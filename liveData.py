import cv2
import speech_recognition as sr
import time
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import nltk

# Initialize nltk's set of filler words
nltk.download("stopwords")
filler_words = set(["um", "uh", "like", "you know", "basically", "so", "actually", "right", "okay", "well"])

# Configuration
DURATION = 2  # Duration in seconds to analyze audio chunks
timestamps = []
speech_rates = []
filler_percentages = []

# Initialize recognizer
recognizer = sr.Recognizer()


# Open camera app
def open_camera_app():
    import subprocess
    subprocess.Popen("start microsoft.windows.camera:", shell=True)  # Adjust this for different OS


# Analyze text for speech rate and filler words
def analyze_text(text):
    words = text.split()
    num_words = len(words)
    fillers = [word for word in words if word.lower() in filler_words]
    num_fillers = len(fillers)

    # Calculate speech rate (words per minute) and filler word percentage
    speech_rate = (num_words / DURATION) * 60  # words per minute
    filler_percentage = (num_fillers / num_words * 100) if num_words > 0 else 0

    return speech_rate, filler_percentage


# Update graph function
def update_graph(i):
    plt.cla()
    plt.plot(timestamps, speech_rates, label="Speech Rate (words/min)")
    plt.plot(timestamps, filler_percentages, label="Filler Word %")
    plt.xlabel("Time (s)")
    plt.ylabel("Value")
    plt.legend(loc="upper left")
    plt.tight_layout()


# Main function
def main():
    open_camera_app()
    plt.figure()
    ani = FuncAnimation(plt.gcf(), update_graph, interval=1000)
    start_time = time.time()

    while True:
        with sr.Microphone() as source:
            print("Listening for audio...")
            recognizer.adjust_for_ambient_noise(source, duration=2)
            audio = recognizer.listen(source, phrase_time_limit=DURATION)

        try:
            print("Transcribing audio...")
            text = recognizer.recognize_google(audio)
            print(f"Transcribed Text: {text}")

            # Analyze text for speech rate and filler words
            speech_rate, filler_percentage = analyze_text(text)
            current_time = round(time.time() - start_time, 1)

            print(
                f"Time: {current_time}s | Speech Rate: {speech_rate:.2f} words/min | Filler Word Usage: {filler_percentage:.2f}%")

            # Append data for graphing
            timestamps.append(current_time)
            speech_rates.append(speech_rate)
            filler_percentages.append(filler_percentage)

        except sr.UnknownValueError:
            print("Could not understand audio, please try speaking more clearly.")
        except sr.RequestError:
            print("Speech recognition service is unavailable.")

        # Break loop with 'Ctrl+C'
        except KeyboardInterrupt:
            print("Exiting...")
            break

    plt.show()


if __name__ == "__main__":
    main()
