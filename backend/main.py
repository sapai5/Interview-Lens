from fastapi import FastAPI, HTTPException, WebSocket, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Deque
from datetime import datetime
import asyncio
import uuid
from collections import deque
import numpy as np
from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import TranscriptEvent
from dotenv import load_dotenv
import json
import base64


load_dotenv()

app = FastAPI(
    title="Media Analysis API",
    description="Backend API for Chrome extension that provides real-time ML-powered suggestions for video and audio content",
    version="1.0.0"
)

# Enable CORS for Chrome extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["chrome-extension://*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models ---

class VideoFrame(BaseModel):
    timestamp: float
    frame_data: str  # Base64 encoded image data
    width: int
    height: int

class AudioSegment(BaseModel):
    start_time: float
    end_time: float
    audio_data: str  # Base64 encoded audio data
    sample_rate: int = Field(default=44100)


class SpeechMetrics(BaseModel):
    speech_rate: float
    filler_percentage: float
    total_words: int
    filler_words: Dict[str, int]

class MLSuggestion(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    category: str
    confidence: float
    suggestion: str
    reference_timestamp: float
    metadata: Dict = Field(default_factory=dict)
    speech_metrics: Optional[SpeechMetrics] = None

class AnalysisSession(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    url: str
    start_time: datetime = Field(default_factory=datetime.utcnow)
    media_type: str  # "video" or "audio"
    status: str = "active"

# --- Speech Analysis Components ---

class SpeechAnalyzer:
    def __init__(self, window_seconds=60):
        self.filler_words = {
            'um': 0, 'uh': 0, 'er': 0, 'ah': 0, 'like': 0,
            'you know': 0, 'sort of': 0, 'kind of': 0
        }
        self.total_words = 0
        self.window_seconds = window_seconds
        self.word_timestamps: Deque[float] = deque()
        self.start_time = datetime.utcnow()

    def add_words(self, text: str) -> None:
        current_time = datetime.utcnow().timestamp()
        words = text.lower().split()

        self.total_words += len(words)

        # Record timestamps for speech rate calculation
        for _ in words:
            self.word_timestamps.append(current_time)

        # Remove outdated timestamps
        while (self.word_timestamps and
               current_time - self.word_timestamps[0] > self.window_seconds):
            self.word_timestamps.popleft()

        # Update filler word counts
        for filler in self.filler_words:
            self.filler_words[filler] += text.lower().count(filler)

    def get_speech_rate(self) -> float:
        if not self.word_timestamps:
            return 0.0

        current_time = datetime.utcnow().timestamp()
        window_words = len([t for t in self.word_timestamps
                          if current_time - t <= self.window_seconds])

        minutes = min(self.window_seconds / 60,
                     (current_time - self.start_time.timestamp()) / 60)
        return (window_words / minutes) if minutes > 0 else 0.0

    def get_filler_percentage(self) -> float:
        total_fillers = sum(self.filler_words.values())
        return (total_fillers / self.total_words * 100) if self.total_words > 0 else 0.0

    def get_metrics(self) -> SpeechMetrics:
        return SpeechMetrics(
            speech_rate=self.get_speech_rate(),
            filler_percentage=self.get_filler_percentage(),
            total_words=self.total_words,
            filler_words=self.filler_words
        )

class TranscriptionHandler(TranscriptResultStreamHandler):
    def __init__(self, *args, speech_analyzer: SpeechAnalyzer, websocket: WebSocket, **kwargs):
        super().__init__(*args, **kwargs)
        self.speech_analyzer = speech_analyzer
        self.websocket = websocket
        self.last_words = set()

    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        # print("\nReceived transcript event")
        results = transcript_event.transcript.results
        
        for result in results:
            try:
                for alt in result.alternatives:
                    words = alt.transcript.strip().split()
                    current_words = set(words)
                    
                    print(f"\nTranscribed text: {alt.transcript}")
                    
                    # Process words and update metrics
                    self.speech_analyzer.add_words(alt.transcript)
                    
                    # Get updated metrics
                    metrics = self.speech_analyzer.get_metrics()
                    print(f"Current metrics: speech_rate={metrics.speech_rate:.1f}, filler_percentage={metrics.filler_percentage:.1f}%")
                    
                    # Create suggestions based on metrics
                    suggestions = []
                    
                    # Check speech rate
                    if metrics.speech_rate > 160:  # Threshold for fast speech
                        suggestions.append(MLSuggestion(
                            category="speech_rate",
                            confidence=0.9,
                            suggestion="Consider slowing down your speech rate",
                            reference_timestamp=int(datetime.utcnow().timestamp()),
                            metadata={"current_rate": metrics.speech_rate},
                            speech_metrics=metrics
                        ))
                    
                    # Check filler word usage
                    if metrics.filler_percentage > 10:  # Threshold for high filler word usage
                        suggestions.append(MLSuggestion(
                            category="filler_words",
                            confidence=0.85,
                            suggestion="Try to reduce filler word usage",
                            reference_timestamp=int(datetime.utcnow().timestamp()),
                            metadata={"filler_counts": metrics.filler_words},
                            speech_metrics=metrics
                        ))
                    
                    # Send suggestions through websocket if any exist
                    if suggestions:
                        try:
                            print(f"\nSending {len(suggestions)} suggestions to client")
                            message = [s.dict() for s in suggestions]
                            print(f"Message content: {json.dumps(message, indent=2, default=str)}")
                            await self.websocket.send_json(message)
                            print("Successfully sent suggestions to client")
                        except Exception as e:
                            print(f"Error sending suggestions to client: {str(e)}")
                            import traceback
                            print(traceback.format_exc())
                    
                    self.last_words = current_words if not result.is_partial else set()
            except Exception as e:
                print(f"Error processing transcript result: {str(e)}")
                import traceback
                print(traceback.format_exc())



# --- In-Memory Storage (replace with proper database in production) ---
active_sessions: Dict[str, AnalysisSession] = {}
suggestions_cache: Dict[str, List[MLSuggestion]] = {}

# --- Helper Functions ---

async def analyze_video(video_frame: VideoFrame) -> List[MLSuggestion]:
    """Stub for ML-powered video analysis"""
    # Simulate processing delay
    await asyncio.sleep(0.1)

    return [
        MLSuggestion(
            category="composition",
            confidence=0.92,
            suggestion="Adjust framing to follow rule of thirds",
            reference_timestamp=int(video_frame.timestamp),
            metadata={"detected_objects": ["person", "microphone"]}
        )
    ]


async def analyze_audio(audio_segment: AudioSegment) -> List[MLSuggestion]:
    """Stub for ML-powered audio analysis"""
    # Simulate processing delay
    await asyncio.sleep(0.1)
    
    return [
        MLSuggestion(
            category="speech_clarity",
            confidence=0.85,
            suggestion="Consider reducing background noise",
            reference_timestamp=int(audio_segment.start_time),
            metadata={"decibel_level": -20}
        )
    ]

async def analyze_video(video_frame: VideoFrame) -> List[MLSuggestion]:
    """Stub for ML-powered video analysis"""
    # Simulate processing delay
    await asyncio.sleep(0.1)
    
    return [
        MLSuggestion(
            category="composition",
            confidence=0.92,
            suggestion="Adjust framing to follow rule of thirds",
            reference_timestamp=int(video_frame.timestamp),
            metadata={"detected_objects": ["person", "microphone"]}
        )
    ]

# --- API Endpoints ---

@app.post("/sessions/", response_model=AnalysisSession)
async def create_session(url: str, media_type: str):
    """Create a new analysis session for a specific URL"""
    if media_type not in ["video", "audio"]:
        raise HTTPException(status_code=400, detail="Invalid media type")
    
    session = AnalysisSession(url=url, media_type=media_type)
    active_sessions[session.session_id] = session
    suggestions_cache[session.session_id] = []
    return session

@app.get("/sessions/{session_id}/suggestions/", response_model=List[MLSuggestion])
async def get_suggestions(session_id: str):
    """Get all suggestions for a specific session"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return suggestions_cache[session_id]

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time media analysis"""
    if session_id not in active_sessions:
        print(f"Session {session_id} not found")
        await websocket.close(code=4000)
        return

    await websocket.accept()
    session = active_sessions[session_id]
    print(f"\nWebSocket connected for session {session_id}")

    try:
        if session.media_type == "audio":
            # Initialize speech analyzer
            speech_analyzer = SpeechAnalyzer()
            print("Speech analyzer initialized")

            # Set up Amazon Transcribe client
            client = TranscribeStreamingClient(region="us-west-2")
            print("Amazon Transcribe client initialized")
            
            stream = await client.start_stream_transcription(
                language_code="en-US",
                media_sample_rate_hz=16000,
                media_encoding="pcm"
            )
            print("Transcription stream started")

            # Initialize handler with speech analyzer and websocket
            handler = TranscriptionHandler(
                stream.output_stream,
                speech_analyzer=speech_analyzer,
                websocket=websocket
            )

            # Start the handler in the background
            handler_task = asyncio.create_task(handler.handle_events())
            print("Handler task started")

            # Process incoming audio data
            while True:
                try:
                    data = await websocket.receive_text()
                    audio_segment = AudioSegment(**json.loads(data))
                    
                    # print(f"\nReceived audio segment: {len(base64.b64decode(audio_segment.audio_data))} bytes")
                    
                    # Debug: check audio data stats
                    audio_data = base64.b64decode(audio_segment.audio_data)
                    audio_array = np.frombuffer(audio_data, dtype=np.int16)
                    # print(f"Audio stats - min: {np.min(audio_array)}, max: {np.max(audio_array)}, mean: {np.mean(audio_array):.2f}")
                    
                    # Send to Transcribe
                    await stream.input_stream.send_audio_event(audio_chunk=audio_data)

                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON data: {str(e)}")
                except Exception as e:
                    print(f"Error processing audio data: {str(e)}")
                    import traceback
                    print(traceback.format_exc())
                    break

    except WebSocketDisconnect:
        print("\nWebSocket disconnected")
    except Exception as e:
        print(f"\nWebSocket error: {str(e)}")
        import traceback
        print(traceback.format_exc())
    finally:
        if session.media_type == "audio":
            print("\nCleaning up audio session...")
            await stream.input_stream.end_stream()
            handler_task.cancel()  # Cancel the handler task
        if session_id in active_sessions:
            active_sessions[session_id].status = "completed"
            print(f"Session {session_id} completed")


@app.delete("/sessions/{session_id}")
async def end_session(session_id: str):
    """End an analysis session and cleanup resources"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = active_sessions[session_id]
    session.status = "completed"
    
    # Cleanup (in production, you might want to archive instead of delete)
    del active_sessions[session_id]
    del suggestions_cache[session_id]
    
    return {"status": "success", "message": "Session ended successfully"}

# --- ML Model Management Endpoints ---

@app.post("/models/reload")
async def reload_models(background_tasks: BackgroundTasks):
    """Endpoint to reload ML models (stub for model management)"""
    async def reload_task():
        await asyncio.sleep(2)  # Simulate model reloading
    
    background_tasks.add_task(reload_task)
    return {"status": "success", "message": "Model reload initiated"}

@app.get("/models/status")
async def get_model_status():
    """Get the status of ML models (stub for model monitoring)"""
    return {
        "video_model": {
            "status": "healthy",
            "last_updated": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "memory_usage": "1.2GB"
        },
        "audio_model": {
            "status": "healthy",
            "last_updated": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "memory_usage": "800MB"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
