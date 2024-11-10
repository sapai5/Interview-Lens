import os

import cv2
import boto3
import matplotlib.pyplot as plt
import seaborn as sns
import datetime
from dotenv import load_dotenv

load_dotenv()

# Initialize AWS Rekognition client
rekognition = boto3.client(
    'rekognition',
    aws_access_key_id=os.eviron['AWS_ACCESS_KEY_ID'],
    aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'],
    region_name=os.environ['AWS_REGION']
)
# Initialize Seaborn
sns.set(style="whitegrid")


# Function to set up real-time plotting
#def setup_plot():
#    plt.ion()  # Interactive mode for real-time updating
#    fig, ax = plt.subplots(2, 1, figsize=(10, 8))
#    return fig, ax


#def update_graph(ax, timestamps, eye_contact_data, confidence_data):
#    ax[0].cla()  # Clear the axis
#    ax[1].cla()  # Clear the axis
#
#    # Real-time Matplotlib plot
#    ax[0].plot(timestamps, eye_contact_data, label="Eye Contact (%)", color="b")
#    ax[0].set_ylim(0, 100)
#    ax[0].set_title("Eye Contact (%)")
#    ax[0].set_xlabel("Time (s)")
#    ax[0].set_ylabel("Percentage")
#    ax[0].legend(loc="upper left")
#
#    ax[1].plot(timestamps, confidence_data, label="Confidence (%)", color="g")
#    ax[1].set_ylim(0, 100)
#    ax[1].set_title("Confidence (%)")
#    ax[1].set_xlabel("Time (s)")
#    ax[1].set_ylabel("Percentage")
#    ax[1].legend(loc="upper left")
#
#    plt.tight_layout()
#    plt.draw()
#    plt.pause(0.001)


# Analyze frame with AWS Rekognition for confidence based on emotions
def analyze_frame_with_rekognition(frame, confidence):
    # Convert frame to bytes
    _, buffer = cv2.imencode('.jpg', frame)
    image_bytes = buffer.tobytes()

    # Call Rekognition for face analysis
    response = rekognition.detect_faces(
        Image={'Bytes': image_bytes},
        Attributes=['ALL']
    )

    # Initialize eye contact as 0 by default
    eye_contact = 0  # Default to no eye contact

    # If Rekognition detects a face, analyze emotions for confidence
    if response['FaceDetails']:
        face = response['FaceDetails'][0]  # Use first detected face

        # Detect eye contact
        eyes_open = (face['EyesOpen']['Value'] and face['EyesOpen']['Confidence'] > 80)
        pitch = abs(face['Pose']['Pitch'])  # Head tilt up/down
        roll = abs(face['Pose']['Roll'])  # Head tilt left/right
        yaw = abs(face['Pose']['Yaw'])  # Head turn left/right

        # Eye contact is considered high if eyes are open and head is facing forward
        if eyes_open and pitch < 15 and roll < 15 and yaw < 15:
            eye_contact = 100

        # Determine confidence based on facial expressions
        emotions = face['Emotions']
        positive_emotions = ['HAPPY', 'SURPRISED']
        negative_emotions = ['SAD', 'DISGUSTED', 'ANGRY', 'CONFUSED']

        # Calculate confidence based on emotion scores
        positive_score = sum(emotion['Confidence'] for emotion in emotions if emotion['Type'] in positive_emotions)
        negative_score = sum(emotion['Confidence'] for emotion in emotions if emotion['Type'] in negative_emotions)

        # Increment or decrement confidence based on detected emotions
        if positive_score > negative_score:
            confidence = min(confidence + 2, 100)  # Increase confidence gradually
        elif negative_score > positive_score:
            confidence = max(confidence - 1, 0)  # Decrease confidence gradually

    return eye_contact, confidence


# Main function to capture video and analyze with Rekognition
def main():
    cap = cv2.VideoCapture(0)  # Capture video from the default camera

#    fig, ax = setup_plot()
    eye_contact_data = []
    confidence_data = []
    timestamps = []

    confidence = 50  # Start with mid-level confidence
    start_time = datetime.datetime.now()  # Track start time

    frame_interval = 30  # Process every 30th frame to avoid high latency with Rekognition

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to capture video frame.")
            break

        # Only process every `frame_interval` frames to reduce latency
        if int((datetime.datetime.now() - start_time).total_seconds() * 30) % frame_interval == 0:
            # Perform analysis with AWS Rekognition
            eye_contact, confidence = analyze_frame_with_rekognition(frame, confidence)
            eye_contact_data.append(eye_contact)
            confidence_data.append(confidence)

            # Track time for x-axis of the plot
            current_time = (datetime.datetime.now() - start_time).total_seconds()
            timestamps.append(current_time)

            # Debugging prints to verify data
            print(f"Timestamp: {current_time:.2f}s, Eye Contact: {eye_contact}%, Confidence: {confidence}%")

            # Update the plot with Matplotlib
 #           update_graph(ax, timestamps, eye_contact_data, confidence_data)

        # Display the frame with OpenCV
        cv2.imshow('Interview Helper', frame)

        # Stop the loop when 'q' is pressed
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
