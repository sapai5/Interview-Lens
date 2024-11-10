from fastapi import FastAPI, HTTPException, WebSocket, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
import asyncio
import uuid

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

class AudioSegment(BaseModel):
    start_time: float
    end_time: float
    audio_data: str  # Base64 encoded audio data
    sample_rate: int = Field(default=44100)

class VideoFrame(BaseModel):
    timestamp: float
    frame_data: str  # Base64 encoded image data
    width: int
    height: int

class MLSuggestion(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    category: str
    confidence: float
    suggestion: str
    reference_timestamp: float
    metadata: Dict = Field(default_factory=dict)

class AnalysisSession(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    url: str
    start_time: datetime = Field(default_factory=datetime.utcnow)
    media_type: str  # "video" or "audio"
    status: str = "active"

# --- In-Memory Storage (replace with proper database in production) ---
active_sessions: Dict[str, AnalysisSession] = {}
suggestions_cache: Dict[str, List[MLSuggestion]] = {}

# --- Helper Functions ---

async def analyze_audio(audio_segment: AudioSegment) -> List[MLSuggestion]:
    """Stub for ML-powered audio analysis"""
    # Simulate processing delay
    await asyncio.sleep(0.1)
    
    return [
        MLSuggestion(
            category="speech_clarity",
            confidence=0.85,
            suggestion="Consider reducing background noise",
            reference_timestamp=audio_segment.start_time,
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
            reference_timestamp=video_frame.timestamp,
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
        await websocket.close(code=4000)
        return

    await websocket.accept()
    session = active_sessions[session_id]

    try:
        while True:
            data = await websocket.receive_json()
            
            if session.media_type == "audio":
                audio_segment = AudioSegment(**data)
                suggestions = await analyze_audio(audio_segment)
            else:  # video
                video_frame = VideoFrame(**data)
                suggestions = await analyze_video(video_frame)
            
            # Cache suggestions
            suggestions_cache[session_id].extend(suggestions)
            
            # Send suggestions back to client
            await websocket.send_json([suggestion.dict() for suggestion in suggestions])
    except:
        await websocket.close()
        if session_id in active_sessions:
            active_sessions[session_id].status = "completed"

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