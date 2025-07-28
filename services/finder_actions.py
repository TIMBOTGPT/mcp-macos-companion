#!/usr/bin/env python3
"""
MCP macOS Companion - Finder Actions Service  
Smart file operations and organization for macOS
"""

import os
import shutil
import hashlib
import mimetypes
import subprocess
import json
import logging
import time
import threading
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class FileInfo:
    """Information about a file"""
    path: str
    name: str
    size: int
    created: float
    modified: float
    file_type: str
    mime_type: str
    hash_md5: Optional[str] = None
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []

@dataclass  
class OrganizationRule:
    """Rule for organizing files"""
    name: str
    condition: Dict[str, Any]  # e.g., {"extension": ".pdf", "size_mb": ">10"}
    action: Dict[str, Any]     # e.g., {"move_to": "/Users/mark/Documents/PDFs"}
    priority: int = 0

class FinderWatcher(FileSystemEventHandler):
    """File system watcher for real-time organization"""
    
    def __init__(self, finder_service):
        self.finder_service = finder_service
        
    def on_created(self, event):
        if not event.is_directory:
            # Small delay to ensure file is fully written
            threading.Timer(2.0, self._process_new_file, [event.src_path]).start()
    
    def on_moved(self, event):
        if not event.is_directory:
            self.finder_service._update_file_tracking(event.src_path, event.dest_path)
    
    def _process_new_file(self, file_path: str):
        """Process newly created file"""
        try:
            if os.path.exists(file_path):
                self.finder_service._apply_organization_rules(file_path)
        except Exception as e:
            logger.error(f"Error processing new file {file_path}: {e}")

