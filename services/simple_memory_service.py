#!/usr/bin/env python3
"""
Simple Memory Service - Basic memory storage for testing
"""

import sqlite3
import json
import logging
import threading
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SimpleMemoryEntry:
    """Simple memory entry without embeddings"""
    id: str
    content: str
    category: str
    timestamp: float
    metadata: Dict[str, Any]
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []

class SimpleMemoryService:
    """Simple memory service with SQLite storage"""
    
    def __init__(self, db_path: str = "/Users/mark/.mcp/simple_memory.db", port: int = 8093):
        self.db_path = db_path
        self.port = port
        self.app = Flask(__name__)
        CORS(self.app)
        
        # Database connection with thread safety
        self.db_lock = threading.Lock()
        
        # Initialize database
        self._init_database()
        
        # Setup Flask routes
        self._setup_routes()
        
        # Service registration
        self._register_with_service_registry()
    
    def _init_database(self):
        """Initialize SQLite database"""
        import os
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    category TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    metadata TEXT NOT NULL,
                    tags TEXT NOT NULL
                )
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_category ON memories(category)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_timestamp ON memories(timestamp)
            ''')
            
            # FTS for text search
            conn.execute('''
                CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                    id, content, category, tags
                )
            ''')
        
        logger.info(f"Initialized memory database at {self.db_path}")
    
    def _setup_routes(self):
        """Setup Flask API routes"""
        
        @self.app.route('/store', methods=['POST'])
        def store_memory():
            """Store a memory entry"""
            data = request.json
            memory_id = data.get('id', f"mem_{int(time.time() * 1000)}")
            
            entry = SimpleMemoryEntry(
                id=memory_id,
                content=data['content'],
                category=data.get('category', 'general'),
                timestamp=data.get('timestamp', time.time()),
                metadata=data.get('metadata', {}),
                tags=data.get('tags', [])
            )
            
            with self.db_lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute('''
                        INSERT OR REPLACE INTO memories 
                        (id, content, category, timestamp, metadata, tags)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        entry.id,
                        entry.content,
                        entry.category,
                        entry.timestamp,
                        json.dumps(entry.metadata),
                        json.dumps(entry.tags)
                    ))
                    
                    # Update FTS index
                    conn.execute('''
                        INSERT OR REPLACE INTO memories_fts 
                        (id, content, category, tags)
                        VALUES (?, ?, ?, ?)
                    ''', (
                        entry.id,
                        entry.content,
                        entry.category,
                        ' '.join(entry.tags)
                    ))
            
            logger.info(f"Stored memory: {memory_id} - {entry.content[:50]}...")
            return jsonify({'status': 'stored', 'id': memory_id})
        
        @self.app.route('/search', methods=['POST'])
        def search_memories():
            """Search memories using keyword matching"""
            data = request.json
            query = data['query'].lower()
            limit = data.get('limit', 10)
            category_filter = data.get('category')
            time_range = data.get('time_range')  # In hours
            
            results = []
            
            with sqlite3.connect(self.db_path) as conn:
                # Build query
                where_conditions = []
                params = []
                
                # Text search
                where_conditions.append("LOWER(content) LIKE ?")
                params.append(f"%{query}%")
                
                # Category filter
                if category_filter:
                    where_conditions.append("category = ?")
                    params.append(category_filter)
                
                # Time range filter
                if time_range:
                    cutoff_time = time.time() - (time_range * 3600)
                    where_conditions.append("timestamp > ?")
                    params.append(cutoff_time)
                
                sql = f"""
                    SELECT id, content, category, timestamp, metadata, tags
                    FROM memories 
                    WHERE {' AND '.join(where_conditions)}
                    ORDER BY timestamp DESC
                    LIMIT ?
                """
                params.append(limit)
                
                cursor = conn.execute(sql, params)
                
                for row in cursor:
                    memory_id, content, category, timestamp, metadata_json, tags_json = row
                    
                    # Calculate simple relevance score based on query matches
                    content_lower = content.lower()
                    score = content_lower.count(query) / len(content_lower) if content_lower else 0
                    
                    results.append({
                        'id': memory_id,
                        'content': content,
                        'category': category,
                        'timestamp': timestamp,
                        'metadata': json.loads(metadata_json),
                        'tags': json.loads(tags_json),
                        'relevance_score': score
                    })
            
            # Sort by relevance
            results.sort(key=lambda x: x['relevance_score'], reverse=True)
            
            return jsonify({'results': results})
        
        @self.app.route('/text_search', methods=['POST'])
        def text_search():
            """Full-text search using SQLite FTS"""
            data = request.json
            query = data['query']
            limit = data.get('limit', 10)
            
            with sqlite3.connect(self.db_path) as conn:
                try:
                    cursor = conn.execute('''
                        SELECT m.id, m.content, m.category, m.timestamp, m.metadata, m.tags
                        FROM memories_fts fts
                        JOIN memories m ON fts.id = m.id
                        WHERE memories_fts MATCH ?
                        ORDER BY rank
                        LIMIT ?
                    ''', (query, limit))
                    
                    results = []
                    for row in cursor:
                        memory_id, content, category, timestamp, metadata_json, tags_json = row
                        results.append({
                            'id': memory_id,
                            'content': content,
                            'category': category,
                            'timestamp': timestamp,
                            'metadata': json.loads(metadata_json),
                            'tags': json.loads(tags_json)
                        })
                
                except Exception as e:
                    logger.error(f"FTS search error: {e}")
                    # Fallback to regular search
                    return search_memories()
            
            return jsonify({'results': results})
        
        @self.app.route('/list', methods=['GET'])
        def list_memories():
            """List recent memories"""
            limit = request.args.get('limit', 20, type=int)
            category = request.args.get('category')
            
            with sqlite3.connect(self.db_path) as conn:
                if category:
                    cursor = conn.execute('''
                        SELECT id, content, category, timestamp, metadata, tags
                        FROM memories 
                        WHERE category = ?
                        ORDER BY timestamp DESC
                        LIMIT ?
                    ''', (category, limit))
                else:
                    cursor = conn.execute('''
                        SELECT id, content, category, timestamp, metadata, tags
                        FROM memories 
                        ORDER BY timestamp DESC
                        LIMIT ?
                    ''', (limit,))
                
                results = []
                for row in cursor:
                    memory_id, content, category, timestamp, metadata_json, tags_json = row
                    results.append({
                        'id': memory_id,
                        'content': content,
                        'category': category,
                        'timestamp': timestamp,
                        'metadata': json.loads(metadata_json),
                        'tags': json.loads(tags_json)
                    })
            
            return jsonify({'memories': results})
        
        @self.app.route('/categories', methods=['GET'])
        def get_categories():
            """Get all unique categories"""
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('SELECT DISTINCT category FROM memories ORDER BY category')
                categories = [row[0] for row in cursor]
            
            return jsonify({'categories': categories})
        
        @self.app.route('/stats', methods=['GET'])
        def get_stats():
            """Get memory statistics"""
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('SELECT COUNT(*) FROM memories')
                total_memories = cursor.fetchone()[0]
                
                cursor = conn.execute('''
                    SELECT category, COUNT(*) 
                    FROM memories 
                    GROUP BY category 
                    ORDER BY COUNT(*) DESC
                ''')
                category_counts = dict(cursor.fetchall())
                
                # Recent activity
                cutoff_time = time.time() - (24 * 3600)  # Last 24 hours
                cursor = conn.execute('SELECT COUNT(*) FROM memories WHERE timestamp > ?', (cutoff_time,))
                recent_count = cursor.fetchone()[0]
            
            return jsonify({
                'total_memories': total_memories,
                'category_counts': category_counts,
                'recent_memories_24h': recent_count
            })
        
        @self.app.route('/delete/<memory_id>', methods=['DELETE'])
        def delete_memory(memory_id):
            """Delete a memory entry"""
            with self.db_lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute('DELETE FROM memories WHERE id = ?', (memory_id,))
                    conn.execute('DELETE FROM memories_fts WHERE id = ?', (memory_id,))
                    
                    if cursor.rowcount > 0:
                        logger.info(f"Deleted memory: {memory_id}")
                        return jsonify({'status': 'deleted', 'id': memory_id})
                    else:
                        return jsonify({'error': 'Memory not found'}), 404
        
        @self.app.route('/health', methods=['GET'])
        def health():
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('SELECT COUNT(*) FROM memories')
                total_memories = cursor.fetchone()[0]
            
            return jsonify({
                'status': 'healthy',
                'timestamp': time.time(),
                'total_memories': total_memories,
                'database_path': self.db_path
            })
    
    def _register_with_service_registry(self):
        """Register this service with the service registry"""
        try:
            registration_data = {
                'name': 'simple_memory_service',
                'host': 'localhost',
                'port': self.port,
                'health_endpoint': '/health',
                'capabilities': ['memory_storage', 'text_search', 'memory_management'],
                'metadata': {
                    'database_path': self.db_path,
                    'description': 'Simple memory service with SQLite storage'
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
        """Start the simple memory service"""
        logger.info(f"Starting Simple Memory Service on port {self.port}")
        self.app.run(host='0.0.0.0', port=self.port, debug=False, threaded=True)
    
    def stop(self):
        """Stop the service"""
        logger.info("Simple Memory Service stopped")

if __name__ == "__main__":
    service = SimpleMemoryService()
    try:
        service.start()
    except KeyboardInterrupt:
        service.stop()
