#!/usr/bin/env python3
"""
Simple Screen Capture Service - Basic screenshot functionality test
"""

import os
import time
import json
import logging
import subprocess
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SimpleScreenshot:
    """Basic screenshot information"""
    timestamp: float
    screenshot_path: str
    file_size: int

class SimpleScreenService:
    """Simple screen capture service for testing"""
    
    def __init__(self, port: int = 8091):
        self.port = port
        self.app = Flask(__name__)
        CORS(self.app)
        
        # Screenshots directory
        self.screenshots_dir = "/Users/mark/.mcp/screenshots"
        os.makedirs(self.screenshots_dir, exist_ok=True)
        
        # Screenshot history
        self.screenshots: List[SimpleScreenshot] = []
        
        # Setup Flask routes
        self._setup_routes()
        
        # Service registration
        self._register_with_service_registry()
    
    def _setup_routes(self):
        """Setup Flask API routes"""
        
        @self.app.route('/capture', methods=['POST'])
        def capture_screen():
            """Capture current screen"""
            screenshot = self._capture_screen()
            
            if screenshot:
                self.screenshots.append(screenshot)
                return jsonify({
                    'timestamp': screenshot.timestamp,
                    'screenshot_path': screenshot.screenshot_path,
                    'file_size': screenshot.file_size,
                    'status': 'success'
                })
            else:
                return jsonify({'error': 'Failed to capture screen'}), 500
        
        @self.app.route('/list_screenshots', methods=['GET'])
        def list_screenshots():
            """List recent screenshots"""
            limit = request.args.get('limit', 10, type=int)
            
            recent_screenshots = []
            for screenshot in self.screenshots[-limit:]:
                recent_screenshots.append({
                    'timestamp': screenshot.timestamp,
                    'screenshot_path': screenshot.screenshot_path,
                    'file_size': screenshot.file_size,
                    'time_ago': time.time() - screenshot.timestamp
                })
            
            return jsonify({'screenshots': recent_screenshots})
        
        @self.app.route('/cleanup', methods=['POST'])
        def cleanup_old_screenshots():
            """Clean up old screenshots"""
            data = request.json or {}
            max_age_hours = data.get('max_age_hours', 24)
            
            removed_count = self._cleanup_screenshots(max_age_hours)
            
            return jsonify({
                'removed_count': removed_count,
                'status': 'cleanup_complete'
            })
        
        @self.app.route('/health', methods=['GET'])
        def health():
            return jsonify({
                'status': 'healthy',
                'timestamp': time.time(),
                'screenshots_count': len(self.screenshots),
                'screenshots_dir': self.screenshots_dir
            })
    
    def _capture_screen(self) -> Optional[SimpleScreenshot]:
        """Capture screen using macOS screencapture"""
        try:
            timestamp = time.time()
            filename = f"simple_screen_{int(timestamp)}.png"
            screenshot_path = os.path.join(self.screenshots_dir, filename)
            
            # Capture using macOS screencapture
            result = subprocess.run([
                'screencapture', '-x', screenshot_path
            ], capture_output=True, text=True)
            
            if result.returncode == 0 and os.path.exists(screenshot_path):
                file_size = os.path.getsize(screenshot_path)
                
                logger.info(f"Screenshot captured: {filename} ({file_size} bytes)")
                
                return SimpleScreenshot(
                    timestamp=timestamp,
                    screenshot_path=screenshot_path,
                    file_size=file_size
                )
            else:
                logger.error(f"Failed to capture screen: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"Error capturing screen: {e}")
            return None
    
    def _cleanup_screenshots(self, max_age_hours: float) -> int:
        """Clean up old screenshots"""
        cutoff_time = time.time() - (max_age_hours * 3600)
        removed_count = 0
        
        # Remove from tracking list
        self.screenshots = [s for s in self.screenshots if s.timestamp > cutoff_time]
        
        # Remove old files from disk
        try:
            for filename in os.listdir(self.screenshots_dir):
                filepath = os.path.join(self.screenshots_dir, filename)
                if os.path.isfile(filepath):
                    file_time = os.path.getmtime(filepath)
                    if file_time < cutoff_time:
                        os.remove(filepath)
                        removed_count += 1
                        logger.info(f"Removed old screenshot: {filename}")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        
        return removed_count
    
    def _register_with_service_registry(self):
        """Register this service with the service registry"""
        try:
            registration_data = {
                'name': 'simple_screen_service',
                'host': 'localhost',
                'port': self.port,
                'health_endpoint': '/health',
                'capabilities': ['screen_capture', 'screenshot_management'],
                'metadata': {
                    'screenshots_directory': self.screenshots_dir,
                    'description': 'Simple screen capture service for testing'
                }
            }
            
            response = requests.post('http://localhost:8080/register', 
                                   json=registration_data, timeout=10)
            
            if response.status_code == 200:
                logger.info("Successfully registered with service registry")
                logger.info(f"Service ID: {response.json().get('service_id')}")
            else:
                logger.error(f"Failed to register with service registry: {response.text}")
        except Exception as e:
            logger.error(f"Could not register with service registry: {e}")
    
    def start(self):
        """Start the simple screen service"""
        logger.info(f"Starting Simple Screen Service on port {self.port}")
        self.app.run(host='0.0.0.0', port=self.port, debug=False, threaded=True)
    
    def stop(self):
        """Stop the service"""
        logger.info("Simple Screen Service stopped")

if __name__ == "__main__":
    service = SimpleScreenService()
    try:
        service.start()
    except KeyboardInterrupt:
        service.stop()
