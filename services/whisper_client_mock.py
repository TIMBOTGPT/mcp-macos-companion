#!/usr/bin/env python3
"""
Whisper Client Service - Mock Version for Testing
Port: 8085
Simple mock without audio dependencies
"""

import asyncio
import json
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
import threading
from datetime import datetime

# Core imports
import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Service discovery
import requests

class WhisperService:
    """Mock Whisper service for testing"""
    
    def __init__(self):
        self.app = FastAPI(title="Whisper Client (Mock)", version="1.0.0")
        self.setup_middleware()
        self.setup_routes()
        
        # Mock state
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
            return {
                "status": "healthy", 
                "service": "whisper_client_mock", 
                "port": 8085,
                "timestamp": time.time(),
                "mode": "mock"
            }
        
        @self.app.get("/info")
        async def service_info():
            return {
                "service": "whisper_client_mock",
                "version": "1.0.0",
                "description": "Mock speech-to-text processing service for testing",
                "capabilities": [
                    "mock_recording",
                    "mock_transcription",
                    "file_upload",
                    "status_tracking"
                ],
                "model_size": "mock",
                "device": "mock"
            }
        
        @self.app.post("/recording/start")
        async def start_recording():
            """Mock start recording"""
            try:
                session_id = f"mock_rec_{int(time.time())}"
                
                self.active_recordings[session_id] = {
                    "start_time": datetime.now().isoformat(),
                    "status": "recording",
                    "mock": True
                }
                
                return {
                    "success": True,
                    "session_id": session_id,
                    "message": "Mock recording started"
                }
                    
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/recording/stop/{session_id}")
        async def stop_recording(session_id: str, background_tasks: BackgroundTasks):
            """Mock stop recording"""
            try:
                if session_id not in self.active_recordings:
                    raise HTTPException(status_code=404, detail="Recording session not found")
                
                # Update session
                self.active_recordings[session_id]["status"] = "processing"
                
                # Mock processing in background
                background_tasks.add_task(self._mock_process_recording, session_id)
                
                return {
                    "success": True,
                    "session_id": session_id,
                    "message": "Mock recording stopped, processing..."
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/recording/status/{session_id}")
        async def get_recording_status(session_id: str):
            """Get recording status and results"""
            if session_id not in self.active_recordings:
                raise HTTPException(status_code=404, detail="Recording session not found")
            
            return self.active_recordings[session_id]
        
        @self.app.post("/transcribe/text")
        async def transcribe_text(data: dict):
            """Mock transcribe text input"""
            try:
                text_input = data.get("text", "sample text")
                
                # Mock transcription result
                result = {
                    "text": f"Mock transcription of: {text_input}",
                    "language": "en",
                    "segments": [
                        {
                            "text": f"Mock transcription of: {text_input}",
                            "start": 0.0,
                            "end": 5.0,
                            "confidence": 0.95
                        }
                    ],
                    "duration": 5.0,
                    "confidence": 0.95,
                    "mock": True
                }
                
                # Store in history
                self.transcription_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "input": text_input,
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
            """Mock change model"""
            try:
                valid_sizes = ["tiny", "base", "small", "medium", "large"]
                if model_size not in valid_sizes:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid model size. Choose from: {valid_sizes}"
                    )
                
                return {
                    "success": True,
                    "model_size": f"mock_{model_size}",
                    "device": "mock",
                    "message": f"Mock model changed to {model_size}"
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
    
    async def _mock_process_recording(self, session_id: str):
        """Mock process recording in background"""
        try:
            # Simulate processing time
            await asyncio.sleep(2)
            
            # Mock transcription result
            result = {
                "text": f"Mock transcription for session {session_id}",
                "language": "en",
                "segments": [
                    {
                        "text": f"Mock transcription for session {session_id}",
                        "start": 0.0,
                        "end": 3.0,
                        "confidence": 0.92
                    }
                ],
                "duration": 3.0,
                "confidence": 0.92,
                "mock": True
            }
            
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
                    "mock_speech_to_text",
                    "mock_audio_recording",
                    "file_upload",
                    "status_tracking"
                ],
                "metadata": {
                    "model_size": "mock",
                    "device": "mock",
                    "mode": "testing"
                }
            }
            
            response = requests.post(
                f"{self.service_registry_url}/register",
                json=service_info,
                timeout=5
            )
            
            if response.status_code == 200:
                logging.info("Successfully registered with service registry")
            else:
                logging.warning(f"Failed to register: {response.status_code}")
                
        except Exception as e:
            logging.warning(f"Could not register with service registry: {e}")

# Global service instance
whisper_service = WhisperService()

async def startup_event():
    """Startup event handler"""
    logging.info("Starting Whisper Client Mock service...")
    await whisper_service.register_service()
    logging.info("Whisper Client Mock service started on port 8085")

async def shutdown_event():
    """Shutdown event handler"""
    logging.info("Shutting down Whisper Client Mock service...")

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
        whisper_service.app,
        host="localhost",
        port=8085,
        reload=False,
        log_level="info"
    )
