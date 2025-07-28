#!/usr/bin/env python3
"""
MCP macOS Companion - Service Registry
Central coordinator for all microservices
"""

import json
import logging
import threading
import time
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import uuid
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ServiceInfo:
    """Information about a registered service"""
    name: str
    host: str
    port: int
    health_endpoint: str
    capabilities: List[str]
    last_heartbeat: float
    service_id: str
    status: str = "healthy"
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class ServiceMessage:
    """Message structure for inter-service communication"""
    message_id: str
    source_service: str
    target_service: str
    message_type: str
    payload: Dict[str, Any]
    timestamp: float
    correlation_id: Optional[str] = None

class ServiceRegistry:
    """Central service registry and message broker"""
    
    def __init__(self, port: int = 8080):
        self.port = port
        self.services: Dict[str, ServiceInfo] = {}
        self.message_handlers: Dict[str, Callable] = {}
        self.app = Flask(__name__)
        CORS(self.app)
        
        # Setup Flask routes
        self._setup_routes()
        
        # Start background tasks
        self.running = True
        self.health_check_thread = threading.Thread(target=self._health_check_loop)
        self.health_check_thread.daemon = True
        
    def _setup_routes(self):
        """Setup Flask API routes"""
        
        @self.app.route('/register', methods=['POST'])
        def register_service():
            data = request.json
            service_info = ServiceInfo(
                name=data['name'],
                host=data['host'],
                port=data['port'],
                health_endpoint=data.get('health_endpoint', '/health'),
                capabilities=data.get('capabilities', []),
                last_heartbeat=time.time(),
                service_id=str(uuid.uuid4()),
                metadata=data.get('metadata', {})
            )
            
            self.services[service_info.service_id] = service_info
            logger.info(f"Registered service: {service_info.name} ({service_info.service_id})")
            
            return jsonify({
                'service_id': service_info.service_id,
                'status': 'registered'
            })
        
        @self.app.route('/services', methods=['GET'])
        def list_services():
            return jsonify({
                service_id: asdict(service_info) 
                for service_id, service_info in self.services.items()
            })
        
        @self.app.route('/services/<service_id>/heartbeat', methods=['POST'])
        def heartbeat(service_id):
            if service_id in self.services:
                self.services[service_id].last_heartbeat = time.time()
                self.services[service_id].status = "healthy"
                return jsonify({'status': 'ok'})
            return jsonify({'error': 'Service not found'}), 404
        
        @self.app.route('/send_message', methods=['POST'])
        def send_message():
            data = request.json
            message = ServiceMessage(
                message_id=str(uuid.uuid4()),
                source_service=data['source_service'],
                target_service=data['target_service'],
                message_type=data['message_type'],
                payload=data['payload'],
                timestamp=time.time(),
                correlation_id=data.get('correlation_id')
            )
            
            # Route message to target service
            result = self._route_message(message)
            return jsonify(result)
        
        @self.app.route('/health', methods=['GET'])
        def health():
            return jsonify({
                'status': 'healthy',
                'timestamp': time.time(),
                'registered_services': len(self.services)
            })
    
    def _route_message(self, message: ServiceMessage) -> Dict[str, Any]:
        """Route message to target service"""
        target_service = None
        
        # Find target service by name
        for service_info in self.services.values():
            if service_info.name == message.target_service:
                target_service = service_info
                break
        
        if not target_service:
            return {'error': f'Target service {message.target_service} not found'}
        
        # Send message to target service
        try:
            url = f"http://{target_service.host}:{target_service.port}/message"
            response = requests.post(url, json=asdict(message), timeout=30)
            return response.json()
        except Exception as e:
            logger.error(f"Failed to route message to {message.target_service}: {e}")
            return {'error': str(e)}
    
    def _health_check_loop(self):
        """Background health check for registered services"""
        while self.running:
            current_time = time.time()
            
            for service_id, service_info in list(self.services.items()):
                # Check if service missed heartbeat
                if current_time - service_info.last_heartbeat > 60:  # 60 second timeout
                    service_info.status = "unhealthy"
                    logger.warning(f"Service {service_info.name} marked as unhealthy")
                
                # Try to ping health endpoint
                try:
                    url = f"http://{service_info.host}:{service_info.port}{service_info.health_endpoint}"
                    response = requests.get(url, timeout=5)
                    if response.status_code == 200:
                        service_info.status = "healthy"
                        service_info.last_heartbeat = current_time
                except Exception:
                    service_info.status = "unhealthy"
            
            time.sleep(30)  # Check every 30 seconds
    
    def broadcast_message(self, message_type: str, payload: Dict[str, Any]):
        """Broadcast message to all services"""
        for service_info in self.services.values():
            if service_info.status == "healthy":
                message = ServiceMessage(
                    message_id=str(uuid.uuid4()),
                    source_service="service_registry",
                    target_service=service_info.name,
                    message_type=message_type,
                    payload=payload,
                    timestamp=time.time()
                )
                self._route_message(message)
    
    def get_services_by_capability(self, capability: str) -> List[ServiceInfo]:
        """Get all services that have a specific capability"""
        return [
            service_info for service_info in self.services.values()
            if capability in service_info.capabilities and service_info.status == "healthy"
        ]
    
    def start(self):
        """Start the service registry"""
        logger.info(f"Starting Service Registry on port {self.port}")
        self.health_check_thread.start()
        
        # Run Flask app
        self.app.run(host='0.0.0.0', port=self.port, debug=False, threaded=True)
    
    def stop(self):
        """Stop the service registry"""
        self.running = False
        logger.info("Service Registry stopped")

if __name__ == "__main__":
    registry = ServiceRegistry(port=8080)
    try:
        registry.start()
    except KeyboardInterrupt:
        registry.stop()
