#!/usr/bin/env python3
"""
Conversational Voice Service
HTTP service that processes voice commands through Claude AI simulation
"""

import asyncio
import json
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os

# Add the services directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from conversational_voice import ConversationalVoiceProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Initialize the conversational processor
processor = ConversationalVoiceProcessor()

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "service": "conversational_voice",
        "port": 8087,
        "capabilities": ["voice_processing", "claude_integration", "action_execution"]
    })

@app.route('/process_command', methods=['POST'])
async def process_command():
    """Main endpoint for processing voice commands"""
    try:
        data = request.get_json()
        command = data.get('command', '')
        context = data.get('context', {})
        
        if not command:
            return jsonify({"error": "No command provided"}), 400
        
        logger.info(f"Processing voice command: '{command}'")
        
        # Process the command through Claude
        result = await processor.process_voice_command(command, context)
        
        return jsonify({
            "status": "success",
            "result": result
        })
        
    except Exception as e:
        logger.error(f"Error processing command: {e}")
        return jsonify({
            "status": "error", 
            "message": str(e)
        }), 500

@app.route('/info', methods=['GET'])
def info():
    return jsonify({
        "service": "conversational_voice",
        "version": "1.0.0",
        "description": "Conversational voice command processor with Claude AI integration",
        "endpoints": [
            "/health - Health check",
            "/process_command - Process voice commands",
            "/info - Service information"
        ]
    })

# Async wrapper for Flask
def run_async_endpoint(func):
    """Wrapper to run async functions in Flask"""
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(func(*args, **kwargs))
        finally:
            loop.close()
    return wrapper

# Apply async wrapper
app.view_functions['process_command'] = run_async_endpoint(app.view_functions['process_command'])

if __name__ == '__main__':
    logger.info("Starting Conversational Voice Service on port 8087")
    app.run(host='0.0.0.0', port=8087, debug=False)
