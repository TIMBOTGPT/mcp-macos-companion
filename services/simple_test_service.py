#!/usr/bin/env python3
"""
Simple Test Service - Basic functionality test
"""

import json
import logging
import time
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleTestService:
    """Simple test service for basic functionality"""
    
    def __init__(self, port: int = 8090):
        self.port = port
        self.app = Flask(__name__)
        CORS(self.app)
        
        # Setup Flask routes
        self._setup_routes()
        
        # Register with service registry
        self._register_with_service_registry()
    
    def _setup_routes(self):
        """Setup Flask API routes"""
        
        @self.app.route('/test', methods=['GET'])
        def test():
            return jsonify({
                'message': 'Test service is working!',
                'timestamp': time.time()
            })
        
        @self.app.route('/echo', methods=['POST'])
        def echo():
            data = request.json
            return jsonify({
                'echo': data,
                'received_at': time.time()
            })
        
        @self.app.route('/health', methods=['GET'])
        def health():
            return jsonify({
                'status': 'healthy',
                'timestamp': time.time(),
                'service': 'simple_test_service'
            })
    
    def _register_with_service_registry(self):
        """Register this service with the service registry"""
        try:
            registration_data = {
                'name': 'simple_test_service',
                'host': 'localhost',
                'port': self.port,
                'health_endpoint': '/health',
                'capabilities': ['test', 'echo'],
                'metadata': {
                    'description': 'Simple test service for infrastructure validation'
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
        """Start the test service"""
        logger.info(f"Starting Simple Test Service on port {self.port}")
        self.app.run(host='0.0.0.0', port=self.port, debug=False, threaded=True)
    
    def stop(self):
        """Stop the service"""
        logger.info("Simple Test Service stopped")

if __name__ == "__main__":
    service = SimpleTestService()
    try:
        service.start()
    except KeyboardInterrupt:
        service.stop()
