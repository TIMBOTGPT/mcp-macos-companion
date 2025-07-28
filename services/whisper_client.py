#!/usr/bin/env python3
"""
Whisper Client Service - Speech-to-Text Processing
Port: 8085
Handles audio recording, processing, and transcription using OpenAI Whisper
"""

import asyncio
import json
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
import wave
import threading
from datetime import datetime

# Core imports
import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pyaudio
import whisper
import torch

# Service discovery
import requests

class AudioRecorder:
    """Handles audio recording from microphone"""
    
    def __init__(self):
        self.audio = pyaudio.PyAudio()
        self.is_recording = False
        self.frames = []
        self.stream = None
        
        # Audio settings
        self.chunk = 1024
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000  # Whisper prefers 16kHz
        
    def start_recording(self) -> bool:
        """Start recording audio"""
        try:
            self.frames = []
            self.is_recording = True
            
            self.stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                frames_per_buffer=self.chunk
            )
            
            def record_audio():
                while self.is_recording:
                    try:
                        data = self.stream.read(self.chunk, exception_on_overflow=False)
                        self.frames.append(data)
                    except Exception as e:
                        logging.error(f"Error recording audio: {e}")
                        break
            
            self.record_thread = threading.Thread(target=record_audio)
            self.record_thread.start()
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to start recording: {e}")
            return False
    
    def stop_recording(self) -> Optional[str]:
        """Stop recording and save to temporary file"""
        try:
            self.is_recording = False
            
            if self.record_thread:
                self.record_thread.join(timeout=2)
            
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
            
            if not self.frames:
                return None
            
            # Save to temporary file
            temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            
            with wave.open(temp_file.name, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.audio.get_sample_size(self.format))
                wf.setframerate(self.rate)
                wf.writeframes(b''.join(self.frames))
            
            return temp_file.name
            
        except Exception as e:
            logging.error(f"Failed to stop recording: {e}")
            return None
    
    def cleanup(self):
        """Cleanup resources"""
        self.is_recording = False
        if self.stream:
            self.stream.close()
        self.audio.terminate()

class WhisperProcessor:
    """Handles Whisper model loading and transcription"""
    
    def __init__(self):
        self.model = None
        self.model_size = "base"  # Start with base model
        self.device = "cpu"  # Force CPU for compatibility
        self.load_model()
    
    def load_model(self, model_size: str = None):
        """Load Whisper model"""
        try:
            if model_size:
                self.model_size = model_size
            
            logging.info(f"Loading Whisper model '{self.model_size}' on {self.device}")
            self.model = whisper.load_model(self.model_size, device=self.device)
            logging.info("Whisper model loaded successfully")
            
        except Exception as e:
            logging.error(f"Failed to load Whisper model: {e}")
            # Fallback to CPU if MPS fails
            if self.device == "mps":
                self.device = "cpu"
                self.model = whisper.load_model(self.model_size, device=self.device)
    
    def transcribe_file(self, file_path: str, language: str = None) -> Dict[str, Any]:
        """Transcribe audio file"""
        try:
            if not self.model:
                raise Exception("Whisper model not loaded")
            
            # Transcribe with options
            options = {
                "fp16": False,  # Use fp32 for better compatibility
                "language": language if language else None
            }
            
            result = self.model.transcribe(file_path, **options)
            
            return {
                "text": result["text"].strip(),
                "language": result["language"],
                "segments": result.get("segments", []),
                "duration": sum(seg.get("end", 0) for seg in result.get("segments", [])),
                "confidence": self._calculate_confidence(result.get("segments", []))
            }
            
        except Exception as e:
            logging.error(f"Transcription failed: {e}")
            raise
    
    def _calculate_confidence(self, segments: List[Dict]) -> float:
        """Calculate average confidence from segments"""
        if not segments:
            return 0.0
        
        confidences = []
        for segment in segments:
            if "avg_logprob" in segment:
                # Convert log probability to confidence (approximate)
                confidence = min(1.0, max(0.0, (segment["avg_logprob"] + 1.0)))
                confidences.append(confidence)
        
        return sum(confidences) / len(confidences) if confidences else 0.0

