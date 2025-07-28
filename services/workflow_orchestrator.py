#!/usr/bin/env python3
"""
MCP macOS Companion - Workflow Orchestrator
Intelligence brain with workflow templates and cross-service coordination
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WorkflowStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TriggerType(Enum):
    SCREEN_CHANGE = "screen_change"
    VOICE_COMMAND = "voice_command"
    TIME_BASED = "time_based"
    FILE_EVENT = "file_event"
    CONTEXT_CHANGE = "context_change"
    MANUAL = "manual"

@dataclass
class WorkflowStep:
    """A single step in a workflow"""
    step_id: str
    service: str
    action: str
    parameters: Dict[str, Any]
    conditions: Optional[Dict[str, Any]] = None
    timeout_seconds: int = 30
    retry_count: int = 0
    max_retries: int = 2

@dataclass
class WorkflowTemplate:
    """Template for creating workflows"""
    template_id: str
    name: str
    description: str
    steps: List[WorkflowStep]
    triggers: List[Dict[str, Any]]
    parameters: Dict[str, Any]
    category: str = "general"

@dataclass
class WorkflowInstance:
    """An active workflow instance"""
    workflow_id: str
    template_id: str
    name: str
    status: WorkflowStatus
    steps: List[WorkflowStep]
    current_step: int
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    context: Dict[str, Any] = None
    results: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.context is None:
            self.context = {}
        if self.results is None:
            self.results = {}

class WorkflowOrchestrator:
    """Workflow orchestration and intelligence coordination"""
    
    def __init__(self, port: int = 8084):
        self.port = port
        self.app = Flask(__name__)
        CORS(self.app)
        
        # Workflow management
        self.templates: Dict[str, WorkflowTemplate] = {}
        self.active_workflows: Dict[str, WorkflowInstance] = {}
        self.workflow_history: List[WorkflowInstance] = []
        
        # Service registry integration
        self.available_services: Dict[str, Dict[str, Any]] = {}
        
        # Load default templates
        self._load_default_templates()
        
        # Setup Flask routes
        self._setup_routes()
        
        # Service registration
        self._register_with_service_registry()
        
        # Refresh service list
        self._refresh_available_services()
        
        # Manually add conversational voice service (fallback)
        self.available_services['conversational_voice'] = {
            'name': 'conversational_voice',
            'host': 'localhost',
            'port': 8092,  # Updated to use the simple Claude bridge
            'status': 'healthy'
        }
    
    def _load_default_templates(self):
        """Load default workflow templates"""
        
        # Smart File Organization Template
        file_org_template = WorkflowTemplate(
            template_id="smart_file_organization",
            name="Smart File Organization",
            description="Automatically organize files based on content and patterns",
            steps=[
                WorkflowStep(
                    step_id="scan_downloads",
                    service="finder_actions",
                    action="organize",
                    parameters={"path": "~/Downloads"}
                ),
                WorkflowStep(
                    step_id="store_organization_result",
                    service="memory_engine",
                    action="store",
                    parameters={
                        "content": "File organization completed: {files_moved} files organized",
                        "category": "file_organization",
                        "tags": ["workflow", "files", "organization"]
                    }
                )
            ],
            triggers=[
                {"type": "file_event", "condition": {"new_files": ">5"}},
                {"type": "time_based", "condition": {"schedule": "daily"}}
            ],
            parameters={}
        )
        
        # Meeting Preparation Template
        meeting_prep_template = WorkflowTemplate(
            template_id="meeting_preparation",
            name="Meeting Preparation Assistant",
            description="Prepare for meetings by gathering context and relevant information",
            steps=[
                WorkflowStep(
                    step_id="capture_screen_context",
                    service="screen_vision",
                    action="capture_screen",
                    parameters={"analyze": True}
                ),
                WorkflowStep(
                    step_id="search_meeting_context",
                    service="memory_engine",
                    action="search",
                    parameters={
                        "query": "meeting {meeting_topic}",
                        "limit": 10
                    }
                ),
                WorkflowStep(
                    step_id="store_meeting_prep",
                    service="memory_engine",
                    action="store",
                    parameters={
                        "content": "Meeting preparation completed for: {meeting_topic}",
                        "category": "meeting_prep",
                        "tags": ["workflow", "meeting", "preparation"]
                    }
                )
            ],
            triggers=[
                {"type": "voice_command", "condition": {"phrase": "prepare for meeting"}},
                {"type": "screen_change", "condition": {"text_contains": ["zoom", "teams", "meet"]}}
            ],
            parameters={"meeting_topic": "general"}
        )
        
        # Simple Voice Command Template
        voice_template = WorkflowTemplate(
            template_id="voice_command_basic",
            name="Basic Voice Commands",
            description="Handle simple voice commands",
            steps=[
                WorkflowStep(
                    step_id="store_voice_command",
                    service="memory_engine",
                    action="store",
                    parameters={
                        "content": "Voice command received: {command_text}",
                        "category": "voice_commands",
                        "tags": ["workflow", "voice", "command"]
                    }
                )
            ],
            triggers=[
                {"type": "voice_command", "condition": {"phrase": "basic"}}
            ],
            parameters={"command_text": ""}
        )
        
        # Conversational Voice AI Template
        conversational_voice_template = WorkflowTemplate(
            template_id="conversational_voice_ai",
            name="Conversational Voice AI",
            description="Process voice commands through Claude AI for natural conversation and execution",
            steps=[
                WorkflowStep(
                    step_id="process_with_claude",
                    service="conversational_voice",
                    action="process_command",
                    parameters={
                        "command": "{command}",
                        "context": "{context}",
                        "timestamp": "{timestamp}"
                    }
                )
            ],
            triggers=[
                {"type": "voice_command", "condition": {}}
            ],
            parameters={"command": "", "context": {}, "timestamp": ""}
        )
        
        # Store templates
        self.templates[file_org_template.template_id] = file_org_template
        self.templates[meeting_prep_template.template_id] = meeting_prep_template
        self.templates[voice_template.template_id] = voice_template
        self.templates[conversational_voice_template.template_id] = conversational_voice_template
        
        logger.info(f"Loaded {len(self.templates)} default workflow templates")
    
    def _setup_routes(self):
        """Setup Flask API routes"""
        
        @self.app.route('/templates', methods=['GET'])
        def list_templates():
            """List all workflow templates"""
            templates_data = []
            for template in self.templates.values():
                templates_data.append({
                    'template_id': template.template_id,
                    'name': template.name,
                    'description': template.description,
                    'category': template.category,
                    'steps_count': len(template.steps),
                    'triggers': template.triggers
                })
            return jsonify({'templates': templates_data})
        
        @self.app.route('/templates/<template_id>', methods=['GET'])
        def get_template(template_id):
            """Get specific template details"""
            if template_id not in self.templates:
                return jsonify({'error': 'Template not found'}), 404
            
            template = self.templates[template_id]
            return jsonify(asdict(template))
        
        @self.app.route('/create_workflow', methods=['POST'])
        def create_workflow():
            """Create a new workflow instance from template"""
            data = request.json
            template_id = data['template_id']
            
            if template_id not in self.templates:
                return jsonify({'error': 'Template not found'}), 404
            
            template = self.templates[template_id]
            
            # Create workflow instance
            workflow_id = str(uuid.uuid4())
            workflow = WorkflowInstance(
                workflow_id=workflow_id,
                template_id=template_id,
                name=template.name,
                status=WorkflowStatus.PENDING,
                steps=template.steps.copy(),
                current_step=0,
                created_at=time.time(),
                context=data.get('context', {})
            )
            
            # Apply parameter overrides
            if 'parameters' in data:
                workflow.context.update(data['parameters'])
            
            self.active_workflows[workflow_id] = workflow
            
            return jsonify({
                'workflow_id': workflow_id,
                'status': 'created',
                'template_id': template_id
            })
        
        @self.app.route('/execute/<workflow_id>', methods=['POST'])
        def execute_workflow(workflow_id):
            """Execute a workflow"""
            if workflow_id not in self.active_workflows:
                return jsonify({'error': 'Workflow not found'}), 404
            
            workflow = self.active_workflows[workflow_id]
            
            if workflow.status != WorkflowStatus.PENDING:
                return jsonify({'error': f'Workflow is {workflow.status.value}, cannot execute'}), 400
            
            # Start execution in background
            result = self._execute_workflow_async(workflow)
            
            return jsonify({
                'workflow_id': workflow_id,
                'status': 'execution_started',
                'message': 'Workflow execution initiated'
            })
        
        @self.app.route('/workflows', methods=['GET'])
        def list_workflows():
            """List all workflows"""
            workflows_data = []
            
            # Active workflows
            for workflow in self.active_workflows.values():
                workflows_data.append({
                    'workflow_id': workflow.workflow_id,
                    'template_id': workflow.template_id,
                    'name': workflow.name,
                    'status': workflow.status.value,
                    'current_step': workflow.current_step,
                    'total_steps': len(workflow.steps),
                    'created_at': workflow.created_at,
                    'started_at': workflow.started_at,
                    'type': 'active'
                })
            
            # Recent completed workflows
            for workflow in self.workflow_history[-10:]:
                workflows_data.append({
                    'workflow_id': workflow.workflow_id,
                    'template_id': workflow.template_id,
                    'name': workflow.name,
                    'status': workflow.status.value,
                    'created_at': workflow.created_at,
                    'completed_at': workflow.completed_at,
                    'type': 'completed'
                })
            
            return jsonify({'workflows': workflows_data})
        
        @self.app.route('/workflows/<workflow_id>/status', methods=['GET'])
        def get_workflow_status(workflow_id):
            """Get workflow status and progress"""
            workflow = None
            
            # Check active workflows
            if workflow_id in self.active_workflows:
                workflow = self.active_workflows[workflow_id]
            else:
                # Check history
                for hist_workflow in self.workflow_history:
                    if hist_workflow.workflow_id == workflow_id:
                        workflow = hist_workflow
                        break
            
            if not workflow:
                return jsonify({'error': 'Workflow not found'}), 404
            
            return jsonify({
                'workflow_id': workflow.workflow_id,
                'template_id': workflow.template_id,
                'name': workflow.name,
                'status': workflow.status.value,
                'current_step': workflow.current_step,
                'total_steps': len(workflow.steps),
                'progress_percent': (workflow.current_step / len(workflow.steps)) * 100 if workflow.steps else 0,
                'created_at': workflow.created_at,
                'started_at': workflow.started_at,
                'completed_at': workflow.completed_at,
                'results': workflow.results
            })
        
        @self.app.route('/workflows/<workflow_id>/cancel', methods=['POST'])
        def cancel_workflow(workflow_id):
            """Cancel a running workflow"""
            if workflow_id not in self.active_workflows:
                return jsonify({'error': 'Workflow not found'}), 404
            
            workflow = self.active_workflows[workflow_id]
            
            if workflow.status not in [WorkflowStatus.PENDING, WorkflowStatus.RUNNING]:
                return jsonify({'error': f'Cannot cancel workflow in {workflow.status.value} state'}), 400
            
            workflow.status = WorkflowStatus.CANCELLED
            workflow.completed_at = time.time()
            
            # Move to history
            self.workflow_history.append(workflow)
            del self.active_workflows[workflow_id]
            
            return jsonify({
                'workflow_id': workflow_id,
                'status': 'cancelled'
            })
        
        @self.app.route('/trigger', methods=['POST'])
        def manual_trigger():
            """Manually trigger workflow execution"""
            data = request.json
            trigger_type = data.get('trigger_type', 'manual')
            trigger_data = data.get('trigger_data', {})
            
            # CRITICAL FIX: Ensure required parameters are available
            # Add missing context and timestamp if not provided
            if 'context' not in trigger_data:
                trigger_data['context'] = {}
            if 'timestamp' not in trigger_data:
                trigger_data['timestamp'] = datetime.utcnow().isoformat()
            
            logger.info(f"Trigger data: {trigger_data}")
            
            # Find templates that match this trigger
            matching_templates = self._find_matching_templates(trigger_type, trigger_data)
            
            results = []
            for template_id in matching_templates:
                # Create and execute workflow
                workflow_id = str(uuid.uuid4())
                template = self.templates[template_id]
                
                workflow = WorkflowInstance(
                    workflow_id=workflow_id,
                    template_id=template_id,
                    name=template.name,
                    status=WorkflowStatus.PENDING,
                    steps=template.steps.copy(),
                    current_step=0,
                    created_at=time.time(),
                    context=trigger_data
                )
                
                self.active_workflows[workflow_id] = workflow
                self._execute_workflow_async(workflow)
                
                results.append({
                    'workflow_id': workflow_id,
                    'template_id': template_id,
                    'triggered': True
                })
            
            return jsonify({
                'triggered_workflows': results,
                'trigger_type': trigger_type
            })
        
        @self.app.route('/health', methods=['GET'])
        def health():
            return jsonify({
                'status': 'healthy',
                'timestamp': time.time(),
                'active_workflows': len(self.active_workflows),
                'templates_loaded': len(self.templates),
                'available_services': len(self.available_services)
            })
    
    def _execute_workflow_async(self, workflow: WorkflowInstance):
        """Execute workflow asynchronously"""
        try:
            workflow.status = WorkflowStatus.RUNNING 
            workflow.started_at = time.time()
            
            logger.info(f"Starting workflow execution: {workflow.name} ({workflow.workflow_id})")
            
            for step_index, step in enumerate(workflow.steps):
                workflow.current_step = step_index
                
                try:
                    # Execute step
                    step_result = self._execute_workflow_step(workflow, step)
                    
                    # Store step result
                    workflow.results[step.step_id] = step_result
                    
                    # Check conditions for next step
                    if step.conditions:
                        if not self._evaluate_conditions(step.conditions, step_result, workflow.context):
                            logger.info(f"Step conditions not met, skipping remaining steps")
                            break
                    
                    logger.info(f"Step {step.step_id} completed successfully")
                    
                except Exception as e:
                    logger.error(f"Step {step.step_id} failed: {e}")
                    
                    # Retry logic
                    if step.retry_count < step.max_retries:
                        step.retry_count += 1
                        logger.info(f"Retrying step {step.step_id} (attempt {step.retry_count})")
                        # Retry the same step (don't increment step_index)
                        continue
                    else:
                        # Step failed, mark workflow as failed
                        workflow.status = WorkflowStatus.FAILED
                        workflow.completed_at = time.time()
                        workflow.results['error'] = str(e)
                        workflow.results['failed_step'] = step.step_id
                        
                        self._move_workflow_to_history(workflow)
                        return
            
            # Workflow completed successfully
            workflow.status = WorkflowStatus.COMPLETED
            workflow.completed_at = time.time()
            workflow.current_step = len(workflow.steps)
            
            logger.info(f"Workflow completed: {workflow.name}")
            
            # Store workflow completion in memory
            self._store_workflow_completion(workflow)
            
            # Move to history
            self._move_workflow_to_history(workflow)
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            workflow.status = WorkflowStatus.FAILED
            workflow.completed_at = time.time()
            workflow.results['error'] = str(e)
            self._move_workflow_to_history(workflow)
    
    def _execute_workflow_step(self, workflow: WorkflowInstance, step: WorkflowStep) -> Dict[str, Any]:
        """Execute a single workflow step"""
        
        # Interpolate parameters with context
        interpolated_params = self._interpolate_parameters(step.parameters, workflow.context, workflow.results)
        
        logger.info(f"Executing step: {step.step_id}")
        logger.info(f"Service: {step.service}")
        logger.info(f"Action: {step.action}")
        logger.info(f"Interpolated params: {interpolated_params}")
        
        # Find target service
        if step.service not in self.available_services:
            # Refresh service list
            self._refresh_available_services()
            
            if step.service not in self.available_services:
                raise Exception(f"Service {step.service} not available. Available services: {list(self.available_services.keys())}")
        
        service_info = self.available_services[step.service]
        
        # Construct service request - CRITICAL FIX: Use correct action mapping
        if step.service == "conversational_voice" and step.action == "process_command":
            service_url = f"http://{service_info['host']}:{service_info['port']}/process_command"
        else:
            service_url = f"http://{service_info['host']}:{service_info['port']}/{step.action}"
        
        logger.info(f"Making HTTP request to: {service_url}")
        
        # Execute service call
        try:
            response = requests.post(service_url, json=interpolated_params, timeout=step.timeout_seconds)
            
            logger.info(f"HTTP response status: {response.status_code}")
            logger.info(f"HTTP response body: {response.text[:200]}...")
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Service call failed: {response.status_code} - {response.text}")
                
        except requests.exceptions.Timeout:
            raise Exception(f"Service call timed out after {step.timeout_seconds} seconds")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Service call failed: {e}")
    
    def _interpolate_parameters(self, parameters: Dict[str, Any], context: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
        """Interpolate parameters with context and previous results"""
        interpolated = {}
        
        for key, value in parameters.items():
            if isinstance(value, str) and '{' in value and '}' in value:
                # String interpolation
                try:
                    interpolated[key] = value.format(**context, **results)
                    logger.info(f"Successfully interpolated {key}: {interpolated[key]}")
                except KeyError as e:
                    logger.error(f"Could not interpolate parameter {key}: missing {e}")
                    # CRITICAL FIX: Don't use the template string, provide a default
                    missing_key = str(e).strip("'")
                    if missing_key == 'context':
                        interpolated[key] = value.replace('{context}', json.dumps(context))
                    elif missing_key == 'timestamp':
                        interpolated[key] = value.replace('{timestamp}', datetime.utcnow().isoformat())
                    else:
                        interpolated[key] = value
            elif isinstance(value, dict):
                # Recursive interpolation for nested dictionaries
                interpolated[key] = self._interpolate_parameters(value, context, results)
            else:
                interpolated[key] = value
        
        return interpolated
    
    def _evaluate_conditions(self, conditions: Dict[str, Any], step_result: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Evaluate step conditions"""
        
        # Simple condition evaluation
        for condition_key, expected_value in conditions.items():
            if condition_key in step_result:
                actual_value = step_result[condition_key]
                
                if isinstance(expected_value, str) and expected_value.startswith('>'):
                    threshold = float(expected_value[1:])
                    if float(actual_value) <= threshold:
                        return False
                elif isinstance(expected_value, str) and expected_value.startswith('<'):
                    threshold = float(expected_value[1:])
                    if float(actual_value) >= threshold:
                        return False
                elif actual_value != expected_value:
                    return False
            elif condition_key in context:
                if context[condition_key] != expected_value:
                    return False
            else:
                return False
        
        return True
    
    def _find_matching_templates(self, trigger_type: str, trigger_data: Dict[str, Any]) -> List[str]:
        """Find templates that match the given trigger"""
        matching_templates = []
        
        for template in self.templates.values():
            for trigger in template.triggers:
                if trigger.get('type') == trigger_type:
                    # Check trigger conditions
                    if self._trigger_matches(trigger, trigger_data):
                        matching_templates.append(template.template_id)
                        break
        
        return matching_templates
    
    def _trigger_matches(self, trigger: Dict[str, Any], trigger_data: Dict[str, Any]) -> bool:
        """Check if trigger matches the provided data"""
        condition = trigger.get('condition', {})
        
        # Basic condition matching
        for key, expected_value in condition.items():
            if key not in trigger_data:
                return False
            
            actual_value = trigger_data[key]
            
            if isinstance(expected_value, list):
                # Check if any value in list matches
                if not any(exp_val in str(actual_value).lower() for exp_val in expected_value):
                    return False
            elif isinstance(expected_value, str):
                if expected_value.startswith('>'):
                    threshold = float(expected_value[1:])
                    if float(actual_value) <= threshold:
                        return False
                elif expected_value not in str(actual_value).lower():
                    return False
            elif actual_value != expected_value:
                return False
        
        return True
    
    def _move_workflow_to_history(self, workflow: WorkflowInstance):
        """Move workflow from active to history"""
        if workflow.workflow_id in self.active_workflows:
            del self.active_workflows[workflow.workflow_id]
        
        self.workflow_history.append(workflow)
        
        # Keep only last 100 workflows in history
        if len(self.workflow_history) > 100:
            self.workflow_history = self.workflow_history[-100:]
    
    def _store_workflow_completion(self, workflow: WorkflowInstance):
        """Store workflow completion in memory"""
        try:
            duration = workflow.completed_at - workflow.started_at if workflow.started_at else 0
            
            memory_data = {
                'content': f"Workflow completed: {workflow.name}",
                'category': 'workflow_execution',
                'metadata': {
                    'workflow_id': workflow.workflow_id,
                    'template_id': workflow.template_id,
                    'status': workflow.status.value,
                    'duration_seconds': duration,
                    'steps_completed': workflow.current_step,
                    'total_steps': len(workflow.steps),
                    'results_summary': str(workflow.results)[:500]
                },
                'tags': ['workflow', workflow.template_id.replace('_', '-'), workflow.status.value]
            }
            
            # CRITICAL FIX: Use correct memory service port
            requests.post('http://localhost:8082/store', json=memory_data, timeout=10)
        except Exception as e:
            logger.error(f"Could not store workflow completion: {e}")
    
    def _refresh_available_services(self):
        """Refresh list of available services from registry"""
        try:
            # CRITICAL FIX: Use correct service registry port
            response = requests.get('http://localhost:8081/services', timeout=10)
            
            if response.status_code == 200:
                services_data = response.json()
                
                self.available_services.clear()
                for service_id, service_info in services_data.items():
                    if service_info['status'] == 'healthy':
                        self.available_services[service_info['name']] = service_info
                
                logger.info(f"Refreshed service list: {len(self.available_services)} services available")
                logger.info(f"Available services: {list(self.available_services.keys())}")
            else:
                logger.error(f"Failed to refresh services: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Could not refresh services: {e}")
            # Ensure the conversational_voice service is available as fallback
            if 'conversational_voice' not in self.available_services:
                self.available_services['conversational_voice'] = {
                    'name': 'conversational_voice',
                    'host': 'localhost',
                    'port': 8092,
                    'status': 'healthy'
                }
    
    def _register_with_service_registry(self):
        """Register this service with the service registry"""
        try:
            registration_data = {
                'name': 'workflow_orchestrator',
                'host': 'localhost',
                'port': self.port,
                'health_endpoint': '/health',
                'capabilities': ['workflow_execution', 'template_management', 'cross_service_coordination'],
                'metadata': {
                    'templates_count': len(self.templates),
                    'supported_triggers': ['screen_change', 'voice_command', 'time_based', 'file_event', 'context_change', 'manual']
                }
            }
            
            # CRITICAL FIX: Use correct service registry port
            response = requests.post('http://localhost:8081/register', 
                                   json=registration_data, timeout=10)
            
            if response.status_code == 200:
                logger.info("Successfully registered with service registry")
            else:
                logger.error(f"Failed to register with service registry: {response.text}")
        except Exception as e:
            logger.error(f"Could not register with service registry: {e}")
    
    def start(self):
        """Start the workflow orchestrator service"""
        logger.info(f"Starting Workflow Orchestrator on port {self.port}")
        self.app.run(host='0.0.0.0', port=self.port, debug=False, threaded=True)
    
    def stop(self):
        """Stop the service"""
        logger.info("Workflow Orchestrator stopped")

if __name__ == "__main__":
    orchestrator = WorkflowOrchestrator()
    try:
        orchestrator.start()
    except KeyboardInterrupt:
        orchestrator.stop()
