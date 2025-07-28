#!/usr/bin/env python3
"""
MCP macOS Companion - Screen Vision Service
Screenshot analysis, OCR, and contextual triggers
"""

import os
import time
import json
import logging
import threading
import subprocess
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
import requests
import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageGrab
from flask import Flask, request, jsonify
from flask_cors import CORS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ScreenContent:
    """Information about screen content"""
    timestamp: float
    screenshot_path: str
    ocr_text: str
    detected_elements: List[Dict[str, Any]]
    content_hash: str
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class ContentTrigger:
    """Trigger for screen content changes"""
    name: str
    condition: Dict[str, Any]  # e.g., {"text_contains": "Claude", "app": "Terminal"}
    action: Dict[str, Any]     # e.g., {"notify": "Claude detected", "execute": "workflow_x"}
    cooldown_seconds: int = 30
    last_triggered: float = 0
    active: bool = True

class ScreenVision:
    """Screen analysis and contextual trigger service"""
    
    def __init__(self, port: int = 8083):
        self.port = port
        self.app = Flask(__name__)
        CORS(self.app)
        
        # Screen monitoring
        self.monitoring_active = False
        self.monitor_thread = None
        self.monitor_interval = 5  # seconds
        
        # Content tracking
        self.last_content: Optional[ScreenContent] = None
        self.content_history: List[ScreenContent] = []
        self.max_history = 100
        
        # Triggers
        self.triggers: List[ContentTrigger] = []
        
        # Screenshots directory
        self.screenshots_dir = "/Users/mark/.mcp/screenshots"
        os.makedirs(self.screenshots_dir, exist_ok=True)
        
        # Load default triggers
        self._load_default_triggers()
        
        # Setup Flask routes
        self._setup_routes()
        
        # Service registration
        self._register_with_service_registry()
    
    def _load_default_triggers(self):
        """Load default content triggers"""
        default_triggers = [
            ContentTrigger(
                name="Claude Terminal Detection",
                condition={"text_contains": "claude", "app_context": "terminal"},
                action={"store_context": "claude_interaction", "priority": "high"}
            ),
            ContentTrigger(
                name="Error Detection", 
                condition={"text_contains": ["error", "failed", "exception"]},
                action={"notify": "Error detected on screen", "capture_context": True}
            ),
            ContentTrigger(
                name="File Download Completion",
                condition={"text_contains": "download complete", "app_context": "browser"},
                action={"execute_workflow": "organize_downloads"}
            ),
            ContentTrigger(
                name="Meeting Detection",
                condition={"text_contains": ["zoom", "teams", "meet"], "app_context": "any"},
                action={"store_context": "meeting_activity", "privacy_mode": True}
            )
        ]
        
        self.triggers.extend(default_triggers)
    
    def _setup_routes(self):
        """Setup Flask API routes"""
        
        @self.app.route('/start_monitoring', methods=['POST'])
        def start_monitoring():
            """Start screen monitoring"""
            if self.monitoring_active:
                return jsonify({'status': 'already_monitoring'})
            
            self.monitoring_active = True
            self.monitor_thread = threading.Thread(target=self._monitor_screen)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
            
            logger.info("Screen monitoring started")
            return jsonify({'status': 'monitoring_started'})
        
        @self.app.route('/stop_monitoring', methods=['POST'])
        def stop_monitoring():
            """Stop screen monitoring"""
            self.monitoring_active = False
            
            if self.monitor_thread and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=2)
            
            logger.info("Screen monitoring stopped")
            return jsonify({'status': 'monitoring_stopped'})
        
        @self.app.route('/capture_screen', methods=['POST'])
        def capture_screen():
            """Capture and analyze current screen"""
            data = request.json or {}
            analyze = data.get('analyze', True)
            
            content = self._capture_and_analyze_screen() if analyze else self._capture_screen_only()
            
            if content:
                return jsonify({
                    'timestamp': content.timestamp,
                    'screenshot_path': content.screenshot_path,
                    'ocr_text': content.ocr_text if analyze else "Analysis skipped",
                    'detected_elements': content.detected_elements if analyze else [],
                    'content_hash': content.content_hash
                })
            else:
                return jsonify({'error': 'Failed to capture screen'}), 500
        
        @self.app.route('/add_trigger', methods=['POST'])
        def add_trigger():
            """Add a new content trigger"""
            data = request.json
            trigger = ContentTrigger(
                name=data['name'],
                condition=data['condition'],
                action=data['action'],
                cooldown_seconds=data.get('cooldown_seconds', 30)
            )
            
            self.triggers.append(trigger)
            logger.info(f"Added trigger: {trigger.name}")
            
            return jsonify({'status': 'trigger_added', 'trigger_name': trigger.name})
        
        @self.app.route('/triggers', methods=['GET'])
        def list_triggers():
            """List all content triggers"""
            triggers_data = []
            for trigger in self.triggers:
                triggers_data.append({
                    'name': trigger.name,
                    'condition': trigger.condition,
                    'action': trigger.action,
                    'cooldown_seconds': trigger.cooldown_seconds,
                    'last_triggered': trigger.last_triggered,
                    'active': trigger.active
                })
            
            return jsonify({'triggers': triggers_data})
        
        @self.app.route('/content_history', methods=['GET'])
        def get_content_history():
            """Get recent screen content history"""
            limit = request.args.get('limit', 10, type=int)
            
            recent_content = []
            for content in self.content_history[-limit:]:
                recent_content.append({
                    'timestamp': content.timestamp,
                    'screenshot_path': content.screenshot_path,
                    'ocr_text': content.ocr_text[:200] + "..." if len(content.ocr_text) > 200 else content.ocr_text,
                    'detected_elements_count': len(content.detected_elements),
                    'content_hash': content.content_hash
                })
            
            return jsonify({'content_history': recent_content})
        
        @self.app.route('/search_content', methods=['POST'])
        def search_content():
            """Search through screen content history"""
            data = request.json
            query = data['query'].lower()
            
            matching_content = []
            for content in self.content_history:
                if query in content.ocr_text.lower():
                    matching_content.append({
                        'timestamp': content.timestamp,
                        'screenshot_path': content.screenshot_path,
                        'matching_text': self._extract_matching_context(content.ocr_text, query),
                        'content_hash': content.content_hash
                    })
            
            return jsonify({'matches': matching_content})
        
        @self.app.route('/health', methods=['GET'])
        def health():
            return jsonify({
                'status': 'healthy',
                'timestamp': time.time(),
                'monitoring_active': self.monitoring_active,
                'triggers_count': len(self.triggers),
                'content_history_size': len(self.content_history)
            })
    
    def _monitor_screen(self):
        """Background screen monitoring loop"""
        logger.info("Screen monitoring loop started")
        
        while self.monitoring_active:
            try:
                # Capture and analyze screen
                content = self._capture_and_analyze_screen()
                
                if content:
                    # Check for content changes
                    if self._has_significant_change(content):
                        # Store in history
                        self.content_history.append(content)
                        if len(self.content_history) > self.max_history:
                            self.content_history.pop(0)
                        
                        # Check triggers
                        self._check_triggers(content)
                        
                        # Store in memory for context
                        self._store_screen_content_memory(content)
                        
                        self.last_content = content
                
                time.sleep(self.monitor_interval)
                
            except Exception as e:
                logger.error(f"Error in screen monitoring: {e}")
                time.sleep(self.monitor_interval * 2)  # Longer delay on error
        
        logger.info("Screen monitoring loop ended")
    
    def _capture_screen_only(self) -> Optional[ScreenContent]:
        """Capture screen without analysis"""
        try:
            timestamp = time.time()
            filename = f"screen_{int(timestamp)}.png"
            screenshot_path = os.path.join(self.screenshots_dir, filename)
            
            # Capture using macOS screencapture
            result = subprocess.run([
                'screencapture', '-x', screenshot_path
            ], capture_output=True, text=True)
            
            if result.returncode == 0 and os.path.exists(screenshot_path):
                # Calculate hash for change detection
                with open(screenshot_path, 'rb') as f:
                    import hashlib
                    content_hash = hashlib.md5(f.read()).hexdigest()
                
                return ScreenContent(
                    timestamp=timestamp,
                    screenshot_path=screenshot_path,
                    ocr_text="",
                    detected_elements=[],
                    content_hash=content_hash
                )
            else:
                logger.error(f"Failed to capture screen: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"Error capturing screen: {e}")
            return None
    
    def _capture_and_analyze_screen(self) -> Optional[ScreenContent]:
        """Capture screen and perform OCR analysis"""
        try:
            timestamp = time.time()
            filename = f"screen_{int(timestamp)}.png"
            screenshot_path = os.path.join(self.screenshots_dir, filename)
            
            # Capture using macOS screencapture
            result = subprocess.run([
                'screencapture', '-x', screenshot_path
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Failed to capture screen: {result.stderr}")
                return None
            
            if not os.path.exists(screenshot_path):
                logger.error("Screenshot file was not created")
                return None
            
            # Load image for analysis
            image = Image.open(screenshot_path)
            
            # OCR text extraction
            ocr_text = pytesseract.image_to_string(image)
            
            # Element detection (basic approach)
            detected_elements = self._detect_ui_elements(image)
            
            # Calculate hash for change detection
            with open(screenshot_path, 'rb') as f:
                import hashlib
                content_hash = hashlib.md5(f.read()).hexdigest()
            
            # Get current application context
            app_context = self._get_current_app_context()
            
            return ScreenContent(
                timestamp=timestamp,
                screenshot_path=screenshot_path,
                ocr_text=ocr_text,
                detected_elements=detected_elements,
                content_hash=content_hash,
                metadata={'app_context': app_context}
            )
            
        except Exception as e:
            logger.error(f"Error capturing and analyzing screen: {e}")
            return None
    
    def _detect_ui_elements(self, image: Image.Image) -> List[Dict[str, Any]]:
        """Basic UI element detection"""
        elements = []
        
        try:
            # Convert to OpenCV format
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            
            # Detect buttons (simplified approach)
            # This is a basic implementation - could be enhanced with ML models
            
            # Find rectangles that might be buttons
            edges = cv2.Canny(gray, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                
                # Filter for button-like shapes
                if 50 < w < 200 and 20 < h < 60:
                    elements.append({
                        'type': 'potential_button',
                        'bounds': {'x': x, 'y': y, 'width': w, 'height': h},
                        'confidence': 0.5
                    })
            
            # Limit results
            elements = elements[:20]
            
        except Exception as e:
            logger.error(f"Error detecting UI elements: {e}")
        
        return elements
    
    def _get_current_app_context(self) -> str:
        """Get current active application"""
        try:
            result = subprocess.run([
                'osascript', '-e', 
                'tell application "System Events" to get name of first application process whose frontmost is true'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return "unknown"
                
        except Exception as e:
            logger.error(f"Error getting app context: {e}")
            return "unknown"
    
    def _has_significant_change(self, content: ScreenContent) -> bool:
        """Check if screen content has changed significantly"""
        if not self.last_content:
            return True
        
        # Compare content hashes
        if content.content_hash != self.last_content.content_hash:
            return True
        
        # Could add more sophisticated comparison here
        return False
    
    def _check_triggers(self, content: ScreenContent):
        """Check if any triggers should fire"""
        current_time = time.time()
        
        for trigger in self.triggers:
            if not trigger.active:
                continue
            
            # Check cooldown
            if current_time - trigger.last_triggered < trigger.cooldown_seconds:
                continue
            
            if self._trigger_matches(trigger, content):
                logger.info(f"Trigger fired: {trigger.name}")
                self._execute_trigger_action(trigger, content)
                trigger.last_triggered = current_time
    
    def _trigger_matches(self, trigger: ContentTrigger, content: ScreenContent) -> bool:
        """Check if trigger condition matches current content"""
        condition = trigger.condition
        
        # Text contains check
        if 'text_contains' in condition:
            text_to_check = condition['text_contains']
            if isinstance(text_to_check, str):
                text_to_check = [text_to_check]
            
            content_text = content.ocr_text.lower()
            for text in text_to_check:
                if text.lower() in content_text:
                    # Check app context if specified
                    if 'app_context' in condition:
                        app_condition = condition['app_context']
                        current_app = content.metadata.get('app_context', '').lower()
                        
                        if app_condition != 'any' and app_condition.lower() not in current_app:
                            continue
                    
                    return True
        
        return False
    
    def _execute_trigger_action(self, trigger: ContentTrigger, content: ScreenContent):
        """Execute trigger action"""
        action = trigger.action
        
        try:
            if 'notify' in action:
                self._send_notification(action['notify'], content)
            
            if 'store_context' in action:
                self._store_trigger_context(trigger, content, action['store_context'])
            
            if 'execute_workflow' in action:
                self._execute_workflow(action['execute_workflow'], content)
            
            if 'capture_context' in action and action['capture_context']:
                self._capture_extended_context(content)
        
        except Exception as e:
            logger.error(f"Error executing trigger action: {e}")
    
    def _extract_matching_context(self, text: str, query: str, context_chars: int = 100) -> str:
        """Extract context around matching query"""
        text_lower = text.lower()
        query_lower = query.lower()
        
        index = text_lower.find(query_lower)
        if index == -1:
            return ""
        
        start = max(0, index - context_chars)
        end = min(len(text), index + len(query) + context_chars)
        
        return text[start:end]
    
    def _store_screen_content_memory(self, content: ScreenContent):
        """Store screen content in memory for context"""
        try:
            # Only store if there's meaningful text
            if len(content.ocr_text.strip()) < 10:
                return
            
            memory_data = {
                'content': f"Screen content: {content.ocr_text[:200]}...",
                'category': 'screen_activity',
                'metadata': {
                    'screenshot_path': content.screenshot_path,
                    'app_context': content.metadata.get('app_context', 'unknown'),
                    'elements_detected': len(content.detected_elements),
                    'timestamp': content.timestamp
                },
                'tags': ['screen_capture', content.metadata.get('app_context', 'unknown')]
            }
            
            requests.post('http://localhost:8081/store', json=memory_data, timeout=10)
        except Exception as e:
            logger.error(f"Could not store screen content memory: {e}")
    
    def _store_trigger_context(self, trigger: ContentTrigger, content: ScreenContent, context_type: str):
        """Store trigger context in memory"""
        try:
            memory_data = {
                'content': f"Trigger '{trigger.name}' fired: {context_type}",
                'category': 'trigger_activity',
                'metadata': {
                    'trigger_name': trigger.name,
                    'context_type': context_type,
                    'app_context': content.metadata.get('app_context'),
                    'screenshot_path': content.screenshot_path,
                    'ocr_excerpt': content.ocr_text[:500]
                },
                'tags': ['trigger', context_type, trigger.name.replace(' ', '_').lower()]
            }
            
            requests.post('http://localhost:8081/store', json=memory_data, timeout=10)
        except Exception as e:
            logger.error(f"Could not store trigger context: {e}")
    
    def _send_notification(self, message: str, content: ScreenContent):
        """Send notification through service registry"""
        try:
            notification_data = {
                'source_service': 'screen_vision',
                'target_service': 'notification_service',
                'message_type': 'screen_notification',
                'payload': {
                    'message': message,
                    'app_context': content.metadata.get('app_context'),
                    'screenshot_path': content.screenshot_path,
                    'timestamp': content.timestamp
                }
            }
            
            requests.post('http://localhost:8080/send_message', json=notification_data, timeout=10)
        except Exception as e:
            logger.error(f"Could not send notification: {e}")
    
    def _execute_workflow(self, workflow_name: str, content: ScreenContent):
        """Execute workflow through orchestrator"""
        try:
            workflow_data = {
                'source_service': 'screen_vision',
                'target_service': 'workflow_orchestrator',
                'message_type': 'execute_workflow',
                'payload': {
                    'workflow_name': workflow_name,
                    'trigger_context': {
                        'screenshot_path': content.screenshot_path,
                        'app_context': content.metadata.get('app_context'),
                        'ocr_text': content.ocr_text,
                        'timestamp': content.timestamp
                    }
                }
            }
            
            requests.post('http://localhost:8080/send_message', json=workflow_data, timeout=10)
        except Exception as e:
            logger.error(f"Could not execute workflow: {e}")
    
    def _capture_extended_context(self, content: ScreenContent):
        """Capture extended context around trigger"""
        # This could include multiple screenshots, clipboard content, etc.
        logger.info(f"Capturing extended context for trigger at {content.timestamp}")
    
    def _register_with_service_registry(self):
        """Register this service with the service registry"""
        try:
            registration_data = {
                'name': 'screen_vision',
                'host': 'localhost',
                'port': self.port,
                'health_endpoint': '/health',
                'capabilities': ['screen_capture', 'ocr', 'content_monitoring', 'contextual_triggers'],
                'metadata': {
                    'screenshots_directory': self.screenshots_dir,
                    'monitor_interval': self.monitor_interval,
                    'max_history': self.max_history
                }
            }
            
            response = requests.post('http://localhost:8080/register', 
                                   json=registration_data, timeout=10)
            
            if response.status_code == 200:
                logger.info("Successfully registered with service registry")
            else:
                logger.error(f"Failed to register with service registry: {response.text}")
        except Exception as e:
            logger.error(f"Could not register with service registry: {e}")
    
    def start(self):
        """Start the screen vision service"""
        logger.info(f"Starting Screen Vision Service on port {self.port}")
        self.app.run(host='0.0.0.0', port=self.port, debug=False, threaded=True)
    
    def stop(self):
        """Stop the service"""
        self.monitoring_active = False
        logger.info("Screen Vision Service stopped")

if __name__ == "__main__":
    service = ScreenVision()
    try:
        service.start()
    except KeyboardInterrupt:
        service.stop()