class WhisperService:
    """Main Whisper service"""
    
    def __init__(self):
        self.app = FastAPI(title="Whisper Client", version="1.0.0")
        self.setup_middleware()
        self.setup_routes()
        
        # Components
        self.recorder = AudioRecorder()
        self.processor = WhisperProcessor()
        
        # State
        self.active_recordings = {}
        self.transcription_history = []
        
        # Service registry
        self.service_registry_url = "http://localhost:8080"
        
    def setup_middleware(self):
        """Setup FastAPI middleware"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def setup_routes(self):
        """Setup API routes"""
        
        @self.app.get("/health")
        async def health_check():
            return {"status": "healthy", "service": "whisper_client", "port": 8085}
        
        @self.app.get("/info")
        async def service_info():
            return {
                "service": "whisper_client",
                "version": "1.0.0",
                "description": "Speech-to-text processing using OpenAI Whisper",
                "capabilities": [
                    "real_time_recording",
                    "file_transcription",
                    "multiple_languages",
                    "confidence_scoring"
                ],
                "model_size": self.processor.model_size,
                "device": self.processor.device
            }
        
        @self.app.post("/recording/start")
        async def start_recording():
            """Start recording audio"""
            try:
                session_id = f"rec_{int(time.time())}"
                
                if self.recorder.start_recording():
                    self.active_recordings[session_id] = {
                        "start_time": datetime.now().isoformat(),
                        "status": "recording"
                    }
                    
                    return {
                        "success": True,
                        "session_id": session_id,
                        "message": "Recording started"
                    }
                else:
                    raise HTTPException(status_code=500, detail="Failed to start recording")
                    
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/recording/stop/{session_id}")
        async def stop_recording(session_id: str, background_tasks: BackgroundTasks):
            """Stop recording and transcribe"""
            try:
                if session_id not in self.active_recordings:
                    raise HTTPException(status_code=404, detail="Recording session not found")
                
                # Stop recording
                audio_file = self.recorder.stop_recording()
                if not audio_file:
                    raise HTTPException(status_code=500, detail="Failed to save recording")
                
                # Update session
                self.active_recordings[session_id]["status"] = "processing"
                self.active_recordings[session_id]["audio_file"] = audio_file
                
                # Transcribe in background
                background_tasks.add_task(self._process_recording, session_id, audio_file)
                
                return {
                    "success": True,
                    "session_id": session_id,
                    "message": "Recording stopped, processing..."
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/recording/status/{session_id}")
        async def get_recording_status(session_id: str):
            """Get recording status and results"""
            if session_id not in self.active_recordings:
                raise HTTPException(status_code=404, detail="Recording session not found")
            
            return self.active_recordings[session_id]
        
        @self.app.post("/transcribe/file")
        async def transcribe_file(
            file: UploadFile = File(...),
            language: Optional[str] = None
        ):
            """Transcribe uploaded audio file"""
            try:
                # Save uploaded file
                temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
                content = await file.read()
                temp_file.write(content)
                temp_file.close()
                
                # Transcribe
                result = self.processor.transcribe_file(temp_file.name, language)
                
                # Cleanup
                os.unlink(temp_file.name)
                
                # Store in history
                self.transcription_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "filename": file.filename,
                    "result": result
                })
                
                return {
                    "success": True,
                    "transcription": result
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/history")
        async def get_transcription_history(limit: int = 10):
            """Get transcription history"""
            return {
                "history": self.transcription_history[-limit:],
                "total": len(self.transcription_history)
            }
        
        @self.app.post("/model/change")
        async def change_model(model_size: str):
            """Change Whisper model size"""
            try:
                valid_sizes = ["tiny", "base", "small", "medium", "large"]
                if model_size not in valid_sizes:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid model size. Choose from: {valid_sizes}"
                    )
                
                self.processor.load_model(model_size)
                
                return {
                    "success": True,
                    "model_size": model_size,
                    "device": self.processor.device
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
    
    async def _process_recording(self, session_id: str, audio_file: str):
        """Process recording in background"""
        try:
            # Transcribe
            result = self.processor.transcribe_file(audio_file)
            
            # Update session
            self.active_recordings[session_id].update({
                "status": "completed",
                "result": result,
                "end_time": datetime.now().isoformat()
            })
            
            # Store in history
            self.transcription_history.append({
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id,
                "result": result
            })
            
            # Cleanup audio file
            try:
                os.unlink(audio_file)
            except:
                pass
                
        except Exception as e:
            self.active_recordings[session_id].update({
                "status": "error",
                "error": str(e),
                "end_time": datetime.now().isoformat()
            })
    
    async def register_service(self):
        """Register with service registry"""
        try:
            service_info = {
                "name": "whisper_client",
                "host": "localhost",
                "port": 8085,
                "health_endpoint": "/health",
                "capabilities": [
                    "speech_to_text",
                    "audio_recording",
                    "multiple_languages",
                    "real_time_processing"
                ],
                "metadata": {
                    "model_size": self.processor.model_size,
                    "device": self.processor.device
                }
            }
            
            response = requests.post(
                f"{self.service_registry_url}/services/register",
                json=service_info,
                timeout=5
            )
            
            if response.status_code == 200:
                logging.info("Successfully registered with service registry")
            else:
                logging.warning(f"Failed to register: {response.status_code}")
                
        except Exception as e:
            logging.warning(f"Could not register with service registry: {e}")
    
    def cleanup(self):
        """Cleanup resources"""
        self.recorder.cleanup()

# Global service instance
whisper_service = WhisperService()

async def startup_event():
    """Startup event handler"""
    logging.info("Starting Whisper Client service...")
    await whisper_service.register_service()
    logging.info("Whisper Client service started on port 8085")

async def shutdown_event():
    """Shutdown event handler"""
    logging.info("Shutting down Whisper Client service...")
    whisper_service.cleanup()

# Add event handlers
whisper_service.app.add_event_handler("startup", startup_event)
whisper_service.app.add_event_handler("shutdown", shutdown_event)

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run service
    uvicorn.run(
        "whisper_client:whisper_service.app",
        host="localhost",
        port=8085,
        reload=False,
        log_level="info"
    )
