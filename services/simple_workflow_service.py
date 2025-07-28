#!/usr/bin/env python3
"""
Simple Workflow Service - Basic workflow execution test
"""

import json
import logging
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SimpleWorkflow:
    """Simple workflow definition"""
    name: str
    description: str
    steps: List[Dict[str, Any]]
    created_at: float

class SimpleWorkflowService:
    """Simple workflow orchestration service for testing"""
    
    def __init__(self, port: int = 8092):
        self.port = port
        self.app = Flask(__name__)
        CORS(self.app)
        
        # Workflow storage
        self.workflows: Dict[str, SimpleWorkflow] = {}
        self.execution_history: List[Dict[str, Any]] = []
        
        # Load default workflows
        self._load_default_workflows()
        
        # Setup Flask routes
        self._setup_routes()
        
        # Service registration
        self._register_with_service_registry()
    
    def _load_default_workflows(self):
        """Load default test workflows"""
        
        # Screenshot and Test Workflow
        screenshot_test = SimpleWorkflow(
            name="screenshot_test",
            description="Take a screenshot and run a test",
            steps=[
                {"action": "call_service", "service": "simple_screen_service", "endpoint": "/capture", "method": "POST"},
                {"action": "call_service", "service": "simple_test_service", "endpoint": "/test", "method": "GET"},
                {"action": "wait", "duration": 1},
                {"action": "log", "message": "Screenshot test workflow completed"}
            ],
            created_at=time.time()
        )
        
        # Multi-service Test Workflow
        multi_test = SimpleWorkflow(
            name="multi_service_test", 
            description="Test multiple services in sequence",
            steps=[
                {"action": "call_service", "service": "simple_test_service", "endpoint": "/echo", "method": "POST", 
                 "data": {"workflow": "multi_service_test", "step": 1}},
                {"action": "call_service", "service": "simple_screen_service", "endpoint": "/list_screenshots", "method": "GET"},
                {"action": "log", "message": "Multi-service test completed"}
            ],
            created_at=time.time()
        )
        
        self.workflows["screenshot_test"] = screenshot_test
        self.workflows["multi_service_test"] = multi_test
        
        logger.info(f"Loaded {len(self.workflows)} default workflows")
    
    def _setup_routes(self):
        """Setup Flask API routes"""
        
        @self.app.route('/workflows', methods=['GET'])
        def list_workflows():
            """List all available workflows"""
            workflows_data = []
            for name, workflow in self.workflows.items():
                workflows_data.append({
                    'name': workflow.name,
                    'description': workflow.description,
                    'steps_count': len(workflow.steps),
                    'created_at': workflow.created_at
                })
            
            return jsonify({'workflows': workflows_data})
        
        @self.app.route('/execute/<workflow_name>', methods=['POST'])
        def execute_workflow(workflow_name):
            """Execute a workflow"""
            if workflow_name not in self.workflows:
                return jsonify({'error': f'Workflow {workflow_name} not found'}), 404
            
            data = request.json or {}
            context = data.get('context', {})
            
            result = self._execute_workflow(workflow_name, context)
            return jsonify(result)
        
        @self.app.route('/execution_history', methods=['GET'])
        def get_execution_history():
            """Get workflow execution history"""
            limit = request.args.get('limit', 10, type=int)
            return jsonify({'executions': self.execution_history[-limit:]})
        
        @self.app.route('/add_workflow', methods=['POST'])
        def add_workflow():
            """Add a new workflow"""
            data = request.json
            
            workflow = SimpleWorkflow(
                name=data['name'],
                description=data['description'],
                steps=data['steps'],
                created_at=time.time()
            )
            
            self.workflows[workflow.name] = workflow
            logger.info(f"Added workflow: {workflow.name}")
            
            return jsonify({'status': 'workflow_added', 'name': workflow.name})
        
        @self.app.route('/health', methods=['GET'])
        def health():
            return jsonify({
                'status': 'healthy',
                'timestamp': time.time(),
                'workflows_count': len(self.workflows),
                'executions_count': len(self.execution_history)
            })
    
    def _execute_workflow(self, workflow_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a workflow"""
        workflow = self.workflows[workflow_name]
        execution_id = f"exec_{int(time.time())}_{workflow_name}"
        
        logger.info(f"Starting workflow execution: {execution_id}")
        
        execution_result = {
            'execution_id': execution_id,
            'workflow_name': workflow_name,
            'started_at': time.time(),
            'context': context,
            'steps_results': [],
            'status': 'running'
        }
        
        try:
            for i, step in enumerate(workflow.steps):
                logger.info(f"Executing step {i+1}/{len(workflow.steps)}: {step.get('action')}")
                
                step_result = self._execute_step(step, context, execution_id)
                step_result['step_number'] = i + 1
                step_result['step'] = step
                
                execution_result['steps_results'].append(step_result)
                
                # If step failed and no continue_on_error flag, stop
                if not step_result['success'] and not step.get('continue_on_error', False):
                    execution_result['status'] = 'failed'
                    execution_result['error'] = f"Step {i+1} failed: {step_result.get('error')}"
                    break
            
            if execution_result['status'] == 'running':
                execution_result['status'] = 'completed'
            
        except Exception as e:
            logger.error(f"Workflow execution error: {e}")
            execution_result['status'] = 'error'
            execution_result['error'] = str(e)
        
        execution_result['completed_at'] = time.time()
        execution_result['duration'] = execution_result['completed_at'] - execution_result['started_at']
        
        # Store in history
        self.execution_history.append(execution_result)
        
        # Keep only last 100 executions
        if len(self.execution_history) > 100:
            self.execution_history.pop(0)
        
        logger.info(f"Workflow execution completed: {execution_id} - {execution_result['status']}")
        
        return execution_result
    
    def _execute_step(self, step: Dict[str, Any], context: Dict[str, Any], execution_id: str) -> Dict[str, Any]:
        """Execute a single workflow step"""
        action = step.get('action')
        
        try:
            if action == 'call_service':
                return self._execute_service_call(step, context)
            
            elif action == 'wait':
                duration = step.get('duration', 1)
                time.sleep(duration)
                return {
                    'success': True,
                    'action': 'wait',
                    'duration': duration,
                    'message': f'Waited {duration} seconds'
                }
            
            elif action == 'log':
                message = step.get('message', 'Log step executed')
                logger.info(f"[{execution_id}] {message}")
                return {
                    'success': True,
                    'action': 'log',
                    'message': message
                }
            
            elif action == 'set_context':
                key = step.get('key')
                value = step.get('value')
                if key:
                    context[key] = value
                    return {
                        'success': True,
                        'action': 'set_context',
                        'key': key,
                        'value': value
                    }
                else:
                    return {
                        'success': False,
                        'action': 'set_context',
                        'error': 'Missing key parameter'
                    }
            
            else:
                return {
                    'success': False,
                    'action': action,
                    'error': f'Unknown action: {action}'
                }
        
        except Exception as e:
            return {
                'success': False,
                'action': action,
                'error': str(e)
            }
    
    def _execute_service_call(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a service call step"""
        service_name = step.get('service')
        endpoint = step.get('endpoint')
        method = step.get('method', 'GET')
        data = step.get('data', {})
        timeout = step.get('timeout', 10)
        
        try:
            # Get service info from registry
            registry_response = requests.get('http://localhost:8080/services', timeout=5)
            if registry_response.status_code != 200:
                return {
                    'success': False,
                    'action': 'call_service',
                    'error': 'Could not get service registry info'
                }
            
            services = registry_response.json()
            
            # Find target service
            target_service = None
            for service_id, service_info in services.items():
                if service_info['name'] == service_name:
                    target_service = service_info
                    break
            
            if not target_service:
                return {
                    'success': False,
                    'action': 'call_service',
                    'error': f'Service {service_name} not found in registry'
                }
            
            # Make service call
            url = f"http://{target_service['host']}:{target_service['port']}{endpoint}"
            
            if method.upper() == 'GET':
                response = requests.get(url, timeout=timeout)
            elif method.upper() == 'POST':
                response = requests.post(url, json=data, timeout=timeout)
            else:
                return {
                    'success': False,
                    'action': 'call_service',
                    'error': f'Unsupported method: {method}'
                }
            
            return {
                'success': response.status_code < 400,
                'action': 'call_service',
                'service': service_name,
                'endpoint': endpoint,
                'method': method,
                'status_code': response.status_code,
                'response': response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text,
                'url': url
            }
        
        except Exception as e:
            return {
                'success': False,
                'action': 'call_service',
                'service': service_name,
                'endpoint': endpoint,
                'error': str(e)
            }
    
    def _register_with_service_registry(self):
        """Register this service with the service registry"""
        try:
            registration_data = {
                'name': 'simple_workflow_service',
                'host': 'localhost',
                'port': self.port,
                'health_endpoint': '/health',
                'capabilities': ['workflow_execution', 'workflow_management'],
                'metadata': {
                    'workflows_count': len(self.workflows),
                    'description': 'Simple workflow orchestration service for testing'
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
        """Start the workflow service"""
        logger.info(f"Starting Simple Workflow Service on port {self.port}")
        self.app.run(host='0.0.0.0', port=self.port, debug=False, threaded=True)
    
    def stop(self):
        """Stop the service"""
        logger.info("Simple Workflow Service stopped")

if __name__ == "__main__":
    service = SimpleWorkflowService()
    try:
        service.start()
    except KeyboardInterrupt:
        service.stop()