class FinderActions:
    """Smart file operations and organization service"""
    
    def __init__(self, port: int = 8082):
        self.port = port
        self.app = Flask(__name__)
        CORS(self.app)
        
        # Organization rules
        self.organization_rules: List[OrganizationRule] = []
        self.watched_directories: Dict[str, Observer] = {}
        
        # File tracking
        self.file_tracker: Dict[str, FileInfo] = {}
        
        # Default organization rules
        self._load_default_rules()
        
        # Service registration
        self._register_with_service_registry()
    
    def _load_default_rules(self):
        """Load default organization rules"""
        default_rules = [
            OrganizationRule(
                name="Downloads Cleanup - Images",
                condition={"directory": "/Users/mark/Downloads", "extensions": [".jpg", ".jpeg", ".png", ".gif", ".heic"]},
                action={"move_to": "/Users/mark/Pictures/Downloads"},
                priority=1
            ),
            OrganizationRule(
                name="Downloads Cleanup - Documents", 
                condition={"directory": "/Users/mark/Downloads", "extensions": [".pdf", ".doc", ".docx", ".txt", ".rtf"]},
                action={"move_to": "/Users/mark/Documents/Downloads"},
                priority=1
            ),
            OrganizationRule(
                name="Desktop Cleanup - Screenshots",
                condition={"directory": "/Users/mark/Desktop", "name_pattern": "Screenshot*"},
                action={"move_to": "/Users/mark/Pictures/Screenshots"},
                priority=2
            ),
            OrganizationRule(
                name="Large File Alert",
                condition={"size_mb": ">100"},
                action={"notify": "Large file detected", "tag": "large-file"},
                priority=0
            )
        ]
        
        self.organization_rules.extend(default_rules)
        
        @self.app.route('/smart_organize', methods=['POST'])
        def smart_organize():
            """Intelligently organize files based on content analysis"""
            data = request.json
            directory = data['directory']
            
            results = self._smart_organize_directory(directory)
            return jsonify({'results': results})
        
        @self.app.route('/add_rule', methods=['POST'])
        def add_organization_rule():
            """Add a new organization rule"""
            data = request.json
            rule = OrganizationRule(
                name=data['name'],
                condition=data['condition'],
                action=data['action'],
                priority=data.get('priority', 0)
            )
            
            self.organization_rules.append(rule)
            self.organization_rules.sort(key=lambda r: r.priority, reverse=True)
            
            return jsonify({'status': 'rule_added', 'rule_name': rule.name})
        
        @self.app.route('/rules', methods=['GET'])
        def list_rules():
            """List all organization rules"""
            rules = []
            for rule in self.organization_rules:
                rules.append({
                    'name': rule.name,
                    'condition': rule.condition,
                    'action': rule.action,
                    'priority': rule.priority
                })
            return jsonify({'rules': rules})
        
        @self.app.route('/watch_directory', methods=['POST'])
        def watch_directory():
            """Start watching a directory for changes"""
            data = request.json
            directory = data['directory']
            
            if directory in self.watched_directories:
                return jsonify({'status': 'already_watching'})
            
            if not os.path.exists(directory):
                return jsonify({'error': 'Directory not found'}), 404
            
            observer = Observer()
            event_handler = FinderWatcher(self)
            observer.schedule(event_handler, directory, recursive=data.get('recursive', False))
            observer.start()
            
            self.watched_directories[directory] = observer
            
            return jsonify({'status': 'watching_started', 'directory': directory})
        
        @self.app.route('/unwatch_directory', methods=['POST'])
        def unwatch_directory():
            """Stop watching a directory"""
            data = request.json
            directory = data['directory']
            
            if directory in self.watched_directories:
                self.watched_directories[directory].stop()
                del self.watched_directories[directory]
                return jsonify({'status': 'watching_stopped'})
            
            return jsonify({'error': 'Directory not being watched'}), 404
        
        @self.app.route('/file_info', methods=['POST'])
        def get_file_info():
            """Get detailed information about a file"""
            data = request.json
            file_path = data['file_path']
            
            if not os.path.exists(file_path):
                return jsonify({'error': 'File not found'}), 404
            
            file_info = self._get_file_info(file_path)
            return jsonify(file_info.__dict__)
        
        @self.app.route('/health', methods=['GET'])
        def health():
            return jsonify({
                'status': 'healthy',
                'timestamp': time.time(),
                'watched_directories': len(self.watched_directories),
                'organization_rules': len(self.organization_rules)
            })
    
    def _organize_directory(self, directory: str, dry_run: bool = False) -> List[Dict[str, Any]]:
        """Organize files in a directory based on rules"""
        results = []
        
        try:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    
                    try:
                        # Apply organization rules
                        actions = self._apply_organization_rules(file_path, dry_run)
                        if actions:
                            results.extend(actions)
                    except Exception as e:
                        logger.error(f"Error processing {file_path}: {e}")
                        results.append({
                            'file': file_path,
                            'action': 'error',
                            'message': str(e)
                        })
        
        except Exception as e:
            logger.error(f"Error organizing directory {directory}: {e}")
            results.append({
                'directory': directory,
                'action': 'error', 
                'message': str(e)
            })
        
        return results
    
    def _apply_organization_rules(self, file_path: str, dry_run: bool = False) -> List[Dict[str, Any]]:
        """Apply organization rules to a specific file"""
        actions = []
        file_info = self._get_file_info(file_path)
        
        for rule in self.organization_rules:
            if self._matches_condition(file_info, rule.condition):
                action_result = self._execute_action(file_info, rule.action, dry_run)
                if action_result:
                    action_result['rule_name'] = rule.name
                    actions.append(action_result)
        
        return actions
    
    def _matches_condition(self, file_info: FileInfo, condition: Dict[str, Any]) -> bool:
        """Check if file matches rule condition"""
        
        # Directory condition
        if 'directory' in condition:
            if not file_info.path.startswith(condition['directory']):
                return False
        
        # Extension condition
        if 'extensions' in condition:
            file_ext = os.path.splitext(file_info.name)[1].lower()
            if file_ext not in [ext.lower() for ext in condition['extensions']]:
                return False
        
        # Name pattern condition
        if 'name_pattern' in condition:
            pattern = condition['name_pattern']
            if '*' in pattern:
                # Simple wildcard matching
                pattern_parts = pattern.split('*')
                if len(pattern_parts) == 2:
                    prefix, suffix = pattern_parts
                    if not (file_info.name.startswith(prefix) and file_info.name.endswith(suffix)):
                        return False
            else:
                if pattern not in file_info.name:
                    return False
        
        # Size condition
        if 'size_mb' in condition:
            size_condition = condition['size_mb']
            file_size_mb = file_info.size / (1024 * 1024)
            
            if size_condition.startswith('>'):
                threshold = float(size_condition[1:])
                if file_size_mb <= threshold:
                    return False
            elif size_condition.startswith('<'):
                threshold = float(size_condition[1:])
                if file_size_mb >= threshold:
                    return False
        
        # File type condition
        if 'file_type' in condition:
            if file_info.file_type != condition['file_type']:
                return False
        
        # Age condition (in days)
        if 'age_days' in condition:
            age_condition = condition['age_days']
            file_age_days = (time.time() - file_info.modified) / (24 * 3600)
            
            if age_condition.startswith('>'):
                threshold = float(age_condition[1:])
                if file_age_days <= threshold:
                    return False
            elif age_condition.startswith('<'):
                threshold = float(age_condition[1:])
                if file_age_days >= threshold:
                    return False
        
        return True
    
    def _execute_action(self, file_info: FileInfo, action: Dict[str, Any], dry_run: bool = False) -> Optional[Dict[str, Any]]:
        """Execute an organization action"""
        
        if 'move_to' in action:
            target_dir = action['move_to']
            
            # Create target directory if it doesn't exist
            if not dry_run:
                os.makedirs(target_dir, exist_ok=True)
            
            target_path = os.path.join(target_dir, file_info.name)
            
            # Handle name conflicts
            counter = 1
            base_name, ext = os.path.splitext(file_info.name)
            while os.path.exists(target_path) and not dry_run:
                new_name = f"{base_name}_{counter}{ext}"
                target_path = os.path.join(target_dir, new_name)
                counter += 1
            
            if not dry_run:
                try:
                    shutil.move(file_info.path, target_path)
                    # Update file tracking
                    self._update_file_tracking(file_info.path, target_path)
                    
                    # Store in memory for context
                    self._store_file_action_memory(file_info, 'moved', target_path)
                    
                except Exception as e:
                    return {
                        'file': file_info.path,
                        'action': 'move_failed',
                        'target': target_path,
                        'error': str(e)
                    }
            
            return {
                'file': file_info.path,
                'action': 'moved' if not dry_run else 'would_move',
                'target': target_path
            }
        
        elif 'notify' in action:
            message = action['notify']
            
            # Send notification through service registry
            if not dry_run:
                self._send_notification(message, file_info)
            
            return {
                'file': file_info.path,
                'action': 'notified' if not dry_run else 'would_notify',
                'message': message
            }
        
        elif 'tag' in action:
            tag = action['tag']
            
            if not dry_run:
                # Add tag to file (store in memory)
                file_info.tags.append(tag)
                self._store_file_action_memory(file_info, 'tagged', tag)
            
            return {
                'file': file_info.path,
                'action': 'tagged' if not dry_run else 'would_tag',
                'tag': tag
            }
        
        return None
    
    def _get_file_info(self, file_path: str) -> FileInfo:
        """Get detailed information about a file"""
        stat = os.stat(file_path)
        name = os.path.basename(file_path)
        
        # Determine file type
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type:
            if mime_type.startswith('image/'):
                file_type = 'image'
            elif mime_type.startswith('video/'):
                file_type = 'video'
            elif mime_type.startswith('audio/'):
                file_type = 'audio'
            elif mime_type.startswith('text/'):
                file_type = 'text'
            elif 'pdf' in mime_type:
                file_type = 'pdf'
            else:
                file_type = 'document'
        else:
            file_type = 'unknown'
        
        return FileInfo(
            path=file_path,
            name=name,
            size=stat.st_size,
            created=stat.st_birthtime,
            modified=stat.st_mtime,
            file_type=file_type,
            mime_type=mime_type or 'unknown'
        )
    
    def _find_duplicates(self, directory: str) -> List[Dict[str, Any]]:
        """Find duplicate files by hash"""
        file_hashes = {}
        duplicates = []
        
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                
                try:
                    # Calculate MD5 hash
                    hash_md5 = hashlib.md5()
                    with open(file_path, "rb") as f:
                        for chunk in iter(lambda: f.read(4096), b""):
                            hash_md5.update(chunk)
                    file_hash = hash_md5.hexdigest()
                    
                    if file_hash in file_hashes:
                        # Found duplicate
                        duplicates.append({
                            'hash': file_hash,
                            'original': file_hashes[file_hash],
                            'duplicate': file_path,
                            'size': os.path.getsize(file_path)
                        })
                    else:
                        file_hashes[file_hash] = file_path
                        
                except Exception as e:
                    logger.error(f"Error hashing {file_path}: {e}")
        
        return duplicates
    
    def _smart_organize_directory(self, directory: str) -> List[Dict[str, Any]]:
        """Intelligently organize files using content analysis"""
        results = []
        
        # First, get memory context about previous file organizations
        try:
            memory_response = requests.post('http://localhost:8081/search', json={
                'query': f'organized files in {directory}',
                'category': 'file_organization',
                'limit': 10
            }, timeout=10)
            
            previous_patterns = []
            if memory_response.status_code == 200:
                memories = memory_response.json().get('results', [])
                for memory in memories:
                    # Extract patterns from previous organizations
                    if 'pattern' in memory.get('metadata', {}):
                        previous_patterns.append(memory['metadata']['pattern'])
        
        except Exception as e:
            logger.error(f"Could not fetch memory context: {e}")
            previous_patterns = []
        
        # Analyze files and create smart organization suggestions
        file_analysis = self._analyze_directory_content(directory)
        
        # Generate organization suggestions based on analysis
        suggestions = self._generate_organization_suggestions(file_analysis, previous_patterns)
        
        # Apply suggestions
        for suggestion in suggestions:
            if suggestion['confidence'] > 0.7:  # Only apply high-confidence suggestions
                try:
                    # Create organization rule temporarily
                    temp_rule = OrganizationRule(
                        name=f"Smart_{suggestion['category']}",
                        condition=suggestion['condition'],
                        action=suggestion['action'],
                        priority=10
                    )
                    
                    # Apply rule to matching files
                    for file_path in suggestion['matching_files']:
                        file_info = self._get_file_info(file_path)
                        if self._matches_condition(file_info, temp_rule.condition):
                            action_result = self._execute_action(file_info, temp_rule.action)
                            if action_result:
                                action_result['suggestion_category'] = suggestion['category']
                                action_result['confidence'] = suggestion['confidence']
                                results.append(action_result)
                
                except Exception as e:
                    logger.error(f"Error applying smart suggestion: {e}")
        
        # Store learning in memory
        self._store_smart_organization_learning(directory, suggestions, results)
        
        return results
    
    def _analyze_directory_content(self, directory: str) -> Dict[str, Any]:
        """Analyze directory content for smart organization"""
        analysis = {
            'file_types': {},
            'size_distribution': {},
            'age_distribution': {},
            'naming_patterns': [],
            'total_files': 0
        }
        
        current_time = time.time()
        
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                file_info = self._get_file_info(file_path)
                
                analysis['total_files'] += 1
                
                # File type distribution
                analysis['file_types'][file_info.file_type] = analysis['file_types'].get(file_info.file_type, 0) + 1
                
                # Size distribution
                size_mb = file_info.size / (1024 * 1024)
                if size_mb < 1:
                    size_cat = 'small'
                elif size_mb < 10:
                    size_cat = 'medium'
                else:
                    size_cat = 'large'
                analysis['size_distribution'][size_cat] = analysis['size_distribution'].get(size_cat, 0) + 1
                
                # Age distribution
                age_days = (current_time - file_info.modified) / (24 * 3600)
                if age_days < 7:
                    age_cat = 'recent'
                elif age_days < 30:
                    age_cat = 'month'
                else:
                    age_cat = 'old'
                analysis['age_distribution'][age_cat] = analysis['age_distribution'].get(age_cat, 0) + 1
                
                # Basic naming patterns
                if file_info.name.startswith('Screenshot'):
                    analysis['naming_patterns'].append('screenshot')
                elif 'download' in file_info.name.lower():
                    analysis['naming_patterns'].append('download')
        
        return analysis
    
    def _generate_organization_suggestions(self, analysis: Dict[str, Any], previous_patterns: List[str]) -> List[Dict[str, Any]]:
        """Generate smart organization suggestions"""
        suggestions = []
        
        # Suggestion 1: Screenshots
        if 'screenshot' in analysis['naming_patterns']:
            suggestions.append({
                'category': 'screenshots',
                'condition': {'name_pattern': 'Screenshot*'},
                'action': {'move_to': '/Users/mark/Pictures/Screenshots'},
                'matching_files': [],  # Will be populated
                'confidence': 0.9,
                'reason': 'Detected screenshot files'
            })
        
        # Suggestion 2: Large files
        if analysis['size_distribution'].get('large', 0) > 3:
            suggestions.append({
                'category': 'large_files',
                'condition': {'size_mb': '>10'},
                'action': {'notify': 'Large files detected', 'tag': 'large-file'},
                'matching_files': [],
                'confidence': 0.8,
                'reason': 'Multiple large files detected'
            })
        
        # Suggestion 3: File type clustering
        dominant_type = max(analysis['file_types'].items(), key=lambda x: x[1])
        if dominant_type[1] > 5:  # More than 5 files of same type
            target_dir = self._get_type_target_directory(dominant_type[0])
            if target_dir:
                suggestions.append({
                    'category': f'{dominant_type[0]}_files',
                    'condition': {'file_type': dominant_type[0]},
                    'action': {'move_to': target_dir},
                    'matching_files': [],
                    'confidence': 0.75,
                    'reason': f'Many {dominant_type[0]} files detected'
                })
        
        return suggestions
    
    def _get_type_target_directory(self, file_type: str) -> Optional[str]:
        """Get target directory for file type"""
        type_mapping = {
            'image': '/Users/mark/Pictures/Organized',
            'video': '/Users/mark/Movies/Organized', 
            'audio': '/Users/mark/Music/Organized',
            'pdf': '/Users/mark/Documents/PDFs',
            'text': '/Users/mark/Documents/Text',
            'document': '/Users/mark/Documents/Organized'
        }
        return type_mapping.get(file_type)
    
    def _update_file_tracking(self, old_path: str, new_path: str):
        """Update file tracking when files are moved"""
        if old_path in self.file_tracker:
            file_info = self.file_tracker[old_path]
            file_info.path = new_path
            file_info.name = os.path.basename(new_path)
            
            # Update tracking
            del self.file_tracker[old_path]
            self.file_tracker[new_path] = file_info
    
    def _store_file_action_memory(self, file_info: FileInfo, action: str, details: str):
        """Store file action in memory for learning"""
        try:
            memory_data = {
                'content': f"File {action}: {file_info.name} - {details}",
                'category': 'file_organization',
                'metadata': {
                    'file_path': file_info.path,
                    'file_type': file_info.file_type,
                    'action': action,
                    'details': details,
                    'file_size': file_info.size
                },
                'tags': ['file_action', action, file_info.file_type]
            }
            
            requests.post('http://localhost:8081/store', json=memory_data, timeout=10)
        except Exception as e:
            logger.error(f"Could not store file action memory: {e}")
    
    def _store_smart_organization_learning(self, directory: str, suggestions: List[Dict[str, Any]], results: List[Dict[str, Any]]):
        """Store smart organization learning in memory"""
        try:
            learning_data = {
                'content': f"Smart organization applied to {directory}",
                'category': 'smart_organization',
                'metadata': {
                    'directory': directory,
                    'suggestions_count': len(suggestions),
                    'actions_taken': len(results),
                    'patterns': [s['category'] for s in suggestions]
                },
                'tags': ['smart_organization', 'learning']
            }
            
            requests.post('http://localhost:8081/store', json=learning_data, timeout=10)
        except Exception as e:
            logger.error(f"Could not store smart organization learning: {e}")
    
    def _send_notification(self, message: str, file_info: FileInfo):
        """Send notification through service registry"""
        try:
            notification_data = {
                'source_service': 'finder_actions',
                'target_service': 'notification_service',
                'message_type': 'file_notification',
                'payload': {
                    'message': message,
                    'file_path': file_info.path,
                    'file_name': file_info.name,
                    'file_size': file_info.size
                }
            }
            
            requests.post('http://localhost:8080/send_message', json=notification_data, timeout=10)
        except Exception as e:
            logger.error(f"Could not send notification: {e}")
    
    def _register_with_service_registry(self):
        """Register this service with the service registry"""
        try:
            registration_data = {
                'name': 'finder_actions',
                'host': 'localhost',
                'port': self.port,
                'health_endpoint': '/health',
                'capabilities': ['file_organization', 'duplicate_detection', 'smart_organization', 'file_watching'],
                'metadata': {
                    'supported_actions': ['move', 'tag', 'notify'],
                    'watched_directories': list(self.watched_directories.keys())
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
        """Start the finder actions service"""
        logger.info(f"Starting Finder Actions Service on port {self.port}")
        self.app.run(host='0.0.0.0', port=self.port, debug=False, threaded=True)
    
    def stop(self):
        """Stop the service and all watchers"""
        for observer in self.watched_directories.values():
            observer.stop()
        logger.info("Finder Actions Service stopped")

if __name__ == "__main__":
    service = FinderActions()
    try:
        service.start()
    except KeyboardInterrupt:
        service.stop()
