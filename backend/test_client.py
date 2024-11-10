import asyncio
import websockets
import soundcard as sc
import numpy as np
import base64
import json
import requests
from datetime import datetime

class AudioStreamer:
    def __init__(self, server_url="http://localhost:8000", websocket_url="ws://localhost:8000"):
        self.server_url = server_url
        self.websocket_url = websocket_url
        self.session_id = None
        
        # Audio recording settings
        self.samplerate = 16000  # Required by Amazon Transcribe
        self.chunk_size = 1024
        self.mic = sc.default_microphone()
        
    async def create_session(self):
        """Create a new analysis session"""
        response = requests.post(
            f"{self.server_url}/sessions/",
            params={"url": "live_recording", "media_type": "audio"}
        )
        response.raise_for_status()
        self.session_id = response.json()["session_id"]
        print(f"Created session with ID: {self.session_id}")

    async def process_suggestions(self, websocket):
        """Process incoming suggestions from the server"""
        try:
            message = await asyncio.wait_for(
                websocket.recv(),
                timeout=0.1
            )
            print("\n--- Received WebSocket Message ---")
            print(f"Raw message: {message}")
            
            if isinstance(message, str):
                try:
                    suggestions = json.loads(message)
                    if suggestions:
                        print("\nProcessed suggestions:")
                        for suggestion in suggestions:
                            print("\nSuggestion details:")
                            print(f"- Category: {suggestion.get('category', 'N/A')}")
                            print(f"- Suggestion: {suggestion.get('suggestion', 'N/A')}")
                            print(f"- Confidence: {suggestion.get('confidence', 'N/A')}")
                            
                            if 'speech_metrics' in suggestion:
                                metrics = suggestion['speech_metrics']
                                print("\nSpeech metrics:")
                                print(f"- Speech rate: {metrics.get('speech_rate', 0):.1f} words/min")
                                print(f"- Filler percentage: {metrics.get('filler_percentage', 0):.1f}%")
                                print(f"- Total words: {metrics.get('total_words', 0)}")
                                
                                if 'filler_words' in metrics:
                                    print("\nFiller word counts:")
                                    for word, count in metrics['filler_words'].items():
                                        if count > 0:  # Only show words that were used
                                            print(f"  - '{word}': {count}")
                            print("-" * 50)
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON: {e}")
                    print(f"Raw message content: {message}")
            else:
                print(f"Received non-string message type: {type(message)}")
                
        except asyncio.TimeoutError:
            pass  # Normal timeout for non-blocking check
        except Exception as e:
            print(f"\nError in process_suggestions: {str(e)}")
            import traceback
            print(traceback.format_exc())

    async def capture_and_stream_audio(self, websocket):
        """Capture and stream audio data through websocket"""
        try:
            with self.mic.recorder(samplerate=self.samplerate, channels=1, blocksize=self.chunk_size) as recorder:
                print("\n🎤 Listening... Press Ctrl+C to stop.")
                print("Waiting for speech analysis results...")
                while True:
                    # Record audio chunk
                    data = recorder.record(self.chunk_size)
                    if len(data.shape) > 1:
                        data = data[:, 0]
                    
                    # Convert float32 to int16 PCM correctly
                    data = np.clip(data, -1, 1)
                    audio_chunk = (data * 32767.0).astype(np.int16).tobytes()
                    
                    # Create audio segment payload
                    payload = {
                        "start_time": datetime.utcnow().timestamp(),
                        "end_time": datetime.utcnow().timestamp() + (self.chunk_size / self.samplerate),
                        "audio_data": base64.b64encode(audio_chunk).decode('utf-8'),
                        "sample_rate": self.samplerate
                    }
                    
                    try:
                        await websocket.send(json.dumps(payload))
                    except Exception as e:
                        print(f"\nError sending audio data: {str(e)}")
                        raise
                    
                    # Process any incoming suggestions
                    await self.process_suggestions(websocket)
                    
                    await asyncio.sleep(0.001)
                    
        except KeyboardInterrupt:
            print("\nStopping audio stream...")
        except Exception as e:
            print(f"\nError in audio capture: {str(e)}")
            raise

    async def stream_audio(self):
        """Connect to WebSocket and start streaming"""
        if not self.session_id:
            raise ValueError("No active session. Call create_session() first.")
            
        websocket_endpoint = f"{self.websocket_url}/ws/{self.session_id}"
        print(f"\nConnecting to WebSocket at: {websocket_endpoint}")
        
        try:
            async with websockets.connect(websocket_endpoint) as websocket:
                print("WebSocket connected successfully!")
                await self.capture_and_stream_audio(websocket)
        except Exception as e:
            print(f"\nWebSocket connection error: {str(e)}")
            raise

    def cleanup(self):
        """Cleanup resources and end session"""
        if self.session_id:
            try:
                requests.delete(f"{self.server_url}/sessions/{self.session_id}")
                print("\nSession ended successfully")
            except Exception as e:
                print(f"\nError during cleanup: {str(e)}")

async def main():
    streamer = AudioStreamer()
    try:
        print("\n=== Starting Audio Analysis Session ===")
        await streamer.create_session()
        await streamer.stream_audio()
    except KeyboardInterrupt:
        print("\n\nStopping due to keyboard interrupt...")
    except Exception as e:
        print(f"\nError in main: {str(e)}")
        import traceback
        print(traceback.format_exc())
    finally:
        streamer.cleanup()

if __name__ == "__main__":
    print("\n=== Audio Streaming Client ===")
    print("Press Ctrl+C to stop recording")
    asyncio.run(main())